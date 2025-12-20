import tkinter as tk
from tkinter import messagebox
import cv2
import pytesseract
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

# --- RESOURCE RESOLVER (REQUIRED FOR COMPILATION) ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- SETUP TESSERACT & IMAGES ---

# 1. Point to the bundled Tesseract inside the exe
# Note: We will name the folder 'Tesseract-OCR' inside the bundle
tesseract_path = resource_path(os.path.join('Tesseract-OCR', 'tesseract.exe'))

# If not frozen (testing locally), fallback to your hardcoded path
if not os.path.exists(tesseract_path):
    tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

pytesseract.pytesseract.tesseract_cmd = tesseract_path

# 2. Wrap your image paths in the resource resolver
IMG_HEADER = resource_path('ssatext.png')
IMG_YES    = resource_path('yestext.png')
IMG_NO     = resource_path('notext.png') 

# Disable failsafes... (Rest of script continues below)
# Disable failsafes
pydirectinput.FAILSAFE = False
pyautogui.FAILSAFE = False

# constants
STAT_RANGES = {
    "Pollen": (8, 20),
    "White Pollen": (15, 70),
    "Blue Pollen": (15, 70),
    "Red Pollen": (15, 70),
    "Bee Gather Pollen": (15, 70),
    "Instant Conversion": (8, 12),
    "Convert Rate": (5, 25), 
    "Bee Ability Rate": (2, 7),
    "Critical Chance": (2, 7)
}

ALL_PASSIVES = [
    "Pop Star", "Guiding Star", "Star Shower", 
    "Gummy Star", "Scorching Star", "Star Saw"
]

# global 
running = False

# utilities bruh

