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

        # Configurable positions (same defaults as original)
        self.pos_menu_open   = (1004, 142)
        self.pos_menu_select = (933, 748)
        self.pos_menu_start  = (1083, 459)
        self.pos_drive_buy   = (897, 836)
        self.pos_drive_next  = (1106, 820)
        self.pos_refresh     = (814, 827)
        self.pos_bee1        = (638, 500)
        self.pos_bee2        = (956, 399)
        self.pos_accept      = (1094, 827)
        self.pos_exit        = (1855, 601)
        self.pos_confirm     = (841, 587)
        self.scan_region     = (632, 351, 625, 326)

        self.fixed_clicks = [self.pos_menu_open] + [self.pos_menu_select] * 5 + [self.pos_menu_start]
        
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

    def setup_ui(self):
        self.title("RBC Macro - Made by Toxbic")
        self.geometry("500x650")
        self.attributes("-topmost", True)

        tabview = ctk.CTkTabview(self)
        tabview.pack(pady=10, padx=20, fill="both", expand=True)

        main_tab = tabview.add("Main")
        config_tab = tabview.add("XY Config")

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

        self.config_entries = {}
        self.create_config_entry(scroll_frame, "Menu Open",   self.pos_menu_open)
        self.create_config_entry(scroll_frame, "Menu Select", self.pos_menu_select)
        self.create_config_entry(scroll_frame, "Menu Start",  self.pos_menu_start)
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

            self.fixed_clicks = [self.pos_menu_open] + [self.pos_menu_select] * 5 + [self.pos_menu_start]
            self.log("All positions updated.")
        except:
            self.log("Error: invalid number in one or more fields.")

    # ── The rest is EXACTLY the same as your previous version ──

    def log(self, msg):
        self.log_box.insert("end", f"> {msg}\n")
        self.log_box.see("end")

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
        self.drives_bought += 1
        time.sleep(1)
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
            for key in ['4','5','6','7']:
                for _ in range(6):
                    if not self.running: break
                    pydirectinput.press(key); time.sleep(1)
        self.digital_bee = 0

    def scan_bee(self):
        region = self.scan_region
        bbox = (region[0], region[1], region[0] + region[2], region[1] + region[3])
        try:
            screenshot = np.array(ImageGrab.grab(bbox=bbox))
            results = self.reader.readtext(screenshot)
            for (bbox_int, text, prob) in results:
                if "digital" in text.lower():
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
        
        while self.running:
            self.walk_to_bear_original()

            while self.running:
                searching_mode = (self.round_counter >= 20)

                if self.running:
                    for pos in self.fixed_clicks:
                        self.action_smooth(pos[0], pos[1], post_pause=0.3)
                        time.sleep(1)

                if self.running and searching_mode:
                    for i in range(3):
                        if not self.running: break
                        bx, by = self.scan_bee()
                        if bx > 0:
                            self.log("Digital Bee detected! Clicking now...")
                            self.action_smooth(bx, by, post_pause=0.5)
                            self.digital_bee = 1
                            self.round_counter = -1
                            break
                        else:
                            if i < 2:
                                self.log(f"Refreshing... ({i+1}/3)")
                                self.action_smooth(self.pos_refresh[0], self.pos_refresh[1], post_pause=0.6)

                time.sleep(0.5)

                if self.running:
                    self.log("scanning 2  bees...")
                    

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
                    self.log("Resetting via UI clicks...")
                    self.action_smooth(self.pos_exit[0], self.pos_exit[1], post_pause=0.5)
                    self.action_smooth(self.pos_confirm[0], self.pos_confirm[1], post_pause=0.5)
                    self.log("Skipping walk, talking to bear again...")
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
                self.log(f"Round {self.round_counter} done.")
                time.sleep(5)

if __name__ == "__main__":
    app = RoboBearDefinitive()
    app.mainloop()  
