# 🤝 Contributing to Always-On Lyrics Overlay

We love contribution! If you want to contribute to the project, here is a quick guide on how you can help:

---

## 🛠️ Developer Setup

1. Fork and clone the repository.
2. Setup your virtual environment:
   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Run the app in development mode from source:
   ```cmd
   python src/main.py
   ```
4. Build and compile the standalone executable using our compilation tool:
   ```cmd
   python build.py
   ```

---

## 📜 Development Guidelines

- **Maintain Documentation Integrity**: Update `README.md` or `RELEASE_NOTES.md` if your pull request introduces new features, config fields, or hotkeys.
- **Transitive Imports Safety**: If you import a new WinRT package module, ensure it is explicitly imported in `src/media_tracker.py` or another core file so that PyInstaller's analyzer successfully packages it inside the standalone executable.
- **Thread Safety**: The media poller and key listeners run in background threads. Ensure all thread-to-thread communication (e.g. updating the UI from background events) is dispatched via native **Qt Signals and Slots**, preserving the PySide6 event loop architecture.
- **Safe Encoding**: Always use `encoding="utf-8"` on all file read/write operations to prevent CJK or emoji character crashes.

---

## 🐞 Submitting Issues & PRs

- **Bug Reports**: Open an issue detailing your system OS, media player source (e.g. Spotify app, Chrome YouTube, VLC), step-by-step reproduction guide, and attach your local `~/.lyrics_overlay.log` output.
- **Pull Requests**: Create a feature branch, commit with clean concise messages, and submit a PR to our main branch. We review all submissions!
