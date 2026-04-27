from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QComboBox, QSpinBox, QLineEdit, 
                               QFormLayout, QFrame, QWidget, QTableWidget, QHeaderView)
import serial.tools.list_ports
from PySide6.QtCore import Qt
from core.translate import tr
import requests
import threading

class AttemptConfirmDialog(QDialog):
    """
    Unified dialog for confirming an attempt. 
    Allows the timekeeper to toggle between Valid and NP, apply penalties, 
    or assign NP reasons dynamically before saving.
    """
    def __init__(self, attempt_state, base_time=0.0, race_config=None, parent=None):
        super().__init__(parent)
        self.initial_state = attempt_state.upper() # 'VALID' or 'NP' passed from hardware
        self.base_time = float(base_time)
        
        self.race_config = race_config or {
            "penalties_enabled": False,
            "penalty_type": "seconds",
            "track_count": 2
        }
        
        self.penalty_spinboxes = []
        
        self.setup_ui()
        self.retranslate_ui()
        self.update_calculations()

    def setup_ui(self):
        self.setModal(True)
        self.setMinimumWidth(450)

        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(15)

        # --- HEADER & STATUS TOGGLE ---
        self.lbl_title = QLabel()
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setObjectName("dialogTitle")
        self.layout.addWidget(self.lbl_title)

        status_layout = QFormLayout()
        self.combo_status = QComboBox()
        self.combo_status.addItem(tr.t("state_valid"), "VALID")
        self.combo_status.addItem(tr.t("state_np"), "NP")
        
        initial_index = 1 if self.initial_state == "NP" else 0
        self.combo_status.setCurrentIndex(initial_index)
        self.combo_status.currentIndexChanged.connect(self.on_status_toggled)
        
        self.lbl_status_select = QLabel()
        status_layout.addRow(self.lbl_status_select, self.combo_status)
        self.layout.addLayout(status_layout)

        # --- SEPARATOR ---
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("separatorLine")
        self.layout.addWidget(line)

        # --- DYNAMIC CONTAINERS ---
        self.valid_container = QWidget()
        self.valid_layout = QFormLayout(self.valid_container)
        self.valid_layout.setContentsMargins(0,0,0,0)
        self.setup_valid_ui()
        self.layout.addWidget(self.valid_container)

        self.np_container = QWidget()
        self.np_layout = QFormLayout(self.np_container)
        self.np_layout.setContentsMargins(0,0,0,0)
        self.setup_np_ui()
        self.layout.addWidget(self.np_container)

        # --- BOTTOM BUTTONS (MOVED UP) ---
        btn_layout = QHBoxLayout()
        
        self.btn_cancel = QPushButton()
        self.btn_cancel.setObjectName("cancelButton")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_confirm = QPushButton()
        self.btn_confirm.setObjectName("confirmButton")
        self.btn_confirm.clicked.connect(self.accept)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_confirm)
        self.layout.addLayout(btn_layout)

        # --- APPLY INITIAL VISIBILITY (MOVED DOWN) ---
        # Now that self.btn_confirm exists, this function can run safely!
        self.on_status_toggled()
        
    def setup_valid_ui(self):
        self.lbl_base_time = QLabel()
        lbl_time_val = QLabel(f"{self.base_time:.3f} s")
        lbl_time_val.setObjectName("validTimeValue")
        self.valid_layout.addRow(self.lbl_base_time, lbl_time_val)

        if self.race_config.get("penalties_enabled", False):
            track_count = self.race_config.get("track_count", 2)
            
            self.lbl_penalty_title = QLabel()
            self.lbl_penalty_title.setObjectName("penaltyTitle")
            self.valid_layout.addRow(self.lbl_penalty_title, QLabel())

            for i in range(track_count):
                spinbox = QSpinBox()
                spinbox.setRange(0, 999) 
                spinbox.valueChanged.connect(self.update_calculations)
                self.penalty_spinboxes.append(spinbox)
                track_lbl = QLabel(f"{tr.t('lbl_track')} {i+1}:")
                self.valid_layout.addRow(track_lbl, spinbox)
            
            self.lbl_penalty_reason = QLabel()
            self.combo_penalty_reason = QComboBox()
            self.valid_layout.addRow(self.lbl_penalty_reason, self.combo_penalty_reason)

            line2 = QFrame()
            line2.setFrameShape(QFrame.Shape.HLine)
            line2.setObjectName("separatorLine")
            self.valid_layout.addRow(line2)

            self.lbl_final_result = QLabel()
            self.val_final_result = QLabel()
            self.val_final_result.setObjectName("finalResultValue")
            self.valid_layout.addRow(self.lbl_final_result, self.val_final_result)

    def setup_np_ui(self):
        self.lbl_np_reason = QLabel()
        self.combo_np_reason = QComboBox()
        self.combo_np_reason.currentTextChanged.connect(self.on_reason_changed)
        
        self.input_custom_reason = QLineEdit()
        self.input_custom_reason.setVisible(False)

        self.np_layout.addRow(self.lbl_np_reason, self.combo_np_reason)
        self.np_layout.addRow("", self.input_custom_reason)

    def on_status_toggled(self):
        """Hides/Shows the correct container based on the dropdown selection."""
        current_state = self.combo_status.currentData()
        
        if current_state == "NP":
            self.valid_container.setVisible(False)
            self.np_container.setVisible(True)
            self.btn_confirm.setProperty("state", "np")
            self.lbl_title.setProperty("state", "np")
            self.lbl_title.setText(tr.t("confirm_np_header"))
        else:
            self.valid_container.setVisible(True)
            self.np_container.setVisible(False)
            self.btn_confirm.setProperty("state", "valid")
            self.lbl_title.setProperty("state", "valid")
            self.lbl_title.setText(tr.t("confirm_valid_header"))
            
        # Refresh UI styling after changing properties
        self.lbl_title.style().unpolish(self.lbl_title)
        self.lbl_title.style().polish(self.lbl_title)
        self.btn_confirm.style().unpolish(self.btn_confirm)
        self.btn_confirm.style().polish(self.btn_confirm)

    def on_reason_changed(self, text):
        if text == tr.t("reason_other"):
            self.input_custom_reason.setVisible(True)
        else:
            self.input_custom_reason.setVisible(False)
            self.input_custom_reason.clear()

    def update_calculations(self):
        if not self.race_config.get("penalties_enabled", False):
            return

        total_penalty = sum(sb.value() for sb in self.penalty_spinboxes)
        penalty_type = self.race_config.get("penalty_type", "seconds")

        if penalty_type == "seconds":
            final_time = self.base_time + total_penalty
            self.val_final_result.setText(f"{final_time:.3f} s")
        else:
            self.val_final_result.setText(f"{self.base_time:.3f} s  (+ {total_penalty} {tr.t('lbl_points')})")

    def retranslate_ui(self):
        self.setWindowTitle(tr.t("confirm_dialog_title"))
        self.lbl_status_select.setText(tr.t("confirm_status_select_lbl"))
        self.combo_status.setItemText(0, tr.t("state_valid"))
        self.combo_status.setItemText(1, tr.t("state_np"))
        
        self.btn_cancel.setText(tr.t("btn_cancel"))
        self.btn_confirm.setText(tr.t("btn_confirm"))

        # NP Translations
        self.lbl_np_reason.setText(tr.t("confirm_np_reason_lbl"))
        self.input_custom_reason.setPlaceholderText(tr.t("ph_custom_reason"))
        self.combo_np_reason.clear()
        
        self.combo_np_reason.addItem(tr.t("reason_np_early_start"), "reason_np_early_start")
        self.combo_np_reason.addItem(tr.t("reason_np_hose"), "reason_np_hose")
        self.combo_np_reason.addItem(tr.t("reason_np_line"), "reason_np_line")
        self.combo_np_reason.addItem(tr.t("reason_other"), "reason_other")
        
        # Valid Translations
        self.lbl_base_time.setText(tr.t("confirm_base_time_lbl"))
        if self.race_config.get("penalties_enabled", False):
            pen_type = tr.t("confirm_penalty_seconds") if self.race_config.get("penalty_type", "seconds") == "seconds" else tr.t("confirm_penalty_points")
            self.lbl_penalty_title.setText(tr.t("confirm_penalties_title").replace("{type}", pen_type))
            self.lbl_penalty_reason.setText(tr.t("confirm_penalty_reason_lbl"))
            self.lbl_final_result.setText(tr.t("confirm_final_result_lbl"))
            
            self.combo_penalty_reason.clear()
            self.combo_penalty_reason.addItems([
                tr.t("reason_pen_none"),
                tr.t("reason_pen_base"),
                tr.t("reason_pen_suction"),
                tr.t("reason_other")
            ])

    def get_result_data(self):
        # Determine the final state selected by the user
        final_selected_state = self.combo_status.currentData()
        
        data = {
            "status": final_selected_state,
            "base_time": self.base_time,
            "final_time": self.base_time,
            "total_penalties": 0,
            "penalties_per_track": [],
            "reason": ""
        }

        if final_selected_state == "NP":
            # Extract the hidden KEY (e.g., "reason_np_early_start")
            reason_key = self.combo_np_reason.currentData()
            
            if reason_key == "reason_other":
                # If it's custom, we have to send the raw typed text
                data["reason"] = self.input_custom_reason.text()
            else:
                # Otherwise, save the KEY to Firestore
                data["reason"] = reason_key
                
            data["final_time"] = None
            
        else:
            if self.race_config.get("penalties_enabled", False):
                penalties = [sb.value() for sb in self.penalty_spinboxes]
                data["penalties_per_track"] = penalties
                data["total_penalties"] = sum(penalties)
                
                # Do the same for penalties!
                penalty_key = self.combo_penalty_reason.currentData()
                data["reason"] = penalty_key if data["total_penalties"] > 0 else ""

                if self.race_config.get("penalty_type", "seconds") == "seconds":
                    data["final_time"] = self.base_time + data["total_penalties"]

        return data
    
    def refresh_com_ports(self):
        self.combo_ports.clear()
        ports = serial.tools.list_ports.comports()
        for port, desc, hwid in sorted(ports):
            self.combo_ports.addItem(f"{port} - {desc}", port) # Shows description, stores just the "COM3" part
        