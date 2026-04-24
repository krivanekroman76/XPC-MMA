import json
import csv
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QComboBox, QFrame, QTableWidget, 
                               QTableWidgetItem, QHeaderView, QMessageBox,
                               QFormLayout, QSpinBox, QCheckBox, QLineEdit,
                               QFileDialog, QInputDialog, QListWidget, 
                               QAbstractItemView, QGroupBox, QScrollArea)
from PySide6.QtCore import Qt
from core.translate import tr

PRESETS_FILE = "sport_presets.json"
CATEGORIES_FILE = "categories.json"
RECOVERY_FILE = "recovery_start_list.json"

class RacePage(QWidget):
    def __init__(self, db_service, dashboard_parent):
        super().__init__()
        self.db = db_service
        self.dashboard = dashboard_parent
        
        self.user_role = self.db.user_info.get('role', 'user')
        self.user_uid = self.db.user_info.get('uid', '')
        self.user_league_id = self.db.user_info.get('assigned_league', '')
        
        self.sport_presets = self.load_json_file(PRESETS_FILE, {})
        self.categories = self.load_json_file(CATEGORIES_FILE, ["Muži", "Ženy", "Dorost"])
        
        # Dictionaries to hold dynamic UI elements
        self.category_checkboxes = {}
        self.category_tables = {}
        self.category_groups = {}
        
        self.setup_ui()
        self.load_initial_dropdowns()
        self.retranslate_ui()
        
        self.race_combo.currentIndexChanged.connect(self.load_race_data)
        self.load_race_data()

    def load_json_file(self, filepath, default_data):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return default_data

    # --- UI SETUP ---

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        self._setup_header()

        main_content_layout = QHBoxLayout()
        main_content_layout.setSpacing(20)
        
        self._setup_config_panel(main_content_layout)
        self._setup_queue_panel(main_content_layout)

        self.layout.addLayout(main_content_layout, stretch=1)

    def _setup_header(self):
        header_frame = QFrame()
        header_frame.setObjectName("panel")
        header_layout = QHBoxLayout(header_frame)
        
        self.league_combo = QComboBox()
        self.race_combo = QComboBox()
        self.lbl_league = QLabel()
        self.lbl_race = QLabel()

        header_layout.addWidget(self.lbl_league)
        header_layout.addWidget(self.league_combo)
        header_layout.addSpacing(20)
        header_layout.addWidget(self.lbl_race)
        header_layout.addWidget(self.race_combo)
        header_layout.addStretch()
        
        self.layout.addWidget(header_frame)
        self.league_combo.currentIndexChanged.connect(self.load_races_for_selected_league)

    def _setup_config_panel(self, parent_layout):
        config_frame = QFrame()
        config_frame.setObjectName("panel")
        config_layout = QVBoxLayout(config_frame)
        
        self.lbl_config_title = QLabel()
        self.lbl_config_title.setObjectName("h2")
        config_layout.addWidget(self.lbl_config_title)

        # 1. Base Settings
        form_layout = QFormLayout()
        self.preset_combo = QComboBox()
        for key, data in self.sport_presets.items():
            self.preset_combo.addItem(data.get("name_key", key), key)
        self.preset_combo.currentIndexChanged.connect(self.apply_preset)

        self.base_logic_combo = QComboBox()
        self.base_logic_combo.addItems(["attack", "relay", "tfa"])
        
        self.attempts_spin = QSpinBox()
        self.attempts_spin.setRange(1, 5)
        self.attempts_spin.valueChanged.connect(self._update_run_order_list)

        # --- RESTORED SETTINGS ---
        self.lanes_spin = QSpinBox()
        self.lanes_spin.setRange(1, 10)
        
        self.sections_spin = QSpinBox()
        self.sections_spin.setRange(1, 10)
        
        self.allow_penalties_cb = QCheckBox()
        self.penalty_type_combo = QComboBox()
        self.penalty_type_combo.addItems(["seconds", "points"])
        
        self.allow_penalties_cb.stateChanged.connect(
            lambda state: self.penalty_type_combo.setEnabled(bool(state))
        )

        self.lbl_preset = QLabel()
        self.lbl_logic = QLabel()
        self.lbl_attempts = QLabel()
        self.lbl_lanes = QLabel()
        self.lbl_sections = QLabel()

        form_layout.addRow(self.lbl_preset, self.preset_combo)
        form_layout.addRow(self.lbl_logic, self.base_logic_combo)
        form_layout.addRow(self.lbl_attempts, self.attempts_spin)
        form_layout.addRow(self.lbl_lanes, self.lanes_spin)
        form_layout.addRow(self.lbl_sections, self.sections_spin)
        
        # Put checkbox and combobox on the same row
        penalties_layout = QHBoxLayout()
        penalties_layout.addWidget(self.allow_penalties_cb)
        penalties_layout.addWidget(self.penalty_type_combo)
        form_layout.addRow("", penalties_layout) # Empty label string so it aligns right
        # -------------------------

        config_layout.addLayout(form_layout)

        # 2. Dynamic Categories
        self.lbl_cats = QLabel(styleSheet="font-weight: bold; margin-top: 10px;")
        config_layout.addWidget(self.lbl_cats)
        
        cat_layout = QVBoxLayout()
        for cat in self.categories:
            cb = QCheckBox(cat)
            cb.setChecked(True) # Default all to true
            cb.stateChanged.connect(self._on_category_toggled)
            self.category_checkboxes[cat] = cb
            cat_layout.addWidget(cb)
        config_layout.addLayout(cat_layout)

        # 3. Run Order Builder (Drag & Drop)
        self.lbl_run_order = QLabel(styleSheet="font-weight: bold; margin-top: 10px;")
        config_layout.addWidget(self.lbl_run_order)
        
        self.run_order_list = QListWidget()
        self.run_order_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.run_order_list.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; padding: 5px;")
        config_layout.addWidget(self.run_order_list)

        self.btn_save_preset = QPushButton()
        self.btn_save_preset.setObjectName("successButton")
        self.btn_save_preset.clicked.connect(self.save_current_as_preset)
        config_layout.addWidget(self.btn_save_preset)

        parent_layout.addWidget(config_frame, stretch=1)
        
    def _setup_queue_panel(self, parent_layout):
        queue_frame = QFrame()
        queue_frame.setObjectName("panel")
        queue_layout = QVBoxLayout(queue_frame)

        self.lbl_queue_title = QLabel()
        self.lbl_queue_title.setObjectName("h2")
        queue_layout.addWidget(self.lbl_queue_title)

        # Team Input Form
        input_layout = QHBoxLayout()
        self.new_team_name = QLineEdit()
        self.new_team_category = QComboBox()
        self.new_team_category.addItems(self.categories)
        self.btn_add_team = QPushButton()
        self.btn_add_team.setObjectName("primaryButton")
        self.btn_add_team.clicked.connect(self.add_team_from_form)

        input_layout.addWidget(self.new_team_name, stretch=2)
        input_layout.addWidget(self.new_team_category, stretch=1)
        input_layout.addWidget(self.btn_add_team)
        queue_layout.addLayout(input_layout)

        # Tools
        tools_layout = QHBoxLayout()
        self.btn_import = QPushButton()
        self.btn_export = QPushButton()
        self.btn_recovery = QPushButton()
        self.btn_import.setObjectName("warningButton")
        self.btn_export.setObjectName("primaryButton")
        self.btn_recovery.setObjectName("dangerButton")
        self.btn_import.clicked.connect(self.import_teams)
        self.btn_export.clicked.connect(self.export_teams)
        self.btn_recovery.clicked.connect(self.load_recovery)
        tools_layout.addWidget(self.btn_import)
        tools_layout.addWidget(self.btn_export)
        tools_layout.addWidget(self.btn_recovery)
        tools_layout.addStretch()
        queue_layout.addLayout(tools_layout)

        # Scroll Area for Stacked Tables
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        self.tables_container = QWidget()
        self.tables_layout = QVBoxLayout(self.tables_container)
        self.tables_layout.setContentsMargins(0, 0, 0, 0)
        self.tables_layout.setSpacing(15)

        # Create a table group for each category
        for cat in self.categories:
            self._create_category_table(cat)

        self.tables_layout.addStretch()
        scroll_area.setWidget(self.tables_container)
        queue_layout.addWidget(scroll_area, stretch=1)

        self.btn_publish = QPushButton()
        self.btn_publish.setObjectName("primaryButton")
        self.btn_publish.setMinimumHeight(40)
        self.btn_publish.clicked.connect(self.publish_to_firestore)
        queue_layout.addWidget(self.btn_publish)

        parent_layout.addWidget(queue_frame, stretch=2)

    def _create_category_table(self, category):
        group_box = QGroupBox(category)
        group_box.setStyleSheet("QGroupBox { color: #89b4fa; font-weight: bold; border: 1px solid #45475a; border-radius: 6px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        group_layout = QVBoxLayout(group_box)

        table = QTableWidget()
        table.setObjectName("dataTable")
        table.setColumnCount(3)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setDragEnabled(True)
        table.setAcceptDrops(True)
        table.viewport().setAcceptDrops(True)
        table.setDragDropMode(QTableWidget.InternalMove)
        
        # Renumber specific table on drop
        table.model().rowsMoved.connect(lambda *args, c=category: self._renumber_queue(c)) 

        group_layout.addWidget(table)
        self.tables_layout.insertWidget(self.tables_layout.count() - 1, group_box) # Insert before stretch
        
        self.category_tables[category] = table
        self.category_groups[category] = group_box

    # --- DYNAMIC LOGIC ---
    
    def _on_category_toggled(self):
        """Shows/hides tables and updates the run order blocks based on active checkboxes."""
        self.new_team_category.clear()
        
        for cat, cb in self.category_checkboxes.items():
            is_active = cb.isChecked()
            self.category_groups[cat].setVisible(is_active)
            if is_active:
                self.new_team_category.addItem(cat)
                
        self._update_run_order_list()

    def _update_run_order_list(self):
        """Generates the required blocks (e.g., 'Muži - Pokus 1') while preserving user reordering."""
        attempts = self.attempts_spin.value()
        active_cats = [cat for cat, cb in self.category_checkboxes.items() if cb.isChecked()]
        
        expected_blocks = []
        for attempt in range(1, attempts + 1):
            for cat in active_cats:
                expected_blocks.append(f"{cat} - {attempt}. {tr.t('lbl_attempt')}")

        # Remove blocks that are no longer expected (e.g. category unchecked or attempts reduced)
        for i in range(self.run_order_list.count() - 1, -1, -1):
            item_text = self.run_order_list.item(i).text()
            if item_text not in expected_blocks:
                self.run_order_list.takeItem(i)

        # Add new blocks that aren't currently in the list
        current_blocks = [self.run_order_list.item(i).text() for i in range(self.run_order_list.count())]
        for block in expected_blocks:
            if block not in current_blocks:
                self.run_order_list.addItem(block)

    def add_team_from_form(self):
        name = self.new_team_name.text().strip()
        category = self.new_team_category.currentText()
        if name and category:
            self._insert_team_to_queue(name, category)
            self.new_team_name.clear()
            self.new_team_name.setFocus()

    def _insert_team_to_queue(self, name, category):
        if category not in self.category_tables: return
        table = self.category_tables[category]
        row = table.rowCount()
        table.insertRow(row)
        
        st_item = QTableWidgetItem(str(row + 1))
        st_item.setTextAlignment(Qt.AlignCenter)
        st_item.setFlags(st_item.flags() & ~Qt.ItemIsEditable) 
        
        table.setItem(row, 0, st_item)
        table.setItem(row, 1, QTableWidgetItem(name))
        
        btn_delete = QPushButton(tr.t("btn_delete"))
        btn_delete.setObjectName("dangerButton")
        btn_delete.clicked.connect(lambda _, b=btn_delete, t=table, c=category: self.delete_row_inline(b, t, c))
        table.setCellWidget(row, 2, btn_delete)
        
        self._renumber_queue(category)
        self.trigger_autosave()

    def delete_row_inline(self, button_ref, table_ref, category):
        for row in range(table_ref.rowCount()):
            if table_ref.cellWidget(row, 2) == button_ref:
                table_ref.removeRow(row)
                self._renumber_queue(category)
                self.trigger_autosave()
                break

    def _renumber_queue(self, category):
        """Ensures Start Numbers are 1-N for the specific category table."""
        table = self.category_tables[category]
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item: item.setText(str(row + 1))

    # --- FIRESTORE / DATA HANDLING ---

    def apply_preset(self):
        """Applies default settings based on the chosen preset."""
        preset_key = self.preset_combo.currentData()
        preset_data = self.sport_presets.get(preset_key, {})
        
        # Block signals briefly so changing these doesn't trigger visual glitches
        self.attempts_spin.blockSignals(True)
        
        # Set logic
        logic = preset_data.get("base_logic", "attack")
        index = self.base_logic_combo.findText(logic)
        if index >= 0:
            self.base_logic_combo.setCurrentIndex(index)
            
        # Apply numerical settings
        self.attempts_spin.setValue(int(preset_data.get("default_attempts", 1)))
        self.lanes_spin.setValue(int(preset_data.get("default_lanes", 1)))
        self.sections_spin.setValue(int(preset_data.get("sections", 1)))
        
        # Apply penalties
        allow_pen = preset_data.get("allow_penalties", False)
        self.allow_penalties_cb.setChecked(allow_pen)
        self.penalty_type_combo.setEnabled(allow_pen)
        
        pen_type = preset_data.get("penalty_type", "seconds")
        if pen_type:
            pt_index = self.penalty_type_combo.findText(pen_type)
            if pt_index >= 0:
                self.penalty_type_combo.setCurrentIndex(pt_index)
        
        self.attempts_spin.blockSignals(False)
        self._update_run_order_list()

    def publish_to_firestore(self):
        league_id = self.league_combo.currentData()
        race_id = self.race_combo.currentData()
        if not league_id or not race_id:
            QMessageBox.warning(self, tr.t("msg_error"), tr.t("race_err_no_race")) 
            return
            
        export_data = []
        active_cats = [cat for cat, cb in self.category_checkboxes.items() if cb.isChecked()]
        
        # Gather all teams from active category tables
        for cat in active_cats:
            table = self.category_tables[cat]
            for row in range(table.rowCount()):
                export_data.append({
                    "start_no": int(table.item(row, 0).text()), 
                    "team": table.item(row, 1).text(),
                    "category": cat,
                    "state": "PREPARING",
                    "attempts": [],
                    "best_time": None
                })

        # Gather run order exactly as arranged by user
        run_order = [self.run_order_list.item(i).text() for i in range(self.run_order_list.count())]

        # Add the restored settings into the database payload
        race_settings = {
            "preset": self.preset_combo.currentData(), 
            "logic": self.base_logic_combo.currentText(),
            "attempts": self.attempts_spin.value(),
            "lanes": self.lanes_spin.value(),
            "sections": self.sections_spin.value(),
            "allow_penalties": self.allow_penalties_cb.isChecked(),
            "penalty_type": self.penalty_type_combo.currentText() if self.allow_penalties_cb.isChecked() else None,
            "active_categories": active_cats,
            "run_order": run_order
        }

        success, message = self.db.update_race_data(league_id, race_id, export_data, race_settings)
        if success:
            QMessageBox.information(self, tr.t("msg_success"), tr.t("race_msg_published"))
        else:
            QMessageBox.critical(self, tr.t("msg_error"), message)
            
    def load_race_data(self):
        league_id = self.league_combo.currentData()
        race_id = self.race_combo.currentData()
        if not league_id or not race_id: return

        race_doc = self.db.get_race(league_id, race_id) 
        if not race_doc: return
        
        # 1. Restore Settings & Categories
        settings = race_doc.get("settings", {})
        
        # Block signals temporarily to prevent premature run order updates
        self.attempts_spin.blockSignals(True)
        for cb in self.category_checkboxes.values(): cb.blockSignals(True)
        
        self.attempts_spin.setValue(int(settings.get("attempts", 1)))
        
        active_cats = settings.get("active_categories", self.categories)
        for cat, cb in self.category_checkboxes.items():
            cb.setChecked(cat in active_cats)
            
        self.attempts_spin.blockSignals(False)
        for cb in self.category_checkboxes.values(): cb.blockSignals(False)
        self._on_category_toggled() # Force UI refresh of tables
        
        # Restore Custom Run Order if it exists
        saved_run_order = settings.get("run_order", [])
        if saved_run_order:
            self.run_order_list.clear()
            for block in saved_run_order:
                self.run_order_list.addItem(block)

        # 2. Restore Teams
        start_list = race_doc.get("start_list", [])
        for table in self.category_tables.values(): table.setRowCount(0)
        
        sorted_list = sorted(start_list, key=lambda x: int(x.get("start_no", 999)))
        for t_data in sorted_list:
            self._insert_team_to_queue(t_data.get("team", ""), t_data.get("category", "-"))

    # --- TRANSLATION METHOD ---
    def retranslate_ui(self):
        self.lbl_league.setText(tr.t("common_lbl_league"))
        self.lbl_race.setText(tr.t("common_lbl_race"))
        self.lbl_config_title.setText(tr.t("race_lbl_config_title"))
        self.lbl_queue_title.setText(tr.t("race_lbl_queue_title"))
        
        current_preset = self.preset_combo.currentData()
        self.preset_combo.blockSignals(True)
        if self.preset_combo.findData("custom") < 0:
            self.preset_combo.insertItem(0, tr.t("race_preset_custom"), "custom")
        else:
            self.preset_combo.setItemText(self.preset_combo.findData("custom"), tr.t("race_preset_custom"))
        self.preset_combo.setCurrentIndex(self.preset_combo.findData(current_preset))
        self.preset_combo.blockSignals(False)

        self.lbl_preset.setText(tr.t("race_lbl_preset"))
        self.lbl_logic.setText(tr.t("race_lbl_logic"))
        self.lbl_attempts.setText(tr.t("race_lbl_attempts"))
        self.btn_save_preset.setText(tr.t("race_btn_save_preset"))

        self.lbl_cats.setText(tr.t("race_lbl_categories"))
        self.lbl_run_order.setText(tr.t("race_lbl_run_order"))
        
        self.new_team_name.setPlaceholderText(tr.t("race_placeholder_team_name"))
        self.btn_add_team.setText(tr.t("race_btn_add_team"))
        self.btn_import.setText(tr.t("race_btn_import"))
        self.btn_export.setText(tr.t("race_btn_export"))
        self.btn_recovery.setText(tr.t("race_btn_recovery"))
        self.btn_publish.setText(tr.t("btn_publish"))

        # Loop through all dynamic tables and set their headers
        for table in self.category_tables.values():
            table.setHorizontalHeaderLabels([
                tr.t("lbl_start_no"), 
                tr.t("common_col_team"), 
                tr.t("lbl_action")
            ])
            
    # --- LOGIC METHODS ---

    def load_initial_dropdowns(self):
        """Loads all available leagues into the league combobox on startup."""
        self.league_combo.blockSignals(True) # Prevent triggering race load multiple times
        self.league_combo.clear()
        
        leagues = self.db.get_all_leagues()
        for league in leagues:
            self.league_combo.addItem(league.get("name", "Unknown"), league.get("id"))
            
        self.league_combo.blockSignals(False)
        
        # Auto-select the user's assigned league if they have one
        if self.user_league_id:
            index = self.league_combo.findData(self.user_league_id)
            if index >= 0:
                self.league_combo.setCurrentIndex(index)
                
        # Trigger the race load for the selected league
        self.load_races_for_selected_league()

    def load_races_for_selected_league(self):
        """Fetches and populates the races based on the selected league."""
        self.race_combo.blockSignals(True)
        self.race_combo.clear()
        
        league_id = self.league_combo.currentData()
        if not league_id:
            self.race_combo.blockSignals(False)
            return
            
        races = self.db.get_races_for_league(league_id)
        for race in races:
            self.race_combo.addItem(race.get("name", "Unknown"), race.get("id"))
            
        self.race_combo.blockSignals(False)
        
        # Load the data for the first race in the list automatically
        self.load_race_data()

    def save_current_as_preset(self):
        name, ok = QInputDialog.getText(self, tr.t("race_dialog_save_preset_title"), tr.t("race_dialog_save_preset_prompt"))
        if ok and name:
            preset_key = name.lower().replace(" ", "_")
            self.sport_presets[preset_key] = {
                "name_key": name, 
                "base_logic": self.base_logic_combo.currentText(),
                "default_lanes": self.lanes_spin.value(), 
                "default_attempts": self.attempts_spin.value(),
                "sections": self.sections_spin.value(), 
                "allow_penalties": self.allow_penalties_cb.isChecked(),
                "penalty_type": self.penalty_type_combo.currentText()
            }
            with open(PRESETS_FILE, "w", encoding="utf-8") as f: 
                json.dump(self.sport_presets, f, ensure_ascii=False, indent=4)
            
            self.preset_combo.blockSignals(True)
            self.preset_combo.addItem(name, preset_key)
            self.preset_combo.setCurrentIndex(self.preset_combo.count() - 1)
            self.preset_combo.blockSignals(False)

    def export_teams(self):
        """Exports the current start list across all categories to a CSV file."""
        file_path, _ = QFileDialog.getSaveFileName(self, tr.t("race_export"), "", "CSV Files (*.csv)")
        if not file_path: return
            
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["StartNo", "Team", "Category"]) # Added Category header
                
                for cat, table in self.category_tables.items():
                    for row in range(table.rowCount()):
                        start_no = table.item(row, 0).text()
                        team = table.item(row, 1).text()
                        writer.writerow([start_no, team, cat])
                        
            QMessageBox.information(self, tr.t("msg_success"), tr.t("msg_export_success"))
        except Exception as e:
            QMessageBox.critical(self, tr.t("msg_error"), str(e))

    def import_teams(self):
        """Imports teams from a CSV file into their respective categories."""
        file_path, _ = QFileDialog.getOpenFileName(self, tr.t("race_import"), "", "CSV Files (*.csv)")
        if not file_path: return
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                
                # Check if it's the new format with category, or fallback to default
                has_category = header and len(header) >= 3 and "Category" in header[2]
                
                # We do NOT clear tables here, we append. If user wants to clear, they can refresh.
                imported_count = 0
                for row in reader:
                    if len(row) >= 2:
                        team_name = row[1]
                        # Use category from CSV if present, otherwise default to the first available category
                        category = row[2] if len(row) >= 3 and has_category else self.categories[0] 
                        
                        # Make sure the category checkbox is checked so the table is visible
                        if category in self.category_checkboxes:
                            self.category_checkboxes[category].setChecked(True)
                            
                        self._insert_team_to_queue(team_name, category)
                        imported_count += 1
                        
            QMessageBox.information(self, tr.t("msg_success"), tr.t("msg_import_success", count=imported_count))
        except Exception as e:
            QMessageBox.critical(self, tr.t("msg_error"), str(e))
            
    def trigger_autosave(self):
        """Saves current state of all category tables to a local JSON file for recovery."""
        recovery_data = []
        
        # Loop through all available category tables
        for cat, table in self.category_tables.items():
            for row in range(table.rowCount()):
                start_no_item = table.item(row, 0)
                team_item = table.item(row, 1)
                
                if start_no_item and team_item:
                    recovery_data.append({
                        "start_no": int(start_no_item.text()),
                        "team": team_item.text(),
                        "category": cat
                    })
        
        try:
            with open(RECOVERY_FILE, "w", encoding="utf-8") as f:
                json.dump(recovery_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[Warning] Failed to autosave: {e}")

    def load_recovery(self):
        """Loads teams from the local autosave file into their respective categories."""
        if not os.path.exists(RECOVERY_FILE):
            QMessageBox.warning(self, tr.t("msg_error"), tr.t("err_file_not_found", file=RECOVERY_FILE))
            return
            
        try:
            with open(RECOVERY_FILE, "r", encoding="utf-8") as f:
                recovery_data = json.load(f)
                
            # Clear all current tables
            for table in self.category_tables.values():
                table.setRowCount(0)
                
            # Sort by start_no just in case, then insert
            sorted_list = sorted(recovery_data, key=lambda x: int(x.get("start_no", 999)))
            for t_data in sorted_list:
                self._insert_team_to_queue(t_data.get("team", ""), t_data.get("category", "-"))
                
            QMessageBox.information(self, tr.t("msg_success"), tr.t("msg_recovery_loaded", count=len(recovery_data)))
        except Exception as e:
            QMessageBox.critical(self, tr.t("msg_error"), f"Recovery error: {e}") 
