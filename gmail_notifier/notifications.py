#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""System notification utilities for Gmail Notifier.

This module provides functions to send desktop notifications using
notify-send with clickable actions for opening emails and snoozing.
"""

import subprocess
import threading
import webbrowser


def send_system_notification(
    title, body, icon="mail-unread", snooze_callback=None, open_url=None
):
    """Send a system notification with optional click actions.

    Uses notify-send to display a desktop notification with "Open Email"
    and optionally "Snooze 1 hour" action buttons.

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
