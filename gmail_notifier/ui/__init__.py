#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UI components for Gmail Notifier.

This package contains all Qt-based UI components:
- ConfigDialog: Settings configuration dialog
- EmailListPopup: Popup showing list of unread emails
- GmailNotifier: Main application class with system tray
"""

from gmail_notifier.ui.config_dialog import ConfigDialog
from gmail_notifier.ui.email_popup import EmailListPopup
from gmail_notifier.ui.main_app import GmailNotifier

__all__ = ["ConfigDialog", "EmailListPopup", "GmailNotifier"]
