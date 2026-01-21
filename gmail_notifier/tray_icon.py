#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tray icon utilities for Gmail Notifier.

This module provides functions for loading the Gmail icon and
creating badge overlays for different states (unread, snoozed, error).
"""

import os

from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QIcon, QColor, QFont, QPainter, QPixmap

from gmail_notifier.config import ICON_PATH

# Opacity for snoozed state (0.0 = invisible, 1.0 = fully visible)
SNOOZE_OPACITY = 0.35


# Fallback paths where Gmail icon might be installed on the system
GMAIL_ICON_FALLBACK_PATHS = [
    "/usr/share/icons/hicolor/scalable/apps/gmail.svg",
    "/usr/share/icons/hicolor/48x48/apps/gmail.png",
    "/usr/share/icons/breeze/apps/48/gmail.svg",
    "/usr/share/pixmaps/gmail.png",
]


def get_gmail_icon():
    """Find Gmail icon, preferring local config dir icon.

    Search order:
    1. Local icon in ~/.config/gmail-notifier/gmail.png (installed by installer)
    2. System-installed Gmail icons
    3. Fallback to system 'mail-unread' theme icon

    Returns:
        QIcon: Gmail icon or fallback mail-unread theme icon.
    """
    # First, check local config directory (installed by our installer)
    if os.path.exists(ICON_PATH):
        return QIcon(ICON_PATH)

    # Then check system paths
    for path in GMAIL_ICON_FALLBACK_PATHS:
        if os.path.exists(path):
            return QIcon(path)

    # If the icon is not found anywhere, use a system theme icon
    return QIcon.fromTheme("mail-unread")


def create_badge_icon(base_icon, has_unread=False, is_snoozed=False, is_error=False):
    """Create icon with badge overlay.

    Badge priority: error (!) > snoozed (faded + Z) > unread (red dot)

    When snoozed, the icon is faded to indicate inactive state.
    If no badge state is active, returns the base icon unchanged.

    Args:
        base_icon: Base QIcon to add badge to.
        has_unread: Show red dot for unread emails.
        is_snoozed: Fade icon and show "Z" for snoozed state.
        is_error: Show "!" for error state.

    Returns:
        QIcon: Icon with appropriate badge, or base_icon if no badge needed.
    """
    # If no interesting state, return base icon
    if not has_unread and not is_snoozed and not is_error:
        return base_icon

    # Create a pixmap from the icon
    # Size 64x64 provides enough resolution for most trays
    pixmap = base_icon.pixmap(64, 64)
    if pixmap.isNull():
        return base_icon

    # For snoozed state, create a faded version of the icon
    if is_snoozed:
        pixmap = _create_faded_pixmap(pixmap, SNOOZE_OPACITY)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    if is_error:
        _draw_error_badge(painter, pixmap)
    elif is_snoozed:
        _draw_snooze_badge(painter, pixmap)
    elif has_unread:
        _draw_unread_badge(painter, pixmap)

    painter.end()

    return QIcon(pixmap)


def _create_faded_pixmap(pixmap, opacity):
    """Create a faded version of a pixmap.

    Args:
        pixmap: Original QPixmap.
        opacity: Opacity value (0.0 = invisible, 1.0 = fully visible).

    Returns:
        QPixmap: Faded pixmap.
    """
    # Create a new transparent pixmap
    faded = QPixmap(pixmap.size())
    faded.fill(Qt.transparent)

    # Draw the original pixmap with reduced opacity
    painter = QPainter(faded)
    painter.setOpacity(opacity)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()

    return faded


def _draw_error_badge(painter, pixmap):
    """Draw orange circle with '!' for error state.

    Args:
        painter: Active QPainter on the pixmap.
        pixmap: The pixmap being painted on.
    """
    # Orange circle background
    painter.setBrush(QColor("#ff9800"))  # Material Orange
    painter.setPen(Qt.NoPen)
    dot_size = 24
    # Position at bottom-right
    painter.drawEllipse(pixmap.width() - dot_size - 2, pixmap.height() - dot_size - 2, dot_size, dot_size)

    # White exclamation mark
    painter.setPen(QColor("white"))
    font = QFont()
    font.setPixelSize(18)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(
        QRect(pixmap.width() - dot_size - 2, pixmap.height() - dot_size - 2, dot_size, dot_size),
        Qt.AlignCenter,
        "!",
    )


def _draw_snooze_badge(painter, pixmap):
    """Draw blue 'Z' for snoozed state.

    Args:
        painter: Active QPainter on the pixmap.
        pixmap: The pixmap being painted on.
    """
    painter.setPen(QColor("#4da6ff"))  # Blue color
    font = QFont()
    font.setPixelSize(28)
    font.setBold(True)
    painter.setFont(font)
    # Draw at bottom right
    painter.drawText(
        pixmap.rect().adjusted(0, 5, -4, 0), Qt.AlignRight | Qt.AlignBottom, "Z"
    )


def _draw_unread_badge(painter, pixmap):
    """Draw KDE blue dot for unread emails.

    Args:
        painter: Active QPainter on the pixmap.
        pixmap: The pixmap being painted on.
    """
    dot_size = 20  # Relative to 64x64
    painter.setBrush(QColor("#1D99F3"))  # KDE Blue
    painter.setPen(Qt.NoPen)
    # Position at bottom-right
    painter.drawEllipse(pixmap.width() - dot_size - 2, pixmap.height() - dot_size - 2, dot_size, dot_size)
