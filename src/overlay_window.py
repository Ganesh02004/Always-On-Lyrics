import ctypes
import logging
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, Signal, QPoint, QRect
from PySide6.QtGui import QFont, QColor, QScreen, QCursor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsOpacityEffect, QGraphicsDropShadowEffect, QApplication

user32 = ctypes.windll.user32
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Win32 constants for SetWindowPos
HWND_TOPMOST   = -1
SWP_NOMOVE     = 0x0002
SWP_NOSIZE     = 0x0001
SWP_SHOWWINDOW = 0x0040
SWP_NOACTIVATE = 0x0010

# Edge resize zones
EDGE_NONE   = 0
EDGE_LEFT   = 1
EDGE_RIGHT  = 2
EDGE_TOP    = 3
EDGE_BOTTOM = 4
EDGE_TL     = 5  # Top-Left corner
EDGE_TR     = 6  # Top-Right corner
EDGE_BL     = 7  # Bottom-Left corner
EDGE_BR     = 8  # Bottom-Right corner

# How many pixels from the border count as a resize zone
RESIZE_MARGIN = 14
# Minimum window dimensions
MIN_WIDTH  = 200
MIN_HEIGHT = 60

class OverlayWindow(QWidget):
    position_dragged = Signal(int, int)         # Emits x, y on mouse release after drag/resize
    size_changed_by_user = Signal(int, int)      # Emits width, height after edge resize
    scrolled = Signal(int)                       # Emits +1 (scroll up/previous) or -1 (scroll down/next)

    def __init__(self, config=None):
        super().__init__()
        
        # Load default or provided config
        self.config = config or self._default_config()
        self._is_dragging = False
        self._is_resizing = False
        self._resize_edge = EDGE_NONE
        self._drag_pos = None
        self._resize_origin_rect = None   # geometry snapshot when resize started
        self._resize_origin_mouse = None  # mouse position when resize started
        
        # Window flags for borderless, always-on-top overlay.
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        
        # Set translucent background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        # Ensure it doesn't take keyboard focus initially
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        
        # Enable mouse tracking so we can change cursors on hover (even without button pressed)
        self.setMouseTracking(True)
        
        self._setup_ui()
        
        # Set initial click-through state
        self.click_through = False
        self.set_click_through(self.config.get("click_through", True))
        
        self._apply_config()
        self._reposition()

        # Periodic re-pin timer: re-applies position every 2 seconds.
        self._repin_timer = QTimer(self)
        self._repin_timer.setInterval(2000)
        self._repin_timer.timeout.connect(self._reposition)
        self._repin_timer.start()

    def _default_config(self) -> dict:
        return {
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
            "shadow_offset": 2
        }

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 8, 15, 8)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

        # Create a container widget for lyrics to apply the fade transition
        self.lyrics_container = QWidget()
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(3)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lyrics_container.setLayout(container_layout)

        # CRITICAL: Make ALL child widgets transparent to mouse events!
        # This ensures drag, resize, and scroll events always reach the OverlayWindow
        # and are not eaten by QLabels or the container widget.
        self.lyrics_container.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        # Current Lyric Label
        self.current_label = QLabel("Waiting for media...")
        self.current_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_label.setWordWrap(True)
        self.current_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        container_layout.addWidget(self.current_label)

        # Drop shadow for current label
        self.shadow_effect = QGraphicsDropShadowEffect(self.current_label)
        self.shadow_effect.setBlurRadius(self.config["shadow_radius"])
        self.shadow_effect.setColor(QColor(self.config["shadow_color"]))
        self.shadow_effect.setOffset(self.config["shadow_offset"])
        self.current_label.setGraphicsEffect(self.shadow_effect)

        # Translation Lyric Label (English translation)
        self.translation_label = QLabel("")
        self.translation_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.translation_label.setWordWrap(True)
        self.translation_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        container_layout.addWidget(self.translation_label)

        self.trans_shadow_effect = QGraphicsDropShadowEffect(self.translation_label)
        self.trans_shadow_effect.setBlurRadius(self.config.get("shadow_radius", 6))
        self.trans_shadow_effect.setColor(QColor(self.config.get("shadow_color", "#000000")))
        self.trans_shadow_effect.setOffset(self.config.get("shadow_offset", 2))
        self.translation_label.setGraphicsEffect(self.trans_shadow_effect)

        # Next Lyric Label
        self.next_label = QLabel("")
        self.next_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.next_label.setWordWrap(True)
        self.next_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        container_layout.addWidget(self.next_label)

        self.next_shadow_effect = QGraphicsDropShadowEffect(self.next_label)
        self.next_shadow_effect.setBlurRadius(self.config["shadow_radius"])
        self.next_shadow_effect.setColor(QColor(self.config["shadow_color"]))
        self.next_shadow_effect.setOffset(self.config["shadow_offset"])
        self.next_label.setGraphicsEffect(self.next_shadow_effect)

        # Add the lyrics container to the window layout
        layout.addWidget(self.lyrics_container)

        # Opacity effect for the container
        self.opacity_effect = QGraphicsOpacityEffect(self.lyrics_container)
        self.lyrics_container.setGraphicsEffect(self.opacity_effect)

        # Setup state targets for transitions (crucial for Main Controller guards)
        self._target_current_text = ""
        self._target_next_text = ""
        self._target_translation_text = ""

        # Set up quick fade-in animation
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(120) # Ultra-responsive 120ms fade duration
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutQuad)

    def _apply_config(self):
        """Applies styles based on current configuration."""
        font_family = self.config.get("font_family", "Segoe UI")
        font_size = self.config.get("font_size", 26)
        
        # Styles for labels
        self.current_label.setFont(QFont(font_family, font_size, QFont.Weight.Bold))
        
        # Translation styles
        trans_font_size = self.config.get("translation_font_size", int(font_size * 0.85))
        self.translation_label.setFont(QFont(font_family, trans_font_size, QFont.Weight.Medium))
        
        self.next_label.setFont(QFont(font_family, int(font_size * 0.75), QFont.Weight.Medium))
        
        font_color = self.config.get("font_color", "#FFFFFF")
        font_color_trans = self.config.get("font_color_trans", "#00ADB5")
        font_color_next = self.config.get("font_color_next", "#B0B0B0")
        
        # Premium Drag State Styling Indicator: dashed teal border and translucent dark panel
        if not self.click_through:
            border_style = "border: 2px dashed #00ADB5; background-color: rgba(10, 10, 10, 0.65);"
        else:
            bg_color = self.config.get("bg_color", "rgba(0, 0, 0, 0)")
            border_style = f"background-color: {bg_color}; border: none;"
        
        # Apply specific stylesheet targeting only OverlayWindow directly to avoid child inheritances
        self.setStyleSheet(f"""
            OverlayWindow {{
                {border_style}
                border-radius: 12px;
            }}
            QLabel {{
                background-color: transparent;
                color: {font_color};
            }}
        """)
        
        # Apply specific colors for sublabels
        self.translation_label.setStyleSheet(f"color: {font_color_trans}; background-color: transparent;")
        self.next_label.setStyleSheet(f"color: {font_color_next}; background-color: transparent;")
        
        # Set visibility of next line
        self.next_label.setVisible(self.config.get("show_next_line", True))
        
        # Shadow adjustments
        self.shadow_effect.setBlurRadius(self.config["shadow_radius"])
        self.shadow_effect.setColor(QColor(self.config["shadow_color"]))
        
        self.trans_shadow_effect.setBlurRadius(self.config["shadow_radius"])
        self.trans_shadow_effect.setColor(QColor(self.config["shadow_color"]))
        
        self.next_shadow_effect.setBlurRadius(self.config["shadow_radius"])
        self.next_shadow_effect.setColor(QColor(self.config["shadow_color"]))

    def _reposition(self):
        """Positions the overlay at the bottom center of the primary screen's available area
        or restores the custom user-dragged coordinates with precise boundary scaling.
        """
        # CRITICAL: Skip snap-backs immediately if the user is actively dragging or resizing!
        if self._is_dragging or self._is_resizing:
            return

        screen = QApplication.primaryScreen()
        if not screen:
            return

        # availableGeometry excludes taskbar/docks
        ag = screen.availableGeometry()
        screen_width  = ag.width()
        screen_height = ag.height()
        origin_x      = ag.x()
        origin_y      = ag.y()

        # Check if we have saved custom width from user edge-resize
        custom_width = self.config.get("custom_width")
        custom_height = self.config.get("custom_height")

        if custom_width and custom_width > MIN_WIDTH:
            window_width = custom_width
        else:
            width_pct = self.config.get("width_percent", 80)
            window_width = int(screen_width * (width_pct / 100.0))

        if custom_height and custom_height > MIN_HEIGHT:
            window_height = custom_height
        else:
            # Dynamic Visual Height Scaling based on font size and translation visibility
            font_size = self.config.get("font_size", 26)
            is_translation_visible = bool(self.translation_label.text()) and self.config.get("translation_enabled", True)
            
            height_multiplier = 5.8 if is_translation_visible else 4.2
            window_height = int(font_size * height_multiplier)
            window_height = max(160 if is_translation_visible else 110, window_height)

        # Check if we have saved custom coordinates from user drag
        custom_x = self.config.get("x")
        custom_y = self.config.get("y")

        if custom_x is not None and custom_y is not None:
            # User has dragged the window — use their saved position.
            # Allow partial off-screen: keep at least 100px visible on each axis
            min_visible = 100
            x = max(origin_x - window_width + min_visible, min(custom_x, origin_x + screen_width - min_visible))
            y = max(origin_y, min(custom_y, origin_y + screen_height - min_visible))
        else:
            x = origin_x + (screen_width - window_width) // 2
            y = origin_y + screen_height - window_height - self.config.get("bottom_offset", 20)

        # Set geometry via Qt
        self.setGeometry(x, y, window_width, window_height)

        # Then pin it with Win32 HWND_TOPMOST
        if self.isVisible():
            hwnd = int(self.winId())
            user32.SetWindowPos(
                hwnd, HWND_TOPMOST,
                x, y, window_width, window_height,
                0x0040 | 0x0010 # SWP_SHOWWINDOW | SWP_NOACTIVATE
            )
        logging.debug(f"Overlay repositioned to ({x}, {y}) size {window_width}x{window_height}")

    def set_click_through(self, enabled: bool):
        """Toggles the WS_EX_TRANSPARENT style on the window using Win32 API."""
        self.click_through = enabled
        
        # Trigger visual stylesheet update (border and background change to capture clicks!)
        self._apply_config()
        
        hwnd = int(self.winId())
        style = user32.GetWindowLongW(hwnd, -20) # GWL_EXSTYLE
        
        if enabled:
            style |= 0x00000020 # WS_EX_TRANSPARENT
            style |= 0x00080000 # WS_EX_LAYERED
            logging.info("Overlay click-through mode ENABLED.")
        else:
            style &= ~0x00000020
            logging.info("Overlay click-through mode DISABLED — drag/scroll/resize now active.")
            
        user32.SetWindowLongW(hwnd, -20, style)
        # Apply the style update
        user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0027) # SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER

    def update_lyrics(self, current_text: str, next_text: str = "", translation_text: str = ""):
        """Updates the lyric text instantly and triggers a smooth quick fade-in animation,
        guaranteeing zero skipped lyrics even in rapid-paced songs.
        """
        # Guard against redundant updates to prevent text flashing
        if (self._target_current_text == current_text and 
            self._target_next_text == next_text and 
            self._target_translation_text == translation_text):
            return

        self._target_current_text = current_text
        self._target_next_text = next_text
        self._target_translation_text = translation_text

        # Swap texts synchronously (zero latency - fixes fast song skipped lines!)
        self.current_label.setText(current_text)
        self.next_label.setText(next_text)
        self.translation_label.setText(translation_text)
        
        # Resolve translation visibility instantly
        self.translation_label.setVisible(
            bool(translation_text) and self.config.get("translation_enabled", True)
        )
        
        # Dynamically recalculate window height — but NEVER during user interaction!
        if not self._is_dragging and not self._is_resizing:
            self._reposition()

        # Run smooth quick fade-in pulse animation
        self.fade_animation.stop()
        self.fade_animation.setStartValue(0.4)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()

    def update_config(self, new_config: dict):
        """Updates the configuration and re-applies styles and positions."""
        self.config.update(new_config)
        self._apply_config()
        self._reposition()
        self.set_click_through(self.config.get("click_through", True))

    def change_font_size(self, delta: int):
        """Adjusts font size dynamically (e.g. from hotkeys).
        Keeps the window center-anchored so text doesn't visually "move/jump".
        """
        current_size = self.config.get("font_size", 26)
        new_size = max(12, min(72, current_size + delta))
        self.config["font_size"] = new_size
        
        # Capture current center point BEFORE resizing
        old_center_x = self.x() + self.width() // 2
        old_center_y = self.y() + self.height() // 2
        
        self._apply_config()
        
        # Clear custom_height so dynamic scaling kicks in for font changes
        self.config.pop("custom_height", None)
        
        self._reposition()
        
        # If user has a custom position, re-center around the previous anchor point
        if self.config.get("x") is not None:
            new_x = old_center_x - self.width() // 2
            new_y = old_center_y - self.height() // 2
            self.move(new_x, new_y)
            self.config["x"] = new_x
            self.config["y"] = new_y
        
        logging.info(f"Font size adjusted to: {new_size}")

    # ===================== Edge Hit-Testing =====================

    def _edge_at(self, local_pos) -> int:
        """Returns which edge/corner the local mouse position is near, or EDGE_NONE."""
        x, y = local_pos.x(), local_pos.y()
        w, h = self.width(), self.height()
        m = RESIZE_MARGIN

        on_left   = x < m
        on_right  = x > w - m
        on_top    = y < m
        on_bottom = y > h - m

        if on_top and on_left:     return EDGE_TL
        if on_top and on_right:    return EDGE_TR
        if on_bottom and on_left:  return EDGE_BL
        if on_bottom and on_right: return EDGE_BR
        if on_left:   return EDGE_LEFT
        if on_right:  return EDGE_RIGHT
        if on_top:    return EDGE_TOP
        if on_bottom: return EDGE_BOTTOM
        return EDGE_NONE

    def _cursor_for_edge(self, edge: int):
        """Returns the appropriate resize cursor for the given edge."""
        if edge in (EDGE_LEFT, EDGE_RIGHT):
            return Qt.CursorShape.SizeHorCursor
        elif edge in (EDGE_TOP, EDGE_BOTTOM):
            return Qt.CursorShape.SizeVerCursor
        elif edge in (EDGE_TL, EDGE_BR):
            return Qt.CursorShape.SizeFDiagCursor
        elif edge in (EDGE_TR, EDGE_BL):
            return Qt.CursorShape.SizeBDiagCursor
        return Qt.CursorShape.ArrowCursor

    # ===================== Mouse Events =====================

    def mousePressEvent(self, event):
        """Enable window dragging and edge resizing when click-through is disabled."""
        if self.click_through or event.button() != Qt.MouseButton.LeftButton:
            return

        local_pos = event.position().toPoint()
        edge = self._edge_at(local_pos)

        if edge != EDGE_NONE:
            # Start edge resize
            self._is_resizing = True
            self._resize_edge = edge
            self._resize_origin_rect = self.geometry()
            self._resize_origin_mouse = event.globalPosition().toPoint()
            logging.info(f"Edge resize started: edge={edge}")
            event.accept()
        else:
            # Start drag
            self._drag_pos = event.globalPosition().toPoint()
            self._is_dragging = True
            logging.info("Window drag started")
            event.accept()

    def mouseMoveEvent(self, event):
        """Handle drag movement, edge resize, and cursor shape updates."""
        if self.click_through:
            return

        # ---- Active resize ----
        if self._is_resizing and self._resize_origin_rect and self._resize_origin_mouse:
            delta = event.globalPosition().toPoint() - self._resize_origin_mouse
            r = QRect(self._resize_origin_rect)  # copy

            edge = self._resize_edge
            if edge in (EDGE_RIGHT, EDGE_TR, EDGE_BR):
                r.setRight(r.right() + delta.x())
            if edge in (EDGE_LEFT, EDGE_TL, EDGE_BL):
                r.setLeft(r.left() + delta.x())
            if edge in (EDGE_BOTTOM, EDGE_BL, EDGE_BR):
                r.setBottom(r.bottom() + delta.y())
            if edge in (EDGE_TOP, EDGE_TL, EDGE_TR):
                r.setTop(r.top() + delta.y())

            # Enforce minimum dimensions
            if r.width() < MIN_WIDTH:
                if edge in (EDGE_LEFT, EDGE_TL, EDGE_BL):
                    r.setLeft(r.right() - MIN_WIDTH)
                else:
                    r.setRight(r.left() + MIN_WIDTH)
            if r.height() < MIN_HEIGHT:
                if edge in (EDGE_TOP, EDGE_TL, EDGE_TR):
                    r.setTop(r.bottom() - MIN_HEIGHT)
                else:
                    r.setBottom(r.top() + MIN_HEIGHT)

            self.setGeometry(r)
            event.accept()
            return

        # ---- Active drag (NO position constraints — user can place anywhere on screen) ----
        if self._is_dragging and self._drag_pos:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self._drag_pos = event.globalPosition().toPoint()
            
            new_pos = self.pos() + delta
            self.move(new_pos)
            event.accept()
            return

        # ---- Hover cursor updates (only when not dragging/resizing) ----
        local_pos = event.position().toPoint()
        edge = self._edge_at(local_pos)
        if edge != EDGE_NONE:
            self.setCursor(self._cursor_for_edge(edge))
        else:
            self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseReleaseEvent(self, event):
        """Save coordinates/dimensions to config on release."""
        if self._is_resizing:
            self._is_resizing = False
            self._resize_edge = EDGE_NONE
            self._resize_origin_rect = None
            self._resize_origin_mouse = None
            # Persist new size and position in overlay's own config
            self.config["x"] = self.x()
            self.config["y"] = self.y()
            self.config["custom_width"] = self.width()
            self.config["custom_height"] = self.height()
            # Emit signals to save in controller config + disk
            self.position_dragged.emit(self.x(), self.y())
            self.size_changed_by_user.emit(self.width(), self.height())
            logging.info(f"Edge resize complete. Pos: ({self.x()}, {self.y()}) Size: {self.width()}x{self.height()}")
            event.accept()
            return

        if self._is_dragging:
            self._is_dragging = False
            self._drag_pos = None
            # Persist position in overlay's own config dict immediately
            self.config["x"] = self.x()
            self.config["y"] = self.y()
            # Emit signal to save position in controller config + disk
            self.position_dragged.emit(self.x(), self.y())
            logging.info(f"Drag released. Saved position: ({self.x()}, {self.y()})")
            event.accept()

    def wheelEvent(self, event):
        """Capture scroll wheel events when click-through is disabled to browse lyrics."""
        if not self.click_through:
            delta = event.angleDelta().y()
            if delta > 0:
                self.scrolled.emit(1) # Scroll up -> Previous lyric
            elif delta < 0:
                self.scrolled.emit(-1) # Scroll down -> Next lyric
            event.accept()
        else:
            event.ignore()
