"""Windows 11 Fluent Design System Theme & Style Definitions."""

ACCENT_COLOR = "#0078D4"
ACCENT_HOVER = "#106EBE"
ACCENT_PRESSED = "#005A9E"
ACCENT_LIGHT = "#2B88D8"

BG_LIGHT = "#F3F3F3"
CARD_BG_LIGHT = "#FFFFFF"
CARD_BORDER_LIGHT = "rgba(0, 0, 0, 0.08)"
TEXT_PRIMARY_LIGHT = "#1C1C1C"
TEXT_SECONDARY_LIGHT = "#5C5C5C"

BG_DARK = "#202020"
CARD_BG_DARK = "#2B2B2B"
CARD_BORDER_DARK = "rgba(255, 255, 255, 0.08)"
TEXT_PRIMARY_DARK = "#FDFDFD"
TEXT_SECONDARY_DARK = "#A0A0A0"

FONT_FAMILY = "Segoe UI, Microsoft YaHei, -apple-system, sans-serif"

POPUP_STYLE_LIGHT = f"""
QFrame#MainCard {{
    background-color: rgba(255, 255, 255, 0.95);
    border: 1px solid rgba(0, 0, 0, 0.12);
    border-radius: 12px;
}}
QLabel {{
    font-family: {FONT_FAMILY};
    color: {TEXT_PRIMARY_LIGHT};
}}
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: rgba(0, 0, 0, 0.2);
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: rgba(0, 0, 0, 0.4);
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QPushButton.IconButton {{
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 4px;
}}
QPushButton.IconButton:hover {{
    background-color: rgba(0, 0, 0, 0.06);
}}
QPushButton.IconButton:pressed {{
    background-color: rgba(0, 0, 0, 0.12);
}}
"""

POPUP_STYLE_DARK = f"""
QFrame#MainCard {{
    background-color: rgba(36, 36, 36, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 12px;
}}
QLabel {{
    font-family: {FONT_FAMILY};
    color: {TEXT_PRIMARY_DARK};
}}
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: rgba(255, 255, 255, 0.2);
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: rgba(255, 255, 255, 0.4);
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QPushButton.IconButton {{
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 4px;
}}
QPushButton.IconButton:hover {{
    background-color: rgba(255, 255, 255, 0.08);
}}
QPushButton.IconButton:pressed {{
    background-color: rgba(255, 255, 255, 0.15);
}}
"""
