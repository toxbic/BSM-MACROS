import tkinter as tk
from tkinter import messagebox, ttk
import cv2
import numpy as np
import pyautogui
import time
import re
import pydirectinput
import threading
import keyboard
import json
import os
import sys
import logging
import math
import webbrowser
import easyocr

# Prevent pyautogui from raising failsafe exception
pydirectinput.PAUSE = 0.001
pydirectinput.FAILSAFE = False
pyautogui.FAILSAFE = False

# Initialize EasyOCR reader
reader = easyocr.Reader(['en'], gpu=True)  # or gpu=False if CUDA issues

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# ────────────────────────────────────────────────
#   Default values
# ────────────────────────────────────────────────

DEFAULT_SCAN = (0.52, 0.43, 0.08, 0.12)          # x, y, w, h
DEFAULT_BTN_NO = (0.55, 0.54)
DEFAULT_BTN_YES = (0.45, 0.54)
DEFAULT_DELAY_INTERACT = 0.4
DEFAULT_DELAY_REFRESH = 0.5

STAT_RANGES = {
    "Pollen (8 - 20)": (8, 20),
    "White Pollen (15 - 70)": (15, 70),
    "Blue Pollen (15 - 70)": (15, 70),
    "Red Pollen (15 - 70)": (15, 70),
    "Bee Gather Pollen (15 - 70)": (15, 70),
    "Instant Conversion (5 - 12)": (5, 12),
    "Convert Rate (1.05 - 1.25)": (1.05, 1.25),
    "Bee Ability Rate (2 - 7)": (2, 7),
    "Critical Chance (2 - 7)": (2, 7),
    "Capacity (1.5 - 2.5)": (1.5, 2.5),           # added
    # Add more stats if needed in future updates
}

ALL_PASSIVES = [
    "Pop Star",
    "Guiding Star",
    "Star Shower",
    "Gummy Star",
    "Scorching Star",
    "Star Saw",

    # Add any newly released passives here
]

running = False


# ────────────────────────────────────────────────
#   Helper / OCR / Parsing / Macro functions
# ────────────────────────────────────────────────

def get_screen_rect(ratio_tuple):
    sw, sh = pyautogui.size()
    rx, ry, rw, rh = ratio_tuple
    return (int(sw * rx), int(sh * ry), int(sw * rw), int(sh * rh))

def get_screen_point(ratio_tuple):
    sw, sh = pyautogui.size()
    rx, ry = ratio_tuple
    return (int(sw * rx), int(sh * ry))

def wiggle_click(ratio_coords):
    x, y = get_screen_point(ratio_coords)
    pydirectinput.moveTo(x, y)
    time.sleep(0.05)
    pydirectinput.moveRel(1, 0)
    pydirectinput.moveRel(-1, 0)
    pydirectinput.mouseDown()
    time.sleep(0.05)
    pydirectinput.mouseUp()

def get_stats_image_dynamic(scan_rect):
    x, y, w, h = get_screen_rect(scan_rect)
    return np.array(pyautogui.screenshot(region=(x, y, w, h)))

def ocr_process(img):
    if img is None:
        return ""
    img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    try:
        results = reader.readtext(img, detail=0, paragraph=False, min_size=10)
        full_text = "\n".join(results)
    except Exception as e:
        print(f"EasyOCR error: {e}")
        return ""
    return full_text

def parse_stats(text):
    passives = []
    stats = {}

    # 1. Normalize for passive searching - handle fragmented words and misread symbols
    # Replace common OCR errors like '#' instead of '+'
    clean_blob = text.lower().replace("\n", " ").replace("#", "+").strip()
    
    passive_rules = {
        "Pop Star": ["pop"],
        "Guiding Star": ["guiding"],
        "Star Shower": ["shower"],
        "Gummy Star": ["gummy"],
        "Scorching Star": ["scorch"], # Using partial 'scorch' to catch misreads
        "Star Saw": ["saw"],
        "Soul Star": ["soul"],
        "Tidal Star": ["tidal"],
    }

    for name, keywords in passive_rules.items():
        if all(kw in clean_blob for kw in keywords):
            if name not in passives:
                passives.append(name)

    # 2. Fix line breaks in stats
    fixed_text = text.replace("Bee\nAbility", "Bee Ability")
    fixed_text = fixed_text.replace("Instant\nConversion", "Instant Conversion")
    fixed_text = fixed_text.replace("Gather\nPollen", "Gather Pollen")
    
    processed_lines = []
    current_line = ''
    for line in fixed_text.splitlines():
        line = line.strip()
        if not line: continue
        # Detect start of a new stat line
        if line.startswith('+') or line.startswith('x') or line.startswith('#') or 'passive' in line.lower():
            if current_line: processed_lines.append(current_line)
            current_line = line
        else:
            if current_line: current_line += ' ' + line
            else: current_line = line
    if current_line: processed_lines.append(current_line)

    # 3. Final Stat Mapping
    for pl in processed_lines:
        # Regex to find numbers and the text following them
        match = re.search(r'([x\+#]?)\s*(\d+[\.,]?\d*)\s*%?\s*(.*)', pl)
        if match:
            val_str = match.group(2).replace(',', '.')
            desc_clean = match.group(3).lower().replace(" ", "").replace("%", "")
            
            try:
                val = float(val_str)
                # Scaling Fix: If OCR reads 3% as 39.0 or 17% as 17.9
                if val > 100 and any(x in desc_clean for x in ["critical", "ability", "pollen", "instant"]):
                    val = float(str(val)[:2]) if val > 100 else val # Trim OCR artifacts

                # Priority Mapping: Colors/Specifics first
                # Map to the correct stat name
                # We check specific pollens BEFORE general pollen
                if "whitepollen" in desc_clean: stats["White Pollen (15 - 70)"] = val
                elif "bluepollen" in desc_clean: stats["Blue Pollen (15 - 70)"] = val
                elif "redpollen" in desc_clean: stats["Red Pollen (15 - 70)"] = val
                elif "beegather" in desc_clean or "pollenfrombees" in desc_clean: 
                    stats["Bee Gather Pollen (15 - 70)"] = val
                # Improved Critical Chance detection
                elif "crit" in desc_clean: stats["Critical Chance (2 - 7)"] = val

