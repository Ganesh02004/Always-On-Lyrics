# 🚀 Release Notes - v1.0.0 (Official Public Release)

We are thrilled to present the first stable public release of the **Always-On Lyrics Overlay for Windows**! This release marks a major milestone, transforming a simple track monitor into a premium, custom-configurable, double-language, high-performance visual widget.

---

## 🌟 Key Release Highlights

### 1. 🎤 Visual Draggable Layout
* The overlay is now fully interactive! Uncheck "Click-Through Mode" (`Ctrl+Shift+C`) and **drag the lyrics overlay anywhere on your desktop**.
* **Memory Slots**: Window coordinates `(x, y)` are saved automatically on mouse release and restored on next launch.
* **Layout Reset**: Restores default bottom-center anchoring in one click from the Settings panel.

### 2. 🔀 background English Translation Sync
* Automatic real-time translation pre-fetch via the Google Translate API.
* Foreign lyrics (Korean, Japanese, etc.) display the original line on top and the English translation directly below, fading in/out seamlessly.
* Smart filtering suppresses redundant displays on tracks already in English.

### 🎧 3. Multi-Channel Stream Priority Dropdown
* Scanning and tracking of all active system audio channels concurrently.
* Dynamically populates a prioritized dropdown in Settings so you can choose exactly which media player to track, falling back automatically to the Windows default active player if closed or idle.

### ⌨️ 4. Dynamic Keyboard Hotkeys Re-Binding
* All global hotkeys can now be customized directly inside Settings!
* Re-binding dynamically halts the active Win32 thread, clears Win32 shortcut hooks, registers the new custom keystroke combos, and restarts the background key listener thread instantly.

### 📦 5. Native Windows Setup Installer
* Added double-clickable `install.bat` and PowerShell `install.ps1` setup installer.
* Copies the app structure under local AppData, creates shortcuts, and registers standard registry strings for full Windows **Apps & Features Add or Remove Programs** uninstaller support.

---

## 🛠️ Architectural Quality & Stability Fixes
* **Visual Freeze Lock Fix**: Rewrote visual transitions in `overlay_window.py` to use a state-based flag (`_is_fading_out`) and coalescing guards, preventing animation restart deadlocks under high-frequency polling.
* **Win32 Window Positioning**: Exchanged `screen.geometry()` for `screen.availableGeometry()`, preventing taskbar overlaps. Removed broken sub-window window flags to resolve random position snapping.
* **WinRT Collections Dependency**: Bundled `winrt-Windows.Foundation.Collections` explicitly, eliminating COM collections iteration crashes on dynamic channels scanning.
* **Unicode/Emoji Logging Safety**: Reconfigured stream logging to UTF-8 with unencodable character fallback replacement, resolving silent load crashes on foreign tracks (e.g. Korean character sets).

---

## 📂 Repository Contents Catalog
* 📂 **`dist\LyricsOverlay.exe`** — The compiled standalone windowed application.
* 📄 **`install.ps1`** / **`install.bat`** — Standard double-clickable native Windows setup installer.
* 📄 **`README.md`** — Comprehensive user instructions, shortcut tables, and build-from-source guides.
* 📄 **`LICENSE`** — Permissive **MIT License** for open-source releases.
* 📄 **`.gitignore`** — Standard version control filter ignoring build/dist and caches.
* 📄 **`requirements.txt`** — Core package dependencies catalog.
* 📄 **`config.example.json`** — Template configuration demonstrating all layout, styling, and hotkey fields.
* 📄 **`build.py`** — Fast PyInstaller compiler script.
