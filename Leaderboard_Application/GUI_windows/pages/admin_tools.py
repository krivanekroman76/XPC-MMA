from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QComboBox, QFormLayout, 
                               QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt

# Import the translator
from core.translate import tr

class AdminToolsPage(QWidget):
    def __init__(self, db_service, dashboard_parent):
        super().__init__()
        self.db = db_service
        self.dashboard = dashboard_parent
        self.setup_ui()
        self.load_leagues_to_combo()
        self.load_users()
        # Apply translations right after initialization
        self.retranslate_ui() 

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(30, 30, 30, 30)
        self.layout.setSpacing(20)

        # Title (Styles inherited from QLabel#title in QSS)
        self.title_label = QLabel()
        self.title_label.setObjectName("title")
        self.layout.addWidget(self.title_label)

        form_layout = QFormLayout()
        
        # Inputs (Styles inherited from global QLineEdit in QSS)
        self.email_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)

        # Combos (Styles inherited from global QComboBox in QSS)
        self.role_combo = QComboBox()
        self.role_combo.addItems(["admin", "writer"])

        self.league_combo = QComboBox()
        self.league_combo.currentIndexChanged.connect(self.toggle_new_league_fields)

        self.new_league_name_input = QLineEdit()
        self.new_league_name_input.hide()

        self.new_league_abbr_input = QLineEdit()
        self.new_league_abbr_input.hide()

        # Labels (Instance variables for retranslate_ui)
        self.email_label = QLabel()
        self.password_label = QLabel()
        self.role_label = QLabel()
        self.league_label = QLabel()
        self.new_league_name_label = QLabel()
        self.new_league_abbr_label = QLabel()

        # Add to form
        form_layout.addRow(self.email_label, self.email_input)
        form_layout.addRow(self.password_label, self.password_input)
        form_layout.addRow(self.role_label, self.role_combo)
        form_layout.addRow(self.league_label, self.league_combo)
        form_layout.addRow(self.new_league_name_label, self.new_league_name_input)
        form_layout.addRow(self.new_league_abbr_label, self.new_league_abbr_input)

        self.layout.addLayout(form_layout)

        # Create Button
        self.create_btn = QPushButton()
        self.create_btn.setObjectName("successButton") # Targeted in QSS
        self.create_btn.clicked.connect(self.handle_create_user)
        self.layout.addWidget(self.create_btn)

        # Users table (Styles inherited from global QTableWidget in QSS)
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(4)
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self.users_table)

    def retranslate_ui(self):
        """Updates all texts in the UI according to the current language."""
        self.title_label.setText(tr.t("admin_title"))
        
        self.email_input.setPlaceholderText(tr.t("admin_email_placeholder"))
        self.password_input.setPlaceholderText(tr.t("admin_password_placeholder"))
        self.new_league_name_input.setPlaceholderText(tr.t("admin_new_league_name_placeholder"))
        self.new_league_abbr_input.setPlaceholderText(tr.t("admin_new_league_abbr_placeholder"))

        self.email_label.setText(tr.t("admin_email_label"))
        self.password_label.setText(tr.t("admin_password_label"))
        self.role_label.setText(tr.t("admin_role_label"))
        self.league_label.setText(tr.t("admin_league_label"))
        self.new_league_name_label.setText(tr.t("admin_new_league_name_label"))
        self.new_league_abbr_label.setText(tr.t("admin_new_league_abbr_label"))

        self.create_btn.setText(tr.t("admin_create_btn"))

        # Table headers
        headers = [
            tr.t("admin_col_email"), 
            tr.t("admin_col_role"), 
            tr.t("admin_col_league"), 
            tr.t("admin_col_permissions")
        ]
        self.users_table.setHorizontalHeaderLabels(headers)

        # Reload combo to apply translation to the "New League" option
        current_league_data = self.league_combo.currentData()
        self.load_leagues_to_combo()
        
        # Try to restore previously selected item
        index = self.league_combo.findData(current_league_data)
        if index != -1:
            self.league_combo.setCurrentIndex(index)

    def load_leagues_to_combo(self):
        """Loads leagues from the DB into the combo box."""
        self.league_combo.clear()
        self.league_combo.addItem(tr.t("admin_combo_new_league"), "NEW")
        leagues = self.db.get_all_leagues()
        for lg in leagues:
            self.league_combo.addItem(f"{lg['abbreviation']} - {lg['name']}", lg['id'])

    def toggle_new_league_fields(self):
        """Shows/hides the new league input fields based on combo selection."""
        if self.league_combo.currentData() == "NEW":
            self.new_league_name_input.show()
            self.new_league_abbr_input.show()
        else:
            self.new_league_name_input.hide()
            self.new_league_abbr_input.hide()

    def handle_create_user(self):
        """Validates inputs and creates a new user (and league if needed)."""
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        role = self.role_combo.currentText()
        league_id = self.league_combo.currentData()

        if not email or not password:
            QMessageBox.warning(self, tr.t("common_msg_error"), tr.t("admin_error_empty_credentials"))
            return

        # If we are creating a new league
        if league_id == "NEW":
            l_name = self.new_league_name_input.text().strip()
            l_abbr = self.new_league_abbr_input.text().strip()
            if not l_name or not l_abbr:
                QMessageBox.warning(self, tr.t("common_msg_error"), tr.t("admin_error_empty_league"))
                return
                
            # Create league in DB and get ID
            league_id = self.db.create_league(l_name, l_abbr)
            if not league_id:
                QMessageBox.critical(self, tr.t("common_msg_error"), tr.t("admin_error_league_creation_failed"))
                return

        self.create_btn.setEnabled(False)
        
        # Ensure your db.create_user_account accepts the league ID
        success, msg = self.db.create_user_account(email, password, role, league_id)
        
        if success:
            QMessageBox.information(self, tr.t("common_msg_success"), msg)
            self.email_input.clear()
            self.password_input.clear()
            self.new_league_name_input.clear()
            self.new_league_abbr_input.clear()
            self.load_leagues_to_combo() # Refreshes dropdown with the new league
            self.load_users()
        else:
            QMessageBox.critical(self, tr.t("common_msg_error"), msg)
            
        self.create_btn.setEnabled(True)

    def load_users(self):
        """Fetches users from the database and populates the table."""
        self.users_table.setRowCount(0)
        users_data = self.db.get_all_users()
        for row_idx, user in enumerate(users_data):
            self.users_table.insertRow(row_idx)
            self.users_table.setItem(row_idx, 0, QTableWidgetItem(user.get('email', '-')))
            self.users_table.setItem(row_idx, 1, QTableWidgetItem(user.get('role', '-')))
            # In DB the user has assigned_league = league ID. Map ID to abbr in real app if possible.
            self.users_table.setItem(row_idx, 2, QTableWidgetItem(user.get('assigned_league', '-')))
            self.users_table.setItem(row_idx, 3, QTableWidgetItem("-"))