# Improved Convert Rate detection (handles the 'I' misread)
                elif "convert" in desc_clean: stats["Convert Rate (1.05 - 1.25)"] = val
                # --- NEW CONVERT RATE LOGIC ---
                elif "convertrate" in desc_clean:
                    stats["Convert Rate (1.05 - 1.25)"] = val
                
                elif "pollen" in desc_clean: 
                    stats["Pollen (8 - 20)"] = val
                elif "abilityrate" in desc_clean: stats["Bee Ability Rate (2 - 7)"] = val
                elif "critical" in desc_clean: stats["Critical Chance (2 - 7)"] = val
                #elif "capacity" in desc_clean: stats["Capacity (1.5 - 2.5)"] = val
                elif "instant" in desc_clean: stats["Instant Conversion (5 - 12)"] = val
                
            except ValueError:
                continue

    return sorted(list(set(passives))), stats
def format_time(seconds):
    if seconds is None or seconds == float('inf') or seconds == 0:
        return "--"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    if d > 0:
        return f"{int(d)}d {int(h)}h"
    if h > 0:
        return f"{int(h)}h {int(m)}m"
    return f"{int(m)}m {int(s)}s"

def format_large_number(num):
    if num >= 1e15:
        return f"{num/1e15:.2f} Qd"
    if num >= 1e12:
        return f"{num/1e12:.2f} T"
    if num >= 1e9:
        return f"{num/1e9:.2f} B"
    return f"{num:.0f}"

def run_debug_test(log_main, log_raw, get_scan_rect):
    log_main("--- TEST OCR STARTED ---", clear=True)
    rect = get_scan_rect()
    img = get_stats_image_dynamic(rect)
    if img is not None:
        raw_text = ocr_process(img)
        log_raw(f"--- RAW READ ---\n{raw_text}\n----------------", clear=True)
        p, s = parse_stats(raw_text)
        if p:
            log_main(f"PASSIVES FOUND:\n> " + "\n> ".join(p))
        else:
            log_main("PASSIVES FOUND: [None]")
        if s:
            log_main("STATS DETECTED:")
            for k, v in s.items():
                log_main(f" {k}: {v}")
        else:
            log_main("STATS DETECTED: [None]")
    else:
        log_main("Error capturing screen.")

def run_macro(gui_data, log_main, log_raw):
    global running
    log_main("--- MACRO STARTED ---", clear=True)

    targets = gui_data['targets']
    debug = gui_data['debug']
    prob_one_in = gui_data['one_in_chance']
    stats_callback = gui_data.get('stats_callback')
    success_callback = gui_data.get('success_callback')
    scan_rect = gui_data['scan_rect']
    coord_yes = gui_data['btn_yes']
    coord_no = gui_data['btn_no']
    max_honey_t = gui_data.get('max_honey', 0)
    max_honey_raw = max_honey_t * 1_000_000_000_000 if max_honey_t > 0 else 0
    delay_interact = gui_data.get('delay_interact', 0.6)
    delay_refresh = gui_data.get('delay_refresh', 0.8)
    gui_app = gui_data.get('gui')  # reference to MacroGUI instance

    any_single_or_less = any(len(t['passives']) < 2 for t in targets)
    if any_single_or_less:
        btn_gen_coords = coord_no
        cost_per_roll = 10_000_000_000
        log_main("Mode: Efficient (No/10B) [Mixed/Single Targets]")
    else:
        btn_gen_coords = coord_yes
        cost_per_roll = 500_000_000_000
        log_main("Mode: Heavy Spending (Yes/500B) [All Targets match Double]")



    start_time = time.time()
    rolls = 0
    avg_roll_time = 0
    stat_order_lookup = list(STAT_RANGES.keys())

    while running:
        if keyboard.is_pressed('f2'):
            running = False
            break

        if max_honey_raw > 0:
            spent_session = rolls * cost_per_roll
            if (spent_session + cost_per_roll) > max_honey_raw:
                log_main("!!! MAX HONEY REACHED !!!")
                if success_callback:
                    success_callback("Max Honey Limit Reached",
                                     "The defined Max Honey limit for this session has been reached.")
                running = False
                break

        pydirectinput.press('e')
        time.sleep(delay_interact)
        wiggle_click(btn_gen_coords)
        time.sleep(delay_refresh)

        stats_img = get_stats_image_dynamic(scan_rect)
        rolls += 1

        current_time = time.time()
        elapsed = current_time - start_time
        avg_roll_time = elapsed / rolls
        est_time_remaining = (prob_one_in * avg_roll_time)

        spent_session = rolls * cost_per_roll

        if stats_callback:
            stats_callback(rolls, avg_roll_time, est_time_remaining, spent_session)

        raw_text = ocr_process(stats_img)
        if debug:
            log_raw(f"--- RAW ---\n{raw_text}", clear=True)

        detected_passives, detected_stats = parse_stats(raw_text)
        sorted_stats_list = []
        for key in stat_order_lookup:
            if key in detected_stats:
                sorted_stats_list.append((key, detected_stats[key]))

        try:
            img_filename = f"roll_{rolls}.jpg"
            img_full_path = os.path.join(session_dir, img_filename)
            if stats_img is not None and stats_img.size > 0:
                bgr_img = cv2.cvtColor(stats_img, cv2.COLOR_RGB2BGR)
                cv2.imwrite(img_full_path, bgr_img, [int(cv2.IMWRITE_JPEG_QUALITY), 60])

            p_html = ", ".join(detected_passives) if detected_passives else "None"
            s_html = "<br>".join([f"{k.split('(')[0]}: {v}" for k, v in sorted_stats_list])

            with open(html_path, "a", encoding="utf-8") as f:
                f.write(
                    f"<tr><td>{rolls}</td>"
                    f"<td><div class='passives'>{p_html}</div>"
                    f"<div class='stats'>{s_html}</div></td>"
                    f"<td><img src='{img_filename}' width='250'></td></tr>"
                )
        except Exception:
            pass

        log_msg = ""
        if detected_passives:
            log_msg += f"Passive: {', '.join(detected_passives)}\n"
        if detected_stats:
            log_msg += "\n".join([f"{k.split('(')[0].strip()}: {v}" for k, v in sorted_stats_list])

        header_stats = f"Runs: {rolls} | Avg: {avg_roll_time:.1f}s"
        log_main(f"--- {header_stats} ---\n{log_msg}", clear=True)

        match_found = False
        hit_target_index = -1
        for i, target in enumerate(targets):
            wanted_passives = target['passives']
            wanted_stats = target['stats']

            match_count = sum(1 for p in wanted_passives if p in detected_passives)
            if match_count < len(wanted_passives):
                continue

            stat_fail = False
            for s, req_v in wanted_stats.items():
                if s not in detected_stats:
                    stat_fail = True
                    break
                if req_v > 0 and detected_stats[s] < req_v:
                    stat_fail = True
                    break
            
            if not stat_fail:
                match_found = True
                hit_target_index = i
                break

        if match_found:
            log_main(f"!!! TARGET FOUND (Amulet {hit_target_index+1}) !!!")
            if success_callback:
                success_callback("Target Found!", f"Target amulet {hit_target_index+1} found!")
            running = False
            if gui_app:
                gui_app.set_running_state(False)
            break

    try:
        with open(html_path, "a", encoding="utf-8") as f:
            f.write("</table></body></html>")
    except Exception:
        pass

    # Final cleanup when loop ends
    if gui_app:
        gui_app.set_running_state(False)


