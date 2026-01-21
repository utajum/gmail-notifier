#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Main application class for Gmail Notifier.

This module contains the GmailNotifier class which manages the system
tray icon, email checking, notifications, and overall application state.
"""

import os
import sys
import time
import imaplib
import threading
import webbrowser

from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtCore import QTimer, QThread, Qt, QRect
from PyQt5.QtGui import QIcon, QCursor, QColor, QFont, QPainter

from gmail_notifier.config import load_settings, save_settings
from gmail_notifier.notifications import send_system_notification
from gmail_notifier.checker import GmailChecker
from gmail_notifier.ui.config_dialog import ConfigDialog
from gmail_notifier.ui.email_popup import EmailListPopup


class GmailNotifier:
    """Main application class managing the Gmail notification system.

    Handles:
    - System tray icon with context menu
    - Background email checking via GmailChecker thread
    - Notification display and snooze functionality
    - Email popup window
    - Configuration dialog

    Attributes:
        app: QApplication instance.
        settings: Dict of configuration settings.
        tray_icon: QSystemTrayIcon for system tray.
        current_emails: List of emails grouped by thread (for display).
        popup: Current EmailListPopup instance or None.
    """

    def __init__(self):
        """Initialize the Gmail Notifier application."""
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setApplicationName("Gmail Notifier")
        self.app.setDesktopFileName("gmail-notifier")
        self.app.setWindowIcon(QIcon.fromTheme("mail-unread"))

        # Current emails storage
        # current_emails: grouped by thread (for display)
        # _all_emails: ungrouped individual emails (for notifications/tracking)
        self.current_emails = []
        self._all_emails = []

        # Click timer for single/double click differentiation
        self.click_timer = QTimer()
        self.click_timer.setSingleShot(True)
        self.click_timer.setInterval(300)  # 300ms delay
        self.click_timer.timeout.connect(self.on_click_timer)

        # Email list popup reference
        self.popup = None

        # Track notified email IDs to avoid duplicate notifications
        self.notified_email_ids = set()

        # Snooze tracking (None = not snoozed, timestamp = snoozed until)
        self.snoozed_until = None

        # Error tracking
        self.is_error = False

        # Load settings
        self.settings = load_settings()

        # Create the system tray icon (must be created before config dialog)
        self.tray_icon = QSystemTrayIcon()
        self.tray_icon.setIcon(self.get_icon())
        self.tray_icon.setToolTip("Gmail Notifier")

        # Check if configuration is needed
        if not self.settings.get("username") or not self.settings.get("password"):
            self.show_config_dialog()

        # Create the icon menu
        self.menu = QMenu()

        self.check_now_action = QAction("Check Now")
        self.check_now_action.triggered.connect(self.check_now)
        self.menu.addAction(self.check_now_action)

        self.open_gmail_action = QAction("Open Gmail")
        self.open_gmail_action.triggered.connect(self.open_gmail)
        self.menu.addAction(self.open_gmail_action)

        self.snooze_action = QAction("Snooze for 1 hour")
        self.snooze_action.triggered.connect(self.toggle_snooze)
        self.menu.addAction(self.snooze_action)

        self.config_action = QAction("Configuration")
        self.config_action.triggered.connect(self.show_config_dialog)
        self.menu.addAction(self.config_action)

        self.menu.addSeparator()

        self.quit_action = QAction("Quit")
        self.quit_action.triggered.connect(self.quit)
        self.menu.addAction(self.quit_action)

        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.activated.connect(self.tray_activated)

        # Start the email checking thread
        self.checker_thread = QThread()
        self.gmail_checker = GmailChecker(self.settings)
        self.gmail_checker.moveToThread(self.checker_thread)

        self.checker_thread.started.connect(self.gmail_checker.run)
        self.gmail_checker.new_emails_signal.connect(self.on_new_emails)
        self.gmail_checker.error_signal.connect(self.on_error)

        # Show the tray icon
        self.tray_icon.show()

        # Start the thread
        self.checker_thread.start()

    def get_icon(self):
        """Get the Gmail icon from common locations.

        Returns:
            QIcon: Gmail icon or fallback mail-unread theme icon.
        """
        # Search for the Gmail icon in several common locations
        icon_paths = [
            "/usr/share/icons/hicolor/scalable/apps/gmail.svg",
            "/usr/share/icons/hicolor/48x48/apps/gmail.png",
            "/usr/share/icons/breeze/apps/48/gmail.svg",
            "/usr/share/pixmaps/gmail.png",
        ]

        for path in icon_paths:
            if os.path.exists(path):
                return QIcon(path)

        # If the icon is not found, use a system icon
        return QIcon.fromTheme("mail-unread")

    def update_tray_icon(self, has_unread, is_snoozed_state=False):
        """Update tray icon with badge indicator.

        Adds visual indicators:
        - Red dot: unread emails
        - "Z": snoozed state
        - "!": error state

        Args:
            has_unread: True if there are unread emails.
            is_snoozed_state: True if notifications are snoozed.
        """
        base_icon = self.get_icon()

        # If no interesting state, show base icon (unless error)
        if not has_unread and not is_snoozed_state and not self.is_error:
            self.tray_icon.setIcon(base_icon)
            return

        # Create a pixmap from the icon
        # Size 64x64 provides enough resolution for most trays
        pixmap = base_icon.pixmap(64, 64)
        if pixmap.isNull():
            return

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        if self.is_error:
            # Draw "!" for error
            painter.setBrush(QColor("#ff9800"))  # Material Orange
            painter.setPen(Qt.NoPen)
            # Circle background for exclamation mark
            dot_size = 24
            painter.drawEllipse(pixmap.width() - dot_size - 2, 2, dot_size, dot_size)

            # Exclamation mark
            painter.setPen(QColor("white"))
            font = QFont()
            font.setPixelSize(18)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(
                QRect(pixmap.width() - dot_size - 2, 2, dot_size, dot_size),
                Qt.AlignCenter,
                "!",
            )
        elif is_snoozed_state:
            # Draw "zzz" for snooze
            painter.setPen(QColor("#4da6ff"))  # Blue color
            font = QFont()
            font.setPixelSize(28)
            font.setBold(True)
            painter.setFont(font)
            # Draw at top right
            painter.drawText(
                pixmap.rect().adjusted(0, -5, -4, 0), Qt.AlignRight | Qt.AlignTop, "Z"
            )
        elif has_unread:
            # Draw a bright red dot in the top-right corner
            dot_size = 20  # Relative to 64x64
            painter.setBrush(QColor("#f44336"))  # Material Red
            painter.setPen(Qt.NoPen)
            # Position it slightly offset from the edge
            painter.drawEllipse(pixmap.width() - dot_size - 2, 2, dot_size, dot_size)

        painter.end()

        self.tray_icon.setIcon(QIcon(pixmap))

    def tray_activated(self, reason):
        """Handle tray icon activation (clicks).

        Args:
            reason: QSystemTrayIcon.ActivationReason value.
        """
        if reason == QSystemTrayIcon.Trigger:
            # Single click (or first click of double click)
            self.click_timer.start()
        elif reason == QSystemTrayIcon.DoubleClick:
            # Double click detected
            self.click_timer.stop()
            self.open_gmail()

    def on_click_timer(self):
        """Handle single click after timer expires."""
        self.show_popup()

    def _dedup_emails(self, emails):
        """Remove duplicate emails by ID and sort by timestamp.

        Args:
            emails: List of email dicts.

        Returns:
            list: Deduplicated emails sorted newest first.
        """
        seen_ids = set()
        deduped = []
        for email in emails:
            email_id = str(email.get("id"))
            if email_id and email_id not in seen_ids:
                seen_ids.add(email_id)
                deduped.append(email)
        # Always sort by timestamp, newest first
        deduped.sort(key=lambda e: e.get("timestamp", 0), reverse=True)
        return deduped

    def _group_by_thread(self, emails):
        """Group emails by thread ID for display.

        Returns list of emails where each entry represents a thread:
        - Uses the newest email's data (sender, subject, link, etc.)
        - Adds 'thread_count' field with number of unread emails in thread
        - Sorted by newest email timestamp (newest thread first)

        Args:
            emails: List of email dicts.

        Returns:
            list: Grouped emails with thread_count field.
        """
        if not emails:
            return []

        # Group emails by thread_id
        threads = {}
        for email in emails:
            thread_id = email.get("thread_id", "")
            # If no thread_id, treat each email as its own thread
            if not thread_id:
                thread_id = f"_no_thread_{email.get('id', '')}"

            if thread_id not in threads:
                threads[thread_id] = []
            threads[thread_id].append(email)

        # For each thread, keep the newest email and add count
        grouped = []
        for thread_id, thread_emails in threads.items():
            # Sort thread emails by timestamp, newest first
            thread_emails.sort(key=lambda e: e.get("timestamp", 0), reverse=True)
            # Take the newest email as the representative
            newest = thread_emails[0].copy()
            # Add count of unread emails in this thread
            newest["thread_count"] = len(thread_emails)
            grouped.append(newest)

        # Sort all threads by their newest email's timestamp, newest first
        grouped.sort(key=lambda e: e.get("timestamp", 0), reverse=True)
        return grouped

    def show_popup(self, check_mail=True):
        """Show the email list popup near the cursor.

        Args:
            check_mail: If True, trigger a mail check when opening.
        """
        # Close and destroy any existing popup first
        if self.popup is not None:
            self.popup.close()
            self.popup.deleteLater()
            self.popup = None

        # Trigger a check for new emails when opening the popup
        if check_mail:
            self.check_now()

        # Create and show the popup near the cursor
        gmail_url = self.settings.get("gmail_url", "https://mail.google.com")
        self.popup = EmailListPopup(self.current_emails, gmail_url)
        self.popup.email_clicked.connect(self.mark_email_read_locally)
        self.popup.delete_requested.connect(self.delete_email)
        self.popup.reshow_requested.connect(lambda: self.show_popup(check_mail=False))
        cursor_pos = QCursor.pos()

        # Adjust position to not go off screen (simple logic)
        x = cursor_pos.x() - 150
        y = cursor_pos.y() - self.popup.height() - 10

        # Ensure x is positive
        if x < 0:
            x = 0

        self.popup.move(x, y)
        self.popup.show()
        self.popup.activateWindow()

    def open_gmail(self):
        """Open Gmail in the default web browser."""
        webbrowser.open(self.settings.get("gmail_url", "https://mail.google.com"))

    def mark_email_read_locally(self, email_id):
        """Remove email from local list and update badge.

        Args:
            email_id: ID of the email to mark as read locally.
        """
        # Remove the email with the matching ID from ungrouped list
        self._all_emails = [
            e for e in self._all_emails if str(e.get("id")) != str(email_id)
        ]

        # Re-group for display
        self.current_emails = self._group_by_thread(self._all_emails)

        # Update tray icon badge (based on ungrouped count)
        self.update_tray_icon(len(self._all_emails) > 0, self.is_snoozed())

        # Trigger a full check from server after 20 seconds
        # This gives time for the user to read/archive the email
        QTimer.singleShot(20000, self.check_now)

    def delete_email(self, email_id):
        """Delete all emails in a thread by moving to trash.

        Runs IMAP delete operation in background thread.

        Args:
            email_id: ID of an email in the thread to delete.
        """
        # Find the thread_id for this email
        thread_id = None
        for e in self._all_emails:
            if str(e.get("id")) == str(email_id):
                thread_id = e.get("thread_id")
                break

        # Get all email IDs in this thread
        if thread_id:
            emails_to_delete = [
                e for e in self._all_emails if e.get("thread_id") == thread_id
            ]
            email_ids_to_delete = [str(e.get("id")) for e in emails_to_delete]
        else:
            # No thread_id, just delete the single email
            email_ids_to_delete = [str(email_id)]

        # Remove all thread emails from local list
        self._all_emails = [
            e for e in self._all_emails if str(e.get("id")) not in email_ids_to_delete
        ]

        # Re-group for display
        self.current_emails = self._group_by_thread(self._all_emails)

        # Update tray icon badge (based on ungrouped count)
        self.update_tray_icon(len(self._all_emails) > 0, self.is_snoozed())

        # Re-show the popup with updated emails (don't trigger another mail check)
        self.show_popup(check_mail=False)

        # Run IMAP delete in background
        def do_delete():
            try:
                username = self.settings.get("username", "")
                password = self.settings.get("password", "")

                if not username or not password:
                    return

                mail = imaplib.IMAP4_SSL("imap.gmail.com")
                mail.login(username, password)
                mail.select("inbox")

                # Delete all emails in the thread
                for eid in email_ids_to_delete:
                    msg_id = eid.encode() if isinstance(eid, str) else eid

                    # For Gmail, copy to Trash folder then delete from inbox
                    # This is the proper way to delete in Gmail via IMAP
                    copy_result = mail.copy(msg_id, "[Gmail]/Trash")
                    if copy_result[0] == "OK":
                        mail.store(msg_id, "+FLAGS", "\\Deleted")

                # Expunge all deleted emails at once
                mail.expunge()

                mail.close()
                mail.logout()
            except Exception as e:
                # Emit error on main thread
                error_msg = f"Failed to delete thread: {str(e)}"
                QTimer.singleShot(0, lambda: self.on_error(error_msg))

        threading.Thread(target=do_delete, daemon=True).start()

    def check_now(self):
        """Trigger an immediate email check."""
        self.gmail_checker.force_check = True

    def toggle_snooze(self):
        """Toggle snooze state - snooze for 1 hour or unsnooze."""
        if self.is_snoozed():
            # Unsnooze
            self.snoozed_until = None
            self.snooze_action.setText("Snooze for 1 hour")
            self.tray_icon.setToolTip("Gmail Notifier")
            # Update icon immediately
            self.update_tray_icon(len(self.current_emails) > 0, False)
        else:
            # Snooze for 1 hour
            self.snoozed_until = time.time() + 3600  # 1 hour from now
            self.snooze_action.setText("Unsnooze")
            self.tray_icon.setToolTip("Gmail Notifier (Snoozed)")
            # Update icon immediately with snooze state
            self.update_tray_icon(len(self.current_emails) > 0, True)

    def is_snoozed(self):
        """Check if notifications are currently snoozed.

        Returns:
            bool: True if snoozed and snooze hasn't expired.
        """
        if self.snoozed_until is None:
            return False
        if time.time() >= self.snoozed_until:
            # Snooze expired, reset state
            self.snoozed_until = None
            self.snooze_action.setText("Snooze for 1 hour")
            self.tray_icon.setToolTip("Gmail Notifier")
            return False
        return True

    def snooze_from_notification(self):
        """Activate snooze from a notification action click."""
        if not self.is_snoozed():
            self.snoozed_until = time.time() + 3600
            self.snooze_action.setText("Unsnooze")
            self.tray_icon.setToolTip("Gmail Notifier (Snoozed)")
            self.update_tray_icon(len(self.current_emails) > 0, True)

    def show_config_dialog(self):
        """Show the configuration dialog."""
        dialog = ConfigDialog(self.settings, self.tray_icon)
        if dialog.exec_():
            # If the dialog is accepted, save the settings
            self.settings = dialog.settings
            save_settings(self.settings)

    def on_new_emails(self, emails):
        """Handle new emails signal from GmailChecker.

        Args:
            emails: List of email dicts from the checker.
        """
        # Clear error state on successful check
        self.is_error = False

        # Deduplicate emails by ID
        emails = self._dedup_emails(emails)

        # Clean up notified_email_ids: only keep IDs that are still on server
        # This prevents the set from growing indefinitely
        server_ids = {str(e.get("id")) for e in emails}
        self.notified_email_ids = self.notified_email_ids & server_ids

        # Store ungrouped emails for internal tracking (notifications, etc.)
        self._all_emails = emails

        # Group emails by thread for display (one entry per thread)
        grouped_emails = self._group_by_thread(emails)

        # Update current list of emails for display (grouped by thread)
        self.current_emails = grouped_emails

        # Update tray icon badge (based on ungrouped count - actual unread emails)
        self.update_tray_icon(len(emails) > 0, self.is_snoozed())

        # Update popup if it's open
        if self.popup is not None and self.popup.isVisible():
            self.popup.update_emails(self.current_emails)

        if not emails:
            return

        # Filter out already notified emails
        new_emails = [e for e in emails if e["id"] not in self.notified_email_ids]
        if not new_emails:
            return

        # Check if snoozed - skip notifications but don't mark as notified
        # so we'll get notifications for these emails when snooze ends
        if self.is_snoozed():
            return

        # Limit notifications and track extras
        max_notifications = 5
        emails_to_notify = new_emails[:max_notifications]
        extra_count = len(new_emails) - max_notifications

        # Send notifications with delay (300ms between each)
        for i, email_item in enumerate(emails_to_notify):
            delay = i * 300
            # Use default argument to capture current email_item value
            QTimer.singleShot(
                delay, lambda e=email_item: self._show_email_notification(e)
            )

        # Show summary if there are more emails
        if extra_count > 0:
            delay = len(emails_to_notify) * 300
            QTimer.singleShot(
                delay, lambda: self._show_summary_notification(extra_count)
            )

        # Mark all new emails as notified (not just the ones we showed)
        for email_item in new_emails:
            self.notified_email_ids.add(email_item["id"])

    def _show_email_notification(self, email_item):
        """Show notification for a single email.

        Args:
            email_item: Dict with email data (sender, subject, link).
        """
        title = f"New email from {email_item['sender']}"
        body = email_item["subject"]
        link = email_item.get("link")

        # Tray icon notification
        self.tray_icon.showMessage(
            title,
            body,
            QSystemTrayIcon.Information,
            5000,  # Show for 5 seconds
        )

        # System notification with snooze option and direct email link
        send_system_notification(
            title,
            body,
            snooze_callback=self.snooze_from_notification,
            open_url=link,
        )

    def _show_summary_notification(self, count):
        """Show summary notification for additional emails.

        Args:
            count: Number of additional emails not individually notified.
        """
        title = "New Emails"
        body = f"And {count} more new email{'s' if count > 1 else ''}..."

        # Tray icon notification
        self.tray_icon.showMessage(
            title,
            body,
            QSystemTrayIcon.Information,
            5000,
        )

        # System notification with snooze option
        send_system_notification(
            title, body, snooze_callback=self.snooze_from_notification
        )

    def on_error(self, error_msg):
        """Handle error signal from GmailChecker.

        Args:
            error_msg: Error message string to display.
        """
        # Set error state
        self.is_error = True
        self.update_tray_icon(len(self.current_emails) > 0, self.is_snoozed())

        self.tray_icon.showMessage(
            "Gmail Notifier Error", error_msg, QSystemTrayIcon.Warning, 5000
        )

    def quit(self):
        """Clean up and exit the application."""
        # Stop the thread
        self.gmail_checker.running = False
        self.checker_thread.quit()
        self.checker_thread.wait()

        # Exit the application
        self.app.quit()

    def run(self):
        """Start the Qt event loop.

        Returns:
            int: Application exit code.
        """
        return self.app.exec_()
