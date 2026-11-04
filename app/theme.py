"""MOVEXA dark theme: neutral editor grays with brand magenta/cyan accents.

Derived from the MOVEXA logo gradient but restrained: accents carry meaning
(primary buttons, selection, focus); structure stays neutral so the canvas
is the brightest surface in the window.
"""

BRAND = {
    "bg":            "#131318",
    "bg_alt":        "#17171e",
    "bg_panel":      "#1b1b23",
    "bg_input":      "#22222c",
    "bg_hover":      "#2a2a36",
    "border":        "#2a2a36",
    "border_strong": "#3a3a4a",
    "magenta":       "#c53ef5",
    "purple":        "#8b5cf6",
    "cyan":          "#22d3ee",
    "text":          "#e8e8f0",
    "text_muted":    "#8f8fa8",
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
QGroupBox {{
    background: transparent;
    border: 1px solid {BRAND['border']};
    border-radius: 7px;
    margin-top: 12px;
    padding: 8px 6px 4px 6px;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 3px; }}

/* ---- native menubar --------------------------------------------------- */
QMenuBar {{
    background: {BRAND['bg_alt']};
    border-bottom: 1px solid {BRAND['border']};
    padding: 1px 4px;
}}
QMenuBar::item {{
    background: transparent;
    padding: 5px 10px;
    border-radius: 4px;
}}
QMenuBar::item:selected {{ background: {BRAND['bg_input']}; }}
QMenu {{
    background: {BRAND['bg_panel']};
    border: 1px solid {BRAND['border_strong']};
    border-radius: 8px;
    padding: 5px 3px;
}}
QMenu::item {{ padding: 6px 24px 6px 14px; border-radius: 4px; }}
QMenu::item:selected {{ background: {BRAND['purple']}; color: #ffffff; }}
QMenu::item:disabled {{ color: {BRAND['text_muted']}; }}
QMenu::separator {{ height: 1px; background: {BRAND['border']}; margin: 5px 8px; }}

/* ---- buttons ---------------------------------------------------------- */
QPushButton {{
    background: {BRAND['bg_input']};
    border: 1px solid {BRAND['border']};
    border-radius: 6px;
    padding: 7px 14px;
}}
QPushButton:hover {{ background: {BRAND['bg_hover']}; border-color: {BRAND['border_strong']}; }}
QPushButton:pressed {{ background: {BRAND['bg_panel']}; }}
QPushButton:disabled {{ color: {BRAND['text_muted']}; border-color: {BRAND['border']}; }}
QPushButton:focus {{ border-color: {BRAND['cyan']}; }}

QPushButton#primary, QPushButton#hero {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {BRAND['magenta']}, stop:1 {BRAND['cyan']});
    border: none;
    color: #ffffff;
    font-weight: 600;
}}
QPushButton#primary:hover, QPushButton#hero:hover {{
    background: {BRAND['purple']};
}}
QPushButton#hero {{
    border-radius: 10px;
    font-size: 15px;
    font-weight: 700;
    min-height: 56px;
}}
QPushButton#secondary {{
    background: {BRAND['bg_input']};
    border: 1px solid {BRAND['border']};
    border-radius: 10px;
    min-height: 56px;
    font-size: 14px;
}}
QPushButton#secondary:hover {{ border-color: {BRAND['cyan']}; background: {BRAND['bg_hover']}; }}
QPushButton#topbarBtn {{
    background: transparent;
    border: 1px solid transparent;
    padding: 6px 12px;
}}
QPushButton#topbarBtn:hover {{ background: {BRAND['bg_input']}; border-color: {BRAND['border']}; }}

