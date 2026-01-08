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
from rapidocr_onnxruntime import RapidOCR

pydirectinput.PAUSE = 0.001
pydirectinput.FAILSAFE = False
pyautogui.FAILSAFE = False

logging.getLogger("ppocr").setLevel(logging.ERROR)
ocr_model = RapidOCR(det_use_gpu=True, cls_use_gpu=True, rec_use_gpu=True)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

DEFAULT_SCAN = (0.52, 0.43, 0.08, 0.12)
DEFAULT_BTN_NO  = (0.55, 0.54)
DEFAULT_BTN_YES = (0.45, 0.54)
DEFAULT_DELAY_INTERACT = 0.6
DEFAULT_DELAY_REFRESH = 0.8

STAT_RANGES = {
    "Pollen (8 - 20)": (8, 20),
    "White Pollen (15 - 70)": (15, 70),
    "Blue Pollen (15 - 70)": (15, 70),
    "Red Pollen (15 - 70)": (15, 70),
    "Bee Gather Pollen (15 - 70)": (15, 70),
    "Instant Conversion (5 - 12)": (5, 12),
    "Convert Rate (1.05 - 1.25)": (1.05, 1.25), 
    "Bee Ability Rate (2 - 7)": (2, 7),
    "Critical Chance (2 - 7)": (2, 7)
}

ALL_PASSIVES = [
    "Pop Star", "Guiding Star", "Star Shower", 
    "Gummy Star", "Scorching Star", "Star Saw"
]

running = False

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
    if img is None: return ""
    img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    try:
        result, _ = ocr_model(img) 
    except Exception:
        return ""
    
    full_text = ""
    if result:
        for item in result:
            if len(item) >= 2:
                full_text += item[1] + "\n"
    return full_text

def parse_stats(text):
    passives = []
    stats = {}
    stat_map = {}
    for k in STAT_RANGES.keys():
        clean_name = k.split('(')[0].replace(" ", "").lower()
        stat_map[clean_name] = k

    passive_map = {p.replace(" ", "").lower(): p for p in ALL_PASSIVES}
    
    # Sort by length
    sorted_stat_keys = sorted(stat_map.keys(), key=len, reverse=True)

    lines = text.split('\n')
    for line in lines:
        if not line.strip(): continue
        line_clean = line.lower().replace(" ", "").replace(":", "").replace(".", "")
        
        # Check Passives
        for clean_p, real_p in passive_map.items():
            if clean_p in line_clean:
                passives.append(real_p)
        
        # Check Stats
        match = re.search(r'[x\+]?\s*(\d+[\.,]?\d*)(.*)', line, re.IGNORECASE)
        if match:
            val_str = match.group(1).replace(',', '.')
            rest_of_line = match.group(2)
            clean_rest = rest_of_line.lower().replace(" ", "").replace("%", "")
            
            found_stat_name = None
            for k in sorted_stat_keys:
                if k in clean_rest:
                    found_stat_name = stat_map[k]
                    break
            
            if found_stat_name:
                try:
                    val = float(val_str)
                    min_r, max_r = STAT_RANGES[found_stat_name]
                    if val > 100 and max_r < 100: val = val // 10
                    if max_r < 20 and val > 20: val = val // 10
                    if found_stat_name == "Convert Rate" and val > 10: val = val / 100
                    
                    stats[found_stat_name] = val
                except ValueError:
                    continue
    return list(set(passives)), stats

def format_time(seconds):
    if seconds is None or seconds == float('inf') or seconds == 0: return "--"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    if d > 0: return f"{int(d)}d {int(h)}h"
    if h > 0: return f"{int(h)}h {int(m)}m"
    return f"{int(m)}m {int(s)}s"

def format_large_number(num):
    if num >= 1e15: return f"{num/1e15:.2f} Qd"
    if num >= 1e12: return f"{num/1e12:.2f} T"
    if num >= 1e9:  return f"{num/1e9:.2f} B"
    return f"{num:.0f}"

