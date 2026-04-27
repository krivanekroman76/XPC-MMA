import re
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QComboBox, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QTabWidget, QFrame, QCheckBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont
from core.translate import tr

class LeaderboardPage(QWidget):
    def __init__(self, db_service, dashboard_parent):
        super().__init__()
        self.db = db_service
        self.dashboard = dashboard_parent
        self.current_results_data = []
        self.race_settings = {}
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_results)
        
        self.setup_ui()
        self.retranslate_ui()

    def showEvent(self, event):
        """Automatically refresh dropdowns and data when the page becomes visible."""
        super().showEvent(event)
        self.load_leagues()
        self.refresh_timer.start(5000)
    
    def hideEvent(self, event):
        """Stop auto-refresh when page is hidden."""
        super().hideEvent(event)
        self.refresh_timer.stop()

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        # --- TOP PANEL ---
        top_panel = QFrame()
        top_panel.setObjectName("panel") 
        top_layout = QHBoxLayout(top_panel)
        top_layout.setContentsMargins(15, 10, 15, 10)

        self.lbl_league = QLabel()
        top_layout.addWidget(self.lbl_league)
        self.combo_league = QComboBox()
        self.combo_league.currentIndexChanged.connect(self.load_races)
        top_layout.addWidget(self.combo_league)

        self.lbl_race = QLabel()
        top_layout.addWidget(self.lbl_race)
        self.combo_race = QComboBox()
        self.combo_race.currentIndexChanged.connect(self.load_results)
        top_layout.addWidget(self.combo_race)

        top_layout.addSpacing(30)

        # Updated Icons: List (Start Order) vs Trophy (Rank)
        self.lbl_sort_start = QLabel("☰") 
        self.lbl_sort_start.setStyleSheet("font-size: 18px; color: #a6adc8;")
        top_layout.addWidget(self.lbl_sort_start)
        
        # Gold themed toggle switch
        self.sort_toggle = QCheckBox()
        self.sort_toggle.setCursor(Qt.PointingHandCursor)
        self.sort_toggle.setStyleSheet("""
            QCheckBox {
                spacing: 0px;
            }
            QCheckBox::indicator {
                width: 45px;
                height: 22px;
                background-color: #313244;
                border-radius: 11px;
                border: 1px solid #45475a;
            }
            QCheckBox::indicator:unchecked {
                image: none;
                background-color: #313244;
            }
            QCheckBox::indicator:checked {
                background-color: #f9e2af; /* GOLD BACKGROUND */
            }
            /* The actual moving slider handle */
            QCheckBox::indicator:unchecked {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #89b4fa, stop:0.4 #89b4fa, stop:0.41 #313244, stop:1 #313244);
                border-radius: 11px;
            }
            QCheckBox::indicator:checked {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #313244, stop:0.59 #313244, stop:0.6 #45475a, stop:1 #45475a);
                image: none;
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #313244, stop:0.59 #313244, stop:0.6 #11111b, stop:1 #11111b);
                background-color: #f9e2af; 
            }
        """)
        self.sort_toggle.stateChanged.connect(self.on_sort_toggle_changed)
        top_layout.addWidget(self.sort_toggle)
        
        self.lbl_sort_end = QLabel("🏆")
        self.lbl_sort_end.setStyleSheet("font-size: 18px; color: #f9e2af;")
        top_layout.addWidget(self.lbl_sort_end)

        top_layout.addStretch()

        self.btn_refresh = QPushButton()
        self.btn_refresh.setObjectName("primaryButton") 
        self.btn_refresh.clicked.connect(self.load_results)
        top_layout.addWidget(self.btn_refresh)

        self.layout.addWidget(top_panel)

        # --- MAIN AREA: Tabs ---
        self.tabs = QTabWidget()
        self.tabs.setObjectName("mainTabs") 
        self.layout.addWidget(self.tabs, stretch=1)

    def retranslate_ui(self):
        self.lbl_league.setText(tr.t("common_lbl_league"))
        self.lbl_race.setText(tr.t("common_lbl_race"))
        self.btn_refresh.setText(tr.t("lb_btn_refresh"))
        self.refresh_tables()
    
    def on_sort_toggle_changed(self):
        self.refresh_tables()

    def load_leagues(self):
        self.combo_league.blockSignals(True)
        self.combo_league.clear()
        all_leagues = self.db.get_all_leagues()
        for lg in all_leagues:
            self.combo_league.addItem(f"{lg.get('abbreviation', '')} - {lg.get('name', 'Unknown')}", lg.get('id'))
        self.combo_league.blockSignals(False)
        self.load_races()

    def load_races(self):
        league_id = self.combo_league.currentData()
        self.combo_race.blockSignals(True)
        self.combo_race.clear()
        if league_id:
            races = self.db.get_races_for_league(league_id)
            for race in races:
                self.combo_race.addItem(race.get('name', tr.t("timing_unknown_race")), race.get('id'))
        self.combo_race.blockSignals(False)
        self.load_results()

    def load_results(self):
        league_id = self.combo_league.currentData()
        race_id = self.combo_race.currentData()
        if not league_id or not race_id:
            self.tabs.clear()
            self.current_results_data = []
            return

        race_doc = self.db.get_race(league_id, race_id)
        if not race_doc: return
        
        self.race_settings = race_doc.get("settings", {})
        raw_teams = race_doc.get("start_list", [])
        
        self.current_results_data = []
        for team_data in raw_teams:
            # Basic parsing logic
            raw_state = str(team_data.get("status", team_data.get("state", "WAITING"))).upper()
            if raw_state in ["DONE", "VALID", "PLATNÝ", "HOTOVO", "FINISHED"]: status = "DONE"
            elif raw_state in ["NP", "NEPLATNÝ", "INV"]: status = "NP"
            elif raw_state in ["PREPARING", "READY"]: status = "PREPARING"
            else: status = "WAITING"

            best_time_raw = team_data.get("best_time", team_data.get("result_time", team_data.get("final_time")))
            best_time_val = None
            if status == "DONE" and best_time_raw not in [None, "NP", "--.---", "", "None"]:
                try: best_time_val = float(str(best_time_raw).replace(",", "."))
                except: best_time_val = None

            self.current_results_data.append({
                "start_no": team_data.get("start_no", 0),
                "team": team_data.get("team", "Unknown"),
                "category": team_data.get("category", "-"),
                "status": status,
                "best_time_val": best_time_val,
                "best_time_str": str(best_time_raw) if best_time_raw else "--.---",
                "attempts": team_data.get("attempts", [])
            })

        self.refresh_tables()

    def refresh_tables(self):
        if not hasattr(self, 'current_results_data') or not self.current_results_data:
            self.tabs.clear()
            return

        # SAVE CURRENT TAB INDEX
        current_tab_idx = self.tabs.currentIndex()
        
        sort_by_placement = self.sort_toggle.isChecked()
        run_order = self.race_settings.get("run_order", [])
        unique_categories = sorted(list(set(item["category"] for item in self.current_results_data)))
        categories_to_render = ["ALL"] + unique_categories
        
        self.tabs.clear()

        for category_tab in categories_to_render:
            if category_tab == "ALL":
                tab_data_pool = self.current_results_data
                tab_title = tr.t("lb_tab_all")
            else:
                tab_data_pool = [item for item in self.current_results_data if item["category"] == category_tab]
                tab_title = category_tab

            # --- SORTING ---
            if sort_by_placement:
                valid_runs = sorted([d for d in tab_data_pool if d["best_time_val"] is not None], key=lambda x: x["best_time_val"])
                np_runs = [d for d in tab_data_pool if d["status"] == "NP"]
                others = [d for d in tab_data_pool if d not in valid_runs and d not in np_runs]
                sorted_data = valid_runs + np_runs + others
            else:
                sorted_data = []
                for block_text in run_order:
                    target_cat, _ = self._parse_block_info(block_text)
                    block_teams = sorted([d for d in tab_data_pool if d["category"] == target_cat], key=lambda x: x["start_no"])
                    for team in block_teams:
                        if team not in sorted_data: sorted_data.append(team)

            # --- TABLE UI ---
            table = QTableWidget()
            table.setObjectName("dataTable")
            max_attempts = max([len(d["attempts"]) for d in self.current_results_data], default=1)
            
            headers = [tr.t("lb_col_rank"), tr.t("lb_col_start_no"), tr.t("lb_col_team"), tr.t("common_col_status"), tr.t("lb_col_top_result")]
            for i in range(1, max_attempts + 1):
                headers.extend([f"L{i}", f"P{i}", f"{tr.t('lb_col_time')} {i}"])
            
            table.setColumnCount(len(headers))
            table.setHorizontalHeaderLabels(headers)
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.setRowCount(len(sorted_data))

            active_highlighted = False
            for row_idx, data in enumerate(sorted_data):
                rank_text = str(row_idx + 1) if sort_by_placement and data["best_time_val"] is not None else "-"
                bg_color, text_color = QColor("#1e1e2e"), QColor("#cdd6f4")
                status_str = data["status"]

                if not sort_by_placement and not active_highlighted and data["status"] in ["PREPARING", "READY"]:
                    bg_color, text_color = QColor("#89b4fa"), QColor("#11111b")
                    status_str = "🚀 " + tr.t("state_running")
                    active_highlighted = True
                
                if data["status"] == "DONE":
                    status_str = "✅ " + tr.t("state_done")
                    if not active_highlighted: bg_color, text_color = QColor("#a6e3a1"), QColor("#11111b")
                elif data["status"] == "NP":
                    status_str = "❌ " + tr.t("state_np")
                    bg_color, text_color = QColor("#f38ba8"), QColor("#11111b")

                top_res = data["best_time_str"]
                if top_res not in ["NP", "--.---", ""]: 
                    try: top_res = f"{float(top_res):.3f}"
                    except: pass

                cells = [QTableWidgetItem(rank_text), QTableWidgetItem(str(data["start_no"])), QTableWidgetItem(data["team"]), QTableWidgetItem(status_str), QTableWidgetItem(top_res)]

                for i in range(max_attempts):
                    if i < len(data["attempts"]):
                        att = data["attempts"][i]
                        cells.extend([QTableWidgetItem(str(att.get("time_left", "--"))), QTableWidgetItem(str(att.get("time_right", "--"))), QTableWidgetItem(str(att.get("final_time", "--") if att.get("final_time") != 999999 else "NP"))])
                    else: cells.extend([QTableWidgetItem("--"), QTableWidgetItem("--"), QTableWidgetItem("--")])

                bold_font = QFont(); bold_font.setBold(True)
                for col, item in enumerate(cells):
                    item.setBackground(bg_color); item.setForeground(text_color); item.setTextAlignment(Qt.AlignCenter)
                    if col == 4:
                        item.setFont(bold_font)
                        if not sort_by_placement and bg_color.name() == "#1e1e2e": item.setForeground(QColor("#f9e2af"))
                    if sort_by_placement and rank_text.isdigit():
                        r_num = int(rank_text)
                        if r_num == 1: item.setBackground(QColor("#f9e2af")); item.setForeground(QColor("#11111b")) # GOLD
                        elif r_num == 2: item.setBackground(QColor("#C0C0C0")); item.setForeground(QColor("#11111b")) # SILVER
                        elif r_num == 3: item.setBackground(QColor("#CD7F32")); item.setForeground(QColor("#ffffff")) # BRONZE
                    table.setItem(row_idx, col, item)

            self.tabs.addTab(table, tab_title)

        # RESTORE TAB INDEX
        if current_tab_idx >= 0 and current_tab_idx < self.tabs.count():
            self.tabs.setCurrentIndex(current_tab_idx)

    def _parse_block_info(self, block_text):
        if " - " not in block_text: return None, 0
        parts = block_text.split(" - ")
        category = parts[0]
        numbers = re.findall(r'\d+', parts[1])
        attempt_num = int(numbers[0]) if numbers else 1
        return category, attempt_num - 1

    def refresh_dropdowns(self):
        self.combo_league.blockSignals(True); self.combo_race.blockSignals(True)
        self.combo_league.clear(); self.combo_race.clear()
        for league in self.db.get_all_leagues():
            self.combo_league.addItem(league["name"], league["id"])
        self.combo_league.blockSignals(False); self.combo_race.blockSignals(False)
        self.load_races()