def find_image_on_screen(template_path, confidence=0.8):
    try:
        screenshot = pyautogui.screenshot()
        screen_np = np.array(screenshot)
        screen_img = cv2.cvtColor(screen_np, cv2.COLOR_RGB2BGR)
        template = cv2.imread(template_path)
        if template is None: return None

        result = cv2.matchTemplate(screen_img, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val >= confidence:
            h, w = template.shape[:2]
            return (max_loc[0], max_loc[1], w, h)
        return None
    except:
        return None

def robust_click(x, y):
    """Aggressive clicking strategy."""
    pydirectinput.moveTo(x, y)
    time.sleep(0.05)
    pydirectinput.moveRel(2, 0)
    time.sleep(0.05)
    pydirectinput.moveRel(-2, 0)
    time.sleep(0.05)
    pydirectinput.click()
    time.sleep(0.05)
    pydirectinput.mouseDown()
    time.sleep(0.15) 
    pydirectinput.mouseUp()
    time.sleep(0.05)
    pydirectinput.click()

def get_stats_image(header_box):
    x, y, w, h = header_box
    start_x = int(x + (w * 0.5))
    start_y = int(y + (h * 1.5))
    width   = int(w * 0.8)
    height  = int(h * 7.0)
    return np.array(pyautogui.screenshot(region=(start_x, start_y, width, height)))

def ocr_process(img):
    scale = 350
    w = int(img.shape[1] * scale / 100)
    h = int(img.shape[0] * scale / 100)
    resized = cv2.resize(img, (w, h), interpolation=cv2.INTER_CUBIC)
    
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    gray = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

    thresh = cv2.adaptiveThreshold(
        gray, 255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 
        31, 
        15 
    )

    return pytesseract.image_to_string(thresh, config=r'--oem 3 --psm 6')

def parse_stats(text):
    passives = []
    stats = {}
    
    # CRITICAL FIX: Sort keys by length (descending).
    # This ensures "Blue Pollen" is checked BEFORE generic "Pollen".
    sorted_stat_keys = sorted(STAT_RANGES.keys(), key=len, reverse=True)

    def clean_number_str(s):
        s = s.upper().replace('O', '0').replace('S', '5').replace('I', '1').replace('L', '1').replace('B', '8')
        return s

    lines = text.split('\n')
    for line in lines:
        if not line.strip(): continue

        # 1. Clean up
        line_clean = line.replace('Polien', 'Pollen').replace('Pallen', 'Pollen') \
                         .replace('Biue', 'Blue').replace('Rea', 'Red') \
                         .replace('Instont', 'Instant').replace('Crltlcal', 'Critical')

        # 2. passives
        if "Passive" in line_clean:
            parts = line_clean.split(':')
            if len(parts) > 1:
                p_name = parts[1].strip()
                for real_p in ALL_PASSIVES:
                    if real_p.lower() in p_name.lower():
                        passives.append(real_p)
                        break
        
        # 3. % checker
        pct_match = re.search(r'([+\w]+)%\s+(.*)', line_clean)
        if pct_match:
            raw_num = pct_match.group(1) 
            stat_name = pct_match.group(2).strip()
            
            clean_num = clean_number_str(raw_num)
            digits = "".join(filter(str.isdigit, clean_num))
            
            if digits:
                val = int(digits)
                # Iterate through sorted keys
                for real_s in sorted_stat_keys:
                    if real_s.lower() in stat_name.lower():
                        stats[real_s] = val
                        break # Stop once specific match is found

        # 4. Check for Multiplier Stats
        else:
            x_match = re.search(r'x([\d\w\.]+)\s+(.*)', line_clean)
            if x_match:
                raw_num = x_match.group(1)
                stat_name = x_match.group(2).strip()
                
                clean_num = clean_number_str(raw_num)
                
                try:
                    clean_num = clean_num.replace('..', '.')
                    val_float = float(clean_num)
                    val_pct = int(round((val_float - 1.0) * 100))
                    
                    for real_s in sorted_stat_keys:
                        if real_s.lower() in stat_name.lower():
                            stats[real_s] = val_pct
                            break
                except:
                    pass
                    
    return passives, stats

# MAIN LOGIC DONT TOUCH

def run_macro(gui_data, log_callback):
    global running
    log_callback("--- MACRO STARTED ---")
    
    wanted_passives = gui_data['passives']
    wanted_stats = gui_data['stats'] 
    debug = gui_data['debug']

    use_double_roll = len(wanted_passives) == 2
    target_btn_img = IMG_YES if use_double_roll else IMG_NO
    target_btn_name = "YES" if use_double_roll else "NO"
    
    log_callback(f"Mode: {len(wanted_passives)} Passives selected.")
    log_callback(f"Clicking '{target_btn_name}' for rolls.")

    cached_btn_box = None
    cached_header_box = None

    while running:
        if keyboard.is_pressed('f2'):
            running = False
            log_callback("Stop signal received.")
            break

        # 1. ATTEMPT TO ROLL
        pydirectinput.keyDown('e')
        time.sleep(0.2) 
        pydirectinput.keyUp('e')
        time.sleep(0.8) 

        # 2. CLICK BUTTON
        if cached_btn_box is None:
            btn_box = find_image_on_screen(target_btn_img)
            if btn_box:
                cached_btn_box = btn_box
        
        if cached_btn_box:
            yx, yy, yw, yh = cached_btn_box
            cx, cy = int(yx + yw//2), int(yy + yh//2)
            robust_click(cx, cy)
            time.sleep(1.5) 
        else:
            time.sleep(0.5)

        # 3. FIND STATS HEADER
        if cached_header_box is None:
            header_box = find_image_on_screen(IMG_HEADER)
            if header_box:
                cached_header_box = header_box
        
        current_header = cached_header_box
        
        if not current_header:
            log_callback("Header not found. Retrying...")
            cached_btn_box = None 
            continue

        # 4. READ STATS
        stats_img = get_stats_image(current_header)
        stats_img = cv2.cvtColor(stats_img, cv2.COLOR_RGB2BGR)
        raw_text = ocr_process(stats_img)
        
        if debug:
            clean_raw = raw_text.replace('\n', ' | ')
            log_callback(f"DEBUG RAW: {clean_raw[:50]}...")

        if len(raw_text) < 10:
            continue

        detected_passives, detected_stats = parse_stats(raw_text)
        
        stat_str = ", ".join([f"{k}:{v}%" for k,v in detected_stats.items()])
        pass_str = ", ".join(detected_passives) if detected_passives else "None"
        log_callback(f"Found: [{pass_str}] | {stat_str}")

        # 5. CHECK REQUIREMENTS
        good_amulet = True
        
        # Check Passives
        if wanted_passives:
            matches = 0
            for wanted in wanted_passives:
                if wanted in detected_passives:
                    matches += 1
            
            if len(wanted_passives) > len(detected_passives):
                good_amulet = False
            elif matches < len(wanted_passives):
                good_amulet = False

        # Check Stats
        for stat_name, required_val in wanted_stats.items():
            if stat_name not in detected_stats:
                good_amulet = False
                break
            
            if required_val > 0:
                if detected_stats[stat_name] < required_val:
                    good_amulet = False
                    break
        
        if good_amulet:
            log_callback("!!! TARGET FOUND !!!")
            print('\a')
            running = False
            break

# --- DEBUG / TEST FUNCTION ---
def run_debug_test(log_callback):
    log_callback("--- TEST OCR STARTED ---")
    header_box = find_image_on_screen(IMG_HEADER)
    
    if not header_box:
        log_callback("Error: Header image not found on screen.")
        return

    stats_img = get_stats_image(header_box)
    stats_img_bgr = cv2.cvtColor(stats_img, cv2.COLOR_RGB2BGR)
    
    raw_text = ocr_process(stats_img_bgr)
    log_callback(f"--- RAW TEXT ---\n{raw_text}\n----------------")
    
    detected_passives, detected_stats = parse_stats(raw_text)
    
    log_callback(f"PASSIVES: {detected_passives}")
    log_callback("STATS:")
    for k, v in detected_stats.items():
        log_callback(f"  - {k}: {v}%")
    log_callback("--- TEST COMPLETE ---")

# --- GUI CLASS ---
class MacroGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SSA Macro")
        try:
            # use the .ico file for the window icon
            icon_path = resource_path("logo.ico")
            
            # .iconbitmap() is the correct function for .ico files on Windows
            self.root.iconbitmap(icon_path) 
        except Exception as e:
            print(f"Could not load logo: {e}")

        self.root.geometry("460x850")
        
        # Config file name
        self.config_file = "ssa_settings.json"

        self.stat_vars = {}      
        self.stat_entries = {}   
        self.passive_vars = {}
        self.always_on_top = tk.BooleanVar(value=False)
        self.debug_mode = tk.BooleanVar(value=False)

        # Main Header (Keep big and bold)
        tk.Label(root, text="SSA Auto Roller", font=("Arial", 14, "bold")).pack(pady=(5, 0))

        # Credits (Make smaller and regular weight)
        tk.Label(root, text="Made by 45LEGEND_X (discord - spctrl)", font=("Arial", 10)).pack(pady=(0, 5))
        
        # Controls Frame
        c_frame = tk.Frame(root)
        c_frame.pack(pady=5)
        tk.Label(c_frame, text="F1: Start | F2: Stop", fg="blue").pack(side="left", padx=10)
        
        # Options Frame
        o_frame = tk.Frame(root)
        o_frame.pack(pady=5)
        tk.Checkbutton(o_frame, text="Always on Top", variable=self.always_on_top, 
                       command=self.toggle_top).pack(side="left", padx=5)
        tk.Checkbutton(o_frame, text="Debug Logs", variable=self.debug_mode).pack(side="left", padx=5)

        # Test Button
        tk.Button(root, text="Test OCR Now (F3)", command=self.start_test_thread, bg="#dddddd").pack(pady=5)

        # Passives Frame
        p_frame = tk.LabelFrame(root, text="Passives (Max 2)")
        p_frame.pack(fill="x", padx=10, pady=5)
        
        for p in ALL_PASSIVES:
            var = tk.BooleanVar()
            chk = tk.Checkbutton(p_frame, text=p, variable=var, 
                                 command=lambda v=var: self.check_passive_limit(v))
            chk.pack(anchor="w")
            self.passive_vars[p] = var

        # Stats Frame
        s_frame = tk.LabelFrame(root, text="Stats (Max 5) - Value 0 for 'Any'")
        s_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        for stat, (min_r, max_r) in STAT_RANGES.items():
            row = tk.Frame(s_frame)
            row.pack(fill="x", pady=2)
            
            chk_var = tk.BooleanVar()
            self.stat_vars[stat] = chk_var
            
            # Helper to enable/disable entry box
            def on_stat_check(s=stat, v=chk_var):
                self.check_stat_limit(v)
                state = 'normal' if v.get() else 'disabled'
                self.stat_entries[s]['widget'].config(state=state)

            cb = tk.Checkbutton(row, variable=chk_var, command=on_stat_check)
            cb.pack(side="left")
            
            lbl_text = f"{stat} ({min_r}-{max_r})"
            tk.Label(row, text=lbl_text, width=25, anchor="w", font=("Arial", 9)).pack(side="left")
            
            entry_var = tk.StringVar(value="0")
            entry = tk.Entry(row, textvariable=entry_var, width=5, state='disabled')
            entry.pack(side="right", padx=10)
            
            self.stat_entries[stat] = {'var': entry_var, 'widget': entry}

        # Logs
        self.log_text = tk.Text(root, height=14, state='disabled', bg="#f0f0f0")
        self.log_text.pack(padx=10, pady=10, fill="both", expand=True)

        keyboard.add_hotkey('f1', self.validate_and_start)
        keyboard.add_hotkey('f2', self.stop_thread)
        keyboard.add_hotkey('f3', self.start_test_thread)

        # Load settings on startup
        self.load_config()

        # Save settings on close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def toggle_top(self):
        self.root.attributes('-topmost', self.always_on_top.get())

    def check_passive_limit(self, changed_var):
        selected = [v for v in self.passive_vars.values() if v.get()]
        if len(selected) > 2:
            changed_var.set(False)
            messagebox.showwarning("Limit Reached", "You can only select up to 2 passives.")

    def check_stat_limit(self, changed_var):
        selected = [v for v in self.stat_vars.values() if v.get()]
        if len(selected) > 5:
            changed_var.set(False)
            messagebox.showwarning("Limit Reached", "You can only select up to 5 stats.")

    def log(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def start_test_thread(self):
        t = threading.Thread(target=run_debug_test, args=(self.log,))
        t.daemon = True
        t.start()

    def validate_and_start(self):
        # Save settings whenever we start, just in case
        self.save_config()

        selected_passives = [p for p, v in self.passive_vars.items() if v.get()]
        selected_stats = {}
        for stat, enabled in self.stat_vars.items():
            if enabled.get():
                raw_val = self.stat_entries[stat]['var'].get()
                try:
                    val = float(raw_val)
                except ValueError:
                    messagebox.showerror("Error", f"Invalid number for {stat}")
                    return
                min_r, max_r = STAT_RANGES[stat]
                if val > 0:
                    if val < min_r or val > max_r:
                        messagebox.showerror("Range Error", 
                            f"{stat} must be between {min_r} and {max_r}.\nOr set to 0 to ignore value.")
                        return
                selected_stats[stat] = val

        self.start_thread(selected_passives, selected_stats)

    def start_thread(self, passives, stats):
        global running
        if not running:
            running = True
            data = {
                'passives': passives, 
                'stats': stats,
                'debug': self.debug_mode.get()
            }
            t = threading.Thread(target=run_macro, args=(data, self.log))
            t.daemon = True
            t.start()

    def stop_thread(self):
        global running
        running = False
        self.log("Stopping...")
    
    # --- CONFIGURATION FUNCTIONS ---
    def save_config(self):
        config_data = {
            "always_on_top": self.always_on_top.get(),
            "debug_mode": self.debug_mode.get(),
            "passives": {k: v.get() for k, v in self.passive_vars.items()},
            "stat_checks": {k: v.get() for k, v in self.stat_vars.items()},
            "stat_values": {k: self.stat_entries[k]['var'].get() for k in self.stat_entries}
        }
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=4)
        except Exception as e:
            self.log(f"Error saving config: {e}")

    def load_config(self):
        if not os.path.exists(self.config_file):
            return

        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)

            self.always_on_top.set(data.get("always_on_top", False))
            self.toggle_top()
            self.debug_mode.set(data.get("debug_mode", False))

            # Load Passives
            saved_passives = data.get("passives", {})
            for p, val in saved_passives.items():
                if p in self.passive_vars:
                    self.passive_vars[p].set(val)

            # Load Stat Checks and update widget states
            saved_checks = data.get("stat_checks", {})
            for s, val in saved_checks.items():
                if s in self.stat_vars:
                    self.stat_vars[s].set(val)
                    state = 'normal' if val else 'disabled'
                    if s in self.stat_entries:
                        self.stat_entries[s]['widget'].config(state=state)

            # Load Stat Values
            saved_values = data.get("stat_values", {})
            for s, val in saved_values.items():
                if s in self.stat_entries:
                    self.stat_entries[s]['var'].set(val)

        except Exception as e:
            self.log(f"Error loading config: {e}")

    def on_close(self):
        self.save_config()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MacroGUI(root)
    root.mainloop()