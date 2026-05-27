# 🎵 Always-On Lyrics Overlay for Windows
### Quick Start & User Guide

Welcome to the **Always-On Lyrics Overlay**! This guide will help you set up and use the application on your Windows laptop in less than 2 minutes.

---

## 🚀 1-Minute Quick Start

If your friend sent you the standalone file (**`LyricsOverlay.exe`**), follow these simple steps to get started:

1. **Move the File**: Drag and copy the **`LyricsOverlay.exe`** file to a folder where you won't accidentally delete it (for example: `C:\Users\<YourUsername>\Documents` or a dedicated folder).
2. **Run the App**: Double-click **`LyricsOverlay.exe`**.
   - *Note: On the very first run, Windows SmartScreen might show a warning ("Windows protected your PC") because the app is a newly compiled standalone executable. Simply click **"More info"** and then **"Run anyway"**.*
3. **Play Music**: Open **Spotify**, **YouTube** (in Chrome/Edge/Firefox), **VLC**, or any other music player and play a song!
4. **Enjoy**: The lyrics will automatically fade in on your screen, fully synchronized to your song in real time!

> [!TIP]
> **Using the Setup Installer**:
> If you have a zip file containing `install.bat` and `install.ps1`, you can double-click **`install.bat`**! This installs the app cleanly under your user folder, creates a **Desktop Shortcut** and a **Start Menu Shortcut**, and registers it under standard **Windows Add/Remove Programs** so you can uninstall it easily later.

---

## ⌨️ Useful Keyboard Shortcuts

These global shortcuts work from anywhere (even when you are in a full-screen game, browser, or document):

| Keyboard Shortcut | Action | What it does |
| :--- | :--- | :--- |
| **`Ctrl + Shift + L`** | **Show/Hide Overlay** | Instantly toggles the lyrics display on or off. |
| **`Ctrl + Shift + C`** | **Toggle Click-Through** | **Disable Click-Through** to drag the lyrics to a new position.<br>**Enable Click-Through** to lock the overlay and click through it! |
| **`Ctrl + Shift + T`** | **Toggle Translation** | Toggles English subtitles on/off for non-English songs (Korean, Spanish, etc.). |
| **`Ctrl + Shift + Up`** | **Increase Font Size** | Boosts the text size by 2px steps. |
| **`Ctrl + Shift + Down`** | **Decrease Font Size** | Shrinks the text size by 2px steps. |

---

## 🖱️ Dragging & Repositioning the Lyrics

To move the lyrics overlay anywhere on your screen:

1. Press **`Ctrl + Shift + C`** to turn **Click-Through Mode OFF**.
2. Hover your mouse cursor over the lyrics. You will see a subtle background panel outline appear.
3. **Click and drag** the overlay anywhere on your screen.
4. Release the mouse button. The position is **automatically saved**!
5. Press **`Ctrl + Shift + C`** to turn **Click-Through Mode ON** again. The overlay is now locked in place, and your mouse clicks will pass right through it, letting you use your laptop normally.

---

## ⚙️ Customizing the Settings

You can customize almost everything to fit your screen aesthetics:

1. Locate the **circular teal musical note badge (♫)** in your Windows system tray (bottom-right of your taskbar, next to the clock/Wi-Fi icons).
2. **Double-click** the icon (or right-click and select **Settings...**).
3. The Settings Panel lets you:
   - Choose a custom **Font Family** installed on your laptop.
   - Adjust **Active/Upcoming Lyrics Colors** and font size.
   - Adjust **Background Box Opacity** and drop shadows.
   - Enable **Windows Auto-Startup** (runs the app when your laptop turns on).
   - Set **Preferred Media Source** (e.g., prioritize Spotify if you have both Spotify and YouTube playing).
   - Edit and customize your **Keyboard Hotkeys**.
   - **Reset Layout** if you ever drag the overlay off-screen.

---

## 🔍 Troubleshooting Guide

* **The overlay is not appearing / stays on "Listening for media..."**:
  Make sure you are playing music on a supported app (Spotify, YouTube in Chrome/Edge, VLC, Apple Music, etc.). Sometimes Windows SMTC needs a moment to register a browser tab. Pause and resume the song once to force a refresh.
* **I cannot click on folders or buttons behind the lyrics**:
  Press **`Ctrl + Shift + C`** to lock the overlay into Click-Through Mode. When click-through is enabled, the overlay ignores the mouse completely.
* **The lyrics are in another language and I want to understand them**:
  Make sure Translation is enabled in settings or press **`Ctrl + Shift + T`**. The app will automatically batch-translate the foreign lyrics (Korean, Japanese, Spanish, etc.) to English subtitles in the background!
* **Where are my settings stored?**
  Your layout positions and preferences are saved at `C:\Users\<YourUsername>\.lyrics_overlay_config.json`. You can delete this file to reset the app to factory defaults.
