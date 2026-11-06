"""MOVEXA premium dark theme: graphite surfaces, thin borders, electric accent.

Design system (review round):
- Background: dark graphite, surfaces lift one step at a time.
- Accent: electric blue, violet reserved for secondary highlights.
- Corners: 8-12px; borders 1px, subtle. Canvas stays the brightest surface.
"""

BRAND = {
    "bg":            "#121216",
    "bg_alt":        "#17171c",
    "bg_panel":      "#1c1c22",
    "bg_input":      "#232329",
    "bg_hover":      "#2a2a33",
    "border":        "#2a2a33",
    "border_strong": "#3a3a46",
    "blue":          "#3b82f6",   # primary accent (electric blue)
    "blue_light":    "#60a5fa",
    "violet":        "#8b5cf6",
    "text":          "#e8e8f0",
    "text_muted":    "#9a9ab0",
    "danger":        "#f43f5e",
}

QSS = f"""
QWidget {{
    background: {BRAND['bg']};
    color: {BRAND['text']};
    font-size: 13px;
    font-family: "Segoe UI";
}}
/* Labels sit on panels, cards, toolbars - never paint their own chips. */
QLabel {{ background: transparent; }}
QCheckBox, QFormLayout {{ background: transparent; }}
QToolTip {{
    background: {BRAND['bg_input']};
    color: {BRAND['text']};
    border: 1px solid {BRAND['border_strong']};
    border-radius: 6px;
    padding: 4px 8px;
}}
QGroupBox {{
    background: {BRAND['bg_panel']};
    border: 1px solid {BRAND['border']};
    border-radius: 8px;
    margin-top: 13px;
    padding: 10px 8px 6px 8px;
}}
QGroupBox::title {{
    subcontrol-origin: margin; left: 9px; padding: 0 4px;
    color: {BRAND['text_muted']}; font-weight: 600;
}}

/* ---- native menubar --------------------------------------------------- */
QMenuBar {{
    background: {BRAND['bg_alt']};
    border-bottom: 1px solid {BRAND['border']};
    padding: 1px 4px;
}}
QMenuBar::item {{
    background: transparent;
    padding: 5px 10px;
    border-radius: 6px;
}}
QMenuBar::item:selected {{ background: {BRAND['bg_input']}; }}
QMenu {{
    background: {BRAND['bg_panel']};
    border: 1px solid {BRAND['border_strong']};
    border-radius: 10px;
    padding: 6px 4px;
}}
QMenu::item {{ padding: 6px 26px 6px 14px; border-radius: 6px; }}
QMenu::item:selected {{ background: {BRAND['blue']}; color: #ffffff; }}
QMenu::item:disabled {{ color: {BRAND['text_muted']}; }}
QMenu::separator {{ height: 1px; background: {BRAND['border']}; margin: 5px 8px; }}

/* ---- buttons ---------------------------------------------------------- */
QPushButton {{
    background: {BRAND['bg_input']};
    border: 1px solid {BRAND['border']};
    border-radius: 8px;
    padding: 6px 13px;
}}
QPushButton:hover {{ background: {BRAND['bg_hover']}; border-color: {BRAND['border_strong']}; }}
QPushButton:pressed {{ background: {BRAND['bg_panel']}; }}
QPushButton:disabled {{ color: {BRAND['text_muted']}; border-color: {BRAND['border']}; }}
QPushButton:focus {{ border-color: {BRAND['blue']}; }}

QPushButton#primary, QPushButton#hero {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {BRAND['blue']}, stop:1 {BRAND['violet']});
    border: none;
    color: #ffffff;
    font-weight: 600;
}}
QPushButton#primary:hover, QPushButton#hero:hover {{
    background: {BRAND['blue_light']};
}}
QPushButton#hero {{
    border-radius: 12px;
    font-size: 15px;
    font-weight: 700;
    min-height: 52px;
}}
QPushButton#secondary {{
    background: {BRAND['bg_input']};
    border: 1px solid {BRAND['border_strong']};
    border-radius: 12px;
    min-height: 52px;
    font-size: 14px;
}}
QPushButton#secondary:hover {{ border-color: {BRAND['blue_light']}; background: {BRAND['bg_hover']}; }}
QPushButton#topbarBtn {{
    background: transparent;
    border: 1px solid transparent;
    padding: 5px 10px;
    border-radius: 6px;
}}
QPushButton#topbarBtn:hover {{ background: {BRAND['bg_input']}; border-color: {BRAND['border']}; }}
QPushButton#topbarBtn:pressed {{ background: {BRAND['bg_panel']}; }}

/* ---- dashboard --------------------------------------------------------- */
QFrame#brandPanel {{
    background: {BRAND['bg_alt']};
    border-right: 1px solid {BRAND['border']};
}}
QWidget#cardsBackground {{ background: {BRAND['bg_alt']}; }}
QFrame#card {{
    background: {BRAND['bg_panel']};
    border: 1px solid {BRAND['border']};
    border-radius: 12px;
}}
QFrame#card:hover {{ border-color: {BRAND['blue']}; background: {BRAND['bg_hover']}; }}
QLabel#cardTitle {{ font-size: 13px; font-weight: 600; }}
QLabel#cardMeta {{ color: {BRAND['text_muted']}; font-size: 11px; }}
QPushButton#cardRemove {{
    background: transparent; border: none; border-radius: 12px;
    color: {BRAND['text_muted']}; font-size: 12px; padding: 0;
}}
QPushButton#cardRemove:hover {{ background: {BRAND['danger']}; color: #ffffff; }}
QLabel#sectionHeader {{ font-size: 14px; font-weight: 700; }}
QLabel#hint {{ color: {BRAND['text_muted']}; }}
QLabel#title {{ font-size: 24px; font-weight: 700; letter-spacing: 1px; }}
QLabel#subtitle {{ color: {BRAND['text_muted']}; font-size: 13px; }}

/* ---- loading ----------------------------------------------------------- */
QFrame#checkFrame {{
    background: {BRAND['bg_panel']};
    border: 1px solid {BRAND['border']};
    border-radius: 10px;
}}
QProgressBar {{
    background: {BRAND['bg_input']};
    border: none;
    border-radius: 3px;
    height: 6px;
}}
QProgressBar::chunk {{ background: {BRAND['blue']}; border-radius: 3px; }}

/* ---- workspace docks ---------------------------------------------------- */
QFrame#topbar {{
    background: {BRAND['bg_alt']};
    border-bottom: 1px solid {BRAND['border']};
}}
QLabel#topbarTitle {{ color: {BRAND['blue_light']}; font-size: 13px; font-weight: 600; }}
QLabel#topbarGroup {{ color: {BRAND['text_muted']}; font-size: 10px; padding: 0 2px; }}
QWidget#rail {{ background: {BRAND['bg_alt']}; border-right: 1px solid {BRAND['border']}; }}
QToolButton#railBtn {{
    background: transparent;
    border: none;
    border-radius: 8px;
    font-size: 15px;
    color: {BRAND['text_muted']};
}}
QToolButton#railBtn:hover {{ background: {BRAND['bg_input']}; color: {BRAND['text']}; }}
QToolButton#railBtn:checked {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {BRAND['blue']}, stop:1 {BRAND['violet']});
    color: #ffffff;
}}
QLabel#panelTitle {{ font-size: 13px; font-weight: 700; }}
QLabel#agentChip {{
    background: transparent; border: 1px solid {BRAND['border_strong']};
    border-radius: 9px; padding: 2px 8px;
    color: {BRAND['text_muted']}; font-size: 11px;
}}
QListWidget#agentLog {{
    background: {BRAND['bg_panel']};
    border: 1px solid {BRAND['border']};
    border-radius: 8px;
}}
QListWidget#agentLog::item {{ padding: 4px; border-radius: 0; }}
QListWidget#agentLog::item:hover {{ background: transparent; }}
QFrame#sceneDock {{
    background: {BRAND['bg_alt']};
    border-bottom: 1px solid {BRAND['border']};
}}
QFrame#transport {{
    background: {BRAND['bg_alt']};
    border-top: 1px solid {BRAND['border']};
}}
QPushButton#transportBtn, QPushButton#transportPlay {{
    background: {BRAND['bg_input']};
    border: 1px solid {BRAND['border']};
    border-radius: 6px;
    padding: 0;
}}
QPushButton#transportBtn:hover, QPushButton#transportPlay:hover {{
    border-color: {BRAND['blue']}; background: {BRAND['bg_hover']};
}}
QPushButton#transportPlay {{ font-size: 14px; }}
QLabel#frameCounter {{
    background: {BRAND['bg_input']};
    border: 1px solid {BRAND['border']};
    border-radius: 6px;
    color: {BRAND['blue_light']};
}}
QFrame#playerBar {{
    background: {BRAND['bg_panel']};
    border-bottom: 1px solid {BRAND['border']};
}}
QLabel#timecode {{
    color: {BRAND['blue_light']};
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    font-size: 12px;
}}
QLabel#panelHeader {{
    font-size: 12px; font-weight: 700; color: {BRAND['text_muted']};
    letter-spacing: 1px; padding: 4px 2px;
}}

/* ---- inspector tabs: dark tabs, accent marks the active one ------------- */
QTabWidget::pane {{
    border: 1px solid {BRAND['border']};
    border-radius: 8px;
    top: -1px;
    background: {BRAND['bg']};
}}
QTabBar::tab {{
    background: {BRAND['bg_input']};
    color: {BRAND['text_muted']};
    border: 1px solid {BRAND['border']};
    border-bottom: none;
    padding: 5px 16px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}}
QTabBar::tab:selected {{
    background: {BRAND['bg_panel']};
    color: #ffffff;
    border-bottom: 2px solid {BRAND['blue']};
    padding-bottom: 3px;
    font-weight: 600;
}}
QTabBar::tab:hover:!selected {{ background: {BRAND['bg_hover']}; color: {BRAND['text']}; }}

/* ---- lists (assets, scenes) -------------------------------------------- */
QListWidget {{
    background: {BRAND['bg_panel']};
    border: 1px solid {BRAND['border']};
    border-radius: 8px;
    outline: none;
    padding: 4px;
}}
QListWidget::item {{ border: 1px solid transparent; border-radius: 6px; padding: 4px; }}
QListWidget::item:hover {{ background: {BRAND['bg_input']}; }}
QListWidget::item:selected {{
    background: {BRAND['blue']};
    color: #ffffff;
}}
QListWidget#sceneList {{
    background: transparent;
    border: 1px solid {BRAND['border']};
}}
QListWidget#sceneList::item:selected {{ background: {BRAND['bg_hover']}; color: {BRAND['blue_light']}; }}

/* ---- inputs ------------------------------------------------------------ */
QLineEdit, QDoubleSpinBox, QSpinBox {{
    background: {BRAND['bg_input']};
    border: 1px solid {BRAND['border']};
    border-radius: 6px;
    padding: 4px 8px;
    selection-background-color: {BRAND['violet']};
}}
QLineEdit:hover, QDoubleSpinBox:hover, QSpinBox:hover {{ border-color: {BRAND['border_strong']}; }}
QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {{
    border-color: {BRAND['blue']};
    background: {BRAND['bg_panel']};
}}
QDoubleSpinBox::up-button, QSpinBox::up-button,
QDoubleSpinBox::down-button, QSpinBox::down-button {{
    background: transparent; border: none; width: 16px;
}}
QDoubleSpinBox::up-arrow:hover, QSpinBox::up-arrow:hover {{ color: {BRAND['blue_light']}; }}
QComboBox {{
    background: {BRAND['bg_input']};
    border: 1px solid {BRAND['border']};
    border-radius: 6px;
    padding: 4px 8px;
}}
QComboBox:focus {{ border-color: {BRAND['blue']}; }}
QComboBox QAbstractItemView {{
    background: {BRAND['bg_panel']};
    border: 1px solid {BRAND['border_strong']};
    selection-background-color: {BRAND['violet']};
}}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {BRAND['border_strong']};
    border-radius: 5px;
    background: {BRAND['bg_input']};
}}
QCheckBox::indicator:checked {{ background: {BRAND['blue']}; }}

/* ---- sliders / splitters / scrollbar ------------------------------------ */
QSlider::groove:horizontal {{ height: 5px; border-radius: 2px; background: {BRAND['bg_input']}; }}
QSlider::handle:horizontal {{
    background: {BRAND['blue']}; width: 11px; margin: -4px 0; border-radius: 5px;
}}
QSlider::handle:horizontal:hover {{ background: {BRAND['blue_light']}; }}
QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {BRAND['blue']}, stop:1 {BRAND['violet']});
    border-radius: 2px;
}}
QSplitter::handle {{ background: {BRAND['bg_alt']}; width: 3px; }}
QSplitter::handle:hover {{ background: {BRAND['blue']}; }}
QSplitter::handle:vertical {{ height: 3px; }}
QStatusBar {{
    background: {BRAND['bg_alt']};
    border-top: 1px solid {BRAND['border']};
    color: {BRAND['text_muted']};
}}
QScrollArea {{ border: none; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{
    background: {BRAND['bg_input']}; border-radius: 3px; min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: {BRAND['violet']}; }}
QScrollBar:horizontal {{ background: transparent; height: 8px; margin: 2px; }}
QScrollBar::handle:horizontal {{
    background: {BRAND['bg_input']}; border-radius: 3px; min-width: 24px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}

/* ---- palette + toasts --------------------------------------------------- */
QDialog {{ background: {BRAND['bg_panel']}; border: 1px solid {BRAND['border_strong']}; }}
QLineEdit#paletteSearch {{
    font-size: 15px; padding: 8px 10px;
    background: {BRAND['bg_input']};
    border: 1px solid {BRAND['blue']};
    border-radius: 8px;
}}
QListWidget#paletteList {{
    background: {BRAND['bg_input']};
    border: 1px solid {BRAND['border']};
    border-radius: 8px;
    font-size: 14px;
}}
QListWidget#paletteList::item {{ padding: 8px 10px; border-radius: 6px; }}
QListWidget#paletteList::item:hover {{ background: {BRAND['bg_hover']}; }}
QFrame#toast {{
    background: {BRAND['bg_panel']};
    border: 1px solid {BRAND['blue']};
    border-radius: 10px;
}}
QLabel#toastText {{ border: none; font-size: 13px; max-width: 360px; }}
"""
