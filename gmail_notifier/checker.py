#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gmail email checking worker for Gmail Notifier.

This module contains the GmailChecker class which runs in a separate
thread and periodically checks for new unread emails via IMAP.
"""

import re
import time
import imaplib
import email
from datetime import datetime, timedelta
from email.header import decode_header
from email.utils import parsedate_to_datetime

from PyQt5.QtCore import QObject, pyqtSignal

from gmail_notifier.config import save_settings


class GmailChecker(QObject):
    """Worker class that checks Gmail for new emails in a background thread.

    Signals:
        new_emails_signal: Emitted with list of email dicts when check completes.
        error_signal: Emitted with error message string on failure.

    Attributes:
        settings: Dict containing username, password, check_interval, etc.
        running: Boolean flag to control the run loop.
        force_check: Boolean flag to trigger immediate check.
    """

    new_emails_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.running = True
        self.force_check = True

    def check_emails(self):
        """Connect to Gmail via IMAP and fetch unread emails.

        Returns:
            list: List of email dicts with keys: id, subject, sender, link,
                  timestamp, thread_id. Returns None on error.
        """
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
        """Safely decode email headers handling different encodings.

        Args:
            header: Raw email header string/bytes.

        Returns:
            str: Decoded header text, or "[Unsupported encoding]" on failure.
        """
        if not header:
            return ""

        try:
            # Try to decode using email.header.decode_header
            decoded_parts = decode_header(header)
            result = ""

            for decoded_text, charset in decoded_parts:
                # If it's bytes, decode with the correct encoding or fallback
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
                                # Fallback to latin-1 (always works)
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
        """Main run loop - checks emails periodically.

        This method runs continuously until self.running is set to False.
        It checks for new emails based on check_interval or when force_check
        is True.
        """
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
