#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Configuration management for Gmail Notifier.

This module handles settings persistence, including loading/saving
configuration from JSON files and securely storing passwords in the
system keyring.
"""

import os
import json
import keyring

# Configuration paths
CONFIG_DIR = os.path.expanduser("~/.config/gmail-notifier")
SETTINGS_PATH = os.path.join(CONFIG_DIR, "settings.json")
ICON_PATH = os.path.join(CONFIG_DIR, "gmail.png")

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


def load_settings():
    """Load settings from the configuration file.

    Returns:
        dict: Settings dictionary with all configuration values.
              Password is retrieved from the system keyring if username exists.
    """
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "r") as f:
            try:
                settings = json.load(f)
            except (json.JSONDecodeError, ValueError):
                print("Settings file corrupted. Loading defaults.")
                return DEFAULT_SETTINGS.copy()

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
    return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    """Save settings to the configuration file.

    Note:
        Password is NOT saved to the JSON file for security.
        It should be stored separately in the system keyring.

    Args:
        settings: Dictionary containing configuration values.
    """
    # Create a copy to avoid modifying the original
    settings_to_save = settings.copy()
    # Don't save password in the json file
    if "password" in settings_to_save:
        del settings_to_save["password"]

    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings_to_save, f, indent=4)
