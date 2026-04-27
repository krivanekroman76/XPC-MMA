import random
import re
import threading
import requests
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QFrame, QTableWidget, 
                               QTableWidgetItem, QHeaderView, QMessageBox,
                               QComboBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor

from core.translate import tr 
from core.sport_logic import get_sport_logic
from .confirm import AttemptConfirmDialog

class TimingPage(QWidget):
    def __init__(self, db_service, dashboard_parent):
        super().__init__()
        self.db = db_service
        self.dashboard = dashboard_parent
        
        self.is_hardware_connected = False
        self.current_start_list = []
        self.race_settings = {}
        self.sport_logic = None
        
        # Auto-refresh timer for dropdowns
        self.dropdown_refresh_timer = QTimer()
        self.dropdown_refresh_timer.timeout.connect(self.load_initial_dropdowns)

        self.setup_ui()
        
        # Keep your existing connections
        self.league_combo.currentIndexChanged.connect(self.load_races_for_selected_league)
        self.race_combo.currentIndexChanged.connect(self.fetch_and_render_data)

        # --- NEW: Auto-load COM ports when the app starts! ---
        self.refresh_com_ports()

    def showEvent(self, event):
        super().showEvent(event)
        self.load_initial_dropdowns()
        self.dropdown_refresh_timer.start(5000)  # Refresh every 5 seconds
    
    def hideEvent(self, event):
        super().hideEvent(event)
        self.dropdown_refresh_timer.stop()

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        # --- HEADER ---
        header_frame = QFrame()
        header_frame.setObjectName("panel")
        header_layout = QHBoxLayout(header_frame)
        
        self.league_combo = QComboBox() 
        self.race_combo = QComboBox()

        header_layout.addWidget(QLabel(tr.t("timing_league")))
        header_layout.addWidget(self.league_combo)
        header_layout.addWidget(QLabel(tr.t("timing_race")))
        header_layout.addWidget(self.race_combo)
        header_layout.addStretch()
        self.layout.addWidget(header_frame)

        # --- HARDWARE CONTROL PANEL ---
        hardware_frame = QFrame()
        hardware_frame.setObjectName("hardwareFrame") 
        hardware_layout = QHBoxLayout(hardware_frame)
        
        # NEW: COM Port Selection
        self.combo_ports = QComboBox()
        self.combo_ports.setMinimumWidth(150)
        
        self.btn_refresh_ports = QPushButton("Obnovit")
        self.btn_refresh_ports.setFixedWidth(30)
        self.btn_refresh_ports.clicked.connect(self.refresh_com_ports)
        
        self.btn_connect = QPushButton(tr.t("timing_btn_connect")) 
        self.btn_connect.setObjectName("primaryButton")
        self.btn_connect.clicked.connect(self.toggle_hardware_connection)
        
        self.lbl_hw_status = QLabel(tr.t("timing_hw_disconnected"))
        self.lbl_hw_status.setObjectName("hwStatusLabelError") 
        
        hardware_layout.addWidget(QLabel("COM Port:"))
        hardware_layout.addWidget(self.combo_ports)
        hardware_layout.addWidget(self.btn_refresh_ports)
        hardware_layout.addWidget(self.btn_connect)
        hardware_layout.addSpacing(15)
        hardware_layout.addWidget(self.lbl_hw_status)
        hardware_layout.addStretch()

        # NEW: "Skip" Button
        self.btn_skip = QPushButton(tr.t("timing_btn_skip"))
        self.btn_skip.setObjectName("warningButton") 
        self.btn_skip.clicked.connect(self.move_current_team_to_bottom)
        
        self.btn_sim_l1 = QPushButton(tr.t("timing_sim_l1"))
        self.btn_sim_l2 = QPushButton(tr.t("timing_sim_l2"))
        self.btn_np = QPushButton(tr.t("timing_btn_np"))
        
        self.btn_sim_l1.setObjectName("primaryButton")
        self.btn_sim_l2.setObjectName("primaryButton")
        self.btn_np.setObjectName("dangerButton")

        self.btn_sim_l1.clicked.connect(lambda: self.trigger_hardware_action("L1"))
        self.btn_sim_l2.clicked.connect(lambda: self.trigger_hardware_action("L2"))
        self.btn_np.clicked.connect(lambda: self.trigger_hardware_action("NP"))

        hardware_layout.addWidget(self.btn_skip)
        hardware_layout.addWidget(self.btn_sim_l1)
        hardware_layout.addWidget(self.btn_sim_l2)
        hardware_layout.addWidget(self.btn_np)
        self.layout.addWidget(hardware_frame)

        # --- MAIN TIMING TABLE ---
        self.table = QTableWidget()
        self.table.setObjectName("dataTable") 
        self.table.setColumnCount(6)
        
        headers = [
            tr.t("timing_header_st_no"), 
            tr.t("timing_header_team"), 
            tr.t("timing_header_cat"), 
            tr.t("timing_header_state"), 
            tr.t("timing_header_targets"), 
            tr.t("timing_header_result")
        ]
        self.table.setHorizontalHeaderLabels(headers)
        
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setShowGrid(False) 
        self.layout.addWidget(self.table, stretch=1)
        
    def load_initial_dropdowns(self):
        self.league_combo.blockSignals(True)
        self.league_combo.clear()
        for lg in self.db.get_all_leagues(): 
            self.league_combo.addItem(f"{lg.get('abbreviation', '')} - {lg.get('name', '')}", lg.get('id'))
        self.league_combo.blockSignals(False)
        self.load_races_for_selected_league()

    def load_races_for_selected_league(self):
        self.race_combo.blockSignals(True)
        self.race_combo.clear()
        league_id = self.league_combo.currentData()
        if league_id:
            for race in self.db.get_races_for_league(league_id):
                self.race_combo.addItem(race.get('name', tr.t("timing_unknown_race")), race.get('id'))
        self.race_combo.blockSignals(False)
        self.fetch_and_render_data()

    def fetch_and_render_data(self):
        league_id = self.league_combo.currentData()
        race_id = self.race_combo.currentData()
        if not league_id or not race_id: return

        race_doc = self.db.get_race(league_id, race_id)
        if not race_doc: return

        self.race_settings = race_doc.get("settings", {})
        self.current_start_list = race_doc.get("start_list", [])
        
        logic_name = self.race_settings.get("logic", "attack")
        self.sport_logic = get_sport_logic(logic_name)

        self.render_table()

    def _parse_block_info(self, block_text):
        """Parses the block text (e.g., 'Muži - 1. pokus') to get category and attempt index."""
        if " - " not in block_text:
            return None, 0
        parts = block_text.split(" - ")
        category = parts[0]
        numbers = re.findall(r'\d+', parts[1])
        attempt_num = int(numbers[0]) if numbers else 1
        return category, attempt_num - 1 

    def render_table(self):
        self.table.clearContents()
        self.table.setRowCount(0)
        
        run_order = self.race_settings.get("run_order", [])
        if not run_order: return

        row_idx = 0
        
        # Iterate through the chronological run order
        for block_text in run_order:
            target_category, attempt_idx = self._parse_block_info(block_text)
            if not target_category: continue

            # --- ADD SEPARATOR ROW ---
            self.table.insertRow(row_idx)
            sep_item = QTableWidgetItem(f"--- {block_text} ---")
            sep_item.setTextAlignment(Qt.AlignCenter)
            sep_item.setBackground(QColor("#313244")) # Dark background for separator
            sep_item.setForeground(QColor("#a6adc8")) # Subtle text color
            
            font = sep_item.font()
            font.setBold(True)
            sep_item.setFont(font)
            
            # Make the item span across all 6 columns
            self.table.setSpan(row_idx, 0, 1, 6)
            self.table.setItem(row_idx, 0, sep_item)
            row_idx += 1

            # --- ADD TEAMS FOR THIS BLOCK ---
            for original_index, run in enumerate(self.current_start_list):
                if run.get("category") != target_category:
                    continue 
                
                self.table.insertRow(row_idx)
                
                attempts = run.get("attempts", [])
                while len(attempts) <= attempt_idx:
                    attempts.append({"state": "PREPARING", "time_left": "--.---", "time_right": "--.---", "final_time": None})
                
                run["attempts"] = attempts 
                current_attempt = attempts[attempt_idx]

                status = str(current_attempt.get("state", "PREPARING")).upper()
                
                # Translations and Colors
                display_status = status 
                if status == "PREPARING": display_status = tr.t("state_preparing")
                elif status == "READY": display_status = tr.t("state_ready")
                elif status == "DONE": display_status = tr.t("state_done")
                elif status == "NP": display_status = tr.t("state_np")

                bg_color, text_color = QColor("#1e1e2e"), QColor("#cdd6f4")
                if status == "PREPARING": bg_color, text_color = QColor("#f9e2af"), QColor("#11111b")
                elif status == "READY": bg_color, text_color = QColor("#89b4fa"), QColor("#11111b")
                elif status == "DONE": bg_color, text_color = QColor("#a6e3a1"), QColor("#11111b")
                elif status == "NP": bg_color, text_color = QColor("#f38ba8"), QColor("#11111b")

                t_left = str(current_attempt.get("time_left", "--.---"))
                t_right = str(current_attempt.get("time_right", "--.---"))
                targets_display = f"{t_left}  |  {t_right}"
                
                res_time = current_attempt.get("final_time")
                res_display = "NP" if res_time == 999999 else (str(res_time) if res_time else "--.---")

                items = [
                    QTableWidgetItem(str(run.get("start_no", "-"))),
                    QTableWidgetItem(run.get("team", tr.t("timing_unknown_team"))),
                    QTableWidgetItem(run.get("category", "-")),
                    QTableWidgetItem(display_status),
                    QTableWidgetItem(targets_display),
                    QTableWidgetItem(res_display)
                ]
                
                for col, item in enumerate(items):
                    item.setBackground(bg_color)
                    item.setForeground(text_color)
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row_idx, col, item)
                
                row_idx += 1

    def trigger_hardware_action(self, action):
        run_order = self.race_settings.get("run_order", [])
        
        active_original_idx = -1
        active_attempt_idx = -1
        current_attempt = None

        # Scan chronologically through the entire run order
        found = False
        for block_text in run_order:
            target_category, attempt_idx = self._parse_block_info(block_text)
            if not target_category: continue

            for idx, run in enumerate(self.current_start_list):
                if run.get("category") == target_category:
                    attempts = run.get("attempts", [])
                    if len(attempts) > attempt_idx:
                        att = attempts[attempt_idx]
                        state = att.get("state", "").upper()
                        if state not in ["DONE", "NP"]:
                            active_original_idx = idx
                            active_attempt_idx = attempt_idx
                            current_attempt = att
                            found = True
                            break
            if found: break 
                
        if not found:
            QMessageBox.information(self, tr.t("msg_info"), tr.t("timing_all_done"))
            return

        run_obj = self.current_start_list[active_original_idx]
        current_attempt["state"] = "READY" 

        t_l = current_attempt.get("time_left")
        t_r = current_attempt.get("time_right")
        has_l = t_l and t_l != "--.---"
        has_r = t_r and t_r != "--.---"
        has_any_time = has_l or has_r

        # Simulation Logic
        if action == "L1" and not has_l:
            if not has_any_time: 
                current_attempt["time_left"] = round(random.uniform(15.0, 20.0), 3)
            else:                
                current_attempt["time_left"] = round(random.uniform(20.0, 30.0), 3)
                
        elif action == "L2" and not has_r:
            if not has_any_time: 
                current_attempt["time_right"] = round(random.uniform(15.0, 20.0), 3)
            else:                
                current_attempt["time_right"] = round(random.uniform(20.0, 30.0), 3)
                
        elif action == "NP":
            if not has_l and not has_r:
                current_attempt["time_left"] = "NP"
                current_attempt["time_right"] = "NP"
            elif has_l and not has_r:
                current_attempt["time_right"] = "NP"
            elif has_r and not has_l:
                current_attempt["time_left"] = "NP"

        t_l = current_attempt.get("time_left")
        t_r = current_attempt.get("time_right")
        is_finished = (t_l and t_l != "--.---") and (t_r and t_r != "--.---")

        self.save_and_refresh()

        if is_finished:
            QTimer.singleShot(100, lambda: self.process_finished_run(run_obj, current_attempt, active_attempt_idx, t_l, t_r))

    def refresh_com_ports(self):
        self.combo_ports.clear()
        try:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            for port, desc, hwid in sorted(ports):
                self.combo_ports.addItem(f"{port} - {desc}", port)
        except Exception as e:
            print(f"Could not load COM ports: {e}")

    def toggle_hardware_connection(self):
        if self.is_hardware_connected:
            # --- DISCONNECT LOGIC ---
            try:
                # Safely close the port if it exists and is open
                if hasattr(self, "serial_port") and self.serial_port and self.serial_port.is_open:
                    self.serial_port.close()
            except Exception as e:
                print(f"Error closing COM port: {e}")

            self.is_hardware_connected = False
            
            # Reset UI to disconnected state
            self.btn_connect.setText(tr.t("timing_btn_connect"))
            self.btn_connect.setObjectName("primaryButton")
            self.combo_ports.setEnabled(True)
            self.btn_refresh_ports.setEnabled(True)
            
            self.lbl_hw_status.setText(tr.t("timing_hw_disconnected"))
            self.lbl_hw_status.setObjectName("hwStatusLabelError")
            
        else:
            # --- CONNECT LOGIC ---
            port_name = self.combo_ports.currentData()
            if not port_name:
                # If the dropdown is empty, don't try to connect
                return
                
            try:
                import serial
                # Configure the serial connection. 
                # Note: Adjust 'baudrate=9600' if your specific hardware uses a different speed (like 115200)
                self.serial_port = serial.Serial(port=port_name, baudrate=9600, timeout=1)
                self.is_hardware_connected = True
                
                # Update UI to connected state
                self.btn_connect.setText(tr.t("timing_btn_disconnect")) # Make sure to add this to your translations!
                self.btn_connect.setObjectName("dangerButton") # Turns the button red/warning color for "Disconnect"
                
                # Disable the dropdowns so the user doesn't change ports while connected
                self.combo_ports.setEnabled(False)
                self.btn_refresh_ports.setEnabled(False)
                
                # Update the status label
                self.lbl_hw_status.setText(f"Hardware: Připojeno ({port_name})") # You can replace with tr.t() if you have a key
                self.lbl_hw_status.setObjectName("hwStatusLabelSuccess") # Assuming you have a green style setup
                
            except Exception as e:
                QMessageBox.critical(self, "Chyba", f"Nelze se připojit k {port_name}:\n{str(e)}")
                self.is_hardware_connected = False

        # --- REFRESH STYLES ---
        # This forces PySide6 to immediately redraw the colors (red/green/blue) based on the new objectNames
        self.btn_connect.style().unpolish(self.btn_connect)
        self.btn_connect.style().polish(self.btn_connect)
        self.lbl_hw_status.style().unpolish(self.lbl_hw_status)
        self.lbl_hw_status.style().polish(self.lbl_hw_status)
        
    def move_current_team_to_bottom(self):
        print("Skip logic goes here")
        
    def process_finished_run(self, run_obj, current_attempt, attempt_idx, t_l, t_r):
        is_np = (t_l == "NP" or t_r == "NP")
        initial_state = "NP" if is_np else "VALID"
        base_time = 0.0 if is_np else max(float(t_l), float(t_r))

        race_config = {
            "penalties_enabled": self.race_settings.get("allow_penalties", False),
            "penalty_type": self.race_settings.get("penalty_type", "seconds"),
            "track_count": self.race_settings.get("lanes", 2)
        }

        dialog = AttemptConfirmDialog(
            attempt_state=initial_state, 
            base_time=base_time, 
            race_config=race_config, 
            parent=self
        )
        
        if dialog.exec(): 
            results = dialog.get_result_data()
            
            # --- GET PREVIOUS BEST TIME ---
            previous_best = self.sport_logic.get_best_time(run_obj.get("attempts", []))
            title_key = "valid_attempt"
            is_np_flag = False
            
            # --- 1. UPDATE LOCAL DATA ---
            if results["status"] == "NP":
                current_attempt["state"] = "NP"
                current_attempt["final_time"] = 999999
                current_attempt["reason"] = results.get("reason", "")
                
                push_reason_key = results.get("reason", "") 
                is_np_flag = True
                title_key = "invalid_attempt"
            else:
                current_attempt["state"] = "DONE"
                
                lanes_dict = {
                    "L1": float(t_l) if t_l != "NP" else 0, 
                    "L2": float(t_r) if t_r != "NP" else 0
                }
                
                penalty_val = results.get("total_penalties", 0)
                final_time_sec = self.sport_logic.calculate_attempt_time(lanes_dict, penalty_val)
                final_time = round(final_time_sec, 3) if final_time_sec != 999999 else 999999
                
                current_attempt["final_time"] = final_time
                current_attempt["reason"] = results.get("reason", "")
                current_attempt["track_penalties"] = results.get("penalties_per_track", [])
                
                push_reason_key = f"{final_time}" # Send only the time
                
                # --- LOGIC FOR TIME COMPARISON ---
                if attempt_idx > 0 and previous_best < 999999:
                    if final_time < previous_best:
                        title_key = "time_improved"
                    elif final_time > previous_best:
                        title_key = "time_worse"

            # write the new best time into the run object for future comparisons
            run_obj["best_time"] = self.sport_logic.get_best_time(run_obj.get("attempts", []))
            
            total_attempts_allowed = self.race_settings.get("attempts", 1)
            if attempt_idx + 1 >= total_attempts_allowed:
                run_obj["state"] = "DONE"
            else:
                run_obj["state"] = "PREPARING" 

            # --- 2. SAVE TO FIRESTORE ---
            self.save_and_refresh()

            # --- 3. TRIGGER CLOUD FUNCTION ---
            league_id = self.league_combo.currentData() or "UNKNOWN_LEAGUE"
            race_id = self.race_combo.currentData() or "UNKNOWN_RACE"
            team_name = run_obj.get("team", "Unknown Team")

            threading.Thread(
                target=self.trigger_push_notification, 
                args=(race_id, league_id, team_name, push_reason_key, is_np_flag, title_key),
                daemon=True
            ).start()
            # moved trigger_push_notification to firebase_service.py for better separation of concerns
            
    def save_and_refresh(self):
        league_id = self.league_combo.currentData()
        race_id = self.race_combo.currentData()
        
        if hasattr(self.db, "update_race_start_list"):
            self.db.update_race_start_list(league_id, race_id, self.current_start_list)
        elif hasattr(self.db, "update_race_data"):
            self.db.update_race_data(league_id, race_id, self.current_start_list, self.race_settings)

        self.render_table()