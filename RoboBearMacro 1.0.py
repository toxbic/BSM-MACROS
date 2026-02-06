import customtkinter as ctk
import threading
import easyocr
import pydirectinput
import time
import numpy as np
import math
import webbrowser
from PIL import ImageGrab
import keyboard  # ← added for hotkeys
import json
import os
import requests
from PIL import ImageGrab
import io

# Set a tiny pause to prevent "doubled" inputs, but keep it fast
pydirectinput.PAUSE = 0.01 

class RoboBearDefinitive(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.reader = easyocr.Reader(['en'])
        self.running = False
        self.digital_bee = 0
        self.round_counter = 0
        self.drives_bought = 0
        self.discord_webhook = ""  
        # Configurable positions (same defaults as original)
        self.pos_menu_open   = (1004, 142)
        self.pos_menu_select = (933, 748)
        self.pos_menu_start  = (0, 0)
        self.pos_quest_a = (1083,459)
        self.pos_drive_buy   = (897, 836)
        self.pos_drive_next  = (1106, 820)
        self.pos_refresh     = (814, 827)
        self.pos_bee1        = (638, 500)
        self.pos_bee2        = (956, 399)
        self.pos_accept      = (1094, 827)
        self.pos_exit        = (1855, 601)
        self.pos_confirm     = (841, 587)
        self.scan_region     = (632, 351, 625, 326)

       
        
        # Config file for saving positions
        self.config_file = "rb_macro_positions.json"
        self.load_config()

        self.setup_ui()
        self.bind_hotkeys()
 
    def bind_hotkeys(self):
        # F6 = start, F7 = stop
        keyboard.add_hotkey('f6', self.start_hotkey)
        keyboard.add_hotkey('f7', self.stop_hotkey)
        self.log("Hotkeys ready: F6 = START | F7 = STOP")

    def start_hotkey(self):
        if not self.running:
            self.start()

    def stop_hotkey(self):
        self.stop()




    def send_screenshot_to_discord(self, filename="screenshot.png"):
        webhook_url = self.discord_webhook.strip()

        # Fallback only if user didn't set anything
        if not webhook_url:
            
            self.log("please set your own in Discord tab!")
            return

        screenshot = ImageGrab.grab()
        
        buffer = io.BytesIO()
        screenshot.save(buffer, format="PNG")
        buffer.seek(0)
        
        files = {"file": (filename, buffer, "image/png")}
        
        try:
            response = requests.post(webhook_url, files=files, timeout=6)
            if response.status_code == 204:
                self.log("Screenshot sent to Discord")
                return True
            else:
                self.log(f"Discord send failed – status {response.status_code}")
                return False
        except Exception as e:
            self.log(f"Discord webhook error: {str(e)}")
            return False




    def setup_ui(self):
        self.title("RBC Macro - Made by Toxbic")
        self.geometry("500x650")
        self.attributes("-topmost", True)

        tabview = ctk.CTkTabview(self)
        tabview.pack(pady=10, padx=20, fill="both", expand=True)

        main_tab = tabview.add("Main")
        config_tab = tabview.add("XY Config")
        discord_tab = tabview.add("Discord")

        # ── Discord Tab ─────────────────────────────────────
        discord_frame = ctk.CTkFrame(discord_tab)
        discord_frame.pack(pady=20, padx=30, fill="both", expand=True)

        ctk.CTkLabel(
            discord_frame,
            text="Custom Discord Webhook",
            font=("Arial", 18, "bold")
        ).pack(pady=(20, 10))

        ctk.CTkLabel(
            discord_frame,
            text="Paste your webhook URL here.\nScreenshot will be sent when Digital Bee is found.",
            font=("Arial", 12),
            wraplength=420,
            justify="center"
        ).pack(pady=(0, 20))

        self.entry_webhook = ctk.CTkEntry(
            discord_frame,
            width=380,
            placeholder_text="https://discord.com/api/webhooks/...",
            show=None   # remove if you want to hide characters
        )
        self.entry_webhook.pack(pady=10)
        self.entry_webhook.insert(0, self.discord_webhook)

        ctk.CTkButton(
            discord_frame,
            text="Save Webhook",
            fg_color="#5865F2",
            hover_color="#4752C4",
            command=self.save_webhook
        ).pack(pady=15)

        ctk.CTkLabel(
            discord_frame,
            text="Tip: Create webhook → Server Settings → Integrations → Webhooks",
            font=("Arial", 10),
            text_color="gray"
        ).pack(pady=10)
        # ── Main Tab ────────────────────────────────────────
        ctk.CTkLabel(main_tab, text="ROBO BEAR MACRO By Toxbic", font=("Arial", 20, "bold")).pack(pady=(20, 5))
        
        selection_frame = ctk.CTkFrame(main_tab)
        selection_frame.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(selection_frame, text="Select Drive Priority:", font=("Arial", 12, "bold")).pack(pady=5)
        
        self.buy_red = ctk.CTkCheckBox(selection_frame, text="Red", fg_color="#e74c3c")
        self.buy_red.pack(pady=2); self.buy_red.select()
        
        self.buy_white = ctk.CTkCheckBox(selection_frame, text="White", fg_color="#ffffff", text_color="#000000")
        self.buy_white.pack(pady=2); self.buy_white.select()
        
        self.buy_blue = ctk.CTkCheckBox(selection_frame, text="Blue", fg_color="#3498db")
        self.buy_blue.pack(pady=2); self.buy_blue.select()
        
        self.buy_glitched = ctk.CTkCheckBox(selection_frame, text="Glitched", fg_color="#9b59b6")
        self.buy_glitched.pack(pady=2); self.buy_glitched.select()
        
        self.log_box = ctk.CTkTextbox(main_tab, height=180)
        self.log_box.pack(pady=10, padx=20, fill="both")

        ctk.CTkButton(main_tab, text="START Macro (F6)", fg_color="green", height=45, font=("Arial", 14, "bold"), command=self.start).pack(pady=5, fill="x", padx=20)
        ctk.CTkButton(main_tab, text="STOP (F7)", fg_color="red", height=40, command=self.stop).pack(pady=5, fill="x", padx=20)
        ctk.CTkButton(main_tab, text="JOIN DISCORD", fg_color="#7289da", command=self.open_discord).pack(pady=10, fill="x", padx=20)

        ctk.CTkLabel(main_tab, text="Tip: Use F6 / F7 to control macro without clicking", font=("Arial", 10)).pack(pady=5)

        # ── XY Config Tab (same as before) ──────────────────
        scroll_frame = ctk.CTkScrollableFrame(config_tab)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.entry_webhook.pack(pady=10)

        # ← Move the insert here, AFTER load_config() has run
        self.entry_webhook.insert(0, self.discord_webhook)
        self.config_entries = {}
        self.create_config_entry(scroll_frame, "Menu Open",   self.pos_menu_open)
        self.create_config_entry(scroll_frame, "Menu Select", self.pos_menu_select)
        self.create_config_entry(scroll_frame, "Menu Start",  self.pos_menu_start)
        self.create_config_entry(scroll_frame, "Quest A", self.pos_quest_a)
        self.create_config_entry(scroll_frame, "Drive Buy",   self.pos_drive_buy)
        self.create_config_entry(scroll_frame, "Drive Next",  self.pos_drive_next)
        self.create_config_entry(scroll_frame, "Refresh",     self.pos_refresh)
        self.create_config_entry(scroll_frame, "Bee 1",       self.pos_bee1)
        self.create_config_entry(scroll_frame, "Bee 2",       self.pos_bee2)
        self.create_config_entry(scroll_frame, "Accept",      self.pos_accept)
        self.create_config_entry(scroll_frame, "Exit",        self.pos_exit)
        self.create_config_entry(scroll_frame, "Confirm",     self.pos_confirm)

        # Scan Region
        region_frame = ctk.CTkFrame(scroll_frame)
        region_frame.pack(pady=10, fill="x")
        ctk.CTkLabel(region_frame, text="Scan Region (Left, Top, Width, Height):", font=("Arial", 12, "bold")).pack(pady=5)

        sub = ctk.CTkFrame(region_frame); sub.pack(fill="x")
        self.entry_scan_left   = ctk.CTkEntry(sub, width=60); self.entry_scan_left.insert(0, str(self.scan_region[0])); self.entry_scan_left.pack(side="left", padx=2)
        self.entry_scan_top    = ctk.CTkEntry(sub, width=60); self.entry_scan_top.insert(0, str(self.scan_region[1]));  self.entry_scan_top.pack(side="left", padx=2)
        self.entry_scan_width  = ctk.CTkEntry(sub, width=60); self.entry_scan_width.insert(0, str(self.scan_region[2])); self.entry_scan_width.pack(side="left", padx=2)
        self.entry_scan_height = ctk.CTkEntry(sub, width=60); self.entry_scan_height.insert(0, str(self.scan_region[3]));self.entry_scan_height.pack(side="left", padx=2)

        ctk.CTkButton(region_frame, text="Capture Region", command=self.start_region_capture).pack(pady=5)

        ctk.CTkButton(config_tab, text="Apply Changes", command=self.apply_changes).pack(pady=10)

    def create_config_entry(self, parent, name, pos):
        frame = ctk.CTkFrame(parent)
        frame.pack(pady=5, fill="x")
        ctk.CTkLabel(frame, text=f"{name} (X, Y):").pack(side="left", padx=5)
        ex = ctk.CTkEntry(frame, width=60); ex.insert(0, str(pos[0])); ex.pack(side="left", padx=2)
        ey = ctk.CTkEntry(frame, width=60); ey.insert(0, str(pos[1])); ey.pack(side="left", padx=2)
        ctk.CTkButton(frame, text="Capture", command=lambda: self.capture_point(ex, ey)).pack(side="left", padx=5)
        self.config_entries[name] = (ex, ey)

    def capture_point(self, ex, ey):
        self.log("Move mouse → capturing in 5s...")
        self.after(5000, lambda: self.set_point(ex, ey))



    def save_webhook(self):
        webhook = self.entry_webhook.get().strip()
        if webhook and not webhook.startswith("https://discord.com/api/webhooks/"):
            self.log("Warning: Doesn't look like a valid Discord webhook URL")
        
        self.discord_webhook = webhook
        self.save_config()           # re-save whole config
        self.log("Webhook URL updated and saved.")
    def set_point(self, ex, ey):
        x, y = pydirectinput.position()
        ex.delete(0, "end"); ex.insert(0, str(x))
        ey.delete(0, "end"); ey.insert(0, str(y))
        self.log("Position captured.")

    def start_region_capture(self):
        self.log("Move to TOP-LEFT → capturing in 5s...")
        self.after(5000, self.capture_tl)

    def capture_tl(self):
        tlx, tly = pydirectinput.position()
        self.entry_scan_left.delete(0, "end"); self.entry_scan_left.insert(0, str(tlx))
        self.entry_scan_top.delete(0, "end");  self.entry_scan_top.insert(0, str(tly))
        self.log("Now move to BOTTOM-RIGHT → capturing in 5s...")
        self.after(5000, self.capture_br)

    def capture_br(self):
        brx, bry = pydirectinput.position()
        try:
            tlx = int(self.entry_scan_left.get())
            tly = int(self.entry_scan_top.get())
            w = brx - tlx
            h = bry - tly
            self.entry_scan_width.delete(0, "end");  self.entry_scan_width.insert(0, str(w))
            self.entry_scan_height.delete(0, "end"); self.entry_scan_height.insert(0, str(h))
            self.log("Region captured.")
        except:
            self.log("Error calculating region.")

    def apply_changes(self):
        try:
            self.pos_menu_open   = (int(self.config_entries["Menu Open"][0].get()),   int(self.config_entries["Menu Open"][1].get()))
            self.pos_menu_select = (int(self.config_entries["Menu Select"][0].get()), int(self.config_entries["Menu Select"][1].get()))
            self.pos_menu_start  = (int(self.config_entries["Menu Start"][0].get()),  int(self.config_entries["Menu Start"][1].get()))
            self.pos_quest_a     = (int(self.config_entries["Quest A"][0].get()),     int(self.config_entries["Quest A"][1].get()))
            self.pos_drive_buy   = (int(self.config_entries["Drive Buy"][0].get()),   int(self.config_entries["Drive Buy"][1].get()))
            self.pos_drive_next  = (int(self.config_entries["Drive Next"][0].get()),  int(self.config_entries["Drive Next"][1].get()))
            self.pos_refresh     = (int(self.config_entries["Refresh"][0].get()),     int(self.config_entries["Refresh"][1].get()))
            self.pos_bee1        = (int(self.config_entries["Bee 1"][0].get()),       int(self.config_entries["Bee 1"][1].get()))
            self.pos_bee2        = (int(self.config_entries["Bee 2"][0].get()),       int(self.config_entries["Bee 2"][1].get()))
            self.pos_accept      = (int(self.config_entries["Accept"][0].get()),      int(self.config_entries["Accept"][1].get()))
            self.pos_exit        = (int(self.config_entries["Exit"][0].get()),        int(self.config_entries["Exit"][1].get()))
            self.pos_confirm     = (int(self.config_entries["Confirm"][0].get()),     int(self.config_entries["Confirm"][1].get()))

            self.scan_region = (
                int(self.entry_scan_left.get()),
                int(self.entry_scan_top.get()),
                int(self.entry_scan_width.get()),
                int(self.entry_scan_height.get())
            )

            self.fixed_clicks = [self.pos_menu_open] + [self.pos_menu_select] * 5 + [self.pos_menu_start] + [self.pos_quest_a]
            self.log("All positions updated.")
            self.save_config()  # ← added: save to JSON after applying changes

        except:
            self.log("Error: invalid number in one or more fields.")

    def save_config(self):
        config = {
            "menu_open":   list(self.pos_menu_open),
            "menu_select": list(self.pos_menu_select),
            "menu_start":  list(self.pos_menu_start),
            "quest_a":     list(self.pos_quest_a),
            "drive_buy":   list(self.pos_drive_buy),
            "drive_next":  list(self.pos_drive_next),
            "refresh":     list(self.pos_refresh),
            "bee1":        list(self.pos_bee1),
            "bee2":        list(self.pos_bee2),
            "accept":      list(self.pos_accept),
            "exit":        list(self.pos_exit),
            "confirm":     list(self.pos_confirm),
            "scan_region": list(self.scan_region),
        }
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            self.log("Positions saved to rb_macro_positions.json")
        except Exception as e:
            self.log(f"Failed to save config: {e}")

    def load_config(self):
        if not os.path.exists(self.config_file):
            self.log("No saved config found → using defaults")
            return

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            def get_pos(key, default):
                val = config.get(key)
                if isinstance(val, list) and len(val) == 2:
                    return tuple(val)
                return default

            self.pos_menu_open   = get_pos("menu_open",   self.pos_menu_open)
            self.pos_menu_select = get_pos("menu_select", self.pos_menu_select)
            self.pos_menu_start  = get_pos("menu_start",  self.pos_menu_start)
            self.pos_quest_a     = get_pos("quest_a",     self.pos_quest_a)
            self.pos_drive_buy   = get_pos("drive_buy",   self.pos_drive_buy)
            self.pos_drive_next  = get_pos("drive_next",  self.pos_drive_next)
            self.pos_refresh     = get_pos("refresh",     self.pos_refresh)
            self.pos_bee1        = get_pos("bee1",        self.pos_bee1)
            self.pos_bee2        = get_pos("bee2",        self.pos_bee2)
            self.pos_accept      = get_pos("accept",      self.pos_accept)
            self.pos_exit        = get_pos("exit",        self.pos_exit)
            self.pos_confirm     = get_pos("confirm",     self.pos_confirm)

            scan = config.get("scan_region")
            if isinstance(scan, list) and len(scan) == 4:
                self.scan_region = tuple(scan)

            # Rebuild fixed_clicks with loaded values
            self.fixed_clicks = [
                self.pos_menu_open,
                *[self.pos_menu_select] * 5,
                self.pos_menu_start,
                self.pos_quest_a
            ]

            self.log("Loaded positions from rb_macro_positions.json")
            self.log(f"Quest A loaded as: {self.pos_quest_a}")

        except Exception as e:
            self.log(f"Failed to load config: {e} → using defaults")
    def log(self, msg):
        if hasattr(self, 'log_box') and self.log_box is not None:
            self.log_box.insert("end", f"> {msg}\n")
            self.log_box.see("end")
        else:
            print(f"> {msg}")   # fallback to console during early init

    def open_discord(self):
        webbrowser.open("https://discord.gg/s9jSwPYv")

    def stop(self):
        if self.running:
            self.running = False
            self.log("Macro STOPPED.")

    def start(self):
        if not self.running:
            self.running = True
            self.log("Starting macro...")
            threading.Thread(target=self.main_loop, daemon=True).start()

    def action_smooth(self, x, y, post_pause=0.6):
        if not self.running: return
        start_x, start_y = pydirectinput.position()
        steps = 10
        for i in range(steps + 1):
            t = i / steps
            f = -(math.cos(math.pi * t) - 1) / 2
            curr_x = int(start_x + (x - start_x) * f)
            curr_y = int(start_y + (y - start_y) * f)
            pydirectinput.moveTo(curr_x, curr_y)
            time.sleep(0.01)
        pydirectinput.moveRel(1, 0); pydirectinput.moveRel(-1, 0)
        time.sleep(0.1)
        pydirectinput.mouseDown(); time.sleep(0.05); pydirectinput.mouseUp()
        time.sleep(post_pause)

    def walk_to_bear_original(self):
        self.log("To Robo Bear...")
        pydirectinput.keyDown('s'); time.sleep(1.504); pydirectinput.keyUp('s')
        pydirectinput.keyDown('d'); time.sleep(0.604); pydirectinput.keyUp('d')
        time.sleep(2)
        pydirectinput.press('e'); time.sleep(1.5)

    def walk_to_drive_reversed(self):
        self.log("Returning to shop...")
        pydirectinput.keyDown('a'); time.sleep(0.604); pydirectinput.keyUp('a')
        pydirectinput.keyDown('w'); time.sleep(2); pydirectinput.keyUp('w')
        pydirectinput.keyDown('space'); time.sleep(0.1); pydirectinput.keyUp('space')
        pydirectinput.keyDown('w'); time.sleep(1.8); pydirectinput.keyUp('w')
        pydirectinput.keyDown('d'); time.sleep(1); pydirectinput.keyUp('d')
        pydirectinput.keyDown('space'); time.sleep(0.1); pydirectinput.keyUp('space')
        pydirectinput.keyDown('d'); time.sleep(0.3); pydirectinput.keyUp('d')
        time.sleep(1)

    def buy_4_different_drives(self):



        pydirectinput.keyDown('e'); time.sleep(1); pydirectinput.keyUp('e')
        drive_selection = [
            ("Red", self.buy_red.get()), ("White", self.buy_white.get()),
            ("Blue", self.buy_blue.get()), ("Glitched", self.buy_glitched.get())
        ]
        items_bought = 0
        self.log("Round 1: Priority buying...")
        for name, active in drive_selection:
            if not self.running: return
            if active:
                self.action_smooth(self.pos_drive_buy[0], self.pos_drive_buy[1], post_pause=0.4)
                items_bought += 1
            self.action_smooth(self.pos_drive_next[0], self.pos_drive_next[1], post_pause=0.3)
        self.action_smooth(self.pos_drive_next[0], self.pos_drive_next[1], post_pause=0.3)

        if items_bought < 4 and self.running:
            for name, active in drive_selection:
                if items_bought >= 4 or not self.running: break
                if not active:
                    self.action_smooth(self.pos_drive_buy[0], self.pos_drive_buy[1], post_pause=0.4)
                    items_bought += 1
                self.action_smooth(self.pos_drive_next[0], self.pos_drive_next[1], post_pause=0.3)

        pydirectinput.keyDown('e'); time.sleep(1); pydirectinput.keyUp('e')

        self.drives_bought += 2
        time.sleep(1)
        # ENDER
        self.action_smooth(self.pos_exit[0], self.pos_exit[1], post_pause=0.5)
        self.action_smooth(self.pos_confirm[0], self.pos_confirm[1], post_pause=0.5)

        time.sleep(1)
        pydirectinput.keyDown('e'); time.sleep(1); pydirectinput.keyUp('e')
        drive_selection = [
            ("Red", self.buy_red.get()), ("White", self.buy_white.get()),
            ("Blue", self.buy_blue.get()), ("Glitched", self.buy_glitched.get())
        ]
        items_bought = 0
        self.log("Round 1: Priority buying...")
        for name, active in drive_selection:
            if not self.running: return
            if active:
                self.action_smooth(self.pos_drive_buy[0], self.pos_drive_buy[1], post_pause=0.4)
                items_bought += 1
            self.action_smooth(self.pos_drive_next[0], self.pos_drive_next[1], post_pause=0.3)
        self.action_smooth(self.pos_drive_next[0], self.pos_drive_next[1], post_pause=0.3)

        if items_bought < 4 and self.running:
            for name, active in drive_selection:
                if items_bought >= 4 or not self.running: break
                if not active:
                    self.action_smooth(self.pos_drive_buy[0], self.pos_drive_buy[1], post_pause=0.4)
                    items_bought += 1
                self.action_smooth(self.pos_drive_next[0], self.pos_drive_next[1], post_pause=0.3)

        pydirectinput.keyDown('e'); time.sleep(1); pydirectinput.keyUp('e')
        pydirectinput.keyDown('a'); time.sleep(0.5); pydirectinput.keyUp('a')
        pydirectinput.keyDown('d'); time.sleep(0.5); pydirectinput.keyUp('d')

    def use_drives(self):
        if self.digital_bee == 1 and self.running:

            time.sleep(1)
            for key in ['4','5','6','7']:
                for _ in range(6):
                    if not self.running: break
                    pydirectinput.press(key); time.sleep(1)
            self.action_smooth(self.pos_exit[0], self.pos_exit[1], post_pause=0.5)
            self.action_smooth(self.pos_confirm[0], self.pos_confirm[1], post_pause=0.5)
        self.digital_bee = 0


    def scan_bee(self):
        region = self.scan_region
        bbox = (region[0], region[1], region[0] + region[2], region[1] + region[3])
        try:
            screenshot = np.array(ImageGrab.grab(bbox=bbox))
            results = self.reader.readtext(screenshot)
            for (bbox_int, text, prob) in results:
                if "digital" in text.lower():
                    self.send_screenshot_to_discord()
                    
                    mx = region[0] + (bbox_int[0][0] + bbox_int[2][0]) / 2
                    my = region[1] + (bbox_int[0][1] + bbox_int[2][1]) / 2
                    self.digital_bee = 1
                    return int(mx), int(my)
        except:
            pass
        return 0, 0

    def main_loop(self):
        self.log("Ready. Start in 3s...")
        time.sleep(3)

        #self.send_screenshot_to_discord()
        while self.running:
            self.fixed_clicks = [self.pos_menu_open] + [self.pos_menu_select] * 3+ [self.pos_menu_start] *2+[self.pos_quest_a]
            self.digital_bee = 0
            self.walk_to_bear_original()
            
            while self.running:

                searching_mode = (self.round_counter >= 20)

                if self.running:
                    for pos in self.fixed_clicks:

                        self.action_smooth(pos[0], pos[1], post_pause=0.3)
                        time.sleep(1)
                time.sleep(1)

                time.sleep(1)
                if self.running and searching_mode:
                    for i in range(6):
                        if not self.running: break
                        bx, by = self.scan_bee()
                        if bx > 0:
                            self.log("Digital Bee detected! Clicking now...")
                            self.action_smooth(bx, by, post_pause=0.5)
                            self.digital_bee = 1    
                            self.round_counter = -1
                            break
                        else:
                            
                                self.log(f"Refreshing... ({i+1}/5)")
                                self.action_smooth(self.pos_refresh[0], self.pos_refresh[1], post_pause=0.6)

                time.sleep(0.5)

                if self.running:


                    

                    if 1==1:
                        bx, by = self.scan_bee()
                        if bx > 0:
                            self.log("Digital Bee detected! Clicking now...")
                            self.action_smooth(bx, by, post_pause=0.5)
                            self.digital_bee = 1
                        else:
                            self.action_smooth(self.pos_bee2[0], self.pos_bee2[1], post_pause=0.5)

                    if self.digital_bee == 0:

                     if 1==1:
                        bx, by = self.scan_bee()
                        if bx > 0:
                            self.log("Digital Bee detected! Clicking now...")
                            self.action_smooth(bx, by, post_pause=0.5)
                            self.digital_bee = 1
                        else:
                            self.action_smooth(self.pos_bee2[0], self.pos_bee2[1], post_pause=0.5)
                    time.sleep(1)
                    self.action_smooth(self.pos_accept[0], self.pos_accept[1], post_pause=0.8)

                if self.running and self.round_counter >= 20:
                 if self.digital_bee == 0:
                    

                    self.action_smooth(self.pos_exit[0], self.pos_exit[1], post_pause=0.5)
                    self.action_smooth(self.pos_confirm[0], self.pos_confirm[1], post_pause=0.5)

                    time.sleep(3)
                    pydirectinput.press('e')
                    time.sleep(1.5)
                    continue

                break

            if self.running and self.round_counter < 20:
                self.log(f"Drives bought so far: {self.drives_bought}")
                self.use_drives()
                self.walk_to_drive_reversed()
                self.buy_4_different_drives()
                self.round_counter += 1

                time.sleep(5)

if __name__ == "__main__":
    app = RoboBearDefinitive()
    app.mainloop()
