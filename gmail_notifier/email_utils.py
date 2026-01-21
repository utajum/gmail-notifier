#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Email data transformation utilities for Gmail Notifier.

This module provides pure functions for processing email data:
- Deduplication by email ID
- Grouping emails by thread for display
"""


def dedup_emails(emails):
    """Remove duplicate emails by ID and sort by timestamp.

    Args:
        emails: List of email dicts with 'id' and 'timestamp' keys.

    Returns:
        list: Deduplicated emails sorted newest first.
    """
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


def group_by_thread(emails):
    """Group emails by thread ID for display.

    Returns list of emails where each entry represents a thread:
    - Uses the newest email's data (sender, subject, link, etc.)
    - Adds 'thread_count' field with number of unread emails in thread
    - Sorted by newest email timestamp (newest thread first)

    Args:
        emails: List of email dicts with 'thread_id', 'id', 'timestamp' keys.

    Returns:
        list: One entry per thread with 'thread_count' field added.
              Sorted by newest email timestamp (newest thread first).
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


def find_thread_email_ids(emails, email_id):
    """Find all email IDs belonging to the same thread as the given email.

    Args:
        emails: List of all email dicts.
        email_id: ID of an email in the thread.

    Returns:
        list: List of email ID strings in the same thread.
    """
    # Find the thread_id for this email
    thread_id = None
    for e in emails:
        if str(e.get("id")) == str(email_id):
            thread_id = e.get("thread_id")
            break

    # Get all email IDs in this thread
    if thread_id:
        return [str(e.get("id")) for e in emails if e.get("thread_id") == thread_id]
    else:
        # No thread_id, just return the single email
        return [str(email_id)]


def remove_emails_by_ids(emails, email_ids_to_remove):
    """Remove emails with matching IDs from the list.

    Args:
        emails: List of email dicts.
        email_ids_to_remove: List/set of email ID strings to remove.

    Returns:
        list: Filtered list without the specified emails.
    """
    ids_set = set(str(eid) for eid in email_ids_to_remove)
    return [e for e in emails if str(e.get("id")) not in ids_set]
