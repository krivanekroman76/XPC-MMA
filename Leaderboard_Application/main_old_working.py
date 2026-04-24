import customtkinter as ctk
import os
import json
import serial
import serial.tools.list_ports
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, db, messaging
import threading
import random
import time
import re
from tkinter import filedialog
from tkinter import messagebox

# Načtení konfigurace
load_dotenv()
try:
    cred = credentials.Certificate(os.getenv('FIREBASE_KEY_PATH'))
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {'databaseURL': os.getenv('FIREBASE_DB_URL')})
except Exception as e:
    print(f"Firebase error: {e}")
    
class RaceManager(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("XPC-MMA Race Control")
        self.geometry("1400x900") # Mírně rozšířeno pro nová NP tlačítka

        self.lanes_count = ctk.IntVar(value=2)
        self.attempts_count = ctk.IntVar(value=1)
        self.auto_confirm_sec = ctk.IntVar(value=60) # NOVÉ: Délka automatického potvrzení v sekundách
        self.teams_list = [] 
        self.current_team_index = 0
        self.current_attempt_index = 0
        self.active_race_name = "Default Race"
        self.race_is_finished = False # NOVÉ: Manuální kontrola konce závodu
        
        self.serial_port = None
        self.is_simulated = ctk.BooleanVar(value=True)
        self.cat_colors = {"Muži": "#3498db", "Ženy": "#e74c3c", "Dorost": "#9b59b6"}
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- MENU ---
        self.navigation_frame = ctk.CTkFrame(self, corner_radius=0, width=200)
        self.navigation_frame.grid(row=0, column=0, sticky="nsew")
        self.navigation_frame.grid_propagate(False)
        
        ctk.CTkLabel(self.navigation_frame, text="MENU", font=("Arial", 16, "bold")).pack(pady=20)
        ctk.CTkButton(self.navigation_frame, text="Settings", command=self.show_settings).pack(pady=10, padx=10)
        ctk.CTkButton(self.navigation_frame, text="Race Dashboard", command=self.show_dashboard).pack(pady=10, padx=10)
        ctk.CTkButton(self.navigation_frame, text="Leaderboard", command=self.show_leaderboard).pack(pady=10, padx=10)

        # --- FRAMES ---
        self.settings_frame = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        self.dashboard_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.leaderboard_frame = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        
        self.setup_settings()
        self.setup_dashboard()
        self.setup_leaderboard()
        self.show_settings()

        self.pending_notifications = {} # Sleduje odpočty notifikací: {(team_idx, attempt_idx): timer_id}
        
        threading.Thread(target=self.serial_reader, daemon=True).start()

    def show_settings(self):
        self.dashboard_frame.grid_forget()
        self.leaderboard_frame.grid_forget()
        self.settings_frame.grid(row=0, column=1, sticky="nsew")

    def show_dashboard(self):
        self.settings_frame.grid_forget()
        self.leaderboard_frame.grid_forget()
        self.dashboard_frame.grid(row=0, column=1, sticky="nsew")
        self.update_lane_buttons()

    def show_leaderboard(self):
        self.settings_frame.grid_forget()
        self.dashboard_frame.grid_forget()
        self.leaderboard_frame.grid(row=0, column=1, sticky="nsew")
        self.refresh_leaderboard()

    # --- SETTINGS PAGE ---
    def setup_settings(self):
        ctk.CTkLabel(self.settings_frame, text="Race Configuration", font=("Arial", 24, "bold")).pack(pady=20)

        self.race_name_entry = ctk.CTkEntry(self.settings_frame, placeholder_text="Race Name", width=400)
        self.race_name_entry.pack(pady=10)
        
        config_f = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        config_f.pack(pady=10)

        l_f = ctk.CTkFrame(config_f, fg_color="transparent")
        l_f.pack(side="left", padx=20)
        ctk.CTkLabel(l_f, text="Lanes:").pack()
        self.lane_value_label = ctk.CTkLabel(l_f, text="Selected: 2")
        self.lane_value_label.pack()
        self.lane_slider = ctk.CTkSlider(l_f, from_=1, to=4, number_of_steps=3, variable=self.lanes_count, command=lambda v: self.lane_value_label.configure(text=f"Selected: {int(v)}"))
        self.lane_slider.pack(pady=5)
        
        a_f = ctk.CTkFrame(config_f, fg_color="transparent")
        a_f.pack(side="left", padx=20)
        ctk.CTkLabel(a_f, text="Attempts:").pack()
        self.attempts_value_label = ctk.CTkLabel(a_f, text="Selected: 1")
        self.attempts_value_label.pack()
        self.attempts_slider = ctk.CTkSlider(a_f, from_=1, to=4, number_of_steps=3, variable=self.attempts_count, command=lambda v: self.attempts_value_label.configure(text=f"Selected: {int(v)}"))
        self.attempts_slider.pack(pady=5)

        # NOVÉ: Blok pro nastavení času automatického potvrzení
        c_f = ctk.CTkFrame(config_f, fg_color="transparent")
        c_f.pack(side="left", padx=20)
        ctk.CTkLabel(c_f, text="Auto-Confirm (s):").pack()
        self.confirm_value_label = ctk.CTkLabel(c_f, text=f"Selected: {self.auto_confirm_sec.get()}")
        self.confirm_value_label.pack()
        # Slider od 10 sekund do 180 sekund (3 minuty)
        self.confirm_slider = ctk.CTkSlider(c_f, from_=10, to=180, number_of_steps=170, variable=self.auto_confirm_sec, command=lambda v: self.confirm_value_label.configure(text=f"Selected: {int(v)}"))
        self.confirm_slider.pack(pady=5)
        
        entry_f = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        entry_f.pack(pady=10)
        self.team_entry = ctk.CTkEntry(entry_f, placeholder_text="Team Name", width=200)
        self.team_entry.pack(side="left", padx=5)
        self.category_menu = ctk.CTkOptionMenu(entry_f, values=["Muži", "Ženy", "Dorost"])
        self.category_menu.pack(side="left", padx=5)
        ctk.CTkButton(entry_f, text="Add Team", command=self.add_team, fg_color="#1f6aa5").pack(side="left", padx=5)
        
        self.teams_scroll = ctk.CTkScrollableFrame(self.settings_frame, width=600, height=350)
        self.teams_scroll.pack(pady=10)

        btn_f = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        btn_f.pack(pady=20)
        ctk.CTkButton(btn_f, text="CLEAR", command=self.clear_teams, fg_color="#c0392b", width=100).pack(side="left", padx=10)
        ctk.CTkButton(btn_f, text="SAVE", command=self.save_to_json, fg_color="#555", width=100).pack(side="left", padx=10)
        ctk.CTkButton(btn_f, text="LOAD", command=self.load_from_json, fg_color="#555", width=100).pack(side="left", padx=10)
        ctk.CTkButton(btn_f, text="RECOVER LAST", command=self.recover_race, fg_color="#e67e22").pack(side="left",padx=10)
        
        ctk.CTkButton(self.settings_frame, text="START / UPDATE RACE", fg_color="#28a745", font=("Arial", 16, "bold"), height=50, command=self.confirm_and_start).pack(pady=10)
        
    def add_team(self):
        if name := self.team_entry.get():
            self.teams_list.append({"id": len(self.teams_list) + 1, "name": name, "category": self.category_menu.get(), "status": "idle", "attempts_data": [], "best_time": 0})
            self.team_entry.delete(0, 'end')
            self.refresh_settings_list()

    def refresh_settings_list(self):
        for widget in self.teams_scroll.winfo_children(): widget.destroy()
        for i, t in enumerate(self.teams_list):
            row = ctk.CTkFrame(self.teams_scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"#{i+1}", width=30).pack(side="left")
            ctk.CTkLabel(row, text=f"{t['name']} ({t['category']})", anchor="w", width=250).pack(side="left", padx=10)
            ctk.CTkButton(row, text="X", width=30, fg_color="#c0392b", command=lambda idx=i: self.delete_team(idx)).pack(side="right", padx=2)
            ctk.CTkButton(row, text="↓", width=30, command=lambda idx=i: self.move_team(idx, 1)).pack(side="right", padx=2)
            ctk.CTkButton(row, text="↑", width=30, command=lambda idx=i: self.move_team(idx, -1)).pack(side="right", padx=2)

    def delete_team(self, index): self.teams_list.pop(index); self.refresh_settings_list()
    
    def move_team(self, index, direction):
        new_idx = index + direction
        if 0 <= new_idx < len(self.teams_list):
            self.teams_list[index], self.teams_list[new_idx] = self.teams_list[new_idx], self.teams_list[index]
            self.refresh_settings_list()
            
    def clear_teams(self):  
        if messagebox.askyesno("Clear", "Smazat všechny týmy?"): self.teams_list = []; self.refresh_settings_list()

    # --- DASHBOARD PAGE ---
    def setup_dashboard(self):
        conn_frame = ctk.CTkFrame(self.dashboard_frame)
        conn_frame.pack(pady=10, padx=20, fill="x")
        ctk.CTkLabel(conn_frame, text="Serial Port:").pack(side="left", padx=10)
        self.port_menu = ctk.CTkOptionMenu(conn_frame, values=["Scanning..."])
        self.port_menu.pack(side="left", padx=10)
        ctk.CTkButton(conn_frame, text="Connect", command=self.connect_serial, width=100).pack(side="left", padx=5)
        self.refresh_ports()

        self.table_container = ctk.CTkScrollableFrame(self.dashboard_frame, width=1150, height=400)
        self.table_container.pack(pady=10, padx=20)

        ctrl_frame = ctk.CTkFrame(self.dashboard_frame)
        ctrl_frame.pack(pady=10, padx=20, fill="x")
        self.active_label = ctk.CTkLabel(ctrl_frame, text="READY", font=("Arial", 18, "bold"))
        self.active_label.pack(side="left", padx=20, pady=10)

        self.sim_button_frame = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        self.sim_button_frame.pack(side="right", padx=10)
        
        ctk.CTkButton(ctrl_frame, text="UKONČIT ZÁVOD 🏁", fg_color="#8e44ad", hover_color="#9b59b6", command=self.end_race, width=130).pack(side="right", padx=10)
        
        self.debug_console = ctk.CTkTextbox(self.dashboard_frame, height=150, width=1150, font=("Courier New", 12))
        self.debug_console.pack(pady=10, padx=20)

    # --- LEADERBOARD PAGE ---
    def setup_leaderboard(self):
        self.lb_container = ctk.CTkFrame(self.leaderboard_frame, fg_color="transparent")
        self.lb_container.pack(fill="both", expand=True)

    # --- SERIAL & LOGIC ---
    def serial_reader(self):
        while True:
            if self.serial_port and self.serial_port.is_open:
                try:
                    line = self.serial_port.readline().decode('utf-8').strip()
                    if line and ":" in line:
                        parts = line.split(":")
                        self.after(0, self.process_hit, int(parts[0].replace("L", "")), int(parts[1]))
                except: pass
            time.sleep(0.01)

    def connect_serial(self):
        try:
            self.serial_port = serial.Serial(self.port_menu.get(), 115200, timeout=0.1)
            self.log(f"Connected to {self.port_menu.get()}")
        except Exception as e: messagebox.showerror("Serial Error", str(e))

    def refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if ports: self.port_menu.configure(values=ports)
        self.after(5000, self.refresh_ports)

    def update_statuses(self):
        for i, team in enumerate(self.teams_list):
            if i < self.current_team_index: team["status"] = "done" if self.current_attempt_index == self.attempts_count.get() - 1 else "waiting"
            elif i == self.current_team_index: team["status"] = "running"
            elif i <= self.current_team_index + 2: team["status"] = "preparing"
            else: team["status"] = "idle"

    # --- FIREBASE & NOTIFICATIONS ---
    def sync_to_firebase(self, full_sync=False):
        try:
            r_name = self.active_race_name.replace(" ", "_")
            update_payload = {}

            if full_sync:
                teams_to_sync = self.teams_list
            else:
                start_idx = max(0, self.current_team_index - 1)
                end_idx = min(len(self.teams_list), self.current_team_index + 3)
                teams_to_sync = self.teams_list[start_idx:end_idx]

            for t in teams_to_sync:
                path = f"{t['category']}/{t['name']}"
                update_payload[f"{path}/status"] = t["status"]
                update_payload[f"{path}/start_no"] = t.get("start_no", 999)
                update_payload[f"{path}/best_time"] = t["best_time"]
                update_payload[f"{path}/attempts"] = t["attempts_data"]

            update_payload["settings"] = {
                "lanes_count": self.lanes_count.get(),
                "attempts_count": self.attempts_count.get(),
                "auto_confirm_sec": self.auto_confirm_sec.get(), # NOVÉ
                "is_finished": self.race_is_finished,
                "current_team_index": self.current_team_index,
                "current_attempt_index": self.current_attempt_index,
                "timestamp": time.time()
            }

            db.reference(f"races/{r_name}").update(update_payload)
            db.reference('current_race').update({"status": "finished" if self.race_is_finished else "running", "race_name": self.active_race_name})
            
            if full_sync: self.log("Firebase: Provedena kompletní synchronizace")
        except Exception as e:
            self.log(f"Firebase Sync Error: {e}")

    def send_fcm_multicast(self, title, body, msg_text, is_np="false", is_better="false"):
        try:
            topic = re.sub(r'[^a-zA-Z0-9_]', '', self.active_race_name.replace(" ", "_"))
            tokens_set = set()
            
            for ref in [f'subscribers/{topic}', 'subscribers/all_races']:
                data = db.reference(ref).get()
                if data: tokens_set.update(data.keys())
                
            if not tokens_set:
                self.log("Žádní odběratelé notifikací.")
                return

            tokens_list = list(tokens_set)
            
            # --- HLAVNÍ ZMĚNA JE ZDE ---
            # Žádné "notification=...", žádné "webpush=..."
            # Všechno posíláme jen jako skrytá "data"
            message = messaging.MulticastMessage(
                data={
                    "title": title,         # Přesunuto sem
                    "body": body,           # Přesunuto sem
                    "raceName": self.active_race_name, 
                    "isNP": is_np, 
                    "isBetter": is_better, 
                    "msg": msg_text
                },
                tokens=tokens_list
            )

            response = messaging.send_each_for_multicast(message)
            self.log(f"Push odeslán (Úspěch: {response.success_count})")

            if response.failure_count > 0:
                for idx, resp in enumerate(response.responses):
                    if not resp.success:
                        bad = tokens_list[idx]
                        db.reference(f'subscribers/{topic}/{bad}').delete()
                        db.reference(f'subscribers/all_races/{bad}').delete()
        except Exception as e:
            self.log(f"Chyba notifikace: {e}")
            
    def send_push_notification(self, team, final_time, is_np, is_better, reason=""):
        try:
            t_name = team['name']
            
            # 1. Příprava textů podle toho, co se stalo
            if is_np:
                reason_text = f" Důvod: {reason}" if reason else ""
                title = "Neplatný pokus (NP) ❌"
                body = f"Tým {t_name} nezaznamenal platný čas.{reason_text}"
                msg_text = f"{t_name}: Zapsáno NP"
            else:
                time_str = f"{final_time / 1000:.2f}s"
                if is_better:
                    title = "Vylepšení času! 🔥"
                    body = f"Tým {t_name} zaběhl skvělý čas {time_str}."
                    msg_text = f"{t_name} čas: {time_str}"
                else:
                    title = "Nový čas v cíli ⏱️"
                    body = f"Tým {t_name} dokončil pokus s časem {time_str}."
                    msg_text = f"{t_name} čas: {time_str}"

            # 2. Odeslání přes tvou hlavní a bezpečnou funkci
            # is_np a is_better musíme převést na malá písmena pro Flutter ("true" / "false")
            self.send_fcm_multicast(
                title=title, 
                body=body, 
                msg_text=msg_text, 
                is_np=str(is_np).lower(), 
                is_better=str(is_better).lower()
            )
            
        except Exception as e:
            self.log(f"Chyba při přípravě notifikace: {e}")
              
    def end_race(self):
        if not messagebox.askyesno("Ukončit závod", "Opravdu chcete závod OFICIÁLNĚ ukončit a rozeslat finální výsledky?"): return
        self.log("Ukončuji závod a generuji výsledky...")
        
        self.race_is_finished = True # NOVÉ: Definitivní ukončení
        self.update_statuses()
        self.update_active_team_display()
        self.refresh_table()
        
        threading.Thread(target=lambda: self.sync_to_firebase(full_sync=True), daemon=True).start()
        threading.Thread(target=self.process_and_send_final_results, daemon=True).start()

    def process_and_send_final_results(self):
        summary_lines = []
        for cat in ["Muži", "Ženy", "Dorost"]:
            cat_teams = sorted([t for t in self.teams_list if t["category"] == cat and 0 < t["best_time"] < 999999], key=lambda x: x["best_time"])
            if not cat_teams: continue
            cat_results = [f"{i+1}. {t['name']} ({t['best_time']/1000:.2f}s)" for i, t in enumerate(cat_teams[:3])]
            summary_lines.append(f"{cat}: " + " | ".join(cat_results))
        
        text = "\n".join(summary_lines) if summary_lines else "Závod byl ukončen bez platných časů."
        self.send_fcm_multicast(f"Závod {self.active_race_name} skončil! 🏁", "Podívejte se na konečné výsledky.", f"🏆 VÍTĚZOVÉ:\n{text}", "false", "true")

    # --- CHYTRÁ OBNOVA ZÁVODU ---
    def recover_race(self):
        try:
            races_data = db.reference('races').get()
            if not races_data: return messagebox.showinfo("Recovery", "Žádné závody nenalezeny.")
            unfinished = [r for r, v in races_data.items() if isinstance(v, dict) and not v.get('settings', {}).get('is_finished', False)]
            if not unfinished: return messagebox.showinfo("Recovery", "Všechny závody jsou dokončené.")
            
            dialog = ctk.CTkToplevel(self)
            dialog.title("Výběr závodu k obnovení"); dialog.geometry("400x350"); dialog.attributes("-topmost", True)
            scroll = ctk.CTkScrollableFrame(dialog, width=350, height=250)
            scroll.pack(pady=15, padx=10, fill="both", expand=True)
            for r_name in unfinished:
                ctk.CTkButton(scroll, text=r_name.replace("_", " "), command=lambda n=r_name: self.load_recovered_race(n, races_data[n], dialog), fg_color="#e67e22").pack(pady=5, fill="x")
        except Exception as e: messagebox.showerror("Chyba", str(e))

    def load_recovered_race(self, race_name_db, race_data, dialog):
        dialog.destroy()
        try:
            def parse_lanes(lanes_data):
                if isinstance(lanes_data, list): return {str(i): v for i, v in enumerate(lanes_data) if v is not None}
                elif isinstance(lanes_data, dict): return {str(k): v for k, v in lanes_data.items() if v is not None}
                return {}

            rec_teams = []
            for cat_name, cat_content in race_data.items():
                if cat_name in ["settings", "complete"] or not isinstance(cat_content, dict): continue
                for team_name, info in cat_content.items():
                    if not isinstance(info, dict): continue
                    raw_att = info.get("attempts", [])
                    p_att = [{"lanes": parse_lanes(a.get("lanes", {})), "final_time": a.get("final_time", 0)} for a in (raw_att.values() if isinstance(raw_att, dict) else raw_att) if isinstance(a, dict)]
                    rec_teams.append({"start_no": info.get("start_no", 0), "name": team_name, "category": cat_name, "status": info.get("status", "idle"), "attempts_data": p_att or [{"lanes": {}, "final_time": 0}], "best_time": info.get("best_time", 0)})
            
            self.teams_list = sorted(rec_teams, key=lambda x: x.get("start_no", 999))
            settings = race_data.get("settings", {})
            self.active_race_name = race_name_db.replace("_", " ")
            self.lanes_count.set(settings.get("lanes_count", 2))
            self.attempts_count.set(settings.get("attempts_count", 1))
            self.auto_confirm_sec.set(settings.get("auto_confirm_sec", 60)) # NOVÉ
            self.current_team_index = settings.get("current_team_index", 0)
            self.current_attempt_index = settings.get("current_attempt_index", 0)
            self.race_is_finished = settings.get("is_finished", False) # NOVÉ

            self.race_name_entry.delete(0, 'end'); self.race_name_entry.insert(0, self.active_race_name)
            self.refresh_settings_list(); self.update_statuses(); self.show_dashboard(); self.refresh_table(); self.update_active_team_display()
            self.sync_to_firebase(full_sync=True)
            messagebox.showinfo("OK", f"Závod obnoven.")
        except Exception as e: messagebox.showerror("Chyba", str(e))
            
    def log(self, message):
        msg = f"[{time.strftime('%H:%M:%S')}] {message}"
        if hasattr(self, 'debug_console'):
            self.after(0, lambda: self.debug_console.insert("end", msg + "\n"))
            self.after(0, lambda: self.debug_console.see("end"))

    # --- ZPRACOVÁNÍ ČASŮ A NP ---
    def process_hit(self, lane, ms):
        # 1. OCHRANA: Ignoruj opožděné časy z HW těsně (2s) po kliknutí na NP
        if getattr(self, 'ignore_hits', False):
            self.log(f"Ignorován čas {ms}ms pro dráhu {lane} – terče dojely po zápisu NP.")
            return
            
        team = self.teams_list[self.current_team_index]
        if team.get("status") != "running":
            return
        
        if self.current_team_index >= len(self.teams_list): return
        team = self.teams_list[self.current_team_index]
        attempt = team["attempts_data"][self.current_attempt_index]
        if str(lane) in attempt["lanes"]: return 

        attempt["lanes"][str(lane)] = ms
        threading.Thread(target=lambda: db.reference('current_race').update({f"lane_{lane}": ms}), daemon=True).start()

        if len(attempt["lanes"]) == self.lanes_count.get():
            attempt["final_time"] = max(attempt["lanes"].values())
            old_best = team["best_time"]
            v_times = [a["final_time"] for a in team["attempts_data"] if 0 < a["final_time"] < 999999]
            team["best_time"] = min(v_times) if v_times else 999999

            is_np = attempt["final_time"] >= 999999
            is_better = not is_np and (old_best == 0 or old_best >= 999999 or attempt["final_time"] < old_best)
            
            if not is_np:
                attempt["pending_confirm"] = True 
                
                # NOVÉ: Přepočet nastavených sekund na milisekundy
                delay_ms = self.auto_confirm_sec.get() * 1000 
                
                # Spustí se odpočet na nastavený čas pro automatické potvrzení
                timer_id = self.after(delay_ms, lambda t_idx=self.current_team_index, a_idx=self.current_attempt_index: self.auto_confirm_time(t_idx, a_idx))
                self.pending_notifications[(self.current_team_index, self.current_attempt_index)] = timer_id
                
                # Zpožděné vyvolání vyskakovacího okna (500ms)
                self.after(500, lambda t_idx=self.current_team_index, a_idx=self.current_attempt_index: self.prompt_run_result(t_idx, a_idx))
            else:
                threading.Thread(target=self.send_push_notification, args=(team, attempt["final_time"], is_np, False, ""), daemon=True).start()

            if self.current_team_index < len(self.teams_list) - 1: self.current_team_index += 1
            elif self.current_attempt_index < self.attempts_count.get() - 1:
                self.current_team_index = 0
                self.current_attempt_index += 1
            else: self.current_team_index = len(self.teams_list)

            self.update_statuses()
            self.update_active_team_display()

        threading.Thread(target=lambda: self.sync_to_firebase(full_sync=False), daemon=True).start()
        self.refresh_table()

    def auto_confirm_time(self, team_idx, attempt_idx):
        # Zavřít okno, pokud je stále otevřené a vypršel čas
        if hasattr(self, 'active_dialogs') and (team_idx, attempt_idx) in self.active_dialogs:
            try:
                self.active_dialogs[(team_idx, attempt_idx)].destroy()
            except: pass
            del self.active_dialogs[(team_idx, attempt_idx)]

        team = self.teams_list[team_idx]
        attempt = team["attempts_data"][attempt_idx]
        
        timer_id = self.pending_notifications.pop((team_idx, attempt_idx), None)
        if timer_id: self.after_cancel(timer_id)

        if attempt.get("pending_confirm"):
            attempt["pending_confirm"] = False
            is_better = team["best_time"] == attempt["final_time"]
            threading.Thread(target=self.send_push_notification, args=(team, attempt["final_time"], False, is_better, ""), daemon=True).start()
            self.refresh_table()
            self.log(f"Čas týmu {team['name']} byl potvrzen a notifikace odeslána.")

    def open_np_dialog(self, team_idx, attempt_idx):
        """Otevře okno pro zadání důvodu NP a pozastaví časovač"""
        team = self.teams_list[team_idx]
        
        # Pozastavíme/zrušíme odpočet notifikace, protože rozhodčí řeší problém
        timer_id = self.pending_notifications.pop((team_idx, attempt_idx), None)
        if timer_id:
            self.after_cancel(timer_id)

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Zadat NP: {team['name']}")
        dialog.geometry("400x250")
        dialog.attributes("-topmost", True)

        ctk.CTkLabel(dialog, text="Důvod neplatného pokusu:", font=("Arial", 14, "bold")).pack(pady=10)
        ctk.CTkLabel(dialog, text="(např. koš, přešlap... nebo nechte prázdné)").pack(pady=5)
        
        reason_entry = ctk.CTkEntry(dialog, width=300)
        reason_entry.pack(pady=10)
        reason_entry.focus()

        def confirm_np():
            reason = reason_entry.get().strip()
            self.execute_np(team_idx, attempt_idx, reason)
            dialog.destroy()

        def cancel_np():
            # Pokud admin okno zavře, musíme obnovit odpočet nebo to nechat na manuální ✅
            self.log("Zadávání NP zrušeno, čeká se na potvrzení času.")
            dialog.destroy()

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="Zrušit", command=cancel_np, fg_color="gray", width=100).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Uložit NP", command=confirm_np, fg_color="#c0392b", width=100).pack(side="right", padx=10)

    def execute_np(self, team_idx, attempt_idx, reason=""):
        try:
            team = self.teams_list[team_idx]
            # SPRÁVNÝ KLÍČ: attempts_data
            attempt = team["attempts_data"][attempt_idx]
            
            # 1. Okamžitě zrušíme čekání na případné automatické potvrzení
            attempt["pending_confirm"] = False
            if (team_idx, attempt_idx) in getattr(self, 'pending_notifications', {}):
                timer_id = self.pending_notifications.pop((team_idx, attempt_idx))
                self.after_cancel(timer_id)

            is_active_team = (team_idx == self.current_team_index and attempt_idx == self.current_attempt_index)
            
            # 2. DOČASNÁ OCHRANA: Pokud dáváme NP aktivnímu týmu, ignorujeme 
            # na 2 sekundy přicházející časy z HW, aby se nepřepsal další tým.
            if is_active_team:
                self.ignore_hits = True
                self.after(2000, lambda: setattr(self, 'ignore_hits', False))
                
            # 3. Zápis samotného NP do výsledků
            attempt["final_time"] = 999999
            
            # Dráhy jsou slovník ("1": ms, "2": ms), zapíšeme všude NP
            for i in range(1, self.lanes_count.get() + 1):
                attempt["lanes"][str(i)] = 999999
                
            # Přepočet nejlepšího času týmu (stejně jako to děláš v process_hit)
            v_times = [a["final_time"] for a in team["attempts_data"] if 0 < a["final_time"] < 999999]
            team["best_time"] = min(v_times) if v_times else 999999

            # 4. Odeslání notifikace 
            threading.Thread(
                target=self.send_push_notification, 
                args=(team, 999999, True, False, reason), 
                daemon=True
            ).start()

            # 5. Posunutí indexu na další tým a překreslení UI
            if is_active_team:
                if self.current_team_index < len(self.teams_list) - 1: 
                    self.current_team_index += 1
                elif self.current_attempt_index < self.attempts_count.get() - 1:
                    self.current_team_index = 0
                    self.current_attempt_index += 1
                else: 
                    self.current_team_index = len(self.teams_list)

                self.update_statuses()
                self.update_active_team_display()
                
            # 6. Synchronizace do Firebase a tabulky
            threading.Thread(target=lambda: self.sync_to_firebase(full_sync=False), daemon=True).start()
            self.refresh_table()
            
        except Exception as e:
            self.log(f"Kritická chyba při zápisu NP: {e}")
            
    def simulate_hit(self, lane): self.process_hit(lane, random.randint(14000, 22000))

    def update_lane_buttons(self):
        for widget in self.sim_button_frame.winfo_children(): widget.destroy()
        for i in range(1, self.lanes_count.get() + 1):
            ctk.CTkButton(self.sim_button_frame, text=f"Sim L{i}", command=lambda l=i: self.simulate_hit(l), width=80).pack(side="left", padx=2)

    def update_active_team_display(self):
        if self.current_team_index < len(self.teams_list):
            team = self.teams_list[self.current_team_index]
            self.active_label.configure(text=f"NOW: {team['name']} | Attempt: {self.current_attempt_index + 1}", text_color=self.cat_colors.get(team['category']))
        else: self.active_label.configure(text="FINISHED", text_color="green")

    def refresh_table(self):
        for widget in self.table_container.winfo_children(): widget.destroy()
        
        headers = ["Status", "#", "Cat", "Team", "TOP RESULT"] 
        for a in range(1, self.attempts_count.get() + 1):
            for l in range(1, self.lanes_count.get() + 1): headers.append(f"P{a}-L{l}")
            headers.append(f"Res {a}")
            headers.append(f"NP") 
            
        for i, h in enumerate(headers): ctk.CTkLabel(self.table_container, text=h, font=("Arial", 10, "bold")).grid(row=0, column=i, padx=5, pady=5)

        for idx, t in enumerate(self.teams_list):
            sc = {"running": "#1f6aa5", "preparing": "#e67e22", "done": "#2ecc71", "waiting": "#f1c40f", "idle": "gray"}.get(t["status"], "white")
            ctk.CTkLabel(self.table_container, text=t["status"].upper(), text_color=sc).grid(row=idx+1, column=0)
            ctk.CTkLabel(self.table_container, text=str(idx+1)).grid(row=idx+1, column=1)
            ctk.CTkLabel(self.table_container, text=t['category'], text_color=self.cat_colors.get(t['category'])).grid(row=idx+1, column=2)
            ctk.CTkLabel(self.table_container, text=t['name'], font=("Arial", 11, "bold")).grid(row=idx+1, column=3)
            ctk.CTkLabel(self.table_container, text="NP" if t['best_time'] >= 999999 else (f"{t['best_time']/1000:.2f}s" if t['best_time'] > 0 else "--"), text_color="#f1c40f").grid(row=idx+1, column=4)
            
            curr_col = 5
            for a_idx in range(self.attempts_count.get()):
                att = t["attempts_data"][a_idx] if a_idx < len(t["attempts_data"]) else {"lanes": {}, "final_time": 0}
                for l_idx in range(1, self.lanes_count.get() + 1):
                    lv = att["lanes"].get(str(l_idx), 0)
                    ctk.CTkLabel(self.table_container, text=f"{lv/1000:.2f}" if lv > 0 else "-").grid(row=idx+1, column=curr_col); curr_col += 1
                
                fv = att["final_time"]
                
                # OPRAVA: Tady chyběl label s vypsáním výsledného času!
                time_text = "NP" if fv >= 999999 else (f"{fv/1000:.2f}s" if fv > 0 else "--")
                ctk.CTkLabel(self.table_container, text=time_text).grid(row=idx+1, column=curr_col)
                curr_col += 1

                # Tlačítko pro POZDĚJŠÍ zadání NP přímo z tabulky
                ctk.CTkButton(self.table_container, text="NP", width=25, height=20, fg_color="#c0392b", hover_color="#922b21", 
                              command=lambda t_i=idx, a_i=a_idx: self.open_np_dialog(t_i, a_i)).grid(row=idx+1, column=curr_col, padx=2)
                curr_col += 1

    def prompt_run_result(self, team_idx, attempt_idx):
        """Vyskakovací okno pro potvrzení platnosti pokusu ihned po doběhnutí"""
        team = self.teams_list[team_idx]
        attempt = team["attempts_data"][attempt_idx]
        
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Rozhodnutí: {team['name']}")
        dialog.geometry("450x300")
        dialog.attributes("-topmost", True)
        
        # Uchováme referenci, abychom okno mohli zavřít při vypršení timeru
        if not hasattr(self, 'active_dialogs'): self.active_dialogs = {}
        self.active_dialogs[(team_idx, attempt_idx)] = dialog

        ctk.CTkLabel(dialog, text=f"Tým: {team['name']}", font=("Arial", 18, "bold")).pack(pady=10)
        ctk.CTkLabel(dialog, text=f"Čas: {attempt['final_time']/1000:.2f} s", font=("Arial", 26, "bold"), text_color="#2ecc71").pack(pady=5)
        
        ctk.CTkLabel(dialog, text="Důvod NP (volitelné):", text_color="gray").pack(pady=5)
        reason_entry = ctk.CTkEntry(dialog, width=300, placeholder_text="Např. koš, přešlap...")
        reason_entry.pack(pady=5)

        def confirm_valid():
            self.auto_confirm_time(team_idx, attempt_idx)
            # dialog.destroy() TU UŽ NESMÍ BÝT, auto_confirm_time ho zavře samo.

        def confirm_np():
            reason = reason_entry.get().strip()
            self.execute_np(team_idx, attempt_idx, reason)
            
            # Správné zavření a vyčištění paměti pro NP
            if hasattr(self, 'active_dialogs') and (team_idx, attempt_idx) in self.active_dialogs:
                del self.active_dialogs[(team_idx, attempt_idx)]
            dialog.destroy()
            
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        ctk.CTkButton(btn_frame, text="✅ PLATNÝ POKUS", command=confirm_valid, fg_color="#27ae60", hover_color="#2ecc71", font=("Arial", 14, "bold"), height=40).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="❌ NEPLATNÝ (NP)", command=confirm_np, fg_color="#c0392b", hover_color="#922b21", font=("Arial", 14, "bold"), height=40).pack(side="right", padx=10)
        
    def refresh_leaderboard(self):
        for widget in self.lb_container.winfo_children(): widget.destroy()
        for cat in ["Muži", "Ženy", "Dorost"]:
            sorted_teams = sorted([t for t in self.teams_list if t["category"] == cat], key=lambda x: (x["best_time"] == 0 or x["best_time"] >= 999999, x["best_time"]))
            if not sorted_teams: continue
            ctk.CTkLabel(self.lb_container, text=f"--- {cat.upper()} ---", font=("Arial", 18, "bold"), text_color=self.cat_colors[cat]).pack(pady=10)
            table = ctk.CTkFrame(self.lb_container); table.pack(pady=5, padx=20, fill="x")
            for rank, team in enumerate(sorted_teams, 1):
                bg = "#f1c40f" if rank == 1 and 0 < team["best_time"] < 999999 else ("#bdc3c7" if rank == 2 else ("#cd7f32" if rank == 3 else "transparent"))
                row = ctk.CTkFrame(table, fg_color=bg, corner_radius=0); row.pack(fill="x", pady=1)
                ctk.CTkLabel(row, text=f"{rank}.", width=40).pack(side="left", padx=10)
                ctk.CTkLabel(row, text=team["name"], font=("Arial", 12, "bold"), width=200).pack(side="left", padx=10)
                ctk.CTkLabel(row, text="NP" if team["best_time"] >= 999999 else (f"{team['best_time']/1000:.2f}s" if team["best_time"] > 0 else "--"), width=100).pack(side="right", padx=10)

    def save_to_json(self):
        if file_path := filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")]):
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump({"race_name": self.race_name_entry.get(), 
                           "lanes": self.lanes_count.get(), 
                           "attempts": self.attempts_count.get(), 
                           "auto_confirm": self.auto_confirm_sec.get(), # NOVÉ
                           "teams": self.teams_list}, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("Saved", "OK")

    def load_from_json(self):
        if file_path := filedialog.askopenfilename(filetypes=[("JSON", "*.json")]):
            with open(file_path, "r", encoding="utf-8") as f: data = json.load(f)
            self.race_name_entry.delete(0, 'end'); self.race_name_entry.insert(0, data.get("race_name", ""))
            self.lanes_count.set(data.get("lanes", 2)); self.attempts_count.set(data.get("attempts", 1))
            self.auto_confirm_sec.set(data.get("auto_confirm", 60)) # NOVÉ
            self.teams_list = data.get("teams", [])
            
            self.lane_value_label.configure(text=f"Selected: {self.lanes_count.get()}")
            self.attempts_value_label.configure(text=f"Selected: {self.attempts_count.get()}")
            self.confirm_value_label.configure(text=f"Selected: {self.auto_confirm_sec.get()}") # NOVÉ
            
            self.race_is_finished = False
            self.refresh_settings_list()
            messagebox.showinfo("Loaded", "OK")

    def confirm_and_start(self):
        self.active_race_name = self.race_name_entry.get()
        if not self.active_race_name: return messagebox.showwarning("Varování", "Zadejte název závodu!")
        
        self.current_team_index = 0; self.current_attempt_index = 0
        self.race_is_finished = False # Reset statusu konce závodu
        
        for i, team in enumerate(self.teams_list):
            team["start_no"] = i + 1; team["best_time"] = 0 
            team["attempts_data"] = [{"lanes": {}, "final_time": 0} for _ in range(self.attempts_count.get())]
        
        self.update_statuses()
        try:
            db.reference(f"races/{self.active_race_name.replace(' ', '_')}").delete()
            self.sync_to_firebase(full_sync=True)
            self.show_dashboard(); self.refresh_table()
        except Exception as e: self.log(f"Initial Sync Error: {e}")

if __name__ == "__main__":
    app = RaceManager()
    app.mainloop()