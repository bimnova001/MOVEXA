"""Dark neon theme derived from the MOVEXA logo gradient (magenta -> cyan)."""

BRAND = {
    "bg":            "#0a0a14",
    "bg_alt":        "#12121f",
    "bg_panel":      "#17172a",
    "bg_input":      "#1e1e33",
    "border":        "#2c2c4a",
    "magenta":       "#c53ef5",
    "purple":        "#8b5cf6",
    "cyan":          "#22d3ee",
    "text":          "#e8e8f4",
    "text_muted":    "#9a9ab8",
    "danger":        "#f43f5e",
}

QSS = f"""
QWidget {{ background: {BRAND['bg']}; color: {BRAND['text']}; font-size: 13px; }}

QMenuBar {{ background: {BRAND['bg_alt']}; border-bottom: 1px solid {BRAND['border']}; }}
QMenuBar::item:selected {{ background: {BRAND['bg_panel']}; }}
QMenu {{ background: {BRAND['bg_panel']}; border: 1px solid {BRAND['border']}; }}
QMenu::item {{ padding: 4px 18px; }}
QMenu::item:selected {{ background: {BRAND['purple']}; }}

 QPushButton {{
    background: {BRAND['bg_input']};
    border: 1px solid {BRAND['border']};
    border-radius: 6px;
    padding: 7px 14px;
}}
QPushButton:hover {{ border-color: {BRAND['purple']}; }}
QPushButton:pressed {{ background: {BRAND['bg_panel']}; }}
QPushButton:disabled {{ color: {BRAND['text_muted']}; border-color: {BRAND['border']}; }}
QToolButton {{
    background: {BRAND['bg_input']};
    border: 1px solid {BRAND['border']};
    border-radius: 6px;
    padding: 6px 12px;
}}
QToolButton:hover {{ border-color: {BRAND['purple']}; }}
QPushButton#primary {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {BRAND['magenta']}, stop:1 {BRAND['cyan']});
    border: none;
    color: #ffffff;
    font-weight: 600;
}}
QPushButton#primary:hover {{ background: {BRAND['purple']}; }}

QPushButton#hero {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {BRAND['magenta']}, stop:1 {BRAND['purple']});
    border: none;
    border-radius: 9px;
    color: #ffffff;
    font-size: 15px;
    font-weight: 700;
}}
QPushButton#hero:hover {{ background: {BRAND['purple']}; }}
QPushButton#secondary {{
    background: {BRAND['bg_input']};
    border: 1px solid {BRAND['border']};
    border-radius: 9px;
    font-size: 14px;
}}
QPushButton#secondary:hover {{ border-color: {BRAND['cyan']}; }}

/* ---- dashboard cards ------------------------------------------------- */
QFrame#card {{
    background: {BRAND['bg_panel']};
    border: 1px solid {BRAND['border']};
    border-radius: 9px;
}}
QFrame#card:hover {{
    border: 1px solid {BRAND['cyan']};
    background: {BRAND['bg_input']};
}}
QWidget#cardsBackground {{ background: {BRAND['bg_alt']}; }}
QFrame#brandPanel {{
    background: {BRAND['bg_alt']};
    border-right: 1px solid {BRAND['border']};
}}
QLabel#cardTitle {{ background: transparent; border: none;
    font-size: 14px; font-weight: 600; color: {BRAND['text']}; }}
QLabel#cardMeta {{ background: transparent; border: none;
    color: {BRAND['text_muted']}; font-size: 11px; }}
QLabel#sectionHeader {{ font-size: 15px; font-weight: 700; padding: 2px 0; }}
QLabel#hint {{ color: {BRAND['text_muted']}; }}

/* ---- loading screen -------------------------------------------------- */
QFrame#checkFrame {{
    background: {BRAND['bg_panel']};
    border: 1px solid {BRAND['border']};
    border-radius: 9px;
}}
QLabel#checkRow {{ background: transparent; border: none; font-size: 13px; }}
QProgressBar {{
    background: {BRAND['bg_input']};
    border: none;
    border-radius: 3px;
    height: 6px;
}}
QProgressBar::chunk {{ background: {BRAND['cyan']}; border-radius: 3px; }}

/* ---- workspace -------------------------------------------------------- */
QFrame#topbar {{
    background: {BRAND['bg_alt']};
    border-bottom: 1px solid {BRAND['border']};
}}
QLabel#topbarTitle {{
    background: transparent; border: none;
    font-size: 14px; font-weight: 600; color: {BRAND['cyan']};
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
QPushButton#transportBtn:hover,
QPushButton#transportPlay:hover {{ border-color: {BRAND['cyan']}; }}
QPushButton#transportPlay {{ font-size: 14px; }}
QLabel#frameCounter {{
    background: {BRAND['bg_input']};
    border: 1px solid {BRAND['border']};
    border-radius: 5px;
    color: {BRAND['cyan']};
    font-variant-numeric: tabular-nums;
}}
QSlider::groove:horizontal {{
    height: 5px;
    border-radius: 2px;
    background: {BRAND['bg_input']};
}}
QSlider::handle:horizontal {{
    background: {BRAND['cyan']};
    width: 11px;
    margin: -4px 0;
    border-radius: 5px;
}}
QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {BRAND['magenta']}, stop:1 {BRAND['cyan']});
    border-radius: 2px;
}}

/* ---- shared lists / inputs ------------------------------------------- */
QListWidget, QTreeWidget {{
    background: {BRAND['bg_panel']};
    border: 1px solid {BRAND['border']};
    border-radius: 6px;
    outline: none;
}}
QListWidget::item {{ padding: 5px; border-radius: 4px; }}
QListWidget::item:hover {{ background: {BRAND['bg_input']}; }}
QListWidget::item:selected {{ background: {BRAND['purple']}; }}

QLineEdit, QDoubleSpinBox, QSpinBox {{
    background: {BRAND['bg_input']};
    border: 1px solid {BRAND['border']};
    border-radius: 5px;
    padding: 4px 6px;
    selection-background-color: {BRAND['purple']};
}}
QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {{ border-color: {BRAND['cyan']}; }}
QComboBox {{
    background: {BRAND['bg_input']};
    border: 1px solid {BRAND['border']};
    border-radius: 5px;
    padding: 4px 8px;
}}
QComboBox:focus {{ border-color: {BRAND['cyan']}; }}
QComboBox::drop-down {{ border: none; width: 18px; }}

QLabel#title {{ font-size: 30px; font-weight: 700; }}
QLabel#subtitle {{ color: {BRAND['text_muted']}; font-size: 14px; }}
QLabel#panelHeader {{
    font-size: 14px; font-weight: 600; color: {BRAND['cyan']};
    padding: 4px 2px;
}}

QStatusBar {{ background: {BRAND['bg_alt']}; border-top: 1px solid {BRAND['border']}; }}
QSplitter::handle {{ background: {BRAND['bg']}; width: 2px; }}
QScrollArea {{ border: none; }}

QScrollBar:vertical {{
    background: {BRAND['bg']}; width: 10px; border: none;
}}
QScrollBar::handle:vertical {{
    background: {BRAND['bg_input']}; border-radius: 4px; min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: {BRAND['purple']}; }}
QScrollBar:horizontal {{
    background: {BRAND['bg']}; height: 10px; border: none;
}}
QScrollBar::handle:horizontal {{
    background: {BRAND['bg_input']}; border-radius: 4px; min-width: 24px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
"""
