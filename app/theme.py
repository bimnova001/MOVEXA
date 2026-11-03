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
QPushButton#primary {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {BRAND['magenta']}, stop:1 {BRAND['cyan']});
    border: none;
    color: #ffffff;
    font-weight: 600;
}}
QPushButton#primary:hover {{ background: {BRAND['purple']}; }}

QListWidget, QTreeWidget {{
    background: {BRAND['bg_panel']};
    border: 1px solid {BRAND['border']};
    border-radius: 6px;
    outline: none;
}}
QListWidget::item {{ padding: 5px; border-radius: 4px; }}
QListWidget::item:selected {{ background: {BRAND['purple']}; }}

QLineEdit, QDoubleSpinBox, QSpinBox {{
    background: {BRAND['bg_input']};
    border: 1px solid {BRAND['border']};
    border-radius: 5px;
    padding: 4px 6px;
    selection-background-color: {BRAND['purple']};
}}
QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {{ border-color: {BRAND['cyan']}; }}

QLabel#title {{ font-size: 30px; font-weight: 700; }}
QLabel#subtitle {{ color: {BRAND['text_muted']}; font-size: 14px; }}
QLabel#panelHeader {{
    font-size: 14px; font-weight: 600; color: {BRAND['cyan']};
    padding: 4px 2px;
}}
QLabel#hint {{ color: {BRAND['text_muted']}; }}

QStatusBar {{ background: {BRAND['bg_alt']}; border-top: 1px solid {BRAND['border']}; }}
QSplitter::handle {{ background: {BRAND['bg']}; width: 2px; }}
QScrollArea {{ border: none; }}
"""