/* ---- dashboard --------------------------------------------------------- */
QFrame#brandPanel {{
    background: {BRAND['bg_alt']};
    border-right: 1px solid {BRAND['border']};
}}
QWidget#cardsBackground {{ background: {BRAND['bg_alt']}; }}
QFrame#card {{
    background: {BRAND['bg_panel']};
    border: 1px solid {BRAND['border']};
    border-radius: 10px;
}}
QFrame#card:hover {{ border-color: {BRAND['cyan']}; background: {BRAND['bg_hover']}; }}
QFrame#cardAccent {{
    border: none;
    border-left: 3px solid {BRAND['magenta']};
    border-radius: 0;
    background: transparent;
}}
QLabel#cardTitle {{ font-size: 14px; font-weight: 600; }}
QLabel#cardMeta {{ color: {BRAND['text_muted']}; font-size: 11px; }}
QPushButton#cardRemove {{
    background: transparent; border: none; border-radius: 12px;
    color: {BRAND['text_muted']}; font-size: 12px; padding: 0;
}}
QPushButton#cardRemove:hover {{ background: {BRAND['danger']}; color: #ffffff; }}
QLabel#sectionHeader {{ font-size: 15px; font-weight: 700; }}
QLabel#hint {{ color: {BRAND['text_muted']}; }}
QLabel#title {{ font-size: 28px; font-weight: 700; letter-spacing: 1px; }}
QLabel#subtitle {{ color: {BRAND['text_muted']}; font-size: 14px; }}

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
QProgressBar::chunk {{ background: {BRAND['cyan']}; border-radius: 3px; }}

/* ---- workspace docks ---------------------------------------------------- */
QFrame#topbar {{
    background: {BRAND['bg_alt']};
    border-bottom: 1px solid {BRAND['border']};
}}
QLabel#topbarTitle {{ color: {BRAND['cyan']}; font-size: 14px; font-weight: 600; }}
QWidget#rail {{ background: {BRAND['bg_alt']}; border-right: 1px solid {BRAND['border']}; }}
QToolButton#railBtn {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    font-size: 16px;
    color: {BRAND['text_muted']};
}}
QToolButton#railBtn:hover {{ background: {BRAND['bg_input']}; color: {BRAND['text']}; }}
QToolButton#railBtn:checked {{
    background: {BRAND['bg_input']};
    border-color: {BRAND['cyan']};
    color: {BRAND['cyan']};
}}
QLabel#panelTitle {{ font-size: 14px; font-weight: 700; }}
QLabel#agentChip {{
    background: transparent; border: 1px solid {BRAND['border']};
    border-radius: 9px; padding: 2px 8px;
    color: {BRAND['text_muted']}; font-size: 11px;
}}
QListWidget#agentLog {{
    background: {BRAND['bg_panel']};
    border: 1px solid {BRAND['border']};
    border-radius: 7px;
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
    border-color: {BRAND['cyan']}; background: {BRAND['bg_hover']};
}}
QPushButton#transportPlay {{ font-size: 14px; }}
QLabel#frameCounter {{
    background: {BRAND['bg_input']};
    border: 1px solid {BRAND['border']};
    border-radius: 5px;
    color: {BRAND['cyan']};
}}
QFrame#playerBar {{
    background: {BRAND['bg_panel']};
    border-bottom: 1px solid {BRAND['border']};
}}
QLabel#timecode {{
    color: {BRAND['cyan']};
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    font-size: 12px;
}}

/* ---- lists (assets, scenes) -------------------------------------------- */
QListWidget {{
    background: {BRAND['bg_panel']};
    border: 1px solid {BRAND['border']};
    border-radius: 7px;
    outline: none;
    padding: 4px;
}}
QListWidget::item {{ border: 1px solid transparent; border-radius: 6px; padding: 4px; }}
QListWidget::item:hover {{ background: {BRAND['bg_input']}; }}
QListWidget::item:selected {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {BRAND['magenta']}, stop:1 {BRAND['purple']});
    color: #ffffff;
}}
QListWidget#sceneList {{
    background: transparent;
    border: 1px solid {BRAND['border']};
}}
QListWidget#sceneList::item:selected {{ background: {BRAND['bg_hover']}; color: {BRAND['cyan']}; }}