def run_debug_test(log_main, log_raw, get_scan_rect):
    log_main("--- TEST OCR STARTED ---", clear=True)
    rect = get_scan_rect()
    img = get_stats_image_dynamic(rect)
    if img is not None:
        raw_text = ocr_process(img)
        log_raw(f"--- RAW READ ---\n{raw_text}\n----------------", clear=True)
        p, s = parse_stats(raw_text)
        if p: log_main(f"PASSIVES FOUND:\n> " + "\n> ".join(p))
        else: log_main("PASSIVES FOUND: [None]")
        if s:
            log_main("STATS DETECTED:")
            for k, v in s.items(): log_main(f"  {k}: {v}")
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
    scan_rect = gui_data['scan_rect']
    
    coord_yes = gui_data['btn_yes']
    coord_no = gui_data['btn_no']

    delay_interact = gui_data.get('delay_interact', 0.6)
    delay_refresh = gui_data.get('delay_refresh', 0.8)

    any_double_passive = any(len(t['passives']) >= 2 for t in targets)
    
    if any_double_passive:
        btn_gen_coords = coord_yes 
        cost_per_roll = 500_000_000_000
        log_main("Mode: Double Passive Gen (Yes/500B)")
    else:
        btn_gen_coords = coord_no 
        cost_per_roll = 10_000_000_000
        log_main("Mode: Single Passive Gen (No/10B)")

    start_time = time.time()
    rolls = 0
    avg_roll_time = 0

    while running:
        if keyboard.is_pressed('f2'):
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
        spent_total = rolls * cost_per_roll

        if stats_callback:
            stats_callback(rolls, avg_roll_time, est_time_remaining, spent_total)

        raw_text = ocr_process(stats_img)
        if debug:
            log_raw(f"--- RAW ---\n{raw_text}", clear=True)

        detected_passives, detected_stats = parse_stats(raw_text)
        
        log_msg = ""
        if detected_passives: log_msg += f"Passive: {', '.join(detected_passives)}\n"
        if detected_stats:
            log_msg += "\n".join([f"{k.split('(')[0].strip()}: {v}" for k, v in detected_stats.items()])
        
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
            running = False
            break

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
                                 command=lambda v=var: [self.check_passive_limit(v), self.calc_callback()], anchor="w")
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
        if new_value == "" or new_value == "0": return True
        try:
            val = float(new_value)
            min_v, max_v = STAT_RANGES[stat_name]
            if min_v <= val <= max_v: return True
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
                try: val = float(self.stat_entries[stat]['var'].get())
                except: val = 0
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

class MacroGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SSA Macro Multi-Target")
        try:
            icon_path = resource_path("logo.ico")
            self.root.iconbitmap(icon_path) 
        except Exception: pass

        self.root.geometry("620x850")
        self.config_file = "ssa_settings.json"

        self.overlay_window = None
        self.btn_overlays = {'yes': None, 'no': None}

        self.amulets = []
        self.always_on_top = tk.BooleanVar(value=False)
        self.debug_mode = tk.BooleanVar(value=False)
        self.honey_var = tk.StringVar(value="0") 

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
        self.var_runs = tk.StringVar(value="0")
        self.var_avg = tk.StringVar(value="--")
        self.var_est_time = tk.StringVar(value="--")
        self.var_spent = tk.StringVar(value="--")

        self.header_label = tk.Label(root, text="SSA Auto Roller (Multi-Target)", font=("Segoe UI", 12, "bold"))
        self.header_label.pack(pady=2)
        
        tk.Label(root, text="Made by spectral (discord - spctrl, Roblox - 45LEGEND_X)", font=("Segoe UI", 8)).pack(pady=0)
        
        c_frame = tk.Frame(root)
        c_frame.pack(pady=0)
        tk.Label(c_frame, text="F1: Start | F2: Stop", fg="blue", font=("Segoe UI", 9, "bold")).pack(side="left", padx=5)

        o_frame = tk.Frame(root)
        o_frame.pack(pady=0)
        tk.Checkbutton(o_frame, text="Always on Top [ENABLE]", variable=self.always_on_top, command=self.toggle_top).pack(side="left", padx=2)
        tk.Checkbutton(o_frame, text="Debug Logs", variable=self.debug_mode).pack(side="left", padx=2)
        tk.Button(o_frame, text="Test OCR (F3)", command=self.start_test_thread, bg="#e1e1e1", width=10, height=1, font=("Arial", 8)).pack(side="left", padx=5)

        self.create_stats_section(root)
        
        region_controls = tk.Frame(root)
        region_controls.pack(fill="x", padx=5, pady=2)
        tk.Label(region_controls, text="Target Amulets", font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Button(region_controls, text="+ Add Amulet", command=self.add_amulet, bg="#ccffcc", font=("Arial", 8)).pack(side="right")

        self.canvas_container = tk.Frame(root, bd=1, relief="sunken")
        self.canvas_container.pack(fill="both", expand=True, padx=5, pady=2)
        
        self.canvas = tk.Canvas(self.canvas_container)
        self.scrollbar = ttk.Scrollbar(self.canvas_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.create_config_section(root)

        self.log_pane = tk.PanedWindow(root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        self.log_pane.pack(padx=2, pady=2, fill="both", expand=True)

        self.main_frame = tk.Frame(self.log_pane)
        tk.Label(self.main_frame, text="Detected Stats", font=("Arial", 8, "bold")).pack(anchor="w")
        self.log_main_txt = tk.Text(self.main_frame, height=5, width=1, state='disabled', font=("Consolas", 8))
        self.log_main_txt.pack(fill="both", expand=True)
        self.log_pane.add(self.main_frame, width=320) 

        self.raw_frame = tk.Frame(self.log_pane)
        tk.Label(self.raw_frame, text="Raw OCR", font=("Arial", 8, "bold")).pack(anchor="w")
        self.log_raw_txt = tk.Text(self.raw_frame, height=5, width=1, state='disabled', font=("Consolas", 7))
        self.log_raw_txt.pack(fill="both", expand=True)
        self.log_pane.add(self.raw_frame, width=220)

        keyboard.add_hotkey('f1', self.validate_and_start)
        keyboard.add_hotkey('f2', self.stop_thread)
        keyboard.add_hotkey('f3', self.start_test_thread)

        self.load_config()
        if not self.amulets:
            self.add_amulet()

        self.calculate_odds()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def add_amulet(self):
        idx = len(self.amulets)
        rf = AmuletFrame(self.scrollable_frame, idx, self.remove_amulet, self.calculate_odds, self)
        rf.pack(fill="x", pady=2, padx=2)
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
            except: pass
        self.calculate_odds()

    def update_overlay(self):
        if self.overlay_window is None: return
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
        if not any(self.btn_overlays.values()): return
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
                if v: v.destroy()
                self.btn_overlays[k] = None
        else:
            for key, color in [('yes', '#00ff00'), ('no', '#ff0000')]:
                win = tk.Toplevel(self.root)
                win.overrideredirect(True)
                win.attributes('-topmost', True)
                win.attributes('-alpha', 0.8)
                win.config(bg=color)
                l = tk.Label(win, text=key[0].upper(), bg=color, font=('Arial', 8, 'bold'))
                l.pack(expand=True, fill='both')
                self.btn_overlays[key] = win
            self.update_btn_overlay()

    def create_stats_section(self, parent):
        container = tk.LabelFrame(parent, text="Stats", font=("Segoe UI", 9, "bold"), padx=2, pady=0)
        container.pack(fill="x", padx=2, pady=2)
        
        header_frame = tk.Frame(container)
        header_frame.pack(fill="x")
        content_frame = tk.Frame(container)
        content_frame.pack(fill="x", padx=2, pady=0)

        def toggle_stats():
            if content_frame.winfo_viewable():
                content_frame.pack_forget()
                btn_toggle.config(text="[+]")
            else:
                content_frame.pack(fill="x", padx=2, pady=0)
                btn_toggle.config(text="[-]")

        btn_toggle = tk.Button(header_frame, text="[-]", font=("Consolas", 7), command=toggle_stats, borderwidth=1, width=3)
        btn_toggle.pack(side="right", padx=2, pady=1)

        tk.Label(content_frame, text="Honey (T):", font=("Arial", 9)).grid(row=0, column=0, sticky="w", padx=5)
        tk.Entry(content_frame, textvariable=self.honey_var, width=8).grid(row=0, column=1, sticky="w")
        self.honey_var.trace_add("write", lambda *args: self.calculate_odds())

        ttk.Separator(content_frame, orient='horizontal').grid(row=1, column=0, columnspan=6, sticky="ew", padx=2, pady=2)

        tk.Label(content_frame, text="Odds (Any):", font=("Arial", 9)).grid(row=2, column=0, sticky="w", padx=5)
        tk.Label(content_frame, textvariable=self.var_odds, font=("Segoe UI", 9, "bold")).grid(row=2, column=1, sticky="w")
        
        tk.Label(content_frame, text="Est Cost:", font=("Arial", 9)).grid(row=3, column=0, sticky="w", padx=5)
        tk.Label(content_frame, textvariable=self.var_cost, font=("Segoe UI", 9, "bold")).grid(row=3, column=1, sticky="w")

        tk.Label(content_frame, text="Avg Time:", font=("Arial", 9)).grid(row=2, column=2, sticky="w", padx=15)
        tk.Label(content_frame, textvariable=self.var_avg, font=("Segoe UI", 9, "bold")).grid(row=2, column=3, sticky="w")

        tk.Label(content_frame, text="Est Time:", font=("Arial", 9)).grid(row=3, column=2, sticky="w", padx=15)
        tk.Label(content_frame, textvariable=self.var_est_time, font=("Segoe UI", 9, "bold")).grid(row=3, column=3, sticky="w")

        tk.Label(content_frame, text="Runs:", font=("Arial", 9)).grid(row=2, column=4, sticky="w", padx=15)
        tk.Label(content_frame, textvariable=self.var_runs, font=("Segoe UI", 9, "bold")).grid(row=2, column=5, sticky="w")

        tk.Label(content_frame, text="Spent:", font=("Arial", 9)).grid(row=3, column=4, sticky="w", padx=15)
        tk.Label(content_frame, textvariable=self.var_spent, font=("Segoe UI", 9, "bold")).grid(row=3, column=5, sticky="w")
    
    def create_config_section(self, parent):
        container = tk.LabelFrame(parent, text="Macro Config", font=("Segoe UI", 9, "bold"), padx=2, pady=0)
        container.pack(fill="x", padx=2, pady=2)

        header_frame = tk.Frame(container)
        header_frame.pack(fill="x")
        content_frame = tk.Frame(container)
        content_frame.pack(fill="x", padx=2, pady=2)

        def toggle_config():
            if content_frame.winfo_viewable():
                content_frame.pack_forget()
                btn_toggle.config(text="[+]")
            else:
                content_frame.pack(fill="x", padx=2, pady=2)
                btn_toggle.config(text="[-]")

        btn_toggle = tk.Button(header_frame, text="[-]", font=("Consolas", 7), command=toggle_config, borderwidth=1, width=3)
        btn_toggle.pack(side="right", padx=2, pady=1)

        grp_delay = tk.LabelFrame(content_frame, text="Timing Delays (Seconds; Increase if Program Breaks", padx=2, pady=2)
        grp_delay.pack(fill="x", pady=2)
        tk.Label(grp_delay, text="Click Delay (0.3-1.5):").pack(side="left", padx=5)
        tk.Scale(grp_delay, variable=self.var_delay_interact, from_=0.3, to=1.5, resolution=0.1, orient="horizontal", showvalue=1, length=80).pack(side="left", padx=5)
        tk.Label(grp_delay, text="Wait Stats (0.3-1.5):").pack(side="left", padx=5)
        tk.Scale(grp_delay, variable=self.var_delay_refresh, from_=0.3, to=1.5, resolution=0.1, orient="horizontal", showvalue=1, length=80).pack(side="left", padx=5)

        grp_scan = tk.LabelFrame(content_frame, text="OCR Scan Area, Modify till it covers the stats and passives text of NEW Amulet", padx=2, pady=2)
        grp_scan.pack(fill="x", pady=2)
        grp_scan.columnconfigure(1, weight=1)
        grp_scan.columnconfigure(3, weight=1)

        def on_drag(val):
            self.update_overlay()
            self.update_btn_overlay()

        tk.Label(grp_scan, text="X").grid(row=0, column=0)
        tk.Scale(grp_scan, variable=self.var_sx, from_=0.0, to=1.0, resolution=0.01, orient="horizontal", showvalue=0, command=on_drag).grid(row=0, column=1, sticky="ew")
        
        tk.Label(grp_scan, text="Y").grid(row=0, column=2)
        tk.Scale(grp_scan, variable=self.var_sy, from_=0.0, to=1.0, resolution=0.01, orient="horizontal", showvalue=0, command=on_drag).grid(row=0, column=3, sticky="ew")
        
        tk.Label(grp_scan, text="W").grid(row=1, column=0)
        tk.Scale(grp_scan, variable=self.var_sw, from_=0.0, to=0.5, resolution=0.01, orient="horizontal", showvalue=0, command=on_drag).grid(row=1, column=1, sticky="ew")
        
        tk.Label(grp_scan, text="H").grid(row=1, column=2)
        tk.Scale(grp_scan, variable=self.var_sh, from_=0.0, to=0.8, resolution=0.01, orient="horizontal", showvalue=0, command=on_drag).grid(row=1, column=3, sticky="ew")
        
        btn_ov = tk.Button(grp_scan, text="Show\nBox", bg="#ffcccc", font=("Arial", 8), width=6, command=self.toggle_overlay)
        btn_ov.grid(row=0, column=4, rowspan=2, padx=5, sticky="ns")

        grp_btns = tk.LabelFrame(content_frame, text="Button Click Points (Modify till No is NO, Yes is on YES)", padx=2, pady=2)
        grp_btns.pack(fill="x", pady=2)

        grp_btns.columnconfigure(2, weight=1)
        grp_btns.columnconfigure(4, weight=1)

        tk.Label(grp_btns, text="No (10B)", fg="red", font=("Arial", 8, "bold")).grid(row=0, column=0, sticky="e")
        tk.Label(grp_btns, text="X").grid(row=0, column=1)
        tk.Scale(grp_btns, variable=self.var_no_x, from_=0.0, to=1.0, resolution=0.01, orient="horizontal", showvalue=0, command=on_drag).grid(row=0, column=2, sticky="ew")
        tk.Label(grp_btns, text="Y").grid(row=0, column=3)
        tk.Scale(grp_btns, variable=self.var_no_y, from_=0.0, to=1.0, resolution=0.01, orient="horizontal", showvalue=0, command=on_drag).grid(row=0, column=4, sticky="ew")

        tk.Label(grp_btns, text="Yes (500B)", fg="green", font=("Arial", 8, "bold")).grid(row=1, column=0, sticky="e")
        tk.Label(grp_btns, text="X").grid(row=1, column=1)
        tk.Scale(grp_btns, variable=self.var_yes_x, from_=0.0, to=1.0, resolution=0.01, orient="horizontal", showvalue=0, command=on_drag).grid(row=1, column=2, sticky="ew")
        tk.Label(grp_btns, text="Y").grid(row=1, column=3)
        tk.Scale(grp_btns, variable=self.var_yes_y, from_=0.0, to=1.0, resolution=0.01, orient="horizontal", showvalue=0, command=on_drag).grid(row=1, column=4, sticky="ew")

        btn_pt = tk.Button(grp_btns, text="Show\nPoints", bg="#ccffcc", font=("Arial", 8), width=6, command=self.toggle_btn_overlay)
        btn_pt.grid(row=0, column=5, rowspan=2, padx=5, sticky="ns")

    def get_scan_rect(self):
        return (self.var_sx.get(), self.var_sy.get(), self.var_sw.get(), self.var_sh.get())
    
    def get_btn_coords(self):
        return {
            "yes": (self.var_yes_x.get(), self.var_yes_y.get()),
            "no": (self.var_no_x.get(), self.var_no_y.get())
        }

    def calculate_odds(self):
        total_p = 0.0
        max_cost_mode = 10_000_000_000
        
        seen_configs = set()

        for region in self.amulets:
            data = region.get_config()
            
            if len(data['passives']) >= 2:
                max_cost_mode = 500_000_000_000

            passives_sig = tuple(sorted(data['passives']))
            
            stats_sig_list = []
            for k, v in data['stats'].items():
                stats_sig_list.append((k, v))
            stats_sig = tuple(sorted(stats_sig_list))
            
            config_signature = (passives_sig, stats_sig)
            
            if config_signature in seen_configs:
                continue 
            
            seen_configs.add(config_signature)

            num_passives = len(data['passives'])
            num_stats = len(data['stats'])
            
            p_passive = 1.0
            
            if num_passives == 1:
                p_passive = 1/6
            elif num_passives == 2:
                p_passive = 1/15
            
            stat_numerator_map = {0: 126, 1: 70, 2: 35, 3: 15, 4: 5, 5: 1}
            numerator = stat_numerator_map.get(num_stats, 0)
            p_stat = numerator / 126.0
            
            p_region = p_passive * p_stat
            total_p += p_region

        if total_p == 0: total_p = 1e-9
        if total_p > 1.0: total_p = 1.0 

        one_in_chance = 1 / total_p
        
        avg_cost_honey = one_in_chance * max_cost_mode
        avg_cost_trillion = avg_cost_honey / 1_000_000_000_000

        try: current_honey_trill = float(self.honey_var.get())
        except ValueError: current_honey_trill = 0.0
        
        current_honey_raw = current_honey_trill * 1_000_000_000_000
        possible_rolls = current_honey_raw // max_cost_mode
        
        if possible_rolls <= 0: success_chance = 0.0
        else: success_chance = 1 - math.pow((1 - total_p), possible_rolls)
        
        self.var_odds.set(f"1 in {int(one_in_chance):,} (Comb)")
        self.var_cost.set(f"{avg_cost_trillion:.2f} T")
        self.var_chance.set(f"{success_chance*100:.2f}%")
        
        return one_in_chance

    def update_live_stats(self, runs, avg_time, est_remain, spent_total):
        def _update():
            self.var_runs.set(str(runs))
            self.var_avg.set(f"{avg_time:.1f}s")
            self.var_est_time.set(format_time(est_remain))
            self.var_spent.set(format_large_number(spent_total))
        self.root.after(0, _update)

    def toggle_top(self):
        self.root.attributes('-topmost', self.always_on_top.get())

    def log_main(self, message, clear=False):
        self.log_main_txt.config(state='normal')
        if clear: self.log_main_txt.delete('1.0', tk.END)
        self.log_main_txt.insert(tk.END, message + "\n")
        self.log_main_txt.see(tk.END)
        self.log_main_txt.config(state='disabled')

    def log_raw(self, message, clear=False):
        self.log_raw_txt.config(state='normal')
        if clear: self.log_raw_txt.delete('1.0', tk.END)
        self.log_raw_txt.insert(tk.END, message + "\n")
        self.log_raw_txt.see(tk.END)
        self.log_raw_txt.config(state='disabled')

    def start_test_thread(self):
        t = threading.Thread(target=run_debug_test, args=(self.log_main, self.log_raw, self.get_scan_rect))
        t.daemon = True
        t.start()

    def validate_and_start(self):
        self.save_config()
        
        all_targets = []
        for r in self.amulets:
            all_targets.append(r.get_config())
            
        one_in_chance = self.calculate_odds()
        self.start_thread(all_targets, one_in_chance)

    def start_thread(self, targets, one_in_chance):
        global running
        if not running:
            running = True
            self.var_runs.set("0")
            self.var_avg.set("0.0s")
            self.var_est_time.set("Calc...")
            self.var_spent.set("0")
            self.log_main(f"Starting... {len(targets)} Target Amulets", clear=True)
            
            btn_coords = self.get_btn_coords()
            data = {
                'targets': targets, 
                'debug': self.debug_mode.get(),
                'one_in_chance': one_in_chance,
                'stats_callback': self.update_live_stats,
                'scan_rect': self.get_scan_rect(),
                'btn_yes': btn_coords['yes'],
                'btn_no': btn_coords['no'],
                'delay_interact': self.var_delay_interact.get(),
                'delay_refresh': self.var_delay_refresh.get()
            }
            t = threading.Thread(target=run_macro, args=(data, self.log_main, self.log_raw))
            t.daemon = True
            t.start()

    def stop_thread(self):
        global running
        running = False
        self.log_main("Stopping...")
    
    def save_config(self):
        amulets_data = []
        for r in self.amulets:
            cfg = r.get_config()
            cfg['stat_checks'] = {k: v.get() for k, v in r.stat_vars.items()}
            cfg['stat_values'] = {k: r.stat_entries[k]['var'].get() for k in r.stat_entries}
            amulets_data.append(cfg)

        config_data = {
            "always_on_top": self.always_on_top.get(),
            "debug_mode": self.debug_mode.get(),
            "honey_amount": self.honey_var.get(),
            "scan_rect": self.get_scan_rect(),
            "btn_coords": self.get_btn_coords(),
            "delays": {
                "interact": self.var_delay_interact.get(),
                "refresh": self.var_delay_refresh.get()
            },
            "amulets": amulets_data 
        }
        try:
            with open(self.config_file, 'w') as f: json.dump(config_data, f, indent=4)
        except Exception: pass

    def load_config(self):
        if not os.path.exists(self.config_file): return
        try:
            with open(self.config_file, 'r') as f: data = json.load(f)
            self.always_on_top.set(data.get("always_on_top", False))
            self.toggle_top()
            self.debug_mode.set(data.get("debug_mode", False))
            self.honey_var.set(data.get("honey_amount", "0"))
            
            scan = data.get("scan_rect", DEFAULT_SCAN)
            if len(scan) == 4:
                self.var_sx.set(scan[0]); self.var_sy.set(scan[1])
                self.var_sw.set(scan[2]); self.var_sh.set(scan[3])

            btns = data.get("btn_coords", {})
            if "yes" in btns:
                self.var_yes_x.set(btns["yes"][0]); self.var_yes_y.set(btns["yes"][1])
            if "no" in btns:
                self.var_no_x.set(btns["no"][0]); self.var_no_y.set(btns["no"][1])
            
            delays = data.get("delays", {})
            self.var_delay_interact.set(delays.get("interact", DEFAULT_DELAY_INTERACT))
            self.var_delay_refresh.set(delays.get("refresh", DEFAULT_DELAY_REFRESH))

            saved_amulets = data.get("amulets", data.get("regions", []))
            
            if saved_amulets:
                for r in self.amulets[:]: self.remove_amulet(r)
                
                for reg_data in saved_amulets:
                    self.add_amulet()
                    self.amulets[-1].set_config(reg_data)
                    
        except Exception: pass

    def on_close(self):
        self.save_config()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MacroGUI(root)
    root.mainloop()
