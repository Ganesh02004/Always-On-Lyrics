import sys
import os
import asyncio
import threading
import time
from PySide6.QtCore import QObject, Signal, Slot, Qt, QTimer
from PySide6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QFont
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu

# Import our custom modules
from utils import load_config, save_config, logger, setup_exception_hook
from media_tracker import MediaTracker
from lyrics_provider import LyricsProvider
from hotkey_manager import HotkeyManager
from overlay_window import OverlayWindow
from settings_window import SettingsWindow

# Initialize crash reporting hook
setup_exception_hook()

class LyricsAppController(QObject):
    # Signals for thread communications
    lyrics_fetched = Signal(str, str, dict) # title, artist, parsed_lyrics_dict
    fetch_failed = Signal(str, str, int)    # title, artist, retry_count

    def __init__(self, app_instance):
        super().__init__()
        self.app = app_instance
        self.config = load_config()
        
        # Initialize Core Services
        self.tracker = MediaTracker()
        self.tracker.preferred_source = self.config.get("preferred_media_source", "")
        
        self.provider = LyricsProvider()
        self.hotkeys = HotkeyManager()
        
        # Initialize UI Components
        self.overlay = OverlayWindow(self.config)
        self.settings = None
        self.tray = None
        
        # State management
        self.current_title = ""
        self.current_artist = ""
        self.current_album = ""
        self.current_duration = 0.0
        self.synced_lyrics = None
        self.static_lyrics = None
        self.static_translation = None
        self.is_instrumental = False
        self.sync_paused = False
        self.is_fetching = False
        self.app_status = "Initializing..."
        self.available_sources = []
        
        # Retry tracking
        self.retry_limit = 2
        self.current_retry_count = 0
        
        # Scroll browsing state initialization
        self.scroll_index = -1
        self.scroll_browsing_active = False
        self.scroll_resume_timer = QTimer(self)
        self.scroll_resume_timer.setSingleShot(True)
        self.scroll_resume_timer.setInterval(4000) # 4 seconds auto-resume
        self.scroll_resume_timer.timeout.connect(self.resume_live_sync)
        
        self._setup_connections()
        self._setup_tray()
        self._setup_hotkeys()
        
        logger.info("Application Controller successfully initialized.")

    def start(self):
        """Starts background tracking threads and displays the overlay."""
        logger.info("Starting background worker threads...")
        self.tracker.start()
        self.hotkeys.start()
        self.overlay.show()
        # Re-pin after show() so Win32 SetWindowPos fires with a valid HWND
        self.overlay._reposition()
        
        # Set listening status
        self.set_app_status("Listening for media...", "Play a song in Spotify, YouTube, VLC, etc. to begin")

    def _setup_connections(self):
        # Media Tracker -> Controller
        self.tracker.signals.track_changed.connect(self.on_track_changed)
        self.tracker.signals.playback_state_changed.connect(self.on_playback_state_changed)
        self.tracker.signals.position_changed.connect(self.on_position_changed)
        self.tracker.signals.duration_changed.connect(self.on_duration_changed)
        self.tracker.signals.session_status.connect(self.on_session_status_changed)
        self.tracker.signals.available_sources_changed.connect(self.on_available_sources_changed)
        
        # Overlay -> Controller
        self.overlay.position_dragged.connect(self.on_overlay_dragged)
        self.overlay.scrolled.connect(self.on_overlay_scrolled)
        self.overlay.size_changed_by_user.connect(self.on_overlay_resized)
        
        # Background fetch worker signals
        self.lyrics_fetched.connect(self.on_lyrics_ready)
        self.fetch_failed.connect(self.on_fetch_failed)
        
        # Hotkeys -> Controller
        self.hotkeys.signals.hotkey_pressed.connect(self.on_hotkey_pressed)

    def _setup_tray(self):
        """Initializes the persistent system tray icon with extensive status controls."""
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self._create_tray_icon())
        self.tray.setToolTip("Lyrics Overlay: Listening for media...")
        
        self.tray_menu = QMenu()
        
        # Status Item (Disabled clickable header showing what's happening)
        self.act_status = QAction("Status: Initializing...", self)
        self.act_status.setEnabled(False)
        self.tray_menu.addAction(self.act_status)
        
        self.tray_menu.addSeparator()
        
        # Toggle Overlay Action
        self.act_toggle = QAction("Hide Overlay", self)
        self.act_toggle.triggered.connect(self.toggle_overlay)
        self.tray_menu.addAction(self.act_toggle)
        
        # Re-sync Action
        act_resync = QAction("Restart Lyrics Sync", self)
        act_resync.triggered.connect(self.restart_sync)
        self.tray_menu.addAction(act_resync)
        
        # Settings Action
        act_settings = QAction("Settings...", self)
        act_settings.triggered.connect(self.show_settings)
        self.tray_menu.addAction(act_settings)
        
        # Click Through Toggle
        self.act_click = QAction("Click-Through Mode", self)
        self.act_click.setCheckable(True)
        self.act_click.setChecked(self.config.get("click_through", True))
        self.act_click.triggered.connect(self.toggle_click_through)
        self.tray_menu.addAction(self.act_click)
        
        self.tray_menu.addSeparator()
        
        # Exit Action
        act_exit = QAction("Exit App", self)
        act_exit.triggered.connect(self.quit_app)
        self.tray_menu.addAction(act_exit)
        
        self.tray.setContextMenu(self.tray_menu)
        self.tray.show()
        
        # Double click opens settings
        self.tray.activated.connect(self._on_tray_activated)
        logger.info("System Tray Icon initialized and displayed.")

    def _create_tray_icon(self) -> QIcon:
        """Generates a high-quality circular teal tray icon, saves to disk, and loads it for maximum Windows shell stability."""
        cache_dir = os.path.join(os.path.expanduser("~"), ".lyrics_overlay_cache")
        os.makedirs(cache_dir, exist_ok=True)
        icon_path = os.path.join(cache_dir, "tray_icon.png")
        
        try:
            pixmap = QPixmap(32, 32)
            pixmap.fill(QColor(0, 0, 0, 0)) # transparent
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Outer circle (smooth circular badge)
            painter.setBrush(QColor("#00ADB5"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(1, 1, 30, 30)
            
            # Music double eighth note (♫) text
            font = QFont("Segoe UI Symbol", 18, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "♫")
            painter.end()
            
            # Save to disk as PNG to ensure it displays perfectly on Windows
            pixmap.save(icon_path, "PNG")
            return QIcon(icon_path)
        except Exception as e:
            logger.error(f"Error drawing dynamic tray icon: {e}")
            return QIcon()

    def set_app_status(self, current_line: str, next_line: str = "", translation_line: str = "", tray_short_status: str = None):
        """Updates the overlay visual text and tray indicators in real-time."""
        self.app_status = tray_short_status or current_line
        
        # Update overlay text
        self.overlay.update_lyrics(current_line, next_line, translation_line)
        
        # Update tray indicators
        if self.tray:
            self.act_status.setText(f"Status: {self.app_status}")
            tooltip = f"Lyrics Overlay: {self.app_status}"
            # Keep tooltip length under Windows limit of 128 characters
            self.tray.setToolTip(tooltip[:127])

    def _setup_hotkeys(self):
        """Dynamic hotkey loading."""
        self.hotkeys.reset_hotkeys()
        self.hotkeys.add_hotkey("toggle_overlay", self.config.get("hotkey_toggle", "Ctrl+Shift+L"))
        self.hotkeys.add_hotkey("toggle_clickthrough", self.config.get("hotkey_clickthrough", "Ctrl+Shift+C"))
        self.hotkeys.add_hotkey("toggle_translation", self.config.get("hotkey_toggle_translation", "Ctrl+Shift+T"))
        self.hotkeys.add_hotkey("font_up", self.config.get("hotkey_font_up", "Ctrl+Shift+Up"))
        self.hotkeys.add_hotkey("font_down", self.config.get("hotkey_font_down", "Ctrl+Shift+Down"))

    @Slot(str)
    def on_hotkey_pressed(self, action: str):
        """Dispatches global keyboard hotkeys."""
        logger.info(f"Global hotkey triggered: {action}")
        if action == "toggle_overlay":
            self.toggle_overlay()
        elif action == "toggle_clickthrough":
            self.toggle_click_through(from_hotkey=True)
        elif action == "toggle_translation":
            self.toggle_translation()
        elif action == "font_up":
            self.overlay.change_font_size(2)
            self._update_saved_font_size()
        elif action == "font_down":
            self.overlay.change_font_size(-2)
            self._update_saved_font_size()

    def toggle_translation(self):
        """Toggles English translation display overlay in real-time."""
        current = not self.config.get("translation_enabled", True)
        self.config["translation_enabled"] = current
        save_config(self.config)
        
        # Update visual styles in overlay
        self.overlay.update_config(self.config)
        
        # Force re-render active lyric to toggle visibility instantly
        self.on_position_changed(self.tracker.position)
        
        # Synchronize Settings UI if open
        if self.settings and self.settings.isVisible():
            self.settings.chk_translation.setChecked(current)
            
        logger.info(f"Translation display toggled: {'ENABLED' if current else 'DISABLED'}")

    @Slot(int, int)
    def on_overlay_dragged(self, x: int, y: int):
        """Persistent drag coordinates coordinator."""
        self.config["x"] = x
        self.config["y"] = y
        # Also ensure overlay's internal config dict stays in sync
        # (they may diverge if Settings was opened and reassigned self.config)
        self.overlay.config["x"] = x
        self.overlay.config["y"] = y
        save_config(self.config)
        logger.info(f"Position coordinate update saved: ({x}, {y})")

    @Slot(int)
    def on_overlay_scrolled(self, direction: int):
        """Processes manual lyric browsing from the mouse wheel."""
        lyrics_source = self.synced_lyrics or self.static_lyrics
        if not lyrics_source:
            return

        max_idx = len(lyrics_source) - 1
        if max_idx < 0:
            return

        # 1. Initialize scrolling index matching current playing position if entering scroll mode
        if not self.scroll_browsing_active:
            self.scroll_browsing_active = True
            
            # Find closest line matching current tracker position
            current_pos = self.tracker.position
            closest_idx = 0
            if self.synced_lyrics:
                for i, line in enumerate(self.synced_lyrics):
                    if line["time"] <= current_pos:
                        closest_idx = i
                    else:
                        break
            elif self.static_lyrics and self.current_duration > 0:
                fraction = min(1.0, max(0.0, current_pos / self.current_duration))
                closest_idx = int(fraction * max_idx)
                
            self.scroll_index = closest_idx
            logger.info("Lyrics scroll-browsing mode entered.")

        # 2. Shift scrolling index: wheel down (-1) moves forward in song, wheel up (1) moves backward
        if direction == 1:
            self.scroll_index = max(0, self.scroll_index - 1)
        else:
            self.scroll_index = min(max_idx, self.scroll_index + 1)

        # 3. Restart the auto-resume timer (auto-resumes in 4 seconds of scroll inactivity)
        self.scroll_resume_timer.start()

        # 4. Display browsed lyrics
        self._update_scroll_display()

    def _update_scroll_display(self):
        """Updates the overlay window text with the manually browsed lyric line."""
        lyrics_source = self.synced_lyrics or self.static_lyrics
        if not lyrics_source or self.scroll_index < 0:
            return

        idx = self.scroll_index
        scroll_status = "[Scroll Mode - Sync Paused]"

        if self.synced_lyrics:
            # Synced lyrics line extraction (direct indexing - zero skipping on manual scroll browsing!)
            current_line = self.synced_lyrics[idx]["text"]
            translation_line = self.synced_lyrics[idx].get("translation", "")

            # Show next upcoming line cleanly
            next_line = ""
            if idx + 1 < len(self.synced_lyrics):
                next_line = self.synced_lyrics[idx + 1]["text"]
                
            if not next_line:
                next_line = scroll_status
            else:
                next_line = f"{next_line}   {scroll_status}"

        else:
            # Static lyrics line extraction
            current_line = self.static_lyrics[idx]
            translation_line = ""
            if self.static_translation and idx < len(self.static_translation):
                translation_line = self.static_translation[idx]

            next_line = ""
            if idx + 1 < len(self.static_lyrics):
                next_line = self.static_lyrics[idx + 1]
            if not next_line:
                next_line = scroll_status
            else:
                next_line = f"{next_line}   {scroll_status}"

        # Update overlay labels immediately
        self.overlay.update_lyrics(current_line, next_line, translation_line)

    def resume_live_sync(self):
        """Automatically resumes standard time synchronization from media playback."""
        if self.scroll_browsing_active:
            self.scroll_browsing_active = False
            self.scroll_index = -1
            logger.info("Lyrics scroll-browsing mode exited. Live-sync resumed.")
            # Trigger immediate position refresh to sync back to current time
            self.on_position_changed(self.tracker.position)

    @Slot(list)
    def on_available_sources_changed(self, sources: list):
        """Pipes dynamic active sessions lists directly to Settings combobox in real-time."""
        self.available_sources = sources
        if self.settings and self.settings.isVisible():
            self.settings.update_available_sources(sources)

    def _update_saved_font_size(self):
        self.config["font_size"] = self.overlay.config["font_size"]
        save_config(self.config)
        if self.settings and self.settings.isVisible():
            self.settings.slider_font_size.setValue(self.config["font_size"])

    @Slot(bool, str)
    def on_session_status_changed(self, active_session: bool, source_app: str):
        """Called when Windows SMTC session state changes."""
        if not active_session:
            logger.info("Session Status Changed: No active system media.")
            self.current_title = ""
            self.current_artist = ""
            self.synced_lyrics = None
            self.static_lyrics = None
            self.static_translation = None
            self.is_instrumental = False
            self.set_app_status("Listening for media...", "Start playing a song on Spotify, Chrome, VLC, etc.")
        else:
            logger.info(f"Session Status Changed: Media detected from source app: {source_app}")

    @Slot(str, str, str)
    def on_track_changed(self, title: str, artist: str, album: str):
        """Triggered on SMTC song change. Fetches lyrics and schedules retries on failure."""
        if not title:
            self.current_title = ""
            self.current_artist = ""
            self.synced_lyrics = None
            self.static_lyrics = None
            self.static_translation = None
            self.is_instrumental = False
            self.set_app_status("Listening for media...", "Start playing a song to view lyrics")
            return

        logger.info(f"Track Change Detected: \"{title}\" by {artist}")
        
        self.current_title = title
        self.current_artist = artist
        self.current_album = album
        self.synced_lyrics = None
        self.static_lyrics = None
        self.static_translation = None
        self.is_instrumental = False
        self.current_retry_count = 0
        
        # Reset scroll browsing state on song change
        self.scroll_browsing_active = False
        self.scroll_index = -1
        self.scroll_resume_timer.stop()
        
        # Display the detected song title and fetching status
        self.set_app_status(f"🎵 {title}", f"Fetching lyrics for {artist}...", "", f"Playing \"{title}\"")
        
        self.trigger_lyrics_fetch()

    def trigger_lyrics_fetch(self):
        """Launches background lyrics retrieval thread."""
        self.is_fetching = True
        threading.Thread(
            target=self._fetch_lyrics_worker,
            args=(self.current_title, self.current_artist, self.current_duration, self.current_retry_count),
            daemon=True,
            name="LyricsFetcherThread"
        ).start()

    def _fetch_lyrics_worker(self, title: str, artist: str, duration: float, retry_count: int):
        """Worker thread executing async lyrics lookup."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            logger.info(f"Fetching lyrics via LRCLIB (Attempt {retry_count + 1})...")
            lyrics = loop.run_until_complete(self.provider.get_lyrics(title, artist, duration))
            
            # If successful (lyrics found) or track is instrumental
            if lyrics.get("synced") or lyrics.get("static") or lyrics.get("is_instrumental"):
                self.lyrics_fetched.emit(title, artist, lyrics)
            else:
                self.fetch_failed.emit(title, artist, retry_count)
        except Exception as e:
            logger.error(f"Lyrics lookup error in worker thread: {e}")
            self.fetch_failed.emit(title, artist, retry_count)
        finally:
            loop.close()

    @Slot(str, str, int)
    def on_fetch_failed(self, title: str, artist: str, retry_count: int):
        """Handles lookup failure, backing off and retrying up to retry_limit."""
        if title != self.current_title or artist != self.current_artist:
            return
            
        if retry_count < self.retry_limit:
            self.current_retry_count = retry_count + 1
            logger.info(f"Lyrics fetch failed for \"{title}\". Scheduling retry {self.current_retry_count} in 4 seconds...")
            self.set_app_status(f"🎵 {title}", f"Lyrics lookup failed. Retrying in 4s... (Attempt {self.current_retry_count + 1})", "", f"Retrying sync...")
            
            # Call back in 4 seconds to try again
            def delayed_retry():
                if title == self.current_title and artist == self.current_artist:
                    self.trigger_lyrics_fetch()
                    
            threading.Timer(4.0, delayed_retry).start()
        else:
            logger.info(f"All retry attempts failed. Lyrics unavailable for \"{title}\".")
            self.is_fetching = False
            self.set_app_status(f"🎵 {self.current_title} - {self.current_artist}", "(Lyrics Unavailable - showing song info)", "", f"Playing \"{self.current_title}\"")

    @Slot(str, str, dict)
    def on_lyrics_ready(self, title: str, artist: str, lyrics: dict):
        """Applies loaded lyrics to display sync queues."""
        if title != self.current_title or artist != self.current_artist:
            return
            
        self.is_fetching = False
        self.is_instrumental = lyrics.get("is_instrumental", False)
        
        if self.is_instrumental:
            logger.info("Applying lyrics: Track is verified instrumental.")
            self.synced_lyrics = None
            self.static_lyrics = None
            self.static_translation = None
            self.set_app_status(f"🎵 {title} - {artist}", "📯 (Instrumental Track) 📯", "", f"Playing \"{title}\"")
            return
            
        self.synced_lyrics = lyrics.get("synced")
        self.static_lyrics = lyrics.get("static")
        self.static_translation = lyrics.get("static_translation")
        
        if self.synced_lyrics:
            logger.info(f"Applying lyrics: Sync successfully locked with {len(self.synced_lyrics)} lines.")
            self.on_position_changed(self.tracker.position)
        elif self.static_lyrics:
            logger.info(f"Applying lyrics: Synced lyrics empty. Locked static fallback with {len(self.static_lyrics)} lines.")
            self.on_position_changed(self.tracker.position)
        else:
            logger.warning("Applying lyrics: Received empty lyrics payload.")
            self.set_app_status(f"🎵 {self.current_title} - {self.current_artist}", "(Lyrics Unavailable on LRCLIB)", "", f"Playing \"{self.current_title}\"")

    @Slot(bool)
    def on_playback_state_changed(self, is_playing: bool):
        """Preserves UI visual alignment when media is paused."""
        pass

    @Slot(float)
    def on_duration_changed(self, duration: float):
        self.current_duration = duration

    @Slot(float)
    def on_position_changed(self, position: float):
        """Drives the lyric scrolling by selecting active and preview lines based on song progress."""
        if self.sync_paused or self.is_fetching or self.is_instrumental or self.scroll_browsing_active:
            return
            
        # Periodic telemetry logging (every 5s) to track position and sync health
        if not hasattr(self, "_last_telemetry_time"):
            self._last_telemetry_time = 0.0
        now = time.time()
        if now - self._last_telemetry_time > 5.0:
            self._last_telemetry_time = now
            logger.info(f"Sync Telemetry - Position: {position:.2f}s | Duration: {self.current_duration:.2f}s | Has Synced: {self.synced_lyrics is not None} | Has Static: {self.static_lyrics is not None}")

        # 1. Standard Synchronized Lyrics
        if self.synced_lyrics:
            active_idx = -1
            for i, line in enumerate(self.synced_lyrics):
                if line["time"] <= position:
                    active_idx = i
                else:
                    break

            if active_idx == -1:
                # Song hasn't started yet — show intro info and first upcoming lyric
                current_line = f"🎵 {self.current_title}"
                translation_line = ""
                # Find first non-empty lyric line as preview
                next_line = ""
                for line in self.synced_lyrics:
                    if line["text"].strip():
                        next_line = line["text"]
                        break
            else:
                # Walk BACKWARD from active_idx to find last non-empty line.
                # LRC files use empty lines as verse-break markers — we skip them.
                current_line = ""
                translation_line = ""
                for k in range(active_idx, -1, -1):
                    if self.synced_lyrics[k]["text"].strip():
                        current_line = self.synced_lyrics[k]["text"]
                        translation_line = self.synced_lyrics[k].get("translation", "")
                        break
                if not current_line:
                    current_line = f"🎵 {self.current_title}"
                    translation_line = ""

                # Walk FORWARD from active_idx+1 to find next non-empty upcoming line
                next_line = ""
                for k in range(active_idx + 1, len(self.synced_lyrics)):
                    if self.synced_lyrics[k]["text"].strip():
                        next_line = self.synced_lyrics[k]["text"]
                        break

            # Guard redundant transitions to prevent screen jitter
            if (self.overlay._target_current_text != current_line or 
                self.overlay._target_next_text != next_line or 
                self.overlay._target_translation_text != translation_line):
                logger.info(f"Lyric Sync Shift - Active: \"{current_line}\" | Next: \"{next_line}\" | Trans: \"{translation_line}\"")
                self.set_app_status(current_line, next_line, translation_line, f"Playing \"{self.current_title}\"")

        # 2. Interpolated Static Lyrics Fallback
        elif self.static_lyrics and self.current_duration > 0:
            num_lines = len(self.static_lyrics)
            fraction = min(1.0, max(0.0, position / self.current_duration))
            active_idx = int(fraction * (num_lines - 1))

            current_line = self.static_lyrics[active_idx]
            translation_line = ""
            if self.static_translation and active_idx < len(self.static_translation):
                translation_line = self.static_translation[active_idx]

            next_line = ""
            if active_idx + 1 < num_lines:
                next_line = self.static_lyrics[active_idx + 1]

            if (self.overlay._target_current_text != current_line or 
                self.overlay._target_next_text != next_line or 
                self.overlay._target_translation_text != translation_line):
                logger.info(f"Static Sync Interpolated Shift - Active: \"{current_line}\" | Next: \"{next_line}\" | Trans: \"{translation_line}\"")
                self.set_app_status(current_line, next_line, translation_line, f"Playing \"{self.current_title}\"")

    # --- Actions & Menu Event Handlers ---
    def toggle_overlay(self):
        """Shows or hides overlay window, updating tray context strings."""
        if self.overlay.isVisible():
            self.overlay.hide()
            self.act_toggle.setText("Show Overlay")
            logger.info("Overlay hidden by user action.")
        else:
            self.overlay.show()
            self.act_toggle.setText("Hide Overlay")
            self.on_position_changed(self.tracker.position)
            logger.info("Overlay shown by user action.")

    def toggle_click_through(self, from_hotkey: bool = False):
        """Toggles click-through mode. When from_hotkey=True, inverts the current state.
        When triggered by tray menu checkbox, uses the checkbox's already-toggled state.
        """
        if from_hotkey:
            # Hotkey: invert current state and sync the tray menu checkbox
            current = not self.config.get("click_through", True)
            self.act_click.setChecked(current)
        else:
            # Tray menu: checkbox already toggled by Qt before this handler runs
            current = self.act_click.isChecked()
            
        self.config["click_through"] = current
        self.overlay.config["click_through"] = current
        save_config(self.config)
        self.overlay.set_click_through(current)
        logger.info(f"Click-through toggled to: {'ON' if current else 'OFF (interactive mode)'}")

    @Slot(int, int)
    def on_overlay_resized(self, width: int, height: int):
        """Persists user's custom overlay dimensions from edge resize."""
        self.config["custom_width"] = width
        self.config["custom_height"] = height
        self.overlay.config["custom_width"] = width
        self.overlay.config["custom_height"] = height
        save_config(self.config)
        logger.info(f"Overlay resized by user: {width}x{height}")

    def restart_sync(self):
        """Forces immediate lookup bypass to re-fetch/re-sync current track."""
        if self.current_title:
            logger.info("Manually restarting lyrics sync...")
            self.on_track_changed(self.current_title, self.current_artist, self.current_album)
        else:
            logger.info("Re-sync skipped: No media currently playing.")

    def show_settings(self):
        if self.settings is None:
            self.settings = SettingsWindow(self.config)
            self.settings.config_changed.connect(self.on_config_changed)
            
        # Prime the settings dropdown with currently running streams
        self.settings.update_available_sources(self.available_sources)
        self.settings.show()
        self.settings.raise_()
        self.settings.activateWindow()

    @Slot(dict)
    def on_config_changed(self, new_config: dict):
        """Handles settings panel update commits, including dynamic Win32 hotkey recycling."""
        # Detect if hotkeys actually modified to avoid unnecessary Win32 thread recycling
        hotkeys_changed = (
            self.config.get("hotkey_toggle") != new_config.get("hotkey_toggle") or
            self.config.get("hotkey_clickthrough") != new_config.get("hotkey_clickthrough") or
            self.config.get("hotkey_toggle_translation") != new_config.get("hotkey_toggle_translation") or
            self.config.get("hotkey_font_up") != new_config.get("hotkey_font_up") or
            self.config.get("hotkey_font_down") != new_config.get("hotkey_font_down")
        )
        
        self.config = new_config
        save_config(self.config)
        
        # Route player prioritizations down to media tracker
        self.tracker.preferred_source = self.config.get("preferred_media_source", "")
        
        # Apply styles and reposition overlays
        self.overlay.update_config(self.config)
        self.act_click.setChecked(self.config["click_through"])
        
        # Force re-render active lyric in case translation visibility changed
        self.on_position_changed(self.tracker.position)
        
        if hotkeys_changed:
            logger.info("Custom hotkeys updated in Settings. Recycling Win32 hotkeys thread...")
            self.hotkeys.stop()
            self._setup_hotkeys()
            self.hotkeys.start()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_settings()

    def quit_app(self):
        """Gracefully cleans up background worker threads and closes the app."""
        logger.info("Quit command received. Initiating teardown...")
        self.tracker.stop()
        self.hotkeys.stop()
        
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self.provider.close())
        except Exception:
            pass
        finally:
            loop.close()
            
        self.overlay.close()
        if self.settings:
            self.settings.close()
            
        self.app.quit()
        logger.info("Teardown complete. Exiting.")

def main():
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    app = QApplication(sys.argv)
    # Ensure application doesn't exit if settings panel close
    app.setQuitOnLastWindowClosed(False)
    
    controller = LyricsAppController(app)
    controller.start()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
