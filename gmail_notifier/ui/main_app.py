#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Main application class for Gmail Notifier.

This module contains the GmailNotifier class which orchestrates the
system tray icon, email checking, notifications, and overall application state.
"""

import sys
import threading
import webbrowser

from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtCore import QTimer, QThread
from PyQt5.QtGui import QIcon, QCursor

from gmail_notifier.config import load_settings, save_settings
from gmail_notifier.tray_icon import get_gmail_icon, create_badge_icon
from gmail_notifier.snooze import SnoozeManager
from gmail_notifier.email_utils import (
    dedup_emails,
    group_by_thread,
    find_thread_email_ids,
    remove_emails_by_ids,
    augment_grouped_with_thread_ids,
)
from gmail_notifier.email_actions import delete_emails_imap
from gmail_notifier.notifications import (
    show_email_notification,
    show_summary_notification,
    show_error_notification,
)
from gmail_notifier.checker import GmailChecker
from gmail_notifier.ui.config_dialog import ConfigDialog
from gmail_notifier.ui.email_popup import EmailListPopup


class GmailNotifier:
    """Main application class managing the Gmail notification system.

    Orchestrates:
    - System tray icon with context menu
    - Background email checking via GmailChecker thread
    - Notification display and snooze functionality
    - Email popup window
    - Configuration dialog

    The source of truth for emails is `_all_emails` (ungrouped).
    `current_emails` is derived from it (grouped by thread) for display.

    Attributes:
        app: QApplication instance.
        settings: Dict of configuration settings.
        tray_icon: QSystemTrayIcon for system tray.
        current_emails: List of emails grouped by thread (for display).
        _all_emails: List of all ungrouped emails (source of truth).
        popup: Current EmailListPopup instance or None.
        snooze_manager: SnoozeManager instance for notification snooze state.
    """

    # Maximum number of individual notifications to show
    MAX_NOTIFICATIONS = 5

    def __init__(self):
        """Initialize the Gmail Notifier application."""
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setApplicationName("Gmail Notifier")
        self.app.setDesktopFileName("gmail-notifier")
        self.app.setWindowIcon(get_gmail_icon())

        # Email storage
        # _all_emails: ungrouped individual emails (source of truth)
        # current_emails: grouped by thread (derived, for display)
        self._all_emails = []
        self.current_emails = []

        # Track notified email IDs to avoid duplicate notifications
        self.notified_email_ids = set()

        # Snooze manager
        self.snooze_manager = SnoozeManager()

        # Error tracking
        self.is_error = False

        # Click timer for single/double click differentiation
        self.click_timer = QTimer()
        self.click_timer.setSingleShot(True)
        self.click_timer.setInterval(300)  # 300ms delay
        self.click_timer.timeout.connect(self._on_single_click)

        # Email list popup reference
        self.popup = None

        # Load settings
        self.settings = load_settings()

        # Create the system tray icon
        self.tray_icon = QSystemTrayIcon()
        self.tray_icon.setIcon(get_gmail_icon())
        self.tray_icon.setToolTip("Gmail Notifier")

        # Check if configuration is needed
        if not self.settings.get("username") or not self.settings.get("password"):
            self.show_config_dialog()

        # Create context menu
        self._setup_menu()

        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.activated.connect(self._on_tray_activated)

        # Start the email checking thread
        self._setup_checker_thread()

        # Show the tray icon and start checking
        self.tray_icon.show()
        self.checker_thread.start()

    def _setup_menu(self):
        """Create the system tray context menu."""
        self.menu = QMenu()

        self.check_now_action = QAction("Check Now")
        self.check_now_action.triggered.connect(self.check_now)
        self.menu.addAction(self.check_now_action)

        self.open_gmail_action = QAction("Open Gmail")
        self.open_gmail_action.triggered.connect(self.open_gmail)
        self.menu.addAction(self.open_gmail_action)

        self.snooze_action = QAction("Snooze for 1 hour")
        self.snooze_action.triggered.connect(self._on_toggle_snooze)
        self.menu.addAction(self.snooze_action)

        self.config_action = QAction("Configuration")
        self.config_action.triggered.connect(self.show_config_dialog)
        self.menu.addAction(self.config_action)

        self.menu.addSeparator()

        self.quit_action = QAction("Quit")
        self.quit_action.triggered.connect(self.quit)
        self.menu.addAction(self.quit_action)

    def _setup_checker_thread(self):
        """Initialize and configure the email checker thread."""
        self.checker_thread = QThread()
        self.gmail_checker = GmailChecker(self.settings)
        self.gmail_checker.moveToThread(self.checker_thread)

        self.checker_thread.started.connect(self.gmail_checker.run)
        self.gmail_checker.new_emails_signal.connect(self._on_new_emails)
        self.gmail_checker.error_signal.connect(self._on_error)

    # -------------------------------------------------------------------------
    # Tray Icon
    # -------------------------------------------------------------------------

    def _update_tray_icon(self):
        """Update tray icon with current state badges."""
        has_unread = len(self._all_emails) > 0
        is_snoozed = self.snooze_manager.is_snoozed()

        icon = create_badge_icon(
            get_gmail_icon(), has_unread, is_snoozed, self.is_error
        )
        self.tray_icon.setIcon(icon)

    def _on_tray_activated(self, reason):
        """Handle tray icon activation (clicks).

        Args:
            reason: QSystemTrayIcon.ActivationReason value.
        """
        if reason == QSystemTrayIcon.Trigger:
            # Single click - start timer to detect double click
            self.click_timer.start()
        elif reason == QSystemTrayIcon.DoubleClick:
            # Double click - cancel single click and open Gmail
            self.click_timer.stop()
            self.open_gmail()

    def _on_single_click(self):
        """Handle confirmed single click (timer expired)."""
        self.show_popup()

    # -------------------------------------------------------------------------
    # Email State Management
    # -------------------------------------------------------------------------

    def _update_email_state(self, emails):
        """Update email state from new email list.

        This is the central method for updating email state. It:
        1. Deduplicates emails
        2. Stores ungrouped emails as source of truth
        3. Derives grouped emails for display
        4. Updates tray icon

        Args:
            emails: List of email dicts from checker.
        """
        # Deduplicate by ID
        emails = dedup_emails(emails)

        # Store ungrouped emails (source of truth)
        self._all_emails = emails

        # Derive grouped emails for display
        self.current_emails = group_by_thread(emails)

        # Update tray icon
        self._update_tray_icon()

        # Update popup if visible
        if self.popup is not None and self.popup.isVisible():
            self.popup.update_emails(self.current_emails)

    def _remove_emails_from_state(self, email_ids):
        """Remove emails from local state by IDs.

        Args:
            email_ids: List of email ID strings to remove.
        """
        self._all_emails = remove_emails_by_ids(self._all_emails, email_ids)
        self.current_emails = group_by_thread(self._all_emails)
        self._update_tray_icon()

    # -------------------------------------------------------------------------
    # Email Actions
    # -------------------------------------------------------------------------

    def mark_email_read_locally(self, email_id):
        """Remove email from local list when user opens it.

        Args:
            email_id: ID of the email to mark as read locally.
        """
        self._remove_emails_from_state([email_id])

        # Trigger a full check from server after 20 seconds
        # This gives time for the user to read/archive the email
        QTimer.singleShot(20000, self.check_now)

    def delete_email(self, email_ids_str):
        """Delete all emails in a thread by moving to trash.

        Updates local state immediately, then runs IMAP delete in background.

        Args:
            email_ids_str: Comma-separated string of email IDs to delete.
        """
        # Parse the comma-separated email IDs
        email_ids_to_delete = [eid.strip() for eid in email_ids_str.split(",") if eid.strip()]

        # Update local state immediately
        self._remove_emails_from_state(email_ids_to_delete)

        # Re-show the popup with updated emails
        self.show_popup(check_mail=False)

        # Run IMAP delete in background
        username = self.settings.get("username", "")
        password = self.settings.get("password", "")

        def do_delete():
            try:
                delete_emails_imap(username, password, email_ids_to_delete)
            except Exception as e:
                error_msg = f"Failed to delete thread: {str(e)}"
                QTimer.singleShot(0, lambda: self._on_error(error_msg))

        threading.Thread(target=do_delete, daemon=True).start()

    def check_now(self):
        """Trigger an immediate email check."""
        self.gmail_checker.force_check = True

    def open_gmail(self):
        """Open Gmail in the default web browser."""
        webbrowser.open(self.settings.get("gmail_url", "https://mail.google.com"))

    # -------------------------------------------------------------------------
    # Popup
    # -------------------------------------------------------------------------

    def show_popup(self, check_mail=True):
        """Show the email list popup near the cursor.

        Args:
            check_mail: If True, trigger a mail check when opening.
        """
        # Close any existing popup
        if self.popup is not None:
            self.popup.close()
            self.popup.deleteLater()
            self.popup = None

        # Trigger email check if requested
        if check_mail:
            self.check_now()

        # Create and configure popup
        gmail_url = self.settings.get("gmail_url", "https://mail.google.com")
        # Augment emails with thread_email_ids to capture state at popup creation time
        emails_with_thread_ids = augment_grouped_with_thread_ids(
            self.current_emails, self._all_emails
        )
        self.popup = EmailListPopup(emails_with_thread_ids, gmail_url)
        self.popup.email_clicked.connect(self.mark_email_read_locally)
        self.popup.delete_requested.connect(self.delete_email)
        self.popup.reshow_requested.connect(lambda: self.show_popup(check_mail=False))

        # Position near cursor
        cursor_pos = QCursor.pos()
        x = max(0, cursor_pos.x() - 150)
        y = cursor_pos.y() - self.popup.height() - 10

        self.popup.move(x, y)
        self.popup.show()
        self.popup.activateWindow()

    # -------------------------------------------------------------------------
    # Snooze
    # -------------------------------------------------------------------------

    def _on_toggle_snooze(self):
        """Handle snooze toggle from menu."""
        is_now_snoozed = self.snooze_manager.toggle()
        self._update_snooze_ui(is_now_snoozed)

    def _snooze_from_notification(self):
        """Handle snooze action from notification click."""
        if not self.snooze_manager.is_snoozed():
            self.snooze_manager.snooze()
            self._update_snooze_ui(True)

    def _update_snooze_ui(self, is_snoozed):
        """Update UI elements to reflect snooze state.

        Args:
            is_snoozed: Current snooze state.
        """
        if is_snoozed:
            self.snooze_action.setText("Unsnooze")
            self.tray_icon.setToolTip("Gmail Notifier (Snoozed)")
        else:
            self.snooze_action.setText("Snooze for 1 hour")
            self.tray_icon.setToolTip("Gmail Notifier")
        self._update_tray_icon()

    # -------------------------------------------------------------------------
    # Notifications
    # -------------------------------------------------------------------------

    def _on_new_emails(self, emails):
        """Handle new emails signal from GmailChecker.

        Args:
            emails: List of email dicts from the checker.
        """
        # Clear error state on successful check
        self.is_error = False

        # Update email state (dedup, store, group, update UI)
        self._update_email_state(emails)

        # Clean up notified_email_ids: only keep IDs still on server
        server_ids = {str(e.get("id")) for e in emails}
        self.notified_email_ids = self.notified_email_ids & server_ids

        if not emails:
            return

        # Filter out already notified emails
        new_emails = [e for e in emails if e["id"] not in self.notified_email_ids]
        if not new_emails:
            return

        # Check if snoozed - skip notifications but don't mark as notified
        if self.snooze_manager.is_snoozed():
            return

        # Send notifications (with delay between each)
        self._send_notifications(new_emails)

        # Mark all new emails as notified
        for email_item in new_emails:
            self.notified_email_ids.add(email_item["id"])

    def _send_notifications(self, new_emails):
        """Send notifications for new emails.

        Shows individual notifications up to MAX_NOTIFICATIONS,
        then a summary for any remaining.

        Args:
            new_emails: List of new email dicts to notify about.
        """
        emails_to_notify = new_emails[: self.MAX_NOTIFICATIONS]
        extra_count = len(new_emails) - self.MAX_NOTIFICATIONS

        # Send individual notifications with 300ms delay between each
        for i, email_item in enumerate(emails_to_notify):
            delay = i * 300
            QTimer.singleShot(
                delay,
                lambda e=email_item: show_email_notification(
                    self.tray_icon,
                    e["sender"],
                    e["subject"],
                    e.get("link"),
                    self._snooze_from_notification,
                ),
            )

        # Show summary if there are more emails
        if extra_count > 0:
            delay = len(emails_to_notify) * 300
            QTimer.singleShot(
                delay,
                lambda: show_summary_notification(
                    self.tray_icon, extra_count, self._snooze_from_notification
                ),
            )

    def _on_error(self, error_msg):
        """Handle error signal from GmailChecker.

        Args:
            error_msg: Error message string to display.
        """
        self.is_error = True
        self._update_tray_icon()
        show_error_notification(self.tray_icon, error_msg)

    # -------------------------------------------------------------------------
    # Configuration
    # -------------------------------------------------------------------------

    def show_config_dialog(self):
        """Show the configuration dialog."""
        dialog = ConfigDialog(self.settings, self.tray_icon)
        if dialog.exec_():
            self.settings = dialog.settings
            save_settings(self.settings)

    # -------------------------------------------------------------------------
    # Application Lifecycle
    # -------------------------------------------------------------------------

    def quit(self):
        """Clean up and exit the application."""
        self.gmail_checker.running = False
        self.checker_thread.quit()
        self.checker_thread.wait()
        self.app.quit()

    def run(self):
        """Start the Qt event loop.

        Returns:
            int: Application exit code.
        """
        return self.app.exec_()
