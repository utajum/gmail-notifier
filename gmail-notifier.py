#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re
import time
import json
import imaplib
import email
import webbrowser
import getpass
import keyring
import subprocess
import threading
from datetime import datetime, timedelta
from email.header import decode_header
from email.utils import parsedate_to_datetime
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication,
    QSystemTrayIcon,
    QMenu,
    QAction,
    QMessageBox,
    QInputDialog,
    QLineEdit,
    QDialog,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QGridLayout,
    QCheckBox,
    QListWidget,
    QListWidgetItem,
    QWidget,
    QSizePolicy,
    QScrollArea,
    QFrame,
)
from PyQt5.QtCore import (
    QTimer,
    QObject,
    pyqtSignal,
    QThread,
    QLockFile,
    QDir,
    Qt,
    QRect,
    QSize,
)
from PyQt5.QtGui import QIcon, QCursor, QColor, QFont, QPainter, QPixmap

# Configuration
CONFIG_DIR = os.path.expanduser("~/.config/gmail-notifier")
SETTINGS_PATH = os.path.join(CONFIG_DIR, "settings.json")

# Ensure the configuration directory exists
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)

# Default settings
DEFAULT_SETTINGS = {
    "check_interval": 300,  # Seconds (5 minutes)
    "gmail_url": "https://mail.google.com",
    "last_check_time": 0,
    "last_uid": 0,
    "username": "",
}


# Load settings
def load_settings():
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "r") as f:
            try:
                settings = json.load(f)
            except (json.JSONDecodeError, ValueError):
                print("Settings file corrupted. Loading defaults.")
                return DEFAULT_SETTINGS

            # Get password from keyring
            if settings.get("username"):
                try:
                    settings["password"] = keyring.get_password(
                        "gmail-notifier", settings["username"]
                    )
                except Exception as e:
                    print(f"Could not retrieve password from keyring: {e}")
                    settings["password"] = None
            return settings
    return DEFAULT_SETTINGS


# Save settings
def save_settings(settings):
    # Create a copy to avoid modifying the original
    settings_to_save = settings.copy()
    # Don't save password in the json file
    if "password" in settings_to_save:
        del settings_to_save["password"]

    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings_to_save, f, indent=4)


# Send system notification using notify-send with click actions
def send_system_notification(
    title, body, icon="mail-unread", snooze_callback=None, open_url=None
):
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


