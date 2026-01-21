#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Snooze state management for Gmail Notifier.

This module provides the SnoozeManager class for managing notification
snooze state with automatic expiration.
"""

import time


class SnoozeManager:
    """Manages notification snooze state.

    Provides methods to snooze, unsnooze, and check snooze status.
    Snooze automatically expires after the configured duration.

    Attributes:
        snoozed_until: Timestamp when snooze expires, or None if not snoozed.
    """

    SNOOZE_DURATION = 3600  # 1 hour in seconds

    def __init__(self):
        """Initialize the snooze manager with no active snooze."""
        self.snoozed_until = None

    def is_snoozed(self):
        """Check if notifications are currently snoozed.

        Automatically clears expired snooze state.

        Returns:
            bool: True if snoozed and snooze hasn't expired.
        """
        if self.snoozed_until is None:
            return False
        if time.time() >= self.snoozed_until:
            # Snooze expired, reset state
            self.snoozed_until = None
            return False
        return True

    def snooze(self):
        """Activate snooze for the configured duration (1 hour)."""
        self.snoozed_until = time.time() + self.SNOOZE_DURATION

    def unsnooze(self):
        """Deactivate snooze immediately."""
        self.snoozed_until = None

    def toggle(self):
        """Toggle snooze state.

        If currently snoozed, unsnoozes. If not snoozed, snoozes.

        Returns:
            bool: True if now snoozed, False if now unsnoozed.
        """
        if self.is_snoozed():
            self.unsnooze()
            return False
        else:
            self.snooze()
            return True

    def get_remaining_time(self):
        """Get remaining snooze time in seconds.

        Returns:
            int: Seconds remaining, or 0 if not snoozed.
        """
        if not self.is_snoozed():
            return 0
        return max(0, int(self.snoozed_until - time.time()))
