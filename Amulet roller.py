import customtkinter as ctk
import threading
import easyocr
import pydirectinput
import pyautogui
import time
import cv2
import numpy as np
import json
import os
import requests
import io
import math
from PIL import Image
import re
import webbrowser
import sys

def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

CONFIG_FILE = resource_path("config.json")
pydirectinput.PAUSE = 0

# ---------------- DRAGGABLE OVERLAY WINDOW ----------------
class DraggableOverlay(ctk.CTkToplevel):
    def __init__(self, parent, title, initial_rect, is_point=False):
        super().__init__(parent)
        self.title(title)
        self.is_point = is_point
        
        # Setup window styling: Transparent center, black border
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.6)
        self.overrideredirect(True) # Remove title bar
        
        # Initial geometry
        x, y, w, h = initial_rect
        self.geometry(f"{w}x{h}+{x}+{y}")
        
        # Create a frame with a thick black border
        self.border_frame = ctk.CTkFrame(self, fg_color="transparent", border_color="black", border_width=4)
        self.border_frame.pack(fill="both", expand=True)
        
        self.label = ctk.CTkLabel(self.border_frame, text=title, font=("Arial", 10, "bold"), text_color="black")
        self.label.pack(pady=2)

        # Dragging logic
        self.bind("<ButtonPress-1>", self.start_move)
        self.bind("<ButtonRelease-1>", self.stop_move)
        self.bind("<B1-Motion>", self.do_move)

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def stop_move(self, event):
        self.x = None
        self.y = None

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.winfo_x() + deltax
        y = self.winfo_y() + deltay
        self.geometry(f"+{x}+{y}")

class BeeMacroGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("BSM AMULET ROLLER By Toxbic & AI")
        self.geometry("500x850")
        self.attributes('-topmost', True)

        self.reader = easyocr.Reader(['en'])
        self.running = False
        self.overlays_visible = False
        self.yes_overlay = None
        self.box_overlay = None

        # Stat mapping
        self.stat_map = {
            "Pollen": "pollen",
            "White Pollen": "white pollen",
            "Red Pollen": "red pollen",
            "Blue Pollen": "blue pollen",
            "Bee Gather Pollen" : "Bee Gather Pollen",
            "Instant Conversion": "instant conversion",
            "Convert Rate": "convert rate",
            "Bee Ability Rate": "ability rate",
            "Critical Chance": "critical"
        }

        self.passives = ["Star Saw", "Scorching Star", "Gummy Star", "Pop Star", "Guiding Star", "Shower"]

        self.config = {
            "yes_pos": [833, 585],
            "scan_region": [790, 360, 210, 240],
            "selected_stats": [],
            "total_rolls": 0,
            "stop_at_6": False,
            "default_webhook": "",
            "delay_before_click_yes": 2.5,
            "delay_after_e_press": 1.0,
            "delay_after_click": 2.5,
            "delay_between_loops": 0.5
        }

        self.checkboxes = {}
        self.delay_entries = {}
        self.load_config()
        self.setup_ui()

    # ---------------- OVERLAY TOGGLE ----------------
    def toggle_overlays(self):
        if not self.overlays_visible:
            # Show "YES" Point Overlay
            y_x, y_y = self.config["yes_pos"]
            self.yes_overlay = DraggableOverlay(self, "YES CLICK", (y_x-25, y_y-25, 50, 50), is_point=True)
            
            # Show "SCAN" Box Overlay
            s_x, s_y, s_w, s_h = self.config["scan_region"]
            self.box_overlay = DraggableOverlay(self, "SCAN AREA", (s_x, s_y, s_w, s_h))
            
            self.overlay_btn.configure(text="SAVE & HIDE OVERLAYS", fg_color="#e67e22")
            self.overlays_visible = True
            self.log("Overlays visible. Drag them to position.")
        else:
            # Save YES position (center of the small box)
            self.config["yes_pos"] = [
                self.yes_overlay.winfo_x() + 25,
                self.yes_overlay.winfo_y() + 25
            ]
            
            # Save SCAN region
            self.config["scan_region"] = [
                self.box_overlay.winfo_x(),
                self.box_overlay.winfo_y(),
                self.box_overlay.winfo_width(),
                self.box_overlay.winfo_height()
            ]
            
            self.yes_overlay.destroy()
            self.box_overlay.destroy()
            self.save_config()
            
            self.overlay_btn.configure(text="SHOW SETUP OVERLAYS", fg_color="#3498db")
            self.overlays_visible = False
            self.log("Coordinates saved and overlays hidden.")

    # ---------------- UI SETUP (Modified) ----------------
    def setup_ui(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(padx=10, pady=10, fill="both", expand=True)

        self.tab_main = self.tabview.add("Main")
        self.tab_stats = self.tabview.add("Stats")
        self.tab_settings = self.tabview.add("Settings")
        self.tab_webhook = self.tabview.add("Webhook")

        # ---- MAIN TAB ----
        self.roll_label = ctk.CTkLabel(self.tab_main, text=f"Rolls: {self.config['total_rolls']}", font=("Arial", 22, "bold"))
        self.roll_label.pack(pady=10)

        self.image_label = ctk.CTkLabel(self.tab_main, text="Amulet Preview", width=250, height=120, fg_color="black")
        self.image_label.pack(pady=10)

        # NEW OVERLAY TOGGLE BUTTON
        self.overlay_btn = ctk.CTkButton(self.tab_main, text="SHOW SETUP OVERLAYS", fg_color="#3498db", 
                                         command=self.toggle_overlays, font=("Arial", 14, "bold"))
        self.overlay_btn.pack(pady=10, padx=20, fill="x")

        self.start_btn = ctk.CTkButton(self.tab_main, text="START MACRO", fg_color="#2ecc71", hover_color="#27ae60",
                                        font=("Arial", 16, "bold"), command=self.start_macro)
        self.start_btn.pack(pady=(20, 5), padx=20, fill="x")

        self.stop_btn = ctk.CTkButton(self.tab_main, text="STOP", fg_color="#e74c3c", hover_color="#c0392b",
                                      command=self.stop_macro)
        self.stop_btn.pack(pady=5, padx=20, fill="x")

        self.discord_btn = ctk.CTkButton(self.tab_main, text="Join Discord", fg_color="#7289da", hover_color="#5b70be",
                                         command=lambda: webbrowser.open("https://discord.gg/s9jSwPYv"))
        self.discord_btn.pack(pady=5, padx=20, fill="x")

        self.log_box = ctk.CTkTextbox(self.tab_main, height=120, font=("Consolas", 11))
        self.log_box.pack(pady=10, padx=10, fill="both")

        # (The rest of the UI setup for Stats, Settings, and Webhook remains identical to your original code)
        # ---- STATS TAB ----
        self.scroll_frame = ctk.CTkScrollableFrame(self.tab_stats, label_text="Select Desired Stats")
        self.scroll_frame.pack(pady=5, padx=5, fill="both", expand=True)

        ctk.CTkLabel(self.scroll_frame, text="--- PASSIVES ---", font=("Arial", 12, "bold"), text_color="#3498db").pack(pady=5)
        for p in self.passives:
            cb = ctk.CTkCheckBox(self.scroll_frame, text=p)
            cb.pack(anchor="w", padx=10, pady=2)
            if p in self.config["selected_stats"]: cb.select()
            self.checkboxes[p] = cb

        ctk.CTkLabel(self.scroll_frame, text="--- BASE STATS ---", font=("Arial", 12, "bold"), text_color="#3498db").pack(pady=(15, 5))
        for display_name in self.stat_map.keys():
            cb = ctk.CTkCheckBox(self.scroll_frame, text=display_name)
            cb.pack(anchor="w", padx=10, pady=2)
            if display_name in self.config["selected_stats"]: cb.select()
            self.checkboxes[display_name] = cb

        # ---- SETTINGS TAB ----
        self.stop6_checkbox = ctk.CTkCheckBox(self.tab_settings, text="Stop macro at 6/7 stats")
        self.stop6_checkbox.pack(pady=10)
        if self.config.get("stop_at_6"): self.stop6_checkbox.select()

        ctk.CTkLabel(self.tab_settings, text="Macro Delays (seconds)", font=("Arial", 14, "bold")).pack(pady=(20, 5))
        delays = [
            ("delay_before_click_yes", "Delay before clicking YES"),
            ("delay_after_e_press", "Delay after pressing E"),
            ("delay_after_click", "Delay after clicking YES"),
            ("delay_between_loops", "Delay between loops")
        ]
        for key, label in delays:
            frame = ctk.CTkFrame(self.tab_settings, fg_color="transparent")
            frame.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(frame, text=label).pack(side="left")
            entry = ctk.CTkEntry(frame, width=80)
            entry.pack(side="right")
            entry.insert(0, str(self.config.get(key, 0.5)))
            self.delay_entries[key] = entry

        # ---- WEBHOOK TAB ----
        ctk.CTkLabel(self.tab_webhook, text="Discord Webhook URL", font=("Arial", 14, "bold")).pack(pady=5)
        self.default_webhook_entry = ctk.CTkEntry(self.tab_webhook, placeholder_text="https://discord.com/api/webhooks/...", width=350)
        self.default_webhook_entry.pack(padx=20, pady=10)
        self.default_webhook_entry.insert(0, self.config.get("default_webhook", ""))
        self.test_webhook_btn = ctk.CTkButton(self.tab_webhook, text="Test Webhook", command=self.test_webhook)
        self.test_webhook_btn.pack(pady=10)

    # ---------------- LOGIC REMAINS SAME AS ORIGINAL ----------------
    def smooth_move(self, target_x, target_y, duration=0.3):
        if not self.running: return
        start_x, start_y = pydirectinput.position()
        steps = 20
        for i in range(steps + 1):
            t = i / steps
            f = -(math.cos(math.pi * t) - 1) / 2
            curr_x = int(start_x + (target_x - start_x) * f)
            curr_y = int(start_y + (target_y - start_y) * f)
            pydirectinput.moveTo(curr_x, curr_y)
            time.sleep(duration / steps)

    def action_smooth(self, x, y, post_pause=0.8):
        if not self.running: return
        self.smooth_move(x, y)
        time.sleep(0.1)
        pydirectinput.click()
        time.sleep(post_pause)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    self.config.update(json.load(f))
            except: pass

    def save_config(self):
        self.config["selected_stats"] = [name for name, cb in self.checkboxes.items() if cb.get()]
        self.config["default_webhook"] = self.default_webhook_entry.get()
        self.config["stop_at_6"] = self.stop6_checkbox.get()
        for key, entry in self.delay_entries.items():
            try: self.config[key] = float(entry.get())
            except ValueError: pass
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)

    def log(self, msg):
        self.log_box.insert("end", f"> {msg}\n")
        self.log_box.see("end")

    def update_preview(self, img_np):
        img = Image.fromarray(img_np)
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(250, 120))
        self.image_label.configure(image=ctk_img, text="")

    def send_webhook(self, matches, required, img_np, found_stats):
        url = self.config["default_webhook"]
        if not url or "discord.com" not in url: return
        try:
            img = Image.fromarray(img_np)
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            data = {
                "content": "🐝 **BSS AMULET HIT!** @everyone",
                "embeds": [{
                    "title": "Amulet FOUND!",
                    "description": f"Stats: **{matches}/{required}**\nRolls: **{self.config['total_rolls']}**\n\n**Stats Found:**\n{', '.join(found_stats)}",
                    "color": 0x00ff99,
                    "footer": {"text": "BSM AMULET ROLLER"}
                }]
            }
            files = {"file": ("amulet.png", buffer, "image/png")}
            requests.post(url, data={"payload_json": json.dumps(data)}, files=files)
        except Exception as e: self.log(f"Webhook failed: {e}")

    def test_webhook(self):
        self.save_config()
        url = self.config["default_webhook"]
        if not url: return
        try:
            requests.post(url, json={"content": "✅ Webhook test successful!"})
            self.log("Test message sent.")
        except Exception as e: self.log(f"Test failed: {e}")

    def macro_loop(self):
        targets = []
        for name in self.config["selected_stats"]:
            if name in self.stat_map: targets.append(self.stat_map[name])
            else: targets.append(name.lower())
        required_count = len(targets)
        if required_count == 0:
            self.log("ERROR: No stats selected!")
            self.running = False
            return
        
        while self.running:
            self.config["total_rolls"] += 1
            self.roll_label.configure(text=f"Rolls: {self.config['total_rolls']}")
            pydirectinput.press('e')
            time.sleep(self.config.get("delay_after_e_press", 1.0))
            time.sleep(self.config.get("delay_before_click_yes", 2.5))
            self.action_smooth(self.config["yes_pos"][0], self.config["yes_pos"][1], 
                               post_pause=self.config.get("delay_after_click", 2.5))
            try:
                ss = pyautogui.screenshot(region=self.config["scan_region"])
                img_np = np.array(ss)
                self.update_preview(img_np)
                gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
                result = self.reader.readtext(gray, detail=0)
                text_found = " ".join(result).lower()
                matches_found = 0
                found_list = []
                wanted_passives = [p for p in self.passives if self.checkboxes[p].get()]


                for t in targets:
                    # Specific fix for the base "Pollen" stat
                    if t == "pollen":
                        # This regex ensures 'pollen' is NOT preceded by white, red, blue, or 'from bees'
                        # It accounts for potential multiple spaces or newlines between words
                        pattern = r'(?<!white\s)(?<!red\s)(?<!blue\s)(?<!from\sbees\s)\bpollen\b'
                        if re.search(pattern, text_found):
                            # Double check: if "pollen" is found, make sure it's not part of the other stats
                            if not any(x in text_found for x in ["white pollen", "red pollen", "blue pollen", "pollen from bees"]):
                                matches_found += 1
                                found_list.append(t)
                            elif text_found.count("pollen") > (("white pollen" in text_found) + ("red pollen" in text_found) + ("blue pollen" in text_found) + ("pollen from bees" in text_found)):
                                # If 'pollen' appears more times than the specific colored variants, 
                                # then the base 'pollen' stat must also be present.
                                matches_found += 1
                                found_list.append(t)
                    else:
                        # Standard matching for everything else
                        pattern = r'\b' + re.escape(t) + r'\b'
                        if re.search(pattern, text_found):
                            matches_found += 1
                            found_list.append(t)




                self.log(f"FOUND: {found_list}, {matches_found}/{required_count}")
                all_passives_hit = all(p.lower() in text_found for p in wanted_passives)
                if all_passives_hit and (matches_found >= required_count or (self.config["stop_at_6"] and matches_found >= 6)):
                    self.log("TARGET REACHED!")
                    self.send_webhook(matches_found, required_count, img_np, found_list)
                    self.running = False
                    import winsound
                    winsound.Beep(1200, 2500)
                    break
            except Exception as e: self.log(f"OCR Error: {e}")
            time.sleep(self.config.get("delay_between_loops", 0.5))

    def start_macro(self):
        if not self.running:
            self.save_config()
            self.running = True
            self.log("Macro Started.")
            threading.Thread(target=self.macro_loop, daemon=True).start()

    def stop_macro(self):
        self.running = False
        self.log("Macro Stopped.")

if __name__ == "__main__":
    app = BeeMacroGUI()
    app.mainloop()

