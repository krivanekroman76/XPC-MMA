from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QComboBox, QFormLayout, 
                               QMessageBox, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QFrame, QDateTimeEdit, QDateEdit, QTimeEdit)
from PySide6.QtCore import Qt, QDate, QTime
from PySide6.QtGui import QColor

# Import the translator
from core.translate import tr

class LeaguePage(QWidget):
    def __init__(self, db_service, dashboard_parent):
        super().__init__()
        self.db = db_service
        self.dashboard = dashboard_parent
        
        self.user_role = self.db.user_info.get('role', 'user')
        self.user_league_id = self.db.user_info.get('assigned_league', '')
        
        self.setup_ui()
        self.retranslate_ui() # Apply translations right after initialization

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(30, 30, 30, 30)
        self.layout.setSpacing(20)

        # --- HEADER PANEL ---
        header_layout = QHBoxLayout()
        self.league_selector = QComboBox()
        self.league_selector.setStyleSheet("background-color: #313244; color: white; border-radius: 4px; padding: 8px;")
        
        # Load leagues from DB
        all_leagues = self.db.get_all_leagues()
        
        self.header_title = QLabel()
        self.header_title.setStyleSheet("color: #cdd6f4; font-size: 16px;")
        
        if self.user_role == "super_admin":
            for lg in all_leagues:
                self.league_selector.addItem(f"{lg['abbreviation']} - {lg['name']}", lg['id'])
            
            self.league_selector.currentIndexChanged.connect(self.load_data)
            header_layout.addWidget(self.header_title)
            header_layout.addWidget(self.league_selector)
        else:
            # Regular admin sees only their league
            self.my_league = next((l for l in all_leagues if l['id'] == self.user_league_id), None)
            lg_name = self.my_league['name'] if self.my_league else "Neznámá liga"
            
            self.header_title.setStyleSheet("font-size: 24px; font-weight: bold; color: #89b4fa;")
            
            self.league_selector.addItem(lg_name, self.user_league_id)
            self.league_selector.hide() # We don't need the selector visible for admin
            header_layout.addWidget(self.header_title)

        header_layout.addStretch()
        self.layout.addLayout(header_layout)

        # --- RACE FORM ---
        create_frame = QFrame()
        create_frame.setStyleSheet("QFrame { background-color: #1e1e2e; border-radius: 8px; border: 1px solid #45475a; }")
        create_layout = QVBoxLayout(create_frame)
        
        self.create_title = QLabel()
        self.create_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #a6e3a1; border: none;")
        create_layout.addWidget(self.create_title)

        form_layout = QFormLayout()
        
        # 1. Instantiate Inputs
        self.race_name_input = QLineEdit()
        self.race_name_input.setStyleSheet("padding: 8px; border-radius: 4px; background-color: #313244; color: white; border: none;")
        
        date_time_layout = QHBoxLayout()
        self.race_date_input = QDateEdit(QDate.currentDate())
        self.race_date_input.setCalendarPopup(True)
        self.race_date_input.setDisplayFormat("dd.MM.yyyy")
        self.race_date_input.setStyleSheet("padding: 8px; border-radius: 4px; background-color: #313244; color: white; border: none;")

        self.race_time_input = QTimeEdit(QTime.currentTime())
        self.race_time_input.setDisplayFormat("HH:mm") 
        self.race_time_input.setStyleSheet("padding: 8px; border-radius: 4px; background-color: #313244; color: white; border: none;")

        date_time_layout.addWidget(self.race_date_input)
        date_time_layout.addWidget(self.race_time_input)

        self.writer_combo = QComboBox()
        self.writer_combo.setStyleSheet("padding: 8px; border-radius: 4px; background-color: #313244; color: white; border: none;")
        
        # 2. Instantiate Labels
        self.lbl_race_name = QLabel(styleSheet="border: none; color: #cdd6f4;")
        self.lbl_race_date = QLabel(styleSheet="border: none; color: #cdd6f4;")
        self.lbl_race_writer = QLabel(styleSheet="border: none; color: #cdd6f4;")
        
        # 3. Add to Form Layout (Order matters!)
        form_layout.addRow(self.lbl_race_name, self.race_name_input)
        form_layout.addRow(self.lbl_race_date, date_time_layout) 
        form_layout.addRow(self.lbl_race_writer, self.writer_combo)
        
        create_layout.addLayout(form_layout)

        self.create_race_btn = QPushButton()
        self.create_race_btn.setStyleSheet("background-color: #a6e3a1; color: #11111b; font-weight: bold; padding: 10px; border-radius: 5px;")
        self.create_race_btn.clicked.connect(self.handle_create_race)
        create_layout.addWidget(self.create_race_btn)
        self.layout.addWidget(create_frame)

        # --- RACES TABLE ---
        self.races_table = QTableWidget()
        self.races_table.setColumnCount(4)
        self.races_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.races_table.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4; border: 1px solid #45475a;")
        self.layout.addWidget(self.races_table)

    def retranslate_ui(self):
        """Updates all texts in the UI according to the current language."""
        if self.user_role == "super_admin":
            self.header_title.setText(tr.t("league_header_select"))
        else:
            lg_name = self.my_league['name'] if self.my_league else tr.t("league_unknown_league")
            self.header_title.setText(tr.t("league_header_manage", league=lg_name))

        self.create_title.setText(tr.t("league_create_title"))
        
        self.lbl_race_name.setText(tr.t("league_lbl_name"))
        self.lbl_race_date.setText(tr.t("league_lbl_date"))
        self.lbl_race_writer.setText(tr.t("league_lbl_writer"))
        
        self.create_race_btn.setText(tr.t("league_btn_add_race"))

        headers = [
            tr.t("league_col_race_name"), 
            tr.t("league_col_date_time"), 
            tr.t("league_col_writer"), 
            tr.t("common_col_status")
        ]
        self.races_table.setHorizontalHeaderLabels(headers)

        # Reloading data also applies translation to dynamic table content
        self.load_data()


    def get_current_league_id(self):
        return self.league_selector.currentData()

    def load_data(self):
        """Main hub: Gets selected league and triggers dropdown and table population."""
        current_league_id = self.get_current_league_id()
        if not current_league_id: return
        
        self.load_writers_to_combo(current_league_id)
        self.load_races(current_league_id)
                
    def load_writers_to_combo(self, league_id):
        """Fills the dropdown with writers and admins belonging to the selected league."""
        self.writer_combo.clear()
        all_users = self.db.get_all_users()
        
        for user in all_users:
            if user.get('role') in ['writer', 'admin'] and user.get('assigned_league') == league_id:
                email = user.get('email', tr.t("league_unknown_email"))
                uid = user.get('uid')
                self.writer_combo.addItem(email, uid)

    def load_races(self, league_id):
        """Loads races from DB, translates writer UID to Email and colors rows."""
        self.races_table.setRowCount(0)
        
        all_users = self.db.get_all_users()
        self.uid_to_email = {}
        for u in all_users:
            if 'uid' in u and 'email' in u:
                self.uid_to_email[u['uid']] = u['email']

        races = self.db.get_races_for_league(league_id)
        
        for row_idx, race in enumerate(races):
            self.races_table.insertRow(row_idx)
            
            raw_status = race.get('status', 'Připravuje se')
            
            if raw_status == "Dokončeno":
                display_status = tr.t("league_status_finished")
                bg_color = QColor("#45475a")
                text_color = QColor("#a6adc8")
            elif raw_status == "Probíhá":
                display_status = tr.t("league_status_running")
                bg_color = QColor("#89b4fa")
                text_color = QColor("#11111b")
            else:
                display_status = tr.t("league_status_preparing")
                bg_color = QColor("#1e1e2e")
                text_color = QColor("#a6e3a1")

            writer_uid = race.get('writer_uid', '')
            writer_display = self.uid_to_email.get(writer_uid, tr.t("league_writer_unassigned"))

            items = [
                QTableWidgetItem(race.get('name', '')),
                QTableWidgetItem(race.get('date_time', '').replace('T', ' ')),
                QTableWidgetItem(writer_display),
                QTableWidgetItem(display_status)
            ]
            
            for col, item in enumerate(items):
                item.setBackground(bg_color)
                item.setForeground(text_color)
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.races_table.setItem(row_idx, col, item)
                
    def handle_create_race(self):
        league_id = self.get_current_league_id()
        name = self.race_name_input.text().strip()
        
        selected_date = self.race_date_input.date().toString("yyyy-MM-dd")
        selected_time = self.race_time_input.time().toString("HH:mm:ss")
        date_time = f"{selected_date}T{selected_time}"
        
        writer_uid = self.writer_combo.currentData()
        
        if not league_id:
            QMessageBox.warning(self, tr.t("common_msg_error"), "Není vybrána žádná liga.")
            return

        if not name or not writer_uid:
            QMessageBox.warning(self, tr.t("common_msg_error"), tr.t("league_error_empty_fields"))
            return

        success = self.db.create_race(league_id, name, date_time, writer_uid)
        if success:
            QMessageBox.information(self, tr.t("common_msg_success"), tr.t("league_success_race_created"))
            self.race_name_input.clear()
            self.load_data()
            
            # THE FIX: Tell the dashboard to refresh the other pages!
            dashboard = self.parent() 
            
            if "races" in dashboard.page_widgets:
                dashboard.page_widgets["races"].refresh_dropdowns()
                
            if "timing" in dashboard.page_widgets:
                dashboard.page_widgets["timing"].refresh_dropdowns()
            dashboard.page_widgets["leaderboard"].refresh_dropdowns()
        else:
            QMessageBox.critical(self, tr.t("common_msg_error"), tr.t("league_error_db_communication"))