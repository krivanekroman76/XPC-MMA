import sys
import json
import os
from PySide6.QtWidgets import QComboBox
from PySide6.QtCore import Qt

class Translator:
    def __init__(self, lang_code="cs"):
        self.translations = {}
        self.current_lang = lang_code
        self.load_language(lang_code)

    def load_language(self, lang_code):
        path = os.path.join("lang", f"{lang_code}.json")
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
                self.current_lang = lang_code
        except FileNotFoundError:
            print(f"[Warning] Language file {path} not found.")
            self.translations = {}

    def get_available_languages(self):
        """Returns a list of available language codes from the lang/ folder."""
        lang_dir = "lang"
        if not os.path.exists(lang_dir): return []
        return sorted([f.replace(".json", "") for f in os.listdir(lang_dir) if f.endswith(".json")])

    def t(self, key, **kwargs):
        text = self.translations.get(key, key)
        if kwargs: return text.format(**kwargs)
        return text

# Initialization of the global translator
tr = Translator("cs")

# ==========================================
# UNIVERSAL LANGUAGE DROPDOWN
# ==========================================
class LanguageSelector(QComboBox):
    """
    This widget can be placed into any window.
    It automatically handles language changes and saving settings.
    """
    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window # The window that has the retranslate_ui() method
        self.setCursor(Qt.PointingHandCursor)
        
        # Load available languages via the Translator
        langs = tr.get_available_languages()
        self.addItems(langs)
        
        # Tell it to always expand according to the longest text inside
        self.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        
        # Modern style (matches your Dashboard)
        self.setStyleSheet("""
            QComboBox {
                background-color: #313244;
                color: #cdd6f4;
                border-radius: 4px;
                padding: 5px 10px;
                min-width: 60px;
                border: 1px solid #45475a;
            }
            QComboBox::drop-down {
                border: 0px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e1e2e;
                color: #cdd6f4;
                selection-background-color: #89b4fa;
                selection-color: #11111b;
            }
        """)
        
        # Set the currently active language
        if tr.current_lang in langs:
            self.setCurrentText(tr.current_lang)
            
        self.currentTextChanged.connect(self._handle_change)

    def _handle_change(self, new_lang):
        # 1. Change the language in the global translator
        tr.load_language(new_lang)
        
        # 2. Save to settings.json (if the parent window has a save method)
        if hasattr(self.parent_window, "local_settings"):
            self.parent_window.local_settings["lang"] = new_lang
            if hasattr(self.parent_window, "save_local_settings"):
                self.parent_window.save_local_settings()
        
        # 3. CALL THE WINDOW TRANSLATION (this is the key part!)
        if hasattr(self.parent_window, "retranslate_ui"):
            self.parent_window.retranslate_ui()