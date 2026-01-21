#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Notification utilities for Gmail Notifier.

This module provides functions to send desktop notifications using
notify-send with clickable actions, as well as higher-level functions
for showing email notifications via both Qt tray and system notifications.
"""

import subprocess
import threading
import webbrowser

from PyQt5.QtWidgets import QSystemTrayIcon


def send_system_notification(
    title, body, icon="mail-unread", snooze_callback=None, open_url=None
):
    """Send a system notification with optional click actions.

    Uses notify-send to display a desktop notification with "Open Email"
    and optionally "Snooze 1 hour" action buttons.

    This function is non-blocking - runs notification in a background thread.

    Args:
        title: Notification title text.
        body: Notification body text.
        icon: Icon name or path (default: "mail-unread").
        snooze_callback: Optional callback function for snooze action.
        open_url: Optional URL to open when "Open" is clicked.
                  Defaults to Gmail inbox if not provided.
    """

    def run_notification():
        try:
            # Use notify-send with actions for clickable notification
            # -e: auto-expire after timeout (prevents lingering)
            # -t: timeout in milliseconds (10 seconds)
            cmd = [
                "notify-send",
                "-a",
                "Gmail Notifier",
                "-i",
                icon,
                "-e",
                "-t",
                "10000",
                "-A",
                "open=Open Email" if open_url else "open=Open Gmail",
            ]
            # Add snooze action if callback provided
            if snooze_callback is not None:
                cmd.extend(["-A", "snooze=Snooze 1 hour"])
            cmd.extend([title, body])

            result = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=15,  # Kill process after 15 seconds max
            )
            # Handle user action
            action = result.stdout.strip()
            if action == "open":
                url = open_url if open_url else "https://mail.google.com"
                webbrowser.open(url)
            elif action == "snooze" and snooze_callback is not None:
                snooze_callback()
        except subprocess.TimeoutExpired:
            # Notification timed out, ignore
            pass
        except FileNotFoundError:
            # notify-send not available, silently ignore
            pass

    # Run in a separate thread to not block the UI
    threading.Thread(target=run_notification, daemon=True).start()


def show_email_notification(
    tray_icon, sender, subject, link=None, snooze_callback=None
):
    """Show notification for a single email.

    Sends both a Qt tray notification and a system notification (via notify-send).

    Args:
        tray_icon: QSystemTrayIcon instance to show message on.
        sender: Email sender name.
        subject: Email subject line.
        link: Optional URL to open email directly.
        snooze_callback: Optional callback for snooze action.
    """
    title = f"New email from {sender}"
    body = subject

    # Qt tray icon notification
    tray_icon.showMessage(
        title,
        body,
        QSystemTrayIcon.Information,
        5000,  # Show for 5 seconds
    )

    # System notification with snooze option and direct email link
    send_system_notification(
        title,
        body,
        snooze_callback=snooze_callback,
        open_url=link,
    )


def show_summary_notification(tray_icon, count, snooze_callback=None):
    """Show summary notification for additional emails.

    Used when there are more emails than the max notification limit.

    Args:
        tray_icon: QSystemTrayIcon instance to show message on.
        count: Number of additional emails not individually notified.
        snooze_callback: Optional callback for snooze action.
    """
    title = "New Emails"
    body = f"And {count} more new email{'s' if count > 1 else ''}..."

    # Qt tray icon notification
    tray_icon.showMessage(
        title,
        body,
        QSystemTrayIcon.Information,
        5000,
    )

    # System notification with snooze option
    send_system_notification(title, body, snooze_callback=snooze_callback)


def show_error_notification(tray_icon, error_msg):
    """Show error notification.

    Args:
        tray_icon: QSystemTrayIcon instance to show message on.
        error_msg: Error message string to display.
    """
    tray_icon.showMessage(
        "Gmail Notifier Error",
        error_msg,
        QSystemTrayIcon.Warning,
        5000,
    )
