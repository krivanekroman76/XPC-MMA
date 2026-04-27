import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, 
                               QFileDialog, QLineEdit, QPushButton, QComboBox, 
                               QFormLayout, QMessageBox, QTableWidget, 
                               QTableWidgetItem, QHeaderView, QDialog)
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
        # Main layout for the whole page (Top to Bottom)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(30, 30, 30, 30)
        self.layout.setSpacing(20)

        # 1. Main Title
        self.title_label = QLabel()
        self.title_label.setObjectName("title") # Dashboard title style
        self.layout.addWidget(self.title_label)
        
        # 2. Upload Translation Button (Green)
        self.upload_trans_btn = QPushButton()
        self.upload_trans_btn.setObjectName("successButton") # Uses your QSS green
        self.upload_trans_btn.setFixedWidth(250)
        self.upload_trans_btn.clicked.connect(self.handle_upload_translation)
        # Add to layout aligned to the left
        self.layout.addWidget(self.upload_trans_btn, alignment=Qt.AlignLeft)

        # 3. User & League Creation Form
        self.user_group = QGroupBox()
        user_group_layout = QVBoxLayout(self.user_group)
        user_group_layout.setSpacing(15)

        form_layout = QFormLayout()
        
        self.email_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)

        self.role_combo = QComboBox()
        self.role_combo.addItems(["admin", "writer"])

        self.league_combo = QComboBox()
        self.league_combo.currentIndexChanged.connect(self.toggle_new_league_fields)

        self.new_league_name_input = QLineEdit()
        self.new_league_name_input.hide()

        self.new_league_abbr_input = QLineEdit()
        self.new_league_abbr_input.hide()

        # Labels
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

        user_group_layout.addLayout(form_layout)

        self.create_btn = QPushButton()
        self.create_btn.setObjectName("successButton") 
        self.create_btn.setFixedWidth(200)
        self.create_btn.clicked.connect(self.handle_create_user)
        user_group_layout.addWidget(self.create_btn)

        self.layout.addWidget(self.user_group)

        # 4. Users Table
        self.table_group = QGroupBox()
        table_layout = QVBoxLayout(self.table_group)
        
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(4) # 0: Email, 1: ID, 2: League/Races, 3: Action
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.users_table.setEditTriggers(QTableWidget.NoEditTriggers) # Make cells read-only
        table_layout.addWidget(self.users_table)

        self.layout.addWidget(self.table_group)

    def retranslate_ui(self):
        """Updates all texts in the UI according to the current language."""
        self.title_label.setText(tr.t("admin_title"))
        self.upload_trans_btn.setText(tr.t("admin_btn_upload_trans"))
        
        # Group Box Titles
        self.user_group.setTitle(tr.t("admin_group_create_user"))
        self.table_group.setTitle(tr.t("admin_group_users_list"))

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
            "ID", # Usually doesn't need translation, but you can add it
            tr.t("admin_col_league"), 
            tr.t("admin_col_action") # The delete column header
        ]
        self.users_table.setHorizontalHeaderLabels(headers)

        current_league_data = self.league_combo.currentData()
        self.load_leagues_to_combo()
        index = self.league_combo.findData(current_league_data)
        if index != -1:
            self.league_combo.setCurrentIndex(index)

    def load_leagues_to_combo(self):
        """Loads leagues from the DB into the combo box."""
        self.league_combo.blockSignals(True) 
        self.league_combo.clear()
        self.league_combo.addItem(tr.t("admin_combo_new_league"), "NEW")
        
        leagues = self.db.get_all_leagues()
        if leagues:
            for lg in leagues:
                self.league_combo.addItem(f"{lg['abbreviation']} - {lg['name']}", lg['id'])
                
        self.league_combo.blockSignals(False) 
        self.toggle_new_league_fields() 

    def toggle_new_league_fields(self):
        if self.league_combo.currentData() == "NEW":
            self.new_league_name_input.show()
            self.new_league_abbr_input.show()
        else:
            self.new_league_name_input.hide()
            self.new_league_abbr_input.hide()

    def handle_create_user(self):
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        role = self.role_combo.currentText()
        league_id = self.league_combo.currentData()

        if not email or not password:
            QMessageBox.warning(self, tr.t("common_msg_error"), tr.t("admin_error_empty_credentials"))
            return

        if league_id == "NEW":
            l_name = self.new_league_name_input.text().strip()
            l_abbr = self.new_league_abbr_input.text().strip()
            if not l_name or not l_abbr:
                QMessageBox.warning(self, tr.t("common_msg_error"), tr.t("admin_error_empty_league"))
                return
                
            league_id = self.db.create_league(l_name, l_abbr)
            if not league_id:
                QMessageBox.critical(self, tr.t("common_msg_error"), tr.t("admin_error_league_creation_failed"))
                return

        self.create_btn.setEnabled(False)
        
        success, msg = self.db.create_user_account(email, password, role, league_id)
        
        if success:
            QMessageBox.information(self, tr.t("common_msg_success"), msg)
            self.email_input.clear()
            self.password_input.clear()
            self.new_league_name_input.clear()
            self.new_league_abbr_input.clear()
            self.load_leagues_to_combo() 
            self.load_users()
        else:
            QMessageBox.critical(self, tr.t("common_msg_error"), msg)
            
        self.create_btn.setEnabled(True)

    def load_users(self):
        """Fetches users from the database and populates the table with a Delete button."""
        self.users_table.setRowCount(0)
        users_data = self.db.get_all_users()
        for row_idx, user in enumerate(users_data):
            self.users_table.insertRow(row_idx)
            
            # Fill user data (make sure the keys match your database return objects)
            user_id = user.get('id', '-')
            self.users_table.setItem(row_idx, 0, QTableWidgetItem(user.get('email', '-')))
            self.users_table.setItem(row_idx, 1, QTableWidgetItem(str(user_id)))
            self.users_table.setItem(row_idx, 2, QTableWidgetItem(str(user.get('assigned_league', '-'))))
            
            # Create a Delete button for the action column
            delete_btn = QPushButton("Delete")
            delete_btn.setCursor(Qt.PointingHandCursor)
            # Simple inline styling to make it look like a danger button
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
            
            # Using a lambda to pass the specific user_id to the delete method
            delete_btn.clicked.connect(lambda checked=False, uid=user_id: self.handle_delete_user(uid))
            
            # Add the button widget to the 4th column (index 3)
            self.users_table.setCellWidget(row_idx, 3, delete_btn)
            
    def handle_delete_user(self, user_id):
        """Confirms and deletes a user."""
        if user_id == '-':
            return
            
        reply = QMessageBox.question(
            self, 
            tr.t("admin_delete_confirm_title", default="Confirm Delete"), 
            tr.t("admin_delete_confirm_msg", default=f"Are you sure you want to delete user ID {user_id}?"),
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # You will need to implement `delete_user` in your firebase_service.py/db script
            success, msg = self.db.delete_user(user_id) 
            if success:
                QMessageBox.information(self, tr.t("common_msg_success"), msg)
                self.load_users() # Refresh table
            else:
                QMessageBox.critical(self, tr.t("common_msg_error"), msg)

    def handle_upload_translation(self):
        """Opens a file dialog to select a JSON file and uploads it."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Translation File", 
            "", 
            "JSON Files (*.json)"
        )

        if file_path:
            self.upload_trans_btn.setEnabled(False)
            
            # Assuming upload_single_translation returns (bool_success, string_message)
            success, msg = self.db.upload_single_translation(file_path)
            
            if success:
                QMessageBox.information(self, tr.t("common_msg_success"), msg)
            else:
                QMessageBox.critical(self, tr.t("common_msg_error"), msg)
                
            self.upload_trans_btn.setEnabled(True)