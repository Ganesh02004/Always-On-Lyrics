import os
import sys
import json
import logging

# Define paths
USER_DIR = os.path.expanduser("~")
CONFIG_PATH = os.path.join(USER_DIR, ".lyrics_overlay_config.json")
LOG_PATH = os.path.join(USER_DIR, ".lyrics_overlay.log")

# Reconfigure stdout to UTF-8 so Korean/emoji lyrics don't crash the console logger.
# errors='replace' means unencodable chars become '?' instead of raising UnicodeEncodeError.
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        # Fallback for environments where reconfigure() isn't available (e.g. older python versions)
        import io
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        except Exception:
            pass

# Configure comprehensive file logging
logger = logging.getLogger("LyricsOverlay")
logger.setLevel(logging.INFO)

# Clear existing handlers to prevent duplicate logging
if logger.hasHandlers():
    logger.handlers.clear()

file_handler = logging.FileHandler(LOG_PATH, mode='w', encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(threadName)s - %(message)s'))
logger.addHandler(file_handler)

# Only add stream handler if stdout/stderr are valid (not None, which happens in windowed EXE)
if sys.stdout is not None:
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(stream_handler)

# IMPORTANT: disable propagation to the root logger.
# overlay_window.py calls logging.basicConfig() which adds a handler to the root logger.
# Without this, every message from the LyricsOverlay logger appears TWICE in the output.
logger.propagate = False

def setup_exception_hook():
    """Sets up a global exception hook to capture all silent crashes and log them."""
    def exception_hook(exctype, value, traceback):
        logger.critical("Unhandled Exception Occurred!", exc_info=(exctype, value, traceback))
        # Keep default behavior as well
        sys.__excepthook__(exctype, value, traceback)
    
    sys.excepthook = exception_hook
    logger.info("Global crash exception hook successfully installed.")

DEFAULT_CONFIG = {
    "font_family": "Segoe UI",
    "font_size": 26,
    "font_color": "#FFFFFF",
    "font_color_next": "#B0B0B0",
    "bg_color": "rgba(0, 0, 0, 0)",
    "bg_opacity": 0.0,
    "click_through": True,
    "width_percent": 80,
    "height": 130,
    "bottom_offset": 60,
    "show_next_line": True,
    "shadow_color": "#000000",
    "shadow_radius": 6,
    "shadow_offset": 2,
    # Global hotkeys
    "hotkey_toggle": "Ctrl+Shift+L",
    "hotkey_clickthrough": "Ctrl+Shift+C",
    "hotkey_font_up": "Ctrl+Shift+Up",
    "hotkey_font_down": "Ctrl+Shift+Down"
}

def load_config() -> dict:
    """Loads configuration from user's directory or returns defaults."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
                updated_config = DEFAULT_CONFIG.copy()
                updated_config.update(config)
                return updated_config
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            
    return DEFAULT_CONFIG.copy()

def save_config(config: dict):
    """Saves configuration to the user's config file."""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        logger.info(f"Config successfully saved to: {CONFIG_PATH}")
    except Exception as e:
        logger.error(f"Error saving config file: {e}")
