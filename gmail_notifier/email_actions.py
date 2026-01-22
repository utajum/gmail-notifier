#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Email IMAP actions for Gmail Notifier.

This module provides functions for performing IMAP operations on emails,
such as deleting emails by moving them to the Gmail Trash folder.
"""

import imaplib


def delete_emails_imap(username, password, email_ids):
    """Delete emails by moving to Gmail Trash via IMAP.

    This function runs synchronously - caller should run in a thread
    to avoid blocking the UI.

    For Gmail, the proper way to delete is:
    1. Use UID to identify messages (stable across mailbox changes)
    2. Copy the message to [Gmail]/Trash using UID
    3. Mark the original as deleted using UID
    4. Expunge to remove from inbox

    Args:
        username: Gmail username/email address.
        password: Gmail app password.
        email_ids: List of email UID strings to delete.

    Raises:
        Exception: On IMAP connection or operation failure.
    """
    if not username or not password:
        return

    if not email_ids:
        return

    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    try:
        mail.login(username, password)
        mail.select("inbox")

        # Delete all emails in the list using UID commands
        for eid in email_ids:
            msg_uid = eid.encode() if isinstance(eid, str) else eid

            # Use UID commands to ensure we're targeting the correct email
            # even if the mailbox changes in the background
            copy_result = mail.uid("copy", msg_uid, "[Gmail]/Trash")
            if copy_result[0] == "OK":
                mail.uid("store", msg_uid, "+FLAGS", "\\Deleted")

        # Expunge all deleted emails at once
        mail.expunge()

        mail.close()
        mail.logout()
    except Exception:
        # Try to clean up connection on error
        try:
            mail.logout()
        except Exception:
            pass
        raise
