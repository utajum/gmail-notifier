#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Email list popup widget for Gmail Notifier.

This module provides the EmailListPopup class which displays a list
of unread emails in a popup near the system tray.
"""

import webbrowser

from PyQt5.QtWidgets import (
    QDialog,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QWidget,
    QSizePolicy,
    QScrollArea,
    QFrame,
    QMessageBox,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon


class EmailListPopup(QDialog):
    """Popup dialog showing list of unread emails.

    Displays emails in a scrollable list with sender, subject, and
    delete button for each item. Clicking an email opens it in browser.

    Signals:
        email_clicked: Emitted with email_id when an email is clicked.
        delete_requested: Emitted with email_id when delete is requested.
        reshow_requested: Emitted when popup should be re-shown.
    """

    email_clicked = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    reshow_requested = pyqtSignal()

    def __init__(self, emails, gmail_url, parent=None):
        """Initialize the email list popup.

        Args:
            emails: List of email dicts to display.
            gmail_url: URL to open when "Open Gmail Inbox" is clicked.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.emails = emails
        self.gmail_url = gmail_url
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.init_ui()

    def init_ui(self):
        """Initialize the popup UI components."""
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
        """Add a single email row with text and delete button.

        Args:
            email_data: Dict with keys: sender, subject, id, link, thread_count.
        """
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
        """Open Gmail inbox in browser."""
        webbrowser.open(self.gmail_url)
        self.close()

    def _on_delete_clicked(self, email_id):
        """Handle delete button click with confirmation.

        Args:
            email_id: ID of the email to delete.
        """
        # Close the popup first, then show confirmation
        self.hide()

        # Create message box with mail icon
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Delete Thread")
        msg_box.setWindowIcon(QIcon.fromTheme("mail-unread"))
        msg_box.setText("Are you sure you want to delete this thread?")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.Yes)
        reply = msg_box.exec_()

        if reply == QMessageBox.Yes:
            self.delete_requested.emit(str(email_id))
        else:
            # Re-show the popup when user clicks No
            self.reshow_requested.emit()

    def _on_email_clicked(self, link, email_id):
        """Handle click on email text to open it.

        Args:
            link: URL to open in browser.
            email_id: ID of the clicked email.
        """
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
        """Update the email list with new emails.

        Args:
            emails: New list of email dicts to display.
        """
        self.emails = emails

        # Clear existing email rows
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Re-add email items
        self._add_email_items()
        # Don't resize - keep fixed height
