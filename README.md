# 🎵 Always-On Lyrics Overlay for Windows

A gorgeous, high-performance, borderless, transparent **Always-On-Top Lyrics Overlay App** for Windows. It integrates with Windows System Media Transport Controls (SMTC) using WinRT to detect playing music in real-time, retrieves synced lyrics via the open-source **LRCLIB API**, and overlays them as sleek, subtitle-like text anywhere on your screen.

---

## ✨ Features

- 🎤 **Perfect Real-Time Sync**: Smoothly interpolates and ticks lyrics every 100ms based on wall-clock time alignment to match the audio player seamlessly.
- 🔀 **English Translation Sync**: Batch-translates foreign lyrics (Korean, Japanese, Spanish, etc.) in the background when a song loads and renders the translation synchronized directly below the original line.
- 🖱️ **Fully Draggable Widget**: Drag and drop the overlay anywhere on your screen when click-through is disabled. Position is saved and restored automatically on next restart!
- 🎧 **Multi-Channel Media Selector**: Prioritize your media stream! If you have multiple apps playing (e.g. Spotify and YouTube in Chrome), select your preferred source from a real-time Settings dropdown, falling back automatically to the Windows default session if closed.
- 🔒 **Click-Through Mode**: Lock the overlay in place! It ignores all mouse clicks, letting you play full-screen games or work seamlessly underneath it.
- ⌨️ **Dynamic Custom Hotkeys**: Re-bind key shortcuts directly inside settings. Unregisters old bindings and registers new ones instantly in a dedicated Win32 thread.
- 🎨 **Premium Glassmorphic Styling**: Customize font family (searches system libraries), active lyric color, shadow intensity, panel size, padding, and background opacity in real-time.
- ⚙️ **Linear Fallback for Plain Lyrics**: If time-coded lyrics aren't available, static lyrics automatically scroll linearly across the song's duration.
- 🚀 **Windows Startup Integration**: Toggle auto-launch directly inside the Settings control panel.
- 📦 **Standard Installer**: Double-click `install.bat` to deploy the app, create Desktop/Start Menu shortcuts, and register a fully-compliant uninstaller directly inside Windows **Apps & Features** settings.

---

## ⌨️ Default Keyboard Shortcuts

| Hotkey | Action | Purpose |
| :--- | :--- | :--- |
| **`Ctrl + Shift + L`** | **Toggle Visibility** | Instantly show or hide the overlay window. |
| **`Ctrl + Shift + C`** | **Toggle Click-Through** | Disables click-through to **drag/position overlay**, or enables it to lock it in place. |
| **`Ctrl + Shift + T`** | **Toggle Translation** | Enables or disables English translation subtitles on foreign songs. |
| **`Ctrl + Shift + Up`** | **Increase Font Size** | Boosts overlay text size globally (+2px steps). |
| **`Ctrl + Shift + Down`** | **Decrease Font Size** | Shrinks overlay text size globally (-2px steps). |

---

## 🚀 Installation

1. Double-click on **`install.bat`** in the release directory.
2. The installation wizard will deploy the application to your `%LocalAppData%` directory, create standard shortcuts on your **Desktop** and **Start Menu**, and register the uninstaller in Windows settings.
3. Start the application! A beautiful circular teal double-note badge (**♫**) will appear in your **System Tray** (near the clock).
4. Play music anywhere on your system!
   - Open **Spotify** and play a song.
   - Or open **YouTube** in Google Chrome or Edge.
   - Or play a video in **VLC** or **Apple Music**.
5. The overlay will fade in at the bottom center of your screen and sync up!
6. **To Customize**: Double-click the tray icon (or right-click and select **Settings...**) to open the configuration panel.

---

## 🔧 Building From Source

### Prerequisites
- Windows 10 or 11
- Python 3.10+

### Step-by-Step Build
1. Clone the repository and navigate into it:
   ```cmd
   git clone https://github.com/yourusername/lyrics-overlay.git
   cd lyrics-overlay
   ```
2. Create and activate a Python virtual environment:
   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. Install dependencies:
   ```cmd
   pip install -r requirements.txt
   ```
4. Run the application from source:
   ```cmd
   python src/main.py
   ```
5. Compile into a single-file standalone windowed `.exe` executable:
   ```cmd
   python build.py
   ```
   The compiled standalone app will be outputted to **`dist/LyricsOverlay.exe`**.

---

## 🛠️ Troubleshooting & Configuration

- **Lyrics Overlay Stays Stuck or Doesn't Update**:
  This happens if a high-frequency polling thread locks. Ensure you are using the latest version which uses state-based transition coalescing.
- **I Cannot Click on anything behind the Lyrics**:
  Press **`Ctrl + Shift + C`** (or right-click the system tray icon and check **Click-Through Mode**). This locks the overlay, ignoring all mouse inputs and piping clicks straight through to the windows underneath.
- **I Cannot Drag the lyrics overlay**:
  Press **`Ctrl + Shift + C`** to *disable* click-through mode. Once disabled, you can hover, click, and drag the lyrics overlay anywhere. When finished, press `Ctrl + Shift + C` again to lock it in place.
- **Korean/Emoji Lyrics show as squares or crash**:
  The application utilizes a custom UTF-8 logging stream reconfigure safety handler. Ensure your chosen font in the Settings panel supports CJK character sets (e.g. *Segoe UI*, *Malgun Gothic*, or *Microsoft YaHei*).
- **Configuration Path**:
  Your layout, preferences, and custom hotkeys are saved on disk under:
  `C:\Users\<YourUsername>\.lyrics_overlay_config.json`
- **Lyrics Cache Directory**:
  Lyrics are cached locally in JSON format to enable offline instant loads and avoid spamming LRCLIB API:
  `C:\Users\<YourUsername>\.lyrics_overlay_cache\`
- **System Logs**:
  Standard logging output is written to:
  `C:\Users\<YourUsername>\.lyrics_overlay.log`

---

## 📄 License

This project is licensed under the permissive **MIT License** - see the [LICENSE](LICENSE) file for details.