# ────────────────────────────────────────────────
#   AmuletFrame
# ────────────────────────────────────────────────

class AmuletFrame(tk.Frame):
    def __init__(self, parent, index, remove_callback, calc_callback, master_app):
        super().__init__(parent, bd=1, relief="groove")
        self.index = index
        self.remove_callback = remove_callback
        self.calc_callback = calc_callback
        self.master_app = master_app

        self.passive_vars = {}
        self.stat_vars = {}
        self.stat_entries = {}

        top_bar = tk.Frame(self, bg="#eeeeee")
        top_bar.pack(fill="x", padx=2, pady=2)

        tk.Label(top_bar, text=f"Amulet {index+1}", font=("Arial", 9, "bold"), bg="#eeeeee").pack(side="left")
        tk.Button(top_bar, text="X", font=("Arial", 8, "bold"), fg="red", width=3,
                  command=lambda: self.remove_callback(self)).pack(side="right")

        content_frame = tk.Frame(self)
        content_frame.pack(fill="x", expand=True)

        p_frame = tk.LabelFrame(content_frame, text="Passives (Max 2)", padx=2, pady=2)
        p_frame.pack(side="left", fill="both", expand=True, padx=2)

        for p in ALL_PASSIVES:
            var = tk.BooleanVar()
            chk = tk.Checkbutton(p_frame, text=p, variable=var,
                                 command=lambda v=var: [self.check_passive_limit(v), self.calc_callback()],
                                 anchor="w")
            chk.pack(fill="x")
            self.passive_vars[p] = var

        s_frame = tk.LabelFrame(content_frame, text="Stats (Max 5)", padx=2, pady=2)
        s_frame.pack(side="left", fill="both", expand=True, padx=2)

        for stat, (min_r, max_r) in STAT_RANGES.items():
            row = tk.Frame(s_frame)
            row.pack(fill="x", pady=0)

            chk_var = tk.BooleanVar()
            self.stat_vars[stat] = chk_var

            def on_stat_check(s=stat, v=chk_var):
                self.check_stat_limit(v)
                self.calc_callback()
                state = 'normal' if v.get() else 'disabled'
                self.stat_entries[s]['widget'].config(state=state)

            cb = tk.Checkbutton(row, variable=chk_var, command=on_stat_check)
            cb.pack(side="left")

            tk.Label(row, text=stat, width=28, anchor="w", font=("Arial", 8)).pack(side="left")

            vcmd = (self.register(self.validate_stat), '%P', stat)
            entry_var = tk.StringVar(value="0")
            entry = tk.Entry(row, textvariable=entry_var, width=4, state='disabled',
                             validate='focusout', validatecommand=vcmd)
            entry.pack(side="right", padx=1)
            self.stat_entries[stat] = {'var': entry_var, 'widget': entry}

    def check_passive_limit(self, changed_var):
        selected = [v for v in self.passive_vars.values() if v.get()]
        if len(selected) > 2:
            changed_var.set(False)
            messagebox.showwarning("Limit Reached", "Max 2 passives per amulet.")

    def check_stat_limit(self, changed_var):
        selected = [v for v in self.stat_vars.values() if v.get()]
        if len(selected) > 5:
            changed_var.set(False)
            messagebox.showwarning("Limit Reached", "Max 5 stats per amulet.")

    def validate_stat(self, new_value, stat_name):
        if new_value == "" or new_value == "0":
            return True
        try:
            val = float(new_value)
            min_v, max_v = STAT_RANGES[stat_name]
            if min_v <= val <= max_v:
                return True
            else:
                self.after_idle(lambda: self.stat_entries[stat_name]['var'].set("0"))
                return False
        except:
            self.after_idle(lambda: self.stat_entries[stat_name]['var'].set("0"))
            return False

    def get_config(self):
        selected_passives = [p for p, v in self.passive_vars.items() if v.get()]

        selected_stats = {}
        for stat, enabled in self.stat_vars.items():
            if enabled.get():
                try:
                    val = float(self.stat_entries[stat]['var'].get())
                except:
                    val = 0
                selected_stats[stat] = val

        return {'passives': selected_passives, 'stats': selected_stats}

    def set_config(self, data):
        for var in self.passive_vars.values():
            var.set(False)

        saved_passives = data.get('passives', [])
        if isinstance(saved_passives, list):
            for p in saved_passives:
                if p in self.passive_vars:
                    self.passive_vars[p].set(True)

        stat_checks = data.get('stat_checks', {})
        for s, val in stat_checks.items():
            if s in self.stat_vars:
                self.stat_vars[s].set(val)
                state = 'normal' if val else 'disabled'
                if s in self.stat_entries:
                    self.stat_entries[s]['widget'].config(state=state)

        stat_values = data.get('stat_values', {})
        for s, val in stat_values.items():
            if s in self.stat_entries:
                self.stat_entries[s]['var'].set(val)


