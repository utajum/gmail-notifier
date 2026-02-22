#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gmail Notifier - Entry point script.

This is a thin wrapper that imports and runs the main application
from the gmail_notifier package.

Usage:
    ./gmail-notifier.py
    python gmail-notifier.py
    python -m gmail_notifier
"""

from gmail_notifier.__main__ import main

if __name__ == "__main__":
    main()
