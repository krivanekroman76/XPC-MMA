from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QComboBox, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QTabWidget, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from core.translate import tr

class LeaderboardPage(QWidget):
    def __init__(self, db_service, dashboard_parent):
        super().__init__()
        self.db = db_service
        self.dashboard = dashboard_parent
        self.current_results_data = []
        
        self.setup_ui()
        self.retranslate_ui()

    def showEvent(self, event):
        """Automatically refresh dropdowns and data when the page becomes visible."""
        super().showEvent(event)
        self.load_leagues()

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

        top_layout.addSpacing(20)

        self.lbl_sort = QLabel()
        top_layout.addWidget(self.lbl_sort)
        self.combo_sort = QComboBox()
        self.combo_sort.currentIndexChanged.connect(self.refresh_tables)
        top_layout.addWidget(self.combo_sort)

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
        self.lbl_sort.setText(tr.t("lb_lbl_sort"))
        self.btn_refresh.setText(tr.t("lb_btn_refresh"))

        current_sort_idx = max(0, self.combo_sort.currentIndex())
        self.combo_sort.blockSignals(True)
        self.combo_sort.clear()
        self.combo_sort.addItems([tr.t("lb_sort_start_order"), tr.t("lb_sort_placement")])
        self.combo_sort.setCurrentIndex(current_sort_idx)
        self.combo_sort.blockSignals(False)

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

        raw_teams = self.db.get_race_start_list(league_id, race_id)
        self.current_results_data = []

        for team_data in raw_teams:
            team_str = str(team_data.get("team", ""))
            start_no = team_data.get("start_no", 0) 
            team_name = team_str
            
            # Legacy format safety check
            if ". " in team_str:
                parts = team_str.split(". ", 1)
                if parts[0].isdigit():
                    if not start_no: start_no = int(parts[0])
                    team_name = parts[1]

            # Parse Overall Team Status
            raw_state = str(team_data.get("status", team_data.get("state", "WAITING"))).upper()
            if raw_state in ["DONE", "VALID", "PLATNÝ", "HOTOVO", "FINISHED"]:
                status = "DONE"
            elif raw_state in ["NP", "NEPLATNÝ", "INV"]:
                status = "NP"
            elif raw_state in ["PREPARING", "READY"]:
                status = "PREPARING"
            else:
                status = "WAITING"

            # Parse Top/Best Result Time
            best_time_raw = team_data.get("best_time", team_data.get("result_time", team_data.get("final_time")))
            best_time_val = None
            
            if status == "DONE" and best_time_raw not in [None, "NP", "--.---", "", "None"]:
                try:
                    best_time_val = float(str(best_time_raw).replace(",", "."))
                except ValueError:
                    best_time_val = None

            best_time_display = str(best_time_raw) if best_time_raw else "--.---"

            # Parse Attempts Data (with fallback for legacy single-run rows)
            attempts = team_data.get("attempts", [])
            if not attempts and ("time_left" in team_data or "base_time" in team_data):
                attempts = [{
                    "time_left": team_data.get("time_left", team_data.get("base_time")),
                    "time_right": team_data.get("time_right", "--.---"),
                    "result_time": team_data.get("result_time", team_data.get("final_time")),
                    "state": status
                }]

            self.current_results_data.append({
                "start_no": start_no,
                "team": team_name,
                "category": team_data.get("category", "-"),
                "status": status,
                "best_time_val": best_time_val,
                "best_time_str": best_time_display,
                "attempts": attempts
            })

        self.refresh_tables()

    def refresh_tables(self):
        if not hasattr(self, 'current_results_data') or not self.current_results_data:
            self.tabs.clear()
            return

        sort_by_placement = (self.combo_sort.currentIndex() == 1)
        
        # Determine the maximum number of attempts any team has taken to build columns
        max_attempts = 1
        for data in self.current_results_data:
            if len(data["attempts"]) > max_attempts:
                max_attempts = len(data["attempts"])

        categories = ["ALL"] + sorted(list(set(item["category"] for item in self.current_results_data)))
        self.tabs.clear()

        for category in categories:
            if category == "ALL":
                cat_data = self.current_results_data
                tab_title = tr.t("lb_tab_all")
            else:
                cat_data = [item for item in self.current_results_data if item["category"] == category]
                tab_title = category

            # Sorting Logic
            if sort_by_placement:
                valid_runs = sorted([d for d in cat_data if d["best_time_val"] is not None], key=lambda x: x["best_time_val"])
                np_runs = [d for d in cat_data if d["status"] == "NP" or str(d["best_time_str"]).upper() == "NP"]
                other_runs = [d for d in cat_data if d not in valid_runs and d not in np_runs]
                sorted_data = valid_runs + np_runs + other_runs
            else:
                sorted_data = sorted(cat_data, key=lambda x: x["start_no"])

            table = QTableWidget()
            table.setObjectName("dataTable") 
            
            # --- Build Dynamic Headers ---
            base_headers = [
                tr.t("lb_col_rank"),
                tr.t("lb_col_start_no"),
                tr.t("lb_col_team"),
                tr.t("common_col_status"),
                tr.t("lb_col_top_result")
            ]
            attempt_headers = []
            for i in range(1, max_attempts + 1):
                attempt_headers.extend([f"L{i}", f"P{i}", f"{tr.t('lb_col_time')} {i}"])

            headers = base_headers + attempt_headers
            table.setColumnCount(len(headers))
            table.setHorizontalHeaderLabels(headers)
            
            # Stretch the "Team" column
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.setSelectionBehavior(QTableWidget.SelectRows)

            table.setRowCount(len(sorted_data))
            
            # --- Populate Rows ---
            for row_idx, data in enumerate(sorted_data):
                rank_text = str(row_idx + 1) if sort_by_placement and data["best_time_val"] is not None else "-"
                
                # Overall Status Colors
                bg_color = QColor("#1e1e2e") 
                text_color = QColor("#cdd6f4")
                
                if data["status"] == "DONE":
                    status_str = "✅ " + tr.t("state_done")
                    bg_color, text_color = QColor("#a6e3a1"), QColor("#11111b") 
                elif data["status"] == "NP":
                    status_str = "❌ " + tr.t("state_np")
                    bg_color, text_color = QColor("#f38ba8"), QColor("#11111b") 
                elif data["status"] == "PREPARING":
                    status_str = "⏳ " + tr.t("state_preparing")
                    bg_color, text_color = QColor("#f9e2af"), QColor("#11111b") 
                else:
                    status_str = "⏳ " + tr.t("lb_status_waiting")

                # Top Result Styling
                top_res_str = data["best_time_str"]
                if top_res_str not in ["NP", "--.---", ""]: 
                    top_res_str = f"{float(top_res_str):.3f}"

                # Create Base Cells
                cells = [
                    QTableWidgetItem(rank_text),
                    QTableWidgetItem(str(data["start_no"])),
                    QTableWidgetItem(data["team"]),
                    QTableWidgetItem(status_str),
                    QTableWidgetItem(top_res_str)
                ]

                # Create Attempt Cells dynamically
                for i in range(max_attempts):
                    if i < len(data["attempts"]):
                        attempt = data["attempts"][i]
                        l_time = str(attempt.get("time_left", "--"))
                        r_time = str(attempt.get("time_right", "--"))
                        res_time = str(attempt.get("result_time", "--"))
                    else:
                        l_time = r_time = res_time = "--"
                    
                    cells.extend([
                        QTableWidgetItem(l_time),
                        QTableWidgetItem(r_time),
                        QTableWidgetItem(res_time)
                    ])

                # Apply formatting
                bold_font = QFont()
                bold_font.setBold(True)

                for col, item in enumerate(cells):
                    # Default row colors
                    item.setBackground(bg_color)
                    item.setForeground(text_color)
                    item.setTextAlignment(Qt.AlignCenter)
                    
                    # Special highlighting for the "TOP RESULT" column (index 4)
                    if col == 4:
                        item.setFont(bold_font)
                        if bg_color.name() == "#1e1e2e": # If standard row, make text Yellow
                            item.setForeground(QColor("#f9e2af")) 
                            
                    table.setItem(row_idx, col, item)

            self.tabs.addTab(table, tab_title)

    def refresh_dropdowns(self):
        """Clears and reloads the leagues and races from Firebase."""
        self.combo_league.blockSignals(True)
        self.combo_race.blockSignals(True)
        
        self.combo_league.clear()
        self.combo_race.clear()
        
        for league in self.db.get_all_leagues():
            self.combo_league.addItem(league["name"], league["id"])
            
        self.combo_league.blockSignals(False)
        self.combo_race.blockSignals(False)
        self.load_races()