# Dialog to configure the account
class ConfigDialog(QDialog):
    # Signal for test connection result (success: bool, message: str)
    test_result_signal = pyqtSignal(bool, str)

    def __init__(self, settings, tray_icon=None, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.tray_icon = tray_icon
        self.test_result_signal.connect(self._on_test_result)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Gmail Notifier - Configuration")
        self.setWindowIcon(QIcon.fromTheme("mail-unread"))
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
Icon=gmail
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
        """Handle test connection result on main thread."""
        self.test_button.setText("Test Connection")
        self.test_button.setEnabled(True)
        if success:
            QMessageBox.information(self, "Connection Successful", message)
        else:
            QMessageBox.critical(self, "Connection Error", message)

    def test_notification(self):
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


# Class to check emails in a separate thread
class GmailChecker(QObject):
    new_emails_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.running = True
        self.force_check = True

    def check_emails(self):
        username = self.settings.get("username", "")
        password = self.settings.get("password", "")

        if not username or not password:
            self.error_signal.emit(
                "Configuration incomplete. Please configure your Gmail account."
            )
            return None

        try:
            # Connect to Gmail with IMAP
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(username, password)
            mail.select("inbox")

            # Search for unread emails from the last 3 days
            # Use English month names for IMAP compatibility (locale-independent)
            months = [
                "Jan",
                "Feb",
                "Mar",
                "Apr",
                "May",
                "Jun",
                "Jul",
                "Aug",
                "Sep",
                "Oct",
                "Nov",
                "Dec",
            ]
            three_days_ago = datetime.now() - timedelta(days=3)
            date_str = f"{three_days_ago.day:02d}-{months[three_days_ago.month - 1]}-{three_days_ago.year}"
            status, messages = mail.search(None, f"(UNSEEN SINCE {date_str})")

            if status != "OK":
                mail.close()
                mail.logout()
                return None

            email_data = []

            # Get unread message IDs
            message_ids = messages[0].split()

            # Check the last 200 unread emails at most
            for msg_id in message_ids[-200:]:
                status, msg_data = mail.fetch(
                    msg_id, "(X-GM-THRID BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])"
                )

                if status != "OK":
                    continue

                # Parse Thread ID for the link
                thread_id_hex = ""
                try:
                    # msg_data[0][0] contains the header line with X-GM-THRID
                    match = re.search(rb"X-GM-THRID (\d+)", msg_data[0][0])
                    if match:
                        thread_id = int(match.group(1))
                        thread_id_hex = hex(thread_id)[2:]  # Remove '0x' prefix
                except Exception:
                    pass

                link = (
                    f"https://mail.google.com/mail/u/0/#inbox/{thread_id_hex}"
                    if thread_id_hex
                    else self.settings.get("gmail_url", "https://mail.google.com")
                )

                # Decode the message
                raw_email = msg_data[0][1]

                msg = email.message_from_bytes(raw_email)

                # Get sender, subject, and date with improved encoding handling
                subject = self._decode_header_safely(msg["Subject"])
                sender = self._decode_header_safely(msg["From"])
                date_str = msg["Date"]

                # Parse date to timestamp for sorting
                timestamp = 0
                if date_str:
                    try:
                        dt = parsedate_to_datetime(date_str)
                        timestamp = dt.timestamp()
                    except Exception:
                        pass

                # Filter only the sender's name if available
                if "<" in sender:
                    sender_name = sender.split("<")[0].strip()
                    sender = sender_name if sender_name else sender

                email_data.append(
                    {
                        "id": msg_id.decode(),
                        "subject": subject,
                        "sender": sender,
                        "link": link,
                        "timestamp": timestamp,
                        "thread_id": thread_id_hex,
                    }
                )

            mail.close()
            mail.logout()

            # Sort by timestamp, newest first
            email_data.sort(key=lambda e: e.get("timestamp", 0), reverse=True)
            return email_data

        except Exception as e:
            error_msg = f"Error checking emails: {str(e)}"
            self.error_signal.emit(error_msg)
            return None

    def _decode_header_safely(self, header):
        """Safely decodes email headers by handling different encodings."""
        if not header:
            return ""

        try:
            # Try to decode using email.header.decode_header
            decoded_parts = decode_header(header)
            result = ""

            for decoded_text, charset in decoded_parts:
                # If it's bytes, decode with the correct encoding or fallback to alternatives
                if isinstance(decoded_text, bytes):
                    if charset:
                        try:
                            # Try with the specified encoding
                            part = decoded_text.decode(charset)
                        except (UnicodeDecodeError, LookupError):
                            # If it fails, try with UTF-8
                            try:
                                part = decoded_text.decode("utf-8")
                            except UnicodeDecodeError:
                                # If UTF-8 fails, try with latin-1 (always works but may show incorrect characters)
                                part = decoded_text.decode("latin-1")
                    else:
                        # No encoding specified, try UTF-8 first
                        try:
                            part = decoded_text.decode("utf-8")
                        except UnicodeDecodeError:
                            # Fallback to latin-1
                            part = decoded_text.decode("latin-1")
                else:
                    # It's already a string
                    part = decoded_text

                result += part

            return result

        except Exception:
            # If everything fails, return a default value
            return "[Unsupported encoding]"

    def run(self):
        last_check_time = self.settings.get("last_check_time", 0)
        check_interval = self.settings.get("check_interval", 300)

        while self.running:
            current_time = time.time()

            # Check if it's time to check for new emails or if forced
            should_check = (
                current_time - last_check_time >= check_interval
            ) or self.force_check

            if should_check:
                # Reset force flag
                self.force_check = False

                emails = self.check_emails()

                if emails is not None:
                    self.new_emails_signal.emit(emails)

                # Update the last check time
                self.settings["last_check_time"] = current_time
                save_settings(self.settings)
                last_check_time = current_time

            # Wait a bit before the next iteration
            time.sleep(1)  # Check every 1 second for responsive "Check Now"


# Popup window to list emails
class EmailListPopup(QDialog):
    email_clicked = pyqtSignal(str)
    delete_requested = pyqtSignal(str)  # Emits email_id for deletion
    reshow_requested = pyqtSignal()  # Request to re-show the popup

    def __init__(self, emails, gmail_url, parent=None):
        super().__init__(parent)
        self.emails = emails
        self.gmail_url = gmail_url
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.init_ui()

    def init_ui(self):
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)

        # Container widget with dark background
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border: 1px solid #3d3d3d;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Open Gmail button at top
        open_gmail_btn = QPushButton("Open Gmail Inbox")
        open_gmail_btn.setCursor(Qt.PointingHandCursor)
        open_gmail_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e1e1e;
                color: #4da6ff;
                border: none;
                border-bottom: 1px solid #2d2d2d;
                padding: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2d2d2d;
            }
        """)
        open_gmail_btn.clicked.connect(self._on_open_gmail)
        container_layout.addWidget(open_gmail_btn)

        # Scroll area for emails
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #1e1e1e;
            }
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 8px;
            }
            QScrollBar::handle:vertical {
                background-color: #3d3d3d;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        # Content widget inside scroll area
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background-color: #1e1e1e;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        self._add_email_items()

        self.scroll_area.setWidget(self.content_widget)
        container_layout.addWidget(self.scroll_area)

        main_layout.addWidget(container)
        self._resize_to_content()

    def _add_email_items(self):
        """Add email items to the content layout."""
        if self.emails:
            for email_data in self.emails:
                self._add_email_row(email_data)
        else:
            # No emails message
            no_emails_label = QLabel("No new emails")
            no_emails_label.setStyleSheet("""
                color: #888888;
                padding: 20px;
                background-color: #1e1e1e;
            """)
            no_emails_label.setAlignment(Qt.AlignCenter)
            self.content_layout.addWidget(no_emails_label)

        # Add stretch to push items to top
        self.content_layout.addStretch()

    def _add_email_row(self, email_data):
        """Add a single email row with text and delete button."""
        sender = email_data.get("sender", "Unknown")
        subject = email_data.get("subject", "(No Subject)")
        email_id = email_data.get("id")
        link = email_data.get("link")
        thread_count = email_data.get("thread_count", 1)

        # Add thread count to subject if more than 1 email in thread
        if thread_count > 1:
            subject = f"{subject} ({thread_count})"

        # Row container
        row_widget = QFrame()
        row_widget.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border: none;
                border-bottom: 1px solid #2d2d2d;
            }
            QFrame:hover {
                background-color: #2d2d2d;
            }
        """)
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(10, 8, 8, 8)
        row_layout.setSpacing(8)

        # Email text label
        text_label = QLabel(
            f"<b>{sender}</b><br><span style='color: #aaaaaa;'>{subject}</span>"
        )
        text_label.setStyleSheet(
            "color: #e0e0e0; background: transparent; border: none;"
        )
        text_label.setWordWrap(True)
        text_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        text_label.setCursor(Qt.PointingHandCursor)
        text_label.mousePressEvent = (
            lambda event, l=link, eid=email_id: self._on_email_clicked(l, eid)
        )
        row_layout.addWidget(text_label)

        # Delete button with trash icon
        delete_btn = QPushButton()
        delete_btn.setIcon(QIcon.fromTheme("user-trash"))
        delete_btn.setFixedSize(28, 28)
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #ff5555;
            }
        """)
        delete_btn.clicked.connect(
            lambda checked, eid=email_id: self._on_delete_clicked(eid)
        )
        row_layout.addWidget(delete_btn, 0, Qt.AlignTop)

        self.content_layout.addWidget(row_widget)

    def _on_open_gmail(self):
        """Open Gmail inbox."""
        webbrowser.open(self.gmail_url)
        self.close()

    def _on_delete_clicked(self, email_id):
        """Handle delete button click with confirmation."""
        # Close the popup first, then show confirmation
        self.hide()

        # Create message box with mail icon
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Delete Email")
        msg_box.setWindowIcon(QIcon.fromTheme("mail-unread"))
        msg_box.setText("Are you sure you want to delete this email?")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.Yes)
        reply = msg_box.exec_()

        if reply == QMessageBox.Yes:
            self.delete_requested.emit(str(email_id))
        else:
            # Re-show the popup when user clicks No
            self.reshow_requested.emit()

    def _on_email_clicked(self, link, email_id):
        """Handle click on email text to open it."""
        if email_id:
            self.email_clicked.emit(str(email_id))
        if link:
            webbrowser.open(link)
        self.close()

    def _resize_to_content(self):
        """Set fixed popup size."""
        # Fixed height - scroll area handles overflow
        self.resize(380, 550)

    def update_emails(self, emails):
        """Update the email list with new emails."""
        self.emails = emails

        # Clear existing email rows
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Re-add email items
        self._add_email_items()
        # Don't resize - keep fixed height


# Main class for the application
class GmailNotifier:
    def __init__(self):
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
        """Adds or removes a badge (dot, zzz, or !) from the tray icon."""
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
        if reason == QSystemTrayIcon.Trigger:
            # Single click (or first click of double click)
            self.click_timer.start()
        elif reason == QSystemTrayIcon.DoubleClick:
            # Double click detected
            self.click_timer.stop()
            self.open_gmail()

    def on_click_timer(self):
        # Timer expired, meaning it was a single click
        self.show_popup()

    def _dedup_emails(self, emails):
        """Remove duplicate emails by ID and sort by timestamp (newest first)."""
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
        """Group emails by thread ID, return one entry per thread with unread count.

        Returns list of emails where each entry represents a thread:
        - Uses the newest email's data (sender, subject, link, etc.)
        - Adds 'thread_count' field with number of unread emails in thread
        - Sorted by newest email timestamp (newest thread first)
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
        webbrowser.open(self.settings.get("gmail_url", "https://mail.google.com"))

    def mark_email_read_locally(self, email_id):
        """Removes the email from the local list and updates the badge immediately."""
        # Remove the email with the matching ID from ungrouped list
        self._all_emails = [
            e for e in self._all_emails if str(e.get("id")) != str(email_id)
        ]

        # Re-group for display
        self.current_emails = self._group_by_thread(self._all_emails)

        # Update tray icon badge (based on ungrouped count)
        self.update_tray_icon(len(self._all_emails) > 0, self.is_snoozed())

        # Trigger a full check from server after 20 seconds
        # This gives time for the user to read/archive the email so the next check reflects the true state
        QTimer.singleShot(20000, self.check_now)

    def delete_email(self, email_id):
        """Delete an email by moving it to trash. Runs in background thread."""
        # Remove from ungrouped list immediately
        self._all_emails = [
            e for e in self._all_emails if str(e.get("id")) != str(email_id)
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

                # Convert email_id to bytes if it's a string
                msg_id = (
                    email_id if isinstance(email_id, bytes) else str(email_id).encode()
                )

                # For Gmail, copy to Trash folder then delete from inbox
                # This is the proper way to delete in Gmail via IMAP
                copy_result = mail.copy(msg_id, "[Gmail]/Trash")
                if copy_result[0] == "OK":
                    mail.store(msg_id, "+FLAGS", "\\Deleted")
                    mail.expunge()

                mail.close()
                mail.logout()
            except Exception as e:
                # Emit error on main thread
                error_msg = f"Failed to delete email: {str(e)}"
                QTimer.singleShot(0, lambda: self.on_error(error_msg))

        threading.Thread(target=do_delete, daemon=True).start()

    def check_now(self):
        # Set flag to force an immediate check in the next cycle
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
        """Check if notifications are currently snoozed."""
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
        """Called when snooze is clicked from a notification."""
        if not self.is_snoozed():
            self.snoozed_until = time.time() + 3600
            self.snooze_action.setText("Unsnooze")
            self.tray_icon.setToolTip("Gmail Notifier (Snoozed)")
            self.update_tray_icon(len(self.current_emails) > 0, True)

    def show_config_dialog(self):
        dialog = ConfigDialog(self.settings, self.tray_icon)
        if dialog.exec_():
            # If the dialog is accepted, save the settings
            self.settings = dialog.settings
            save_settings(self.settings)

    def on_new_emails(self, emails):
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
        """Show notification for a single email."""
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
        """Show summary notification for additional emails."""
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
        # Set error state
        self.is_error = True
        self.update_tray_icon(len(self.current_emails) > 0, self.is_snoozed())

        self.tray_icon.showMessage(
            "Gmail Notifier Error", error_msg, QSystemTrayIcon.Warning, 5000
        )

    def quit(self):
        # Stop the thread
        self.gmail_checker.running = False
        self.checker_thread.quit()
        self.checker_thread.wait()

        # Exit the application
        self.app.quit()

    def run(self):
        return self.app.exec_()


# Main function
def main():
    # Verify that the configuration directory exists
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)

    # Check if another instance is running
    lock_file = QLockFile(os.path.join(QDir.tempPath(), "gmail-notifier.lock"))

    if not lock_file.tryLock():
        # You need to create a dummy QApplication to show a QMessageBox
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
