import sys
import json
import os
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QPushButton, QMessageBox, 
                               QComboBox, QCheckBox)
from PySide6.QtCore import Qt

# Import your custom Firebase class
from core import FirebaseService, ConfigManager, tr, LanguageSelector

from GUI_windows.dashboard import DashboardWindow

# ==========================================
# LOGIN WINDOW
# ==========================================
class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.db = FirebaseService()
        
        # Load settings and apply language
        self.local_settings = self.load_local_settings()
        tr.load_language(self.local_settings.get("lang", "cs"))

        self.setFixedSize(350, 450)

        self.setup_ui()
        self.retranslate_ui() # Applies texts immediately after startup

    def load_local_settings(self):
        """Loads settings.json. If it doesn't exist, returns default values."""
        settings = ConfigManager.load_json("settings.json")
        if settings:
            return settings
        # Default values
        return {"remember_email": False, "saved_email": "", "lang": "cs"}

    def save_local_settings(self):
        """Saves the current settings to a file."""
        from core.config_manager import ConfigManager
        ConfigManager.save_json("settings.json", self.local_settings)

    def setup_ui(self):
        # Main vertical layout
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(40, 20, 40, 40)

        # --- TOP BAR FOR LANGUAGE ---
        top_layout = QHBoxLayout()
        top_layout.addStretch()
        
        # Create our new smart dropdown
        self.lang_selector = LanguageSelector(self) 
        self.lang_selector.setCursor(Qt.PointingHandCursor)
        self.lang_selector.setObjectName("langSelector")
        
        top_layout.addWidget(self.lang_selector)
        layout.addLayout(top_layout)
        # -----------------------------

        self.title_label = QLabel() 
        self.title_label.setObjectName("title") # Targetable by QSS
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.email_input = QLineEdit()
        self.email_input.setObjectName("emailInput")
        
        # If the user had a remembered email, fill it in right away
        if self.local_settings.get("remember_email"):
            self.email_input.setText(self.local_settings.get("saved_email", ""))

        self.password_input = QLineEdit()
        self.password_input.setObjectName("passwordInput")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        # --- CHECKBOX FOR SAVING EMAIL ---
        self.remember_cb = QCheckBox() 
        self.remember_cb.setCursor(Qt.PointingHandCursor)
        self.remember_cb.setObjectName("rememberCheckbox")
        self.remember_cb.setChecked(self.local_settings.get("remember_email", False))
        # -----------------------------------

        self.login_btn = QPushButton()
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setObjectName("primaryButton") # Targetable by QSS
        self.login_btn.clicked.connect(self.handle_login)

        # Add widgets to layout
        layout.addWidget(self.title_label)
        layout.addSpacing(10)
        layout.addWidget(self.email_input)
        layout.addWidget(self.remember_cb)
        layout.addWidget(self.password_input)
        layout.addWidget(self.login_btn)
        
        layout.addStretch() 
        self.setLayout(layout)

    def retranslate_ui(self):
        """Updates all texts in the UI according to the current language."""
        self.setWindowTitle(tr.t("app_title"))
        self.title_label.setText(tr.t("app_title"))
        self.email_input.setPlaceholderText(tr.t("ph_email"))
        self.password_input.setPlaceholderText(tr.t("ph_password"))
        
        # We use a fallback string here in case you haven't added this key to cs.json yet
        self.remember_cb.setText(tr.t("lbl_remember_email", default="Pamatovat e-mail"))
        
        self.login_btn.setText(tr.t("btn_login"))

    def handle_login(self):
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()

        if not email or not password:
            QMessageBox.warning(self, tr.t("msg_error"), tr.t("err_empty"))
            return

        # Show a loading state on the button
        self.login_btn.setText(tr.t("status_running", default="Načítání..."))
        self.login_btn.setEnabled(False)
        QApplication.processEvents()

        success, message = self.db.login(email, password)

        if success:
            # SAVE EMAIL TO SETTINGS.JSON ON SUCCESS
            self.local_settings["remember_email"] = self.remember_cb.isChecked()
            if self.remember_cb.isChecked():
                self.local_settings["saved_email"] = email
            else:
                self.local_settings["saved_email"] = "" # Clear it if unchecked
            self.save_local_settings()
            
            self.dashboard = DashboardWindow(self.db)
            self.dashboard.show()
            self.close()
        else:
            QMessageBox.critical(self, tr.t("msg_error"), tr.t("err_invalid"))
            self.login_btn.setText(tr.t("btn_login"))
            self.login_btn.setEnabled(True)