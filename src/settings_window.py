import os
import sys
import logging
import subprocess
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QFontDatabase, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QCheckBox, 
    QPushButton, QComboBox, QGroupBox, QFormLayout, QColorDialog, 
    QMessageBox, QScrollArea, QLineEdit
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SettingsWindow(QWidget):
    # Signal emitted when configuration changes
    config_changed = Signal(dict)

    def __init__(self, current_config):
        super().__init__()
        self.config = current_config.copy()
        
        self.setWindowTitle("Lyrics Overlay Settings")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint)
        self.resize(520, 700)
        
        self._setup_ui()
        self._load_config_into_ui()
        
        # Apply premium styling
        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E1E;
                color: #F0F0F0;
                font-family: "Segoe UI", sans-serif;
                font-size: 13px;
            }
            QGroupBox {
                border: 1px solid #3A3A3A;
                border-radius: 8px;
                margin-top: 15px;
                font-weight: bold;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                color: #00ADB5;
            }
            QLabel {
                color: #D3D3D3;
            }
            QSlider::groove:horizontal {
                border: 1px solid #3A3A3A;
                height: 6px;
                background: #2D2D2D;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #00ADB5;
                border: none;
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #08D9D6;
            }
            QComboBox {
                background-color: #2D2D2D;
                border: 1px solid #3A3A3A;
                border-radius: 4px;
                padding: 5px;
                color: #F0F0F0;
                min-width: 180px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QCheckBox {
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                background-color: #2D2D2D;
                border: 1px solid #3A3A3A;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #00ADB5;
                border-color: #00ADB5;
            }
            QLineEdit {
                background-color: #2D2D2D;
                border: 1px solid #3A3A3A;
                border-radius: 4px;
                padding: 5px;
                color: #F0F0F0;
                font-family: "Consolas", monospace;
            }
            QLineEdit:focus {
                border-color: #00ADB5;
            }
            QPushButton {
                background-color: #2D2D2D;
                border: 1px solid #3A3A3A;
                border-radius: 4px;
                padding: 6px 12px;
                color: #F0F0F0;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #3D3D3D;
                border-color: #00ADB5;
            }
            QPushButton#btn_primary {
                background-color: #00ADB5;
                border: none;
                color: #1E1E1E;
                font-weight: bold;
            }
            QPushButton#btn_primary:hover {
                background-color: #08D9D6;
            }
        """)

    def _setup_ui(self):
        # Create a scrollable container for settings
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        main_layout.addWidget(scroll)
        
        content = QWidget()
        scroll.setWidget(content)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)
        content.setLayout(layout)

        # Title
        title_label = QLabel("ALWAYS-ON LYRICS CONFIGURATION")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #00ADB5; margin-bottom: 10px;")
        layout.addWidget(title_label)

        # --- Group 1: Typography ---
        grp_font = QGroupBox("Typography")
        font_layout = QFormLayout()
        
        # Font Family
        self.combo_font = QComboBox()
        db = QFontDatabase()
        fonts = sorted(db.families())
        self.combo_font.addItems(fonts)
        font_layout.addRow("Font Family:", self.combo_font)
        
        # Font Size
        self.slider_font_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_font_size.setRange(12, 72)
        self.lbl_font_size_val = QLabel("26px")
        self.slider_font_size.valueChanged.connect(lambda v: self.lbl_font_size_val.setText(f"{v}px"))
        
        size_layout = QHBoxLayout()
        size_layout.addWidget(self.slider_font_size)
        size_layout.addWidget(self.lbl_font_size_val)
        font_layout.addRow("Font Size:", size_layout)

        # Font Colors
        self.btn_color = QPushButton("Choose...")
        self.btn_color.clicked.connect(self._choose_font_color)
        font_layout.addRow("Active Lyric Color:", self.btn_color)

        self.btn_color_next = QPushButton("Choose...")
        self.btn_color_next.clicked.connect(self._choose_font_color_next)
        font_layout.addRow("Next Lyric Color:", self.btn_color_next)

        grp_font.setLayout(font_layout)
        layout.addWidget(grp_font)

        # --- Group 2: Media Source Selector ---
        grp_media = QGroupBox("Media Channel Priority")
        media_form = QFormLayout()
        
        self.combo_media_source = QComboBox()
        self.combo_media_source.addItem("Default (Windows Active Session)")
        media_form.addRow("Preferred Source:", self.combo_media_source)
        
        grp_media.setLayout(media_form)
        layout.addWidget(grp_media)

        # --- Group 3: English Translation ---
        grp_trans = QGroupBox("English Translation (For Non-English Songs)")
        trans_form = QFormLayout()
        
        self.chk_translation = QCheckBox("Enable English Translation")
        trans_form.addRow("Translation Toggle:", self.chk_translation)
        
        # Translation Font Size
        self.slider_trans_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_trans_size.setRange(10, 50)
        self.lbl_trans_size_val = QLabel("22px")
        self.slider_trans_size.valueChanged.connect(lambda v: self.lbl_trans_size_val.setText(f"{v}px"))
        
        trans_size_layout = QHBoxLayout()
        trans_size_layout.addWidget(self.slider_trans_size)
        trans_size_layout.addWidget(self.lbl_trans_size_val)
        trans_form.addRow("Translation Font Size:", trans_size_layout)
        
        # Translation Color
        self.btn_color_trans = QPushButton("Choose...")
        self.btn_color_trans.clicked.connect(self._choose_trans_color)
        trans_form.addRow("Translation Color:", self.btn_color_trans)
        
        grp_trans.setLayout(trans_form)
        layout.addWidget(grp_trans)

        # --- Group 4: Overlay Size & Positioning ---
        grp_layout = QGroupBox("Layout & Positioning")
        layout_form = QFormLayout()

        # Width Percentage
        self.slider_width = QSlider(Qt.Orientation.Horizontal)
        self.slider_width.setRange(40, 100)
        self.lbl_width_val = QLabel("80%")
        self.slider_width.valueChanged.connect(lambda v: self.lbl_width_val.setText(f"{v}%"))
        
        width_layout = QHBoxLayout()
        width_layout.addWidget(self.slider_width)
        width_layout.addWidget(self.lbl_width_val)
        layout_form.addRow("Width Percent:", width_layout)

        # Height
        self.slider_height = QSlider(Qt.Orientation.Horizontal)
        self.slider_height.setRange(80, 350)
        self.lbl_height_val = QLabel("130px")
        self.slider_height.valueChanged.connect(lambda v: self.lbl_height_val.setText(f"{v}px"))
        
        height_layout = QHBoxLayout()
        height_layout.addWidget(self.slider_height)
        height_layout.addWidget(self.lbl_height_val)
        layout_form.addRow("Overlay Height:", height_layout)

        # Bottom Offset
        self.slider_offset = QSlider(Qt.Orientation.Horizontal)
        self.slider_offset.setRange(10, 500)
        self.lbl_offset_val = QLabel("60px")
        self.slider_offset.valueChanged.connect(lambda v: self.lbl_offset_val.setText(f"{v}px"))
        
        offset_layout = QHBoxLayout()
        offset_layout.addWidget(self.slider_offset)
        offset_layout.addWidget(self.lbl_offset_val)
        layout_form.addRow("Bottom Offset:", offset_layout)

        # Background Transparency
        self.slider_bg_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_bg_opacity.setRange(0, 100)
        self.lbl_opacity_val = QLabel("0%")
        self.slider_bg_opacity.valueChanged.connect(lambda v: self.lbl_opacity_val.setText(f"{v}%"))
        
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(self.slider_bg_opacity)
        opacity_layout.addWidget(self.lbl_opacity_val)
        layout_form.addRow("Background Opacity:", opacity_layout)

        # Reset Dragged Position
        self.btn_reset_pos = QPushButton("Reset Dragged Position")
        self.btn_reset_pos.clicked.connect(self._reset_position)
        layout_form.addRow("Overlay Layout Reset:", self.btn_reset_pos)

        grp_layout.setLayout(layout_form)
        layout.addWidget(grp_layout)

        # --- Group 5: Custom Keyboard Hotkeys ---
        grp_hotkeys = QGroupBox("Custom Global Keyboard Hotkeys")
        hotkeys_form = QFormLayout()
        
        self.txt_hotkey_toggle = QLineEdit()
        self.txt_hotkey_toggle.setPlaceholderText("e.g. Ctrl+Shift+L")
        hotkeys_form.addRow("Toggle Overlay:", self.txt_hotkey_toggle)
        
        self.txt_hotkey_clickthrough = QLineEdit()
        self.txt_hotkey_clickthrough.setPlaceholderText("e.g. Ctrl+Shift+C")
        hotkeys_form.addRow("Toggle Click-Through:", self.txt_hotkey_clickthrough)
        
        self.txt_hotkey_translation = QLineEdit()
        self.txt_hotkey_translation.setPlaceholderText("e.g. Ctrl+Shift+T")
        hotkeys_form.addRow("Toggle Translation:", self.txt_hotkey_translation)
        
        self.txt_hotkey_font_up = QLineEdit()
        self.txt_hotkey_font_up.setPlaceholderText("e.g. Ctrl+Shift+Up")
        hotkeys_form.addRow("Increase Font Size:", self.txt_hotkey_font_up)
        
        self.txt_hotkey_font_down = QLineEdit()
        self.txt_hotkey_font_down.setPlaceholderText("e.g. Ctrl+Shift+Down")
        hotkeys_form.addRow("Decrease Font Size:", self.txt_hotkey_font_down)
        
        lbl_info = QLabel("Hotkey format: Modifier+Key (e.g. Ctrl+Shift+Key). Re-registers instantly.")
        lbl_info.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        lbl_info.setStyleSheet("color: #888888; font-style: italic;")
        hotkeys_form.addRow(lbl_info)
        
        grp_hotkeys.setLayout(hotkeys_form)
        layout.addWidget(grp_hotkeys)

        # --- Group 6: Features & Interactions ---
        grp_features = QGroupBox("Features & Interactions")
        feat_layout = QVBoxLayout()
        
        self.chk_next_line = QCheckBox("Show Next Lyric Line")
        feat_layout.addWidget(self.chk_next_line)

        self.chk_click_through = QCheckBox("Click-Through Mode (Overlay ignores mouse)")
        feat_layout.addWidget(self.chk_click_through)

        self.chk_startup = QCheckBox("Start automatically with Windows")
        feat_layout.addWidget(self.chk_startup)

        grp_features.setLayout(feat_layout)
        layout.addWidget(grp_features)

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 15, 0, 0)
        
        self.btn_apply = QPushButton("Apply")
        self.btn_apply.clicked.connect(self._apply_settings)
        btn_layout.addWidget(self.btn_apply)
        
        self.btn_save = QPushButton("Save")
        self.btn_save.setObjectName("btn_primary")
        self.btn_save.clicked.connect(self._save_settings)
        btn_layout.addWidget(self.btn_save)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)

    def _load_config_into_ui(self):
        """Populates form controls with settings values."""
        # Fonts
        font_idx = self.combo_font.findText(self.config.get("font_family", "Segoe UI"), Qt.MatchFlag.MatchExactly)
        if font_idx >= 0:
            self.combo_font.setCurrentIndex(font_idx)
            
        self.slider_font_size.setValue(self.config.get("font_size", 26))
        self.lbl_font_size_val.setText(f"{self.config.get('font_size', 26)}px")
        
        self._update_color_button(self.btn_color, self.config.get("font_color", "#FFFFFF"))
        self._update_color_button(self.btn_color_next, self.config.get("font_color_next", "#B0B0B0"))

        # Translation
        self.chk_translation.setChecked(self.config.get("translation_enabled", True))
        self.slider_trans_size.setValue(self.config.get("translation_font_size", 22))
        self.lbl_trans_size_val.setText(f"{self.config.get('translation_font_size', 22)}px")
        self._update_color_button(self.btn_color_trans, self.config.get("font_color_trans", "#00ADB5"))

        # Positioning
        self.slider_width.setValue(self.config.get("width_percent", 80))
        self.lbl_width_val.setText(f"{self.config.get('width_percent', 80)}%")

        self.slider_height.setValue(self.config.get("height", 130))
        self.lbl_height_val.setText(f"{self.config.get('height', 130)}px")

        self.slider_offset.setValue(self.config.get("bottom_offset", 60))
        self.lbl_offset_val.setText(f"{self.config.get('bottom_offset', 60)}px")

        bg_opacity = int(self.config.get("bg_opacity", 0.0) * 100)
        self.slider_bg_opacity.setValue(bg_opacity)
        self.lbl_opacity_val.setText(f"{bg_opacity}%")

        # Hotkeys
        self.txt_hotkey_toggle.setText(self.config.get("hotkey_toggle", "Ctrl+Shift+L"))
        self.txt_hotkey_clickthrough.setText(self.config.get("hotkey_clickthrough", "Ctrl+Shift+C"))
        self.txt_hotkey_translation.setText(self.config.get("hotkey_toggle_translation", "Ctrl+Shift+T"))
        self.txt_hotkey_font_up.setText(self.config.get("hotkey_font_up", "Ctrl+Shift+Up"))
        self.txt_hotkey_font_down.setText(self.config.get("hotkey_font_down", "Ctrl+Shift+Down"))

        # Features
        self.chk_next_line.setChecked(self.config.get("show_next_line", True))
        self.chk_click_through.setChecked(self.config.get("click_through", True))
        
        # Check startup
        self.chk_startup.setChecked(self._check_startup_shortcut())

        # Media Preference Loader
        saved_pref = self.config.get("preferred_media_source", "")
        if saved_pref:
            self.combo_media_source.addItem(f"Preserved Preference: {saved_pref}", saved_pref)
            self.combo_media_source.setCurrentIndex(self.combo_media_source.count() - 1)

    def _update_color_button(self, btn, color_hex):
        btn.setStyleSheet(f"background-color: {color_hex}; color: {'#000000' if QColor(color_hex).lightness() > 130 else '#FFFFFF'}; border: 1px solid #5A5A5A;")
        btn.setText(color_hex)

    def _choose_font_color(self):
        color = QColorDialog.getColor(QColor(self.config.get("font_color", "#FFFFFF")), self, "Choose Active Font Color")
        if color.isValid():
            self.config["font_color"] = color.name().upper()
            self._update_color_button(self.btn_color, self.config["font_color"])

    def _choose_font_color_next(self):
        color = QColorDialog.getColor(QColor(self.config.get("font_color_next", "#B0B0B0")), self, "Choose Next Font Color")
        if color.isValid():
            self.config["font_color_next"] = color.name().upper()
            self._update_color_button(self.btn_color_next, self.config["font_color_next"])

    def _choose_trans_color(self):
        color = QColorDialog.getColor(QColor(self.config.get("font_color_trans", "#00ADB5")), self, "Choose Translation Font Color")
        if color.isValid():
            self.config["font_color_trans"] = color.name().upper()
            self._update_color_button(self.btn_color_trans, self.config["font_color_trans"])

    def _reset_position(self):
        self.config["x"] = None
        self.config["y"] = None
        QMessageBox.information(self, "Reset Position", "Overlay position successfully reset to bottom-center. Apply or Save to commit changes.")

    def update_available_sources(self, sources: list):
        """Dynamically populates the media source dropdown in real-time."""
        current_data = self.combo_media_source.itemData(self.combo_media_source.currentIndex())
        self.combo_media_source.clear()
        
        self.combo_media_source.addItem("Default (Windows Active Session)", "")
        
        unique_sources = sorted(list(set(sources)))
        for src in unique_sources:
            if not src:
                continue
            clean_name = src
            if "spotify" in src.lower():
                clean_name = "Spotify Player"
            elif "chrome" in src.lower():
                clean_name = "Google Chrome (YouTube/Web)"
            elif "msedge" in src.lower():
                clean_name = "Microsoft Edge (YouTube/Web)"
            
            self.combo_media_source.addItem(f"{clean_name} ({src[:12]}...)", src)
            
        # Re-select the previously active/saved source
        saved_pref = self.config.get("preferred_media_source", "")
        idx = -1
        
        # Try to match the saved preference
        if saved_pref:
            for i in range(self.combo_media_source.count()):
                if self.combo_media_source.itemData(i) == saved_pref:
                    idx = i
                    break
                    
        # If not matched, try to match the currently selected dropdown text
        if idx == -1 and current_data:
            for i in range(self.combo_media_source.count()):
                if self.combo_media_source.itemData(i) == current_data:
                    idx = i
                    break
                    
        if idx >= 0:
            self.combo_media_source.setCurrentIndex(idx)
        elif saved_pref:
            # Add saved preference as a preserved offline option so they don't lose it!
            self.combo_media_source.addItem(f"Preserved Preference: {saved_pref[:20]}...", saved_pref)
            self.combo_media_source.setCurrentIndex(self.combo_media_source.count() - 1)

    def _gather_ui_config(self) -> dict:
        """Gathers values from UI controls and builds a config dict."""
        opacity = self.slider_bg_opacity.value() / 100.0
        
        # Background color formatting: rgba(0, 0, 0, opacity)
        bg_color = f"rgba(0, 0, 0, {opacity})"
        
        # Extract preferred media source App ID from combo box userdata
        preferred_src = self.combo_media_source.itemData(self.combo_media_source.currentIndex()) or ""
        
        return {
            "font_family": self.combo_font.currentText(),
            "font_size": self.slider_font_size.value(),
            "font_color": self.config.get("font_color", "#FFFFFF"),
            "font_color_trans": self.config.get("font_color_trans", "#00ADB5"),
            "font_color_next": self.config.get("font_color_next", "#B0B0B0"),
            "bg_color": bg_color,
            "bg_opacity": opacity,
            "width_percent": self.slider_width.value(),
            "height": self.slider_height.value(),
            "bottom_offset": self.slider_offset.value(),
            "show_next_line": self.chk_next_line.isChecked(),
            "click_through": self.chk_click_through.isChecked(),
            "translation_enabled": self.chk_translation.isChecked(),
            "translation_font_size": self.slider_trans_size.value(),
            "preferred_media_source": preferred_src,
            "x": self.config.get("x"), # Retain custom coordinates
            "y": self.config.get("y"),
            # Customizable keyboard hotkeys
            "hotkey_toggle": self.txt_hotkey_toggle.text().strip(),
            "hotkey_clickthrough": self.txt_hotkey_clickthrough.text().strip(),
            "hotkey_toggle_translation": self.txt_hotkey_translation.text().strip(),
            "hotkey_font_up": self.txt_hotkey_font_up.text().strip(),
            "hotkey_font_down": self.txt_hotkey_font_down.text().strip()
        }

    def _apply_settings(self):
        """Gathers settings and fires the signal so the overlay updates immediately."""
        gathered = self._gather_ui_config()
        self.config.update(gathered)
        self.config_changed.emit(self.config)
        self._toggle_startup(self.chk_startup.isChecked())

    def _save_settings(self):
        """Applies, saves to disk via controller, and closes."""
        self._apply_settings()
        self.close()

    # --- Startup management ---
    def _get_startup_shortcut_path(self) -> str:
        startup_dir = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
        return os.path.join(startup_dir, "LyricsOverlay.lnk")

    def _check_startup_shortcut(self) -> bool:
        return os.path.exists(self._get_startup_shortcut_path())

    def _toggle_startup(self, enable: bool):
        shortcut_path = self._get_startup_shortcut_path()
        if enable:
            if not os.path.exists(shortcut_path):
                try:
                    # Retrieve the path to the executable or the main.py running script
                    if getattr(sys, 'frozen', False):
                        target = os.path.abspath(sys.executable)
                        args = ""
                    else:
                        target = os.path.abspath(sys.executable)
                        args = f'"{os.path.abspath(sys.argv[0])}"'
                        
                    # Create shortcut using Windows PowerShell
                    ps_cmd = f"$s = (New-Object -ComObject WScript.Shell).CreateShortcut('{shortcut_path}'); $s.TargetPath = '{target}'; "
                    if args:
                        ps_cmd += f"$s.Arguments = '{args}'; "
                    ps_cmd += "$s.WorkingDirectory = '" + os.path.dirname(target if not args else os.path.abspath(sys.argv[0])) + "'; $s.Save()"
                    
                    subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, check=True)
                    logging.info("Startup shortcut created.")
                except Exception as e:
                    logging.error(f"Failed to create startup shortcut: {e}")
                    QMessageBox.warning(self, "Startup Settings", f"Failed to enable startup: {e}")
        else:
            if os.path.exists(shortcut_path):
                try:
                    os.remove(shortcut_path)
                    logging.info("Startup shortcut removed.")
                except Exception as e:
                    logging.error(f"Failed to remove startup shortcut: {e}")
                    QMessageBox.warning(self, "Startup Settings", f"Failed to disable startup: {e}")
