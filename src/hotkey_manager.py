import ctypes
import threading
from ctypes import wintypes
from PySide6.QtCore import QObject, Signal

# Import our shared logger
from utils import logger

# Win32 Constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

WM_HOTKEY = 0x0312

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

MODIFIERS = {
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "shift": MOD_SHIFT,
    "alt": MOD_ALT,
    "win": MOD_WIN,
    "windows": MOD_WIN
}

VK_CODES = {
    "backspace": 0x08, "tab": 0x09, "clear": 0x0C, "enter": 0x0D, "pause": 0x13, "caps_lock": 0x14,
    "escape": 0x1B, "space": 0x20, "page_up": 0x21, "page_down": 0x22, "end": 0x23, "home": 0x24,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28, "select": 0x29, "print": 0x2A,
    "execute": 0x2B, "print_screen": 0x2C, "insert": 0x2D, "delete": 0x2E, "help": 0x2F,
    "0": 0x30, "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34, "5": 0x35, "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39,
    "a": 0x41, "b": 0x42, "c": 0x43, "d": 0x44, "e": 0x45, "f": 0x46, "g": 0x47, "h": 0x48, "i": 0x49, "j": 0x4A,
    "k": 0x4B, "l": 0x4C, "m": 0x4D, "n": 0x4E, "o": 0x4F, "p": 0x50, "q": 0x51, "r": 0x52, "s": 0x53, "t": 0x54,
    "u": 0x55, "v": 0x56, "w": 0x57, "x": 0x58, "y": 0x59, "z": 0x5A,
    "numpad0": 0x60, "numpad1": 0x61, "numpad2": 0x62, "numpad3": 0x63, "numpad4": 0x64,
    "numpad5": 0x65, "numpad6": 0x66, "numpad7": 0x67, "numpad8": 0x68, "numpad9": 0x69,
    "multiply": 0x6A, "add": 0x6B, "separator": 0x6C, "subtract": 0x6D, "decimal": 0x6E, "divide": 0x6F,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73, "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77, "f9": 0x78,
    "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    "num_lock": 0x90, "scroll_lock": 0x91
}

class HotkeySignals(QObject):
    hotkey_pressed = Signal(str)

class HotkeyManager:
    def __init__(self):
        self.signals = HotkeySignals()
        self._thread = None
        self._thread_id = None
        self._running = False
        self._registered_hotkeys = {}
        self._next_hotkey_id = 1
    def reset_hotkeys(self):
        """Clears all registered hotkeys."""
        self._registered_hotkeys = {}
        self._next_hotkey_id = 1

    def add_hotkey(self, action_name: str, shortcut_str: str):
        parts = [p.strip().lower() for p in shortcut_str.split("+")]
        modifiers_mask = 0
        vk_code = 0
        
        for part in parts:
            if part in MODIFIERS:
                modifiers_mask |= MODIFIERS[part]
            elif part in VK_CODES:
                vk_code = VK_CODES[part]
            elif len(part) == 1:
                char = part.upper()
                vk_code = ord(char)
            else:
                logger.warning(f"Unknown key part in shortcut '{shortcut_str}': {part}")
                
        if vk_code == 0:
            logger.error(f"Failed to find valid virtual key for shortcut '{shortcut_str}'")
            return
            
        hotkey_id = self._next_hotkey_id
        self._next_hotkey_id += 1
        
        self._registered_hotkeys[hotkey_id] = {
            "action": action_name,
            "modifiers": modifiers_mask,
            "vk": vk_code,
            "shortcut": shortcut_str,
            "registered": False
        }
        
    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="HotkeyListener")
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, 18, 0, 0)
        if self._thread:
            self._thread.join(timeout=1.0)
            
    def _run_loop(self):
        self._thread_id = kernel32.GetCurrentThreadId()
        
        for hotkey_id, item in self._registered_hotkeys.items():
            success = user32.RegisterHotKey(
                None,
                hotkey_id,
                item["modifiers"] | MOD_NOREPEAT,
                item["vk"]
            )
            if success:
                item["registered"] = True
                logger.info(f"Registered global hotkey: {item['shortcut']} for '{item['action']}'")
            else:
                item["registered"] = False
                err = kernel32.GetLastError()
                logger.error(f"Failed to register hotkey {item['shortcut']}: Win32 Error Code {err}")
                
        msg = wintypes.MSG()
        while self._running:
            res = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if res <= 0:
                break
                
            if msg.message == WM_HOTKEY:
                hotkey_id = msg.wParam
                if hotkey_id in self._registered_hotkeys:
                    action = self._registered_hotkeys[hotkey_id]["action"]
                    logger.info(f"Hotkey triggered: {self._registered_hotkeys[hotkey_id]['shortcut']} -> {action}")
                    self.signals.hotkey_pressed.emit(action)
                    
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
            
        for hotkey_id, item in self._registered_hotkeys.items():
            if item["registered"]:
                user32.UnregisterHotKey(None, hotkey_id)
                item["registered"] = False
                logger.info(f"Unregistered global hotkey: {item['shortcut']}")
