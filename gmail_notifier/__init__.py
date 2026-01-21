#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gmail Notifier - A system tray application for Gmail notifications.

This package provides a desktop notification system for Gmail that:
- Monitors your Gmail inbox via IMAP
- Shows system tray notifications for new emails
- Displays an email list popup on click
- Supports snooze functionality
- Securely stores credentials in the system keyring

Usage:
    # As a module
    python -m gmail_notifier

    # Or import and call main()
    from gmail_notifier import main
    main()
"""

from gmail_notifier.__main__ import main

__version__ = "1.0.0"
__all__ = ["main"]
