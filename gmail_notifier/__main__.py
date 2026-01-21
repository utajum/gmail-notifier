#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entry point for Gmail Notifier when run as a module.

Usage:
    python -m gmail_notifier

This module handles application startup including:
- Lock file to prevent multiple instances
- Configuration directory creation
- Main application initialization
"""

import os
import sys

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QLockFile, QDir

from gmail_notifier.config import CONFIG_DIR
from gmail_notifier.ui.main_app import GmailNotifier


def main():
    """Main entry point for Gmail Notifier.

    Handles lock file to prevent multiple instances and starts
    the main application.
    """
    # Verify that the configuration directory exists
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)

    # Check if another instance is running
    lock_file = QLockFile(os.path.join(QDir.tempPath(), "gmail-notifier.lock"))

    if not lock_file.tryLock():
        # Need to create a dummy QApplication to show a QMessageBox
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Gmail Notifier")
        msg.setText("Another instance of Gmail Notifier seems to be running.")
        msg.setInformativeText(
            "If you are sure it's not running, the lock file might be stale."
        )

        force_btn = msg.addButton("Force Start", QMessageBox.ActionRole)
        msg.addButton("Exit", QMessageBox.RejectRole)

        msg.exec_()

        if msg.clickedButton() == force_btn:
            # Remove stale lock file and try again
            lock_path = os.path.join(QDir.tempPath(), "gmail-notifier.lock")
            if os.path.exists(lock_path):
                os.remove(lock_path)

            # Try to lock again
            if not lock_file.tryLock():
                QMessageBox.critical(
                    None, "Error", "Could not acquire lock even after forcing."
                )
                sys.exit(1)
        else:
            sys.exit(0)

    # Start the application
    notifier = GmailNotifier()
    sys.exit(notifier.run())


if __name__ == "__main__":
    main()