/* ---- inputs ------------------------------------------------------------ */
QLineEdit, QDoubleSpinBox, QSpinBox {{
    background: {BRAND['bg_input']};
    border: 1px solid {BRAND['border']};
    border-radius: 5px;
    padding: 4px 8px;
    selection-background-color: {BRAND['purple']};
}}
QLineEdit:hover, QDoubleSpinBox:hover, QSpinBox:hover {{ border-color: {BRAND['border_strong']}; }}
QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {{
    border-color: {BRAND['cyan']};
    background: {BRAND['bg_panel']};
}}
QDoubleSpinBox::up-button, QSpinBox::up-button,
QDoubleSpinBox::down-button, QSpinBox::down-button {{
    background: transparent; border: none; width: 16px;
}}
QDoubleSpinBox::up-arrow:hover, QSpinBox::up-arrow:hover {{ color: {BRAND['cyan']}; }}
QComboBox {{
    background: {BRAND['bg_input']};
    border: 1px solid {BRAND['border']};
    border-radius: 5px;
    padding: 4px 8px;
}}
QComboBox:focus {{ border-color: {BRAND['cyan']}; }}
QComboBox QAbstractItemView {{
    background: {BRAND['bg_panel']};
    border: 1px solid {BRAND['border_strong']};
    selection-background-color: {BRAND['purple']};
}}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {BRAND['border_strong']};
    border-radius: 4px;
    background: {BRAND['bg_input']};
}}
QCheckBox::indicator:checked {{ background: {BRAND['cyan']}; }}

QLabel#panelHeader {{
    font-size: 12px; font-weight: 700; color: {BRAND['text_muted']};
    letter-spacing: 1px; padding: 4px 2px;
}}

/* ---- sliders / splitters / scrollbar ------------------------------------ */
QSlider::groove:horizontal {{ height: 5px; border-radius: 2px; background: {BRAND['bg_input']}; }}
QSlider::handle:horizontal {{
    background: {BRAND['cyan']}; width: 11px; margin: -4px 0; border-radius: 5px;
}}
QSlider::handle:horizontal:hover {{ background: #ffffff; }}
QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {BRAND['magenta']}, stop:1 {BRAND['cyan']});
    border-radius: 2px;
}}
QSplitter::handle {{ background: {BRAND['bg']}; width: 2px; }}
QStatusBar {{
    background: {BRAND['bg_alt']};
    border-top: 1px solid {BRAND['border']};
    color: {BRAND['text_muted']};
}}
QScrollArea {{ border: none; }}
QScrollBar:vertical {{ background: transparent; width: 9px; margin: 2px; }}
QScrollBar::handle:vertical {{
    background: {BRAND['bg_input']}; border-radius: 3px; min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: {BRAND['purple']}; }}
QScrollBar:horizontal {{ background: transparent; height: 9px; margin: 2px; }}
QScrollBar::handle:horizontal {{
    background: {BRAND['bg_input']}; border-radius: 3px; min-width: 24px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}

/* ---- palette + toasts --------------------------------------------------- */
QDialog {{ background: {BRAND['bg_panel']}; border: 1px solid {BRAND['border_strong']}; }}
QLineEdit#paletteSearch {{
    font-size: 15px; padding: 8px 10px;
    background: {BRAND['bg_input']};
    border: 1px solid {BRAND['purple']};
    border-radius: 7px;
}}
QListWidget#paletteList {{
    background: {BRAND['bg_input']};
    border: 1px solid {BRAND['border']};
    border-radius: 7px;
    font-size: 14px;
}}
QListWidget#paletteList::item {{ padding: 8px 10px; border-radius: 5px; }}
QListWidget#paletteList::item:hover {{ background: {BRAND['bg_hover']}; }}
QFrame#toast {{
    background: {BRAND['bg_panel']};
    border: 1px solid {BRAND['cyan']};
    border-radius: 8px;
}}
QLabel#toastText {{ border: none; font-size: 13px; max-width: 360px; }}
"""
