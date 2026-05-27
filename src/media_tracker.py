import asyncio
import threading
import time
from datetime import datetime, timezone
import winrt.windows.foundation.collections  # Explicit import for PyInstaller analyzer detection!
from PySide6.QtCore import QObject, Signal

# Import our shared logger
from utils import logger

class MediaTrackerSignals(QObject):
    # Signals for Qt thread integration
    track_changed = Signal(str, str, str)  # title, artist, album
    playback_state_changed = Signal(bool)  # is_playing
    position_changed = Signal(float)       # current position in seconds
    duration_changed = Signal(float)       # duration in seconds
    session_status = Signal(bool, str)     # active_session_exists, session_source_app_name
    available_sources_changed = Signal(list) # List of currently active media player source app names

class MediaTracker:
    def __init__(self):
        self.signals = MediaTrackerSignals()
        self.current_title = ""
        self.current_artist = ""
        self.current_album = ""
        self.is_playing = False
        self.position = 0.0
        self.duration = 0.0
        self.preferred_source = ""
        
        self._loop = None
        self._thread = None
        self._running = False
        self._session_manager = None
        self._current_session = None
        self._last_update_time = time.time() # Guard: initialize to current time instead of 0.0
        self._last_timeline_position = 0.0

    def start(self):
        """Starts the media tracker in a background thread with its own asyncio loop."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_async_loop, daemon=True, name="MediaTrackerThread")
        self._thread.start()
        # Start a local polling thread for smooth position updates
        threading.Thread(target=self._smooth_position_poller, daemon=True, name="PositionPoller").start()

    def stop(self):
        """Stops the media tracker."""
        self._running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=1.0)

    def _run_async_loop(self):
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._setup_winrt())
            self._loop.run_forever()
        except Exception as e:
            logger.critical(f"Critical error in media tracker async loop: {e}")

    async def _setup_winrt(self):
        """Initializes the WinRT session manager and registers callbacks."""
        try:
            from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager
            
            self._session_manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()
            
            # Register for changes in the active session list
            def sessions_changed(sender, args):
                logger.info("Windows active media sessions changed event received.")
                asyncio.run_coroutine_threadsafe(self._update_session(), self._loop)
                
            self._session_manager.add_sessions_changed(sessions_changed)
            
            # Initial session fetch
            await self._update_session()
            logger.info("WinRT SMTC media tracker successfully initialized.")
        except Exception as e:
            logger.error(f"Error setting up WinRT media tracker: {e}")
            self.signals.session_status.emit(False, f"Initialization Error: {str(e)}")

    async def _update_session(self):
        """Updates the active session reference and sets up listeners on the new session."""
        try:
            if not self._session_manager:
                return
                
            sessions = self._session_manager.get_sessions()
            available_sources = []
            for s in sessions:
                if s:
                    available_sources.append(s.source_app_user_model_id)
            
            # Broadcast the running player sources list for the Settings UI dropdown
            self.signals.available_sources_changed.emit(available_sources)
            
            session = None
            if self.preferred_source:
                # Seek matching session among active channels
                for s in sessions:
                    if s and self.preferred_source.lower() in s.source_app_user_model_id.lower():
                        session = s
                        break
            
            # Fallback to the Windows-designated default active session
            if not session:
                session = self._session_manager.get_current_session()
            
            # Check if reference actually swapped immediately to prevent duplicate registrations and time skips
            if session == self._current_session:
                return
            
            self._current_session = session

            if session:
                app_name = session.source_app_user_model_id
                logger.info(f"Active Windows media session detected: {app_name}")
                self.signals.session_status.emit(True, app_name)
                
                # Setup event handlers with threadsafe loop routing
                def media_properties_changed(sender, args):
                    asyncio.run_coroutine_threadsafe(self._update_media_properties(), self._loop)

                def playback_info_changed(sender, args):
                    asyncio.run_coroutine_threadsafe(self._update_playback_info(), self._loop)

                session.add_media_properties_changed(media_properties_changed)
                session.add_playback_info_changed(playback_info_changed)
                
                # Fetch initial metadata and state
                await self._update_media_properties()
                await self._update_playback_info()
            else:
                logger.info("No active Windows media session detected.")
                self.signals.session_status.emit(False, "")
                self._clear_state()
        except Exception as e:
            logger.error(f"Error updating media session: {e}")

    async def _update_media_properties(self):
        """Fetches track metadata (title, artist, album) from the current session."""
        if not self._current_session:
            return
        try:
            props = await self._current_session.try_get_media_properties_async()
            if props:
                title = props.title or "Unknown Title"
                artist = props.artist or "Unknown Artist"
                album = props.album_title or ""
                
                if (title != self.current_title or 
                    artist != self.current_artist or 
                    album != self.current_album):
                    
                    self.current_title = title
                    self.current_artist = artist
                    self.current_album = album
                    
                    logger.info(f"SMTC Metadata Changed: \"{title}\" by {artist}")
                    self.signals.track_changed.emit(title, artist, album)
                    
                    # Whenever the track changes, trigger a timeline refresh
                    await self._update_playback_info()
        except Exception as e:
            logger.error(f"Error fetching media properties: {e}")

    async def _update_playback_info(self):
        """Fetches play state and time properties from the current session."""
        if not self._current_session:
            return
        try:
            info = self._current_session.get_playback_info()
            if info:
                # Playback status (Playing = 4 in SMTC enum)
                is_playing = (int(info.playback_status) == 4)
                
                if is_playing != self.is_playing:
                    self.is_playing = is_playing
                    logger.info(f"SMTC Playback State Changed: {'Playing' if is_playing else 'Paused'}")
                    self.signals.playback_state_changed.emit(is_playing)
                    
                    if is_playing:
                        # Resuming: grab a fresh SMTC position snapshot right now so the
                        # smooth poller starts extrapolating from the correct resume point.
                        try:
                            timeline = self._current_session.get_timeline_properties()
                            if timeline:
                                self._last_timeline_position = timeline.position.total_seconds()
                                self._last_update_time = time.time()
                                self.position = self._last_timeline_position
                                logger.info(f"Resume anchor refreshed at position={self.position:.2f}s")
                        except Exception:
                            # Non-fatal: poller will self-correct within 3s
                            pass

            # Timeline properties (Position, Duration)
            timeline = self._current_session.get_timeline_properties()
            if timeline:
                try:
                    # In modern WinRT Python library, timeline.end_time and position are datetime.timedelta objects
                    duration = timeline.end_time.total_seconds()
                    position = timeline.position.total_seconds()
                    
                    # Guard: only reject small *backward* jumps — these are stale OS rubber-band events.
                    # We do NOT filter small forward movements; those are real position reports.
                    if self.is_playing and self.position > 0:
                        drift = position - self.position
                        if drift < 0 and abs(drift) < 2.0:
                            # Stale OS event going backward by < 2s — ignore to prevent backward jumping
                            return
                    
                    # Guard and update duration if valid
                    if duration > 0 and abs(duration - self.duration) > 0.1:
                        self.duration = duration
                        self.signals.duration_changed.emit(duration)

                    # Always update the anchors so the smooth poller extrapolates from the right base
                    self._last_timeline_position = position
                    self._last_update_time = time.time()
                    
                    # Always update position and emit so UI reflects true state
                    self.position = position
                    self.signals.position_changed.emit(position)
                except Exception as inner_ex:
                    logger.error(f"Error parsing timeline timedeltas: {inner_ex}")
            else:
                # If timeline is temporarily None, re-initialize update anchor to current time to avoid drift
                self._last_update_time = time.time()
        except Exception as e:
            logger.error(f"Error fetching playback info/timeline: {e}")

    def _smooth_position_poller(self):
        """Primary position driver: advances playback position using wall-clock time.
        
        SMTC does NOT emit continuous position events — it only fires on pause/play/seek.
        This poller fills the gap by extrapolating from the last known SMTC anchor at 1x
        real-time speed. Every 3 seconds we also grab a fresh SMTC snapshot to catch any
        drift or silent seeks.
        """
        last_force_sync = time.time()
        last_channels_scan = 0.0
        POLL_INTERVAL = 0.1      # 100ms = smooth subtitle updates
        SYNC_INTERVAL = 3.0      # Re-anchor from SMTC every 3 seconds
        SCAN_INTERVAL = 3.0      # Scan running player channels every 3 seconds
 
        while self._running:
            now = time.time()
            
            # Periodically scan running player channels for dynamic settings dropdown populating
            if now - last_channels_scan >= SCAN_INTERVAL:
                last_channels_scan = now
                if self._loop and self._session_manager:
                    asyncio.run_coroutine_threadsafe(self._update_session(), self._loop)
 
            if self._current_session and self.is_playing:
                # -- Periodic hard sync: pull real position from SMTC to detect user seeks --
                if now - last_force_sync >= SYNC_INTERVAL:
                    last_force_sync = now
                    try:
                        timeline = self._current_session.get_timeline_properties()
                        if timeline:
                            smtc_pos = timeline.position.total_seconds()
                            extrapolated = self._last_timeline_position + (now - self._last_update_time)
                            delta = smtc_pos - extrapolated

                            # Guard: if SMTC returns the exact same position as last check,
                            # it's returning a stale/cached value — skip re-anchor to prevent
                            # infinite oscillation (drift→reset→drift loop)
                            if not hasattr(self, '_last_smtc_sync_pos'):
                                self._last_smtc_sync_pos = -1.0
                            
                            smtc_is_stale = (abs(smtc_pos - self._last_smtc_sync_pos) < 0.01)
                            self._last_smtc_sync_pos = smtc_pos

                            # Only re-anchor on genuine user seeks with non-stale SMTC data:
                            #   - smtc_pos must be > 0  (0.0s = SMTC returning uninitialized value)
                            #   - NOT stale (same value as last check = cached OS data)
                            #   - delta > +2s  → user skipped forward
                            #   - delta < -5s  → user skipped backward
                            is_forward_seek = delta > 2.0
                            is_backward_seek = delta < -5.0
                            if smtc_pos > 0 and not smtc_is_stale and (is_forward_seek or is_backward_seek):
                                logger.info(f"Position re-anchor: estimated={extrapolated:.1f}s SMTC={smtc_pos:.1f}s (drift={delta:+.1f}s)")
                                self._last_timeline_position = smtc_pos
                                self._last_update_time = now
                                self.position = smtc_pos
                            else:
                                logger.debug(f"Periodic sync skipped: SMTC={smtc_pos:.1f}s estimated={extrapolated:.1f}s delta={delta:+.1f}s stale={smtc_is_stale}")
                    except Exception as e:
                        logger.debug(f"Periodic sync error (non-fatal): {e}")

                # -- Smooth extrapolation: advance time at 1x wall-clock speed --
                try:
                    elapsed = now - self._last_update_time
                    estimated_pos = self._last_timeline_position + elapsed

                    # Cap at track duration
                    if self.duration > 0 and estimated_pos > self.duration:
                        estimated_pos = self.duration

                    if estimated_pos >= 0 and abs(estimated_pos - self.position) >= POLL_INTERVAL * 0.9:
                        self.position = estimated_pos
                        self.signals.position_changed.emit(estimated_pos)
                except Exception as e:
                    logger.error(f"Error in smooth position poller: {e}")

            time.sleep(POLL_INTERVAL)

    def _clear_state(self):
        """Clears state when no media is active."""
        self.current_title = ""
        self.current_artist = ""
        self.current_album = ""
        self.is_playing = False
        self.position = 0.0
        self.duration = 0.0
        self._last_update_time = time.time()
        self._last_timeline_position = 0.0
        self.signals.track_changed.emit("", "", "")
        self.signals.playback_state_changed.emit(False)
        self.signals.position_changed.emit(0.0)
        self.signals.duration_changed.emit(0.0)
