#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Configuration dialog for Gmail Notifier.

This module provides the ConfigDialog class for configuring Gmail
account credentials, check intervals, and autostart settings.
"""

import os
import sys
import imaplib
import threading

import keyring
from PyQt5.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QGridLayout,
    QVBoxLayout,
    QCheckBox,
    QMessageBox,
    QSystemTrayIcon,
)
from PyQt5.QtCore import pyqtSignal

from gmail_notifier.config import ICON_PATH, save_settings
from gmail_notifier.notifications import send_system_notification
from gmail_notifier.tray_icon import get_gmail_icon


class ConfigDialog(QDialog):
    """Dialog for configuring Gmail Notifier settings.

    Allows users to:
    - Enter Gmail credentials (email + app password)
    - Set check interval
    - Enable/disable autostart
    - Test connection and notifications

    Signals:
        test_result_signal: Emitted with (success: bool, message: str)
                           when connection test completes.
    """

    test_result_signal = pyqtSignal(bool, str)

    def __init__(self, settings, tray_icon=None, parent=None):
        """Initialize the configuration dialog.

        Args:
            settings: Dict containing current settings.
            tray_icon: Optional QSystemTrayIcon for test notifications.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.settings = settings
        self.tray_icon = tray_icon
        self.test_result_signal.connect(self._on_test_result)
        self.init_ui()

    def init_ui(self):
        """Initialize the dialog UI components."""
        self.setWindowTitle("Gmail Notifier - Configuration")
        self.setWindowIcon(get_gmail_icon())
        self.setMinimumWidth(400)

        layout = QGridLayout()

        # Input fields
        layout.addWidget(QLabel("Email:"), 0, 0)
        self.username_input = QLineEdit(self.settings.get("username", ""))
        layout.addWidget(self.username_input, 0, 1)

        layout.addWidget(QLabel("App Password:"), 1, 0)
        self.password_input = QLineEdit(self.settings.get("password", ""))
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input, 1, 1)

        # Information about App Password
        info_label = QLabel(
            'Note: You must use a specific "App Password" for Gmail.\n'
            "1. Go to your Google Account > Security\n"
            "2. Enable 2-Step Verification if you haven't already\n"
            '3. Find "App passwords"\n'
            '4. Generate a new one for "Mail" > "Other (Gmail Notifier)"'
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label, 2, 0, 1, 2)

        # Check interval
        layout.addWidget(QLabel("Check every (minutes):"), 3, 0)
        self.interval_input = QLineEdit(
            str(self.settings.get("check_interval", 300) // 60)
        )
        layout.addWidget(self.interval_input, 3, 1)

        # Autostart
        self.autostart_checkbox = QCheckBox("Start automatically with the system")
        desktop_file = os.path.expanduser("~/.config/autostart/gmail-notifier.desktop")
        self.autostart_checkbox.setChecked(os.path.exists(desktop_file))
        layout.addWidget(self.autostart_checkbox, 4, 0, 1, 2)

        # Buttons
        button_layout = QVBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_config)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        self.test_button = QPushButton("Test Connection")
        self.test_button.clicked.connect(self.test_connection)
        test_notification_button = QPushButton("Test Notification")
        test_notification_button.clicked.connect(self.test_notification)

        button_layout.addWidget(self.test_button)
        button_layout.addWidget(test_notification_button)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout, 5, 0, 1, 2)

        self.setLayout(layout)

    def save_config(self):
        """Validate and save configuration settings."""
        # Validate data
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(
                self, "Error", "You must enter a valid email and password"
            )
            return

        try:
            interval = int(self.interval_input.text()) * 60  # Convert to seconds
            if interval < 60:
                interval = 60  # Minimum 1 minute
        except ValueError:
            interval = 300  # 5 minutes by default

        # Save settings
        self.settings["username"] = username
        self.settings["password"] = password
        self.settings["check_interval"] = interval

        # Save password to keyring
        try:
            keyring.set_password("gmail-notifier", username, password)
        except Exception as e:
            QMessageBox.critical(
                self, "Keyring Error", f"Could not save password to system keyring: {e}"
            )
            return

        # Configure autostart
        desktop_file = os.path.expanduser("~/.config/autostart/gmail-notifier.desktop")
        if self.autostart_checkbox.isChecked():
            # Create .desktop file for autostart
            os.makedirs(os.path.dirname(desktop_file), exist_ok=True)
            script_path = os.path.abspath(sys.argv[0])

            with open(desktop_file, "w") as f:
                f.write(f"""[Desktop Entry]
Name=Gmail Notifier
Comment=Gmail Notifier for KDE
Exec={script_path}
Icon={ICON_PATH}
Terminal=false
Type=Application
Categories=Network;Email;
StartupNotify=true
X-GNOME-Autostart-enabled=true
""")
        else:
            # Remove .desktop file if it exists
            if os.path.exists(desktop_file):
                os.remove(desktop_file)

        # Save other settings to JSON file
        save_settings(self.settings)
        self.accept()

    def test_connection(self):
        """Test Gmail IMAP connection in a background thread."""
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(
                self, "Error", "You must enter a valid email and password"
            )
            return

        # Disable button while testing
        self.test_button.setText("Testing...")
        self.test_button.setEnabled(False)

        def run_test():
            try:
                # Try to connect to Gmail with IMAP
                mail = imaplib.IMAP4_SSL("imap.gmail.com")
                mail.login(username, password)
                mail.select("inbox")
                mail.close()
                mail.logout()
                self.test_result_signal.emit(
                    True,
                    "The connection with Gmail has been established successfully.",
                )
            except Exception as e:
                self.test_result_signal.emit(
                    False, f"Could not connect to Gmail: {str(e)}"
                )

        threading.Thread(target=run_test, daemon=True).start()

    def _on_test_result(self, success, message):
        """Handle test connection result on main thread.

        Args:
            success: True if connection succeeded.
            message: Result message to display.
        """
        self.test_button.setText("Test Connection")
        self.test_button.setEnabled(True)
        if success:
            QMessageBox.information(self, "Connection Successful", message)
        else:
            QMessageBox.critical(self, "Connection Error", message)

    def test_notification(self):
        """Send a test notification to verify notification system."""
        if self.tray_icon is None:
            QMessageBox.warning(
                self,
                "Error",
                "Tray icon not available. Please save your configuration and restart the application.",
            )
            return

        # Dummy data for testing
        dummy_sender = "John Doe"
        dummy_subject = "Meeting tomorrow at 10am - Project Review"
        title = f"New email from {dummy_sender}"
        body = dummy_subject

        # Tray icon notification
        self.tray_icon.showMessage(
            title,
            body,
            QSystemTrayIcon.Information,
            5000,  # Show for 5 seconds
        )

        # System notification
        send_system_notification(title, body)