# ────────────────────────────────────────────────
#   Main GUI with TABS
# ────────────────────────────────────────────────

class MacroGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Amulet Roller - Made by Toxbic")
        try:
            pass
            #icon_path = resource_path("logo.ico")
            #self.root.iconbitmap(icon_path)
        except Exception:
            pass

        self.root.geometry("680x920")
        self.config_file = "config_amulets.json"

        self.overlay_window = None
        self.btn_overlays = {'yes': None, 'no': None}

        self.amulets = []
        self.always_on_top = tk.BooleanVar(value=True)
        self.debug_mode = tk.BooleanVar(value=False)

        self.honey_var = tk.StringVar(value="0")
        self.max_honey_var = tk.StringVar(value="0")


        # Create a Discord Button
  
        self.var_sx = tk.DoubleVar(value=DEFAULT_SCAN[0])
        self.var_sy = tk.DoubleVar(value=DEFAULT_SCAN[1])
        self.var_sw = tk.DoubleVar(value=DEFAULT_SCAN[2])
        self.var_sh = tk.DoubleVar(value=DEFAULT_SCAN[3])

        self.var_no_x = tk.DoubleVar(value=DEFAULT_BTN_NO[0])
        self.var_no_y = tk.DoubleVar(value=DEFAULT_BTN_NO[1])
        self.var_yes_x = tk.DoubleVar(value=DEFAULT_BTN_YES[0])
        self.var_yes_y = tk.DoubleVar(value=DEFAULT_BTN_YES[1])

        self.var_delay_interact = tk.DoubleVar(value=DEFAULT_DELAY_INTERACT)
        self.var_delay_refresh = tk.DoubleVar(value=DEFAULT_DELAY_REFRESH)

        self.var_odds = tk.StringVar(value="--")
        self.var_cost = tk.StringVar(value="--")
        self.var_chance = tk.StringVar(value="--")
        self.var_avg = tk.StringVar(value="--")
        self.var_est_time = tk.StringVar(value="--")
        self.var_runs_session = tk.StringVar(value="0")
        self.var_runs_total = tk.StringVar(value="0")
        self.var_spent_session = tk.StringVar(value="--")
        self.var_spent_total = tk.StringVar(value="--")

        self.current_session_runs = 0
        self.current_session_spent = 0
        self.loaded_all_time_runs = 0
        self.loaded_all_time_spent = 0

        # ── Notebook (Tabs) ───────────────────────────────────────
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=4, pady=4)

        self.tab_targets = tk.Frame(self.notebook)
        self.notebook.add(self.tab_targets, text="Targets")
  
        self.tab_config = tk.Frame(self.notebook)
        self.notebook.add(self.tab_config, text="Config & Coordinates")

        self.tab_stats = tk.Frame(self.notebook)
        self.notebook.add(self.tab_stats, text="Stats & Odds")

        self.tab_logs = tk.Frame(self.notebook)
        self.notebook.add(self.tab_logs, text="Logs")


        self._build_tab_targets()
        self._build_tab_config()
        self._build_tab_stats()
        self._build_tab_logs()

        # Separator before controls
        ttk.Separator(self.root, orient='horizontal').pack(fill="x", pady=(6, 0))

        # ── Start / Stop controls ────────────────────────────────
        control_frame = tk.Frame(self.root, bg="#f8f8f8")
        control_frame.pack(fill="x", padx=20, pady=12, ipady=8)

        self.btn_start = tk.Button(
            control_frame,
            text="START MACRO   (F1)",
            command=self.validate_and_start,
            font=("Segoe UI", 12, "bold"),
            bg="#4CAF50", fg="white",
            activebackground="#45a049",
            width=18,
            height=2,
            relief="raised"
        )
        self.btn_start.pack(side="left", padx=30)

        self.btn_stop = tk.Button(
            control_frame,
            text="STOP MACRO    (F2)",
            command=self.stop_thread,
            font=("Segoe UI", 12, "bold"),
            bg="#f44336", fg="white",
            activebackground="#e53935",
            width=18,
            height=2,
            relief="raised",
            state="disabled"
        )
        self.btn_discord = tk.Button(text="Join Discord Server",command=self.open_discord,font=("Segoe UI", 9, "bold"),bg="#5865F2",activebackground="#4752C4",padx=10)
        
        self.btn_discord.pack(side="left", padx=8)        
        self.btn_stop.pack(side="left", padx=30)

        # Status indicator
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(
            control_frame,
            textvariable=self.status_var,
            font=("Segoe UI", 11, "bold"),
            fg="#444"
        ).pack(side="right", padx=30)

        # Global hotkeys
        keyboard.add_hotkey('f1', self.validate_and_start)
        keyboard.add_hotkey('f2', self.stop_thread)
        keyboard.add_hotkey('f3', self.start_test_thread)

        self.load_config()
        if not self.amulets:
            self.add_amulet()

        self.calculate_odds()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.toggle_top()

    def set_running_state(self, is_running):
        if is_running:
            self.btn_start.config(state="disabled")
            self.btn_stop.config(state="normal")
            self.status_var.set("RUNNING")
        else:
            self.btn_start.config(state="normal")
            self.btn_stop.config(state="disabled")
            self.status_var.set("Stopped / Ready")
    def open_discord(self):
        webbrowser.open("https://discord.gg/s9jSwPYv")
    def _build_tab_targets(self):
        tk.Label(self.tab_targets, text="Target Amulets", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=8, pady=(6,2))

        btn_frame = tk.Frame(self.tab_targets)
        btn_frame.pack(fill="x", padx=8, pady=4)
        tk.Button(btn_frame, text="+ Add Amulet", command=self.add_amulet,
                  bg="#ccffcc", font=("Arial", 9, "bold")).pack(side="right")

        canvas_container = tk.Frame(self.tab_targets, bd=1, relief="sunken")
        canvas_container.pack(fill="both", expand=True, padx=8, pady=4)

        self.canvas = tk.Canvas(canvas_container)
        scrollbar = ttk.Scrollbar(canvas_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _build_tab_config(self):
        tk.Label(self.tab_config, text="Macro Settings", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=8, pady=(6,2))

        options_f = tk.Frame(self.tab_config)
        options_f.pack(fill="x", padx=8, pady=4)
        tk.Checkbutton(options_f, text="Always on Top", variable=self.always_on_top, command=self.toggle_top).pack(side="left", padx=6)
        tk.Checkbutton(options_f, text="Debug Logs", variable=self.debug_mode).pack(side="left", padx=6)
        tk.Button(options_f, text="Test OCR (F3)", command=self.start_test_thread,
                  bg="#e1e1e1", font=("Arial", 9)).pack(side="left", padx=8)

        delay_f = tk.LabelFrame(self.tab_config, text="Timing Delays (seconds)", padx=6, pady=6)
        delay_f.pack(fill="x", padx=8, pady=4)

        tk.Label(delay_f, text="Click Delay:").pack(side="left", padx=6)
        tk.Scale(delay_f, variable=self.var_delay_interact, from_=0.3, to=1.5, resolution=0.1,
                 orient="horizontal", showvalue=1, length=100).pack(side="left", padx=6)

        tk.Label(delay_f, text="Wait Stats:").pack(side="left", padx=12)
        tk.Scale(delay_f, variable=self.var_delay_refresh, from_=0.3, to=1.5, resolution=0.1,
                 orient="horizontal", showvalue=1, length=100).pack(side="left", padx=6)

        self.create_config_section(self.tab_config)

    def _build_tab_stats(self):
        tk.Label(self.tab_stats, text="Session & Probability Stats", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=8, pady=(6,2))

        self.create_stats_section(self.tab_stats)

    def _build_tab_logs(self):
        log_pane = tk.PanedWindow(self.tab_logs, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        log_pane.pack(fill="both", expand=True, padx=6, pady=6)

        main_f = tk.Frame(log_pane)
        tk.Label(main_f, text="Detected Stats", font=("Arial", 9, "bold")).pack(anchor="w")
        self.log_main_txt = tk.Text(main_f, height=12, state='disabled', font=("Consolas", 9))
        self.log_main_txt.pack(fill="both", expand=True)
        log_pane.add(main_f, width=380)

        raw_f = tk.Frame(log_pane)
        tk.Label(raw_f, text="Raw OCR Output", font=("Arial", 9, "bold")).pack(anchor="w")
        self.log_raw_txt = tk.Text(raw_f, height=12, state='disabled', font=("Consolas", 8))
        self.log_raw_txt.pack(fill="both", expand=True)
        log_pane.add(raw_f, width=300)

    def create_config_section(self, parent):
        container = tk.LabelFrame(parent, text="Scan Area & Click Points", padx=6, pady=6)
        container.pack(fill="x", padx=8, pady=6)

        scan_f = tk.LabelFrame(container, text="OCR Scan Region", padx=4, pady=4)
        scan_f.pack(fill="x", pady=4)

        def on_drag(*args):
            self.update_overlay()
            self.update_btn_overlay()

        tk.Label(scan_f, text="X:").grid(row=0, column=0, sticky="e")
        tk.Scale(scan_f, variable=self.var_sx, from_=0.0, to=1.0, resolution=0.01, orient="horizontal",
                 showvalue=0, command=on_drag).grid(row=0, column=1, sticky="ew")
        scan_f.columnconfigure(1, weight=1)

        tk.Label(scan_f, text="Y:").grid(row=0, column=2, sticky="e", padx=(12,0))
        tk.Scale(scan_f, variable=self.var_sy, from_=0.0, to=1.0, resolution=0.01, orient="horizontal",
                 showvalue=0, command=on_drag).grid(row=0, column=3, sticky="ew")
        scan_f.columnconfigure(3, weight=1)

        tk.Label(scan_f, text="W:").grid(row=1, column=0, sticky="e")
        tk.Scale(scan_f, variable=self.var_sw, from_=0.0, to=0.5, resolution=0.01, orient="horizontal",
                 showvalue=0, command=on_drag).grid(row=1, column=1, sticky="ew")

        tk.Label(scan_f, text="H:").grid(row=1, column=2, sticky="e", padx=(12,0))
        tk.Scale(scan_f, variable=self.var_sh, from_=0.0, to=0.8, resolution=0.01, orient="horizontal",
                 showvalue=0, command=on_drag).grid(row=1, column=3, sticky="ew")

        tk.Button(scan_f, text="Show Box", bg="#ffdddd", command=self.toggle_overlay).grid(row=0, column=4, rowspan=2, padx=12, sticky="ns")

        btn_f = tk.LabelFrame(container, text="Click Positions", padx=4, pady=4)
        btn_f.pack(fill="x", pady=4)

        tk.Label(btn_f, text="No (10B)", fg="red", font=("Arial", 9, "bold")).grid(row=0, column=0, sticky="e", padx=(0,6))
        tk.Label(btn_f, text="X:").grid(row=0, column=1, sticky="e")
        tk.Scale(btn_f, variable=self.var_no_x, from_=0.0, to=1.0, resolution=0.01, orient="horizontal",
                 showvalue=0, command=on_drag).grid(row=0, column=2, sticky="ew")
        tk.Label(btn_f, text="Y:").grid(row=0, column=3, sticky="e", padx=(12,0))
        tk.Scale(btn_f, variable=self.var_no_y, from_=0.0, to=1.0, resolution=0.01, orient="horizontal",
                 showvalue=0, command=on_drag).grid(row=0, column=4, sticky="ew")
        btn_f.columnconfigure(2, weight=1)
        btn_f.columnconfigure(4, weight=1)

        tk.Label(btn_f, text="Yes (500B)", fg="darkgreen", font=("Arial", 9, "bold")).grid(row=1, column=0, sticky="e", padx=(0,6))
        tk.Label(btn_f, text="X:").grid(row=1, column=1, sticky="e")
        tk.Scale(btn_f, variable=self.var_yes_x, from_=0.0, to=1.0, resolution=0.01, orient="horizontal",
                 showvalue=0, command=on_drag).grid(row=1, column=2, sticky="ew")
        tk.Label(btn_f, text="Y:").grid(row=1, column=3, sticky="e", padx=(12,0))
        tk.Scale(btn_f, variable=self.var_yes_y, from_=0.0, to=1.0, resolution=0.01, orient="horizontal",
                 showvalue=0, command=on_drag).grid(row=1, column=4, sticky="ew")

        tk.Button(btn_f, text="Show Points", bg="#ddffdd", command=self.toggle_btn_overlay).grid(row=0, column=5, rowspan=2, padx=12, sticky="ns")

    def create_stats_section(self, parent):
        container = tk.LabelFrame(parent, text="Live Statistics", padx=6, pady=6)
        container.pack(fill="x", padx=8, pady=6)

        f = tk.Frame(container)
        f.pack(fill="x", padx=4, pady=2)

        tk.Label(f, text="Current Honey (T):").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        tk.Entry(f, textvariable=self.honey_var, width=8).grid(row=0, column=1, sticky="w", padx=4)
        self.honey_var.trace_add("write", lambda *a: self.calculate_odds())

        tk.Label(f, text="Max Usable Honey (T):").grid(row=0, column=2, sticky="w", padx=(20,4), pady=2)
        tk.Entry(f, textvariable=self.max_honey_var, width=8).grid(row=0, column=3, sticky="w", padx=4)

        tk.Label(f, text="Chance this session:").grid(row=0, column=4, sticky="w", padx=(30,4))
        tk.Label(f, textvariable=self.var_chance, font=("Segoe UI", 10, "bold"), fg="#006600").grid(row=0, column=5, sticky="w")

        ttk.Separator(container, orient='horizontal').pack(fill="x", pady=6)

        stats_grid = tk.Frame(container)
        stats_grid.pack(fill="x", padx=4)

        labels = [
            ("Odds (any target):",   self.var_odds,       0,0),
            ("Avg Time / roll:",     self.var_avg,        0,2),
            ("Runs (session):",      self.var_runs_session,0,4),
            ("Runs (all time):",     self.var_runs_total,  0,6),

            ("Est. Cost:",           self.var_cost,       1,0),
            ("Est. Time remaining:", self.var_est_time,   1,2),
            ("Spent (session):",     self.var_spent_session,1,4),
            ("Spent (all time):",    self.var_spent_total, 1,6),
        ]

        for text, var, r, c in labels:
            tk.Label(stats_grid, text=text, font=("Arial", 9)).grid(row=r, column=c, sticky="w", padx=4, pady=1)
            tk.Label(stats_grid, textvariable=var, font=("Segoe UI", 10, "bold")).grid(row=r, column=c+1, sticky="w", padx=4, pady=1)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def add_amulet(self):
        idx = len(self.amulets)
        rf = AmuletFrame(self.scrollable_frame, idx, self.remove_amulet, self.calculate_odds, self)
        rf.pack(fill="x", pady=3, padx=4)
        self.amulets.append(rf)
        self.calculate_odds()

    def remove_amulet(self, amulet_frame):
        if len(self.amulets) <= 1:
            messagebox.showwarning("Warning", "You must have at least one amulet.")
            return
        amulet_frame.destroy()
        self.amulets.remove(amulet_frame)

        for i, r in enumerate(self.amulets):
            r.index = i
            try:
                top_bar = r.winfo_children()[0]
                label = top_bar.winfo_children()[0]
                label.config(text=f"Amulet {i+1}")
            except:
                pass
        self.calculate_odds()

    def update_overlay(self):
        if self.overlay_window is None:
            return
        x, y, w, h = get_screen_rect(self.get_scan_rect())
        if w < 1: w = 1
        if h < 1: h = 1
        self.overlay_window.geometry(f"{w}x{h}+{x}+{y}")

    def toggle_overlay(self):
        if self.overlay_window:
            self.overlay_window.destroy()
            self.overlay_window = None
        else:
            self.overlay_window = tk.Toplevel(self.root)
            self.overlay_window.overrideredirect(True)
            self.overlay_window.attributes('-topmost', True)
            self.overlay_window.attributes('-alpha', 0.3)
            self.overlay_window.config(bg='red')
            self.update_overlay()

    def update_btn_overlay(self, *args):
        if not any(self.btn_overlays.values()):
            return
        sw, sh = pyautogui.size()
        coords = self.get_btn_coords()
        for key in ['yes', 'no']:
            win = self.btn_overlays.get(key)
            if win:
                rx, ry = coords[key]
                px, py = int(sw * rx), int(sh * ry)
                win.geometry(f"20x20+{px-10}+{py-10}")
                win.update_idletasks()

    def toggle_btn_overlay(self):
        if any(self.btn_overlays.values()):
            for k, v in self.btn_overlays.items():
                if v:
                    v.destroy()
                self.btn_overlays[k] = None
        else:
            for key, color in [('yes', '#00ff00'), ('no', '#ff0000')]:
                win = tk.Toplevel(self.root)
                win.overrideredirect(True)
                win.attributes('-topmost', True)
                win.attributes('-alpha', 0.8)
                win.config(bg=color)
                l = tk.Label(win, text=key[0].upper(), bg=color, font=('Arial', 9, 'bold'))
                l.pack(expand=True, fill='both')
                self.btn_overlays[key] = win
            self.update_btn_overlay()

    def calculate_odds(self):
        total_p = 0.0
        max_cost_mode = 10_000_000_000
        seen_configs = set()

        for region in self.amulets:
            data = region.get_config()
            if len(data['passives']) >= 2:
                max_cost_mode = 500_000_000_000

            passives_sig = tuple(sorted(data['passives']))
            stats_sig_list = [(k, v) for k, v in data['stats'].items()]
            stats_sig = tuple(sorted(stats_sig_list))
            config_signature = (passives_sig, stats_sig)

            if config_signature in seen_configs:
                continue
            seen_configs.add(config_signature)

            num_passives = len(data['passives'])
            num_stats = len(data['stats'])

            p_passive = 1.0
            if num_passives == 1:
                p_passive = 1 / 6
            elif num_passives == 2:
                p_passive = 1 / 15

            stat_numerator_map = {0: 126, 1: 70, 2: 35, 3: 15, 4: 5, 5: 1}
            numerator = stat_numerator_map.get(num_stats, 0)
            p_stat = numerator / 126.0

            p_region = p_passive * p_stat
            total_p += p_region

        if total_p == 0:
            total_p = 1e-9
        if total_p > 1.0:
            total_p = 1.0

        one_in_chance = 1 / total_p
        avg_cost_honey = one_in_chance * max_cost_mode
        avg_cost_trillion = avg_cost_honey / 1_000_000_000_000

        try:
            current_honey_trill = float(self.honey_var.get())
        except ValueError:
            current_honey_trill = 0.0

        current_honey_raw = current_honey_trill * 1_000_000_000_000
        possible_rolls = current_honey_raw // max_cost_mode

        if possible_rolls <= 0:
            success_chance = 0.0
        else:
            success_chance = 1 - math.pow((1 - total_p), possible_rolls)

        self.var_odds.set(f"1 in {int(one_in_chance):,} (Comb)")
        self.var_cost.set(f"{avg_cost_trillion:.2f} T")
        self.var_chance.set(f"{success_chance*100:.2f}%")

        return one_in_chance

    def update_live_stats(self, runs, avg_time, est_remain, spent_session):
        self.current_session_runs = runs
        self.current_session_spent = spent_session

        def _update():
            self.var_runs_session.set(str(runs))
            self.var_spent_session.set(format_large_number(spent_session))
            self.var_avg.set(f"{avg_time:.1f}s")
            self.var_est_time.set(format_time(est_remain))

            total_runs = self.loaded_all_time_runs + runs
            total_spent = self.loaded_all_time_spent + spent_session

            self.var_runs_total.set(str(total_runs))
            self.var_spent_total.set(format_large_number(total_spent))

        self.root.after(0, _update)

    def toggle_top(self):
        self.root.attributes('-topmost', self.always_on_top.get())

    def log_main(self, message, clear=False):
        self.log_main_txt.config(state='normal')
        if clear:
            self.log_main_txt.delete('1.0', tk.END)
        self.log_main_txt.insert(tk.END, message + "\n")
        self.log_main_txt.see(tk.END)
        self.log_main_txt.config(state='disabled')

    def log_raw(self, message, clear=False):
        self.log_raw_txt.config(state='normal')
        if clear:
            self.log_raw_txt.delete('1.0', tk.END)
        self.log_raw_txt.insert(tk.END, message + "\n")
        self.log_raw_txt.see(tk.END)
        self.log_raw_txt.config(state='disabled')

    def start_test_thread(self):
        t = threading.Thread(target=run_debug_test, args=(self.log_main, self.log_raw, self.get_scan_rect))
        t.daemon = True
        t.start()

    def show_success_popup(self, title, msg):
        self.root.after(0, lambda: messagebox.showinfo(title, msg))

    def validate_and_start(self):
        self.save_config()
        all_targets = [r.get_config() for r in self.amulets]
        one_in_chance = self.calculate_odds()
        self.start_thread(all_targets, one_in_chance)

    def start_thread(self, targets, one_in_chance):
        global running
        if not running:
            running = True
            self.set_running_state(True)
            self.var_runs_session.set("0")
            self.current_session_runs = 0
            self.current_session_spent = 0
            self.var_avg.set("0.0s")
            self.var_est_time.set("Calc...")
            self.var_spent_session.set("0")

            self.log_main(f"Starting... {len(targets)} Target Amulets", clear=True)

            try:
                max_h = float(self.max_honey_var.get())
            except:
                max_h = 0.0

            btn_coords = self.get_btn_coords()

            data = {
                'targets': targets,
                'debug': self.debug_mode.get(),
                'one_in_chance': one_in_chance,
                'stats_callback': self.update_live_stats,
                'success_callback': self.show_success_popup,
                'scan_rect': self.get_scan_rect(),
                'btn_yes': btn_coords['yes'],
                'btn_no': btn_coords['no'],
                'max_honey': max_h,
                'delay_interact': self.var_delay_interact.get(),
                'delay_refresh': self.var_delay_refresh.get(),
                'gui': self
            }

            t = threading.Thread(target=run_macro, args=(data, self.log_main, self.log_raw))
            t.daemon = True
            t.start()

    def stop_thread(self):
        global running
        running = False
        self.log_main("Stopping...")
        self.set_running_state(False)
        self.save_config()

    def get_scan_rect(self):
        return (self.var_sx.get(), self.var_sy.get(), self.var_sw.get(), self.var_sh.get())

    def get_btn_coords(self):
        return {
            "yes": (self.var_yes_x.get(), self.var_yes_y.get()),
            "no": (self.var_no_x.get(), self.var_no_y.get())
        }

    def save_config(self):
        amulets_data = []
        for r in self.amulets:
            cfg = r.get_config()
            cfg['stat_checks'] = {k: v.get() for k, v in r.stat_vars.items()}
            cfg['stat_values'] = {k: r.stat_entries[k]['var'].get() for k in r.stat_entries}
            amulets_data.append(cfg)

        new_total_runs = self.loaded_all_time_runs + self.current_session_runs
        new_total_spent = self.loaded_all_time_spent + self.current_session_spent

        config_data = {
            "always_on_top": self.always_on_top.get(),
            "debug_mode": self.debug_mode.get(),
            "honey_amount": self.honey_var.get(),
            "max_honey": self.max_honey_var.get(),
            "total_runs": new_total_runs,
            "total_spent": new_total_spent,
            "scan_rect": self.get_scan_rect(),
            "btn_coords": self.get_btn_coords(),
            "delays": {"interact": self.var_delay_interact.get(), "refresh": self.var_delay_refresh.get()},
            "amulets": amulets_data
        }

        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4)
        except Exception:
            pass

        self.loaded_all_time_runs = new_total_runs
        self.loaded_all_time_spent = new_total_spent
        self.current_session_runs = 0
        self.current_session_spent = 0

    def load_config(self):
        if not os.path.exists(self.config_file):
            return

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.always_on_top.set(data.get("always_on_top", True))
            self.debug_mode.set(data.get("debug_mode", False))
            self.honey_var.set(data.get("honey_amount", "0"))
            self.max_honey_var.set(data.get("max_honey", "0"))
            self.loaded_all_time_runs = data.get("total_runs", 0)
            self.loaded_all_time_spent = data.get("total_spent", 0)

            self.var_runs_total.set(str(self.loaded_all_time_runs))
            self.var_spent_total.set(format_large_number(self.loaded_all_time_spent))

            scan = data.get("scan_rect", DEFAULT_SCAN)
            if len(scan) == 4:
                self.var_sx.set(scan[0])
                self.var_sy.set(scan[1])
                self.var_sw.set(scan[2])
                self.var_sh.set(scan[3])

            btns = data.get("btn_coords", {})
            if "yes" in btns:
                self.var_yes_x.set(btns["yes"][0])
                self.var_yes_y.set(btns["yes"][1])
            if "no" in btns:
                self.var_no_x.set(btns["no"][0])
                self.var_no_y.set(btns["no"][1])

            delays = data.get("delays", {})
            self.var_delay_interact.set(delays.get("interact", DEFAULT_DELAY_INTERACT))
            self.var_delay_refresh.set(delays.get("refresh", DEFAULT_DELAY_REFRESH))

            saved_amulets = data.get("amulets", [])
            if saved_amulets:
                for r in self.amulets[:]:
                    self.remove_amulet(r)

                for reg_data in saved_amulets:
                    self.add_amulet()
                    self.amulets[-1].set_config(reg_data)

        except Exception:
            pass

    def on_close(self):
        self.save_config()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = MacroGUI(root)
    root.mainloop()
