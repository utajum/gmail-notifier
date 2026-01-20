# Gmail Notifier for KDE

<div align="center">
  <img src="https://avatars.githubusercontent.com/u/83629496?v=4" alt="Gmail Notifier Logo" width="120px" style="border-radius: 10px;"/>
  <br><br>
  <p>
    <img src="https://img.shields.io/badge/KDE-1D99F3?style=for-the-badge&logo=kde&logoColor=white" alt="KDE"/>
    <img src="https://img.shields.io/badge/Ubuntu-E95420?style=for-the-badge&logo=ubuntu&logoColor=white" alt="Ubuntu"/>
    <img src="https://img.shields.io/badge/Arch_Linux-1793D1?style=for-the-badge&logo=arch-linux&logoColor=white" alt="Arch Linux"/>
    <img src="https://img.shields.io/badge/Gmail-D14836?style=for-the-badge&logo=gmail&logoColor=white" alt="Gmail"/>
    <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  </p>
</div>

## 📋 Description

**Gmail Notifier** is a lightweight tool for monitoring Google Workspace email accounts without needing to have an email client open. It runs in the background to show notifications in the KDE system tray when new emails arrive.

<div align="center">
  <p style="font-style: italic;">Stay up-to-date with your important emails without interrupting your workflow.</p>
</div>

## ✨ Key Features

- 🔔 **Dual notification system**: both tray icon popups and system notifications (via `notify-send`)
- 🚀 **Lightweight and efficient**: uses minimal system resources
- 🔐 **Secure authentication** using app passwords
- 🔑 **Secure password storage**: uses system keyring instead of file-based encryption
- 🔄 **Periodic checking** for new emails
- 📱 **Quick access** to Gmail with a double-click
- 📋 **Recent Email List**: Single-click to see a themed popup list of the latest emails
- 🔗 **Direct Email Linking**: Click any email in the list to open it directly in your browser
- 🔧 **Seamless integration** with KDE and other desktop environments
- 🧪 **Test notification button**: verify notifications work on your system from the config dialog
- 📋 **Start menu integration**: launcher icon in your applications menu
- 🐧 **Multi-distro support**: works on Ubuntu/Debian and Arch Linux

## 🖥️ Screenshots

<div align="center">
  <table>
    <tr>
      <td align="center"><strong>Notification in the system tray</strong></td>
      <td align="center"><strong>Account configuration</strong></td>
    </tr>
    <tr>
      <td><img src="screenshots/notification.png?other=true" alt="Notifications" width="400px"/></td>
      <td><img src="screenshots/config.png?other=true" alt="Configuration" width="400px"/></td>
    </tr>
    <tr>
      <td align="center"><strong>Recent Emails Popup (Dark Theme)</strong></td>
      <td align="center"><strong>System Tray Badge (Unread)</strong></td>
    </tr>
    <tr>
      <td><img src="screenshots/unread-emails.png?other=true" alt="Unread Emails" width="400px"/></td>
      <td><img src="screenshots/systray.png?other=true" alt="System Tray" width="400px"/></td>
    </tr>
    <tr>
      <td align="center"><strong>Context Menu</strong></td>
      <td align="center"><strong>Snooze Badge (Z)</strong></td>
    </tr>
    <tr>
      <td><img src="screenshots/right-click.png?other=true" alt="Right Click" width="400px"/></td>
      <td><img src="screenshots/snooze.png?other=true" alt="Snooze Badge" width="400px"/></td>
    </tr>
    <tr>
      <td align="center"><strong>Delete Email Confirmation</strong></td>
      <td></td>
    </tr>
    <tr>
      <td><img src="screenshots/delete-email.png?other=true" alt="Delete Confirmation" width="400px"/></td>
      <td></td>
    </tr>

  </table>
</div>

## 🔧 Requirements

- **Linux**: Ubuntu/Debian or Arch Linux (or derivatives)
- **KDE Plasma** 5.x or higher (other desktop environments may work)
- **Python** 3.6 or higher
- **pip** and **virtualenv**
- **PyQt5**
- **Google Workspace** or **Gmail** account
- **Two-step verification** enabled in your Google account

## 📦 Installation

### 1. Clone the repository

```bash
git clone https://github.com/utajum/gmail-notifier.git
cd gmail-notifier
```

### 2. Run the installer

```bash
chmod +x installer-script.sh
./installer-script.sh
```

The installer will:
1. Check and install the necessary dependencies
2. Create a virtual environment for the required Python libraries
3. Configure automatic startup with your KDE session
4. Install the script and configuration files

### 3. Create an app password for Gmail

To use Gmail Notifier, you need to create a specific app password:

1. Go to your [Google account security settings](https://myaccount.google.com/security)
2. Make sure you have "Two-step verification" enabled ([see instructions](https://support.google.com/mail/answer/185833?hl=en))
3. Look for "App passwords" and click on it
4. Select "Mail" as the app and "Other (custom name)" as the device
5. Type "Gmail Notifier" as the name and click "Generate"
6. Google will show a 16-character password - copy it (you will need it to configure Gmail Notifier)

<div align="center">
  <img src="screenshots/app-password.png" alt="App password" width="500px"/>
</div>

### 4. Configure Gmail Notifier

When you start Gmail Notifier for the first time, the configuration window will open automatically:

1. Enter your Gmail email address
2. Paste the app password you generated earlier
3. Adjust the check interval if you wish (default: 5 minutes)
4. Click "Test Connection" to verify that everything is working correctly
5. Click "Test Notification" to verify notifications display properly on your system
6. Save the configuration

Gmail Notifier will start working immediately and an icon will appear in the system tray.

## 🚀 Usage

- **Single-click** on the icon: Opens a dark-themed popup showing your recent unread emails.
  - **Click an email**: Opens that specific email thread in your browser.
  - **Click Trash icon**: Moves the email to Gmail's Trash (after confirmation).
  - **Open Gmail Inbox**: Link at the top opens your full inbox.
- **Double-click** on the icon: Instantly opens Gmail Inbox in your default browser.
- **Right-click** on the icon: Shows a menu with options
  - **Open Gmail**: Opens Gmail in your browser
  - **Check now**: Forces an immediate check for new emails
  - **Settings**: Opens the configuration dialog
  - **Exit**: Closes the application

## ⚙️ Custom configuration

You can reconfigure Gmail Notifier at any time by right-clicking the system tray icon and selecting "Settings".

From the configuration dialog you can:
- Change the Gmail account
- Update the app password
- Modify the check interval
- Enable/disable automatic startup
- Test notifications to verify they work on your system

## 🗑️ Uninstallation

If you want to uninstall Gmail Notifier, run:

```bash
./installer-script.sh --remove
```

This will remove all files and settings related to Gmail Notifier.

## 🔍 Troubleshooting

### I'm not receiving notifications for new emails
- Verify that the connection has been established correctly in the settings
- Make sure the app password is correct
- Check that you don't have filters in Gmail that automatically mark emails as read

### Authentication error
- Make sure you are using an app password, not your main Google password
- Verify that you have correctly enabled two-step verification
- Generate a new app password and try again

### The icon does not appear in the system tray
- Verify that your KDE panel has the system tray applet enabled
- Run `gmail-notifier` from the terminal to see possible errors

### "externally-managed-environment" error
- The installer creates a virtual environment to avoid this problem
- If it persists, delete the environment and run the installer again

## 🛠️ Development

This is a fork of the original project, intended for further development and feature additions.

### Changes in this fork

- **Multi-distro support**: Added Ubuntu/Debian support alongside Arch Linux
- **Secure password storage**: Migrated from simple file encryption to system keyring
- **Dual notifications**: Added system notifications via `notify-send` in addition to tray popups
- **Test notification button**: Added ability to test notifications from the config dialog
- **Start menu integration**: Installs a .desktop file in the applications menu
- **English translation**: Translated UI and installer from Spanish to English
- **Code cleanup**: Reformatted code and improved structure
- **Clickable Notifications**: Notifications are now clickable and open Gmail directly.
- **Improved Email Checking**: More efficient email fetching, limited to the last 24 hours.
- **Responsive "Check Now"**: The "Check Now" feature is significantly more responsive.
- **Smart Notification Grouping**: Prevents duplicate notifications and groups multiple new emails into a summary notification.
- **Snooze Functionality**:
  - **Snooze state tracking**: Tracks when the snooze expires (for 1 hour).
  - **Tray menu snooze option**: Added "Snooze for 1 hour" menu item (toggles to "Unsnooze" when active), with tooltip indicating snooze status.
  - **System notification snooze action**: Notifications now include "Snooze 1 hour" button that activates a 1-hour snooze.
  - **Visual Snooze Indicator**: A blue "Z" badge appears on the tray icon when snooze is active.
- **Email List Popup**: Added a sleek, dark-themed popup that displays the latest received emails on a single click.
  - **Quick Delete**: Each email in the list features a trash icon to move the message directly to Gmail's Trash folder.
  - **Click-to-Open**: Clicking anywhere else on the email opens the specific message thread in your web browser.
- **Thread ID Fetching**: Now fetches Gmail Thread IDs to allow opening specific conversations directly from the email list.
- **Double-Click Interaction**: Implemented custom click differentiation for single and double-click actions on the tray icon.
- **Visual Status Badge**: System tray icon now displays a red dot badge when unread emails are present.
- **Immediate Startup Check**: Added a forced email check upon application launch for instant updates.
- **Connection Error Indicator**: Displays an orange "!" badge on the tray icon if connection or credentials fail.



### Project structure
```
gmail-notifier/
├── gmail-notifier.py    # Main script
├── installer-script.sh  # Installer/uninstaller
├── README.md            # Documentation
└── screenshots/         # Screenshots for documentation
```

## 📄 License

This project is under the Creative Commons Attribution 4.0 International (CC BY 4.0) license.

<a rel="license" href="http://creativecommons.org/licenses/by/4.0/">
  <img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by/4.0/88x31.png" />
</a>

## 👨‍💻 Authors

**Maintained and Enhanced by:**

*   **utajum (utajum macedonia)** - [GitHub](https://github.com/utajum)

**Original Author:**

*   **P4NX0S** - [GitHub](https://github.com/panxos)

---

<div align="center">
  <p>
    <sub>This is a fork from the original project. You can find the original project <a href="https://github.com/panxos/gmail-notifier">here</a>.</sub>
  </p>
  <p>
    <sub>👨‍💻 Maintained and Enhanced by <b>utajum macedonia</b> (forked from P4NX0S © 2025)</sub>
  </p>
</div>
