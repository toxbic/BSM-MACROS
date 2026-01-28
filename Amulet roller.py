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
from PIL import Image
import re  # for whole-word matching
import webbrowser
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")


class BeeMacroGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("BSM AMULET ROLLER By Toxbic")
        self.geometry("500x800")
        self.attributes('-topmost', True)

        self.reader = easyocr.Reader(['en'])
        self.running = False

        # Stat mapping
        self.stat_map = {
            "Pollen": "pollen",
            "White Pollen": "white pollen",
            "Red Pollen": "red pollen",
            "Blue Pollen": "blue pollen",
            "pollen from bees": "pollen from bees",
            "Instant Conversion": "instant conversion",
            "Convert Rate": "convert rate",
            "Bee Ability Rate": "ability rate",
            "Critical Chance": "critical"
        }

        self.passives = ["Star Saw", "Scorching Star", "Gummy Star", "Pop Star", "Guiding Star", "Shower"]

        # Config with delays
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

    # ---------------- CONFIG ----------------
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    self.config.update(json.load(f))
            except:
                pass

    def save_config(self):
        self.config["selected_stats"] = [name for name, cb in self.checkboxes.items() if cb.get()]
        self.config["default_webhook"] = self.default_webhook_entry.get()
        self.config["stop_at_6"] = self.stop6_checkbox.get()

        # Save delays from entries
        for key, entry in self.delay_entries.items():
            try:
                self.config[key] = float(entry.get())
            except ValueError:
                pass  # Keep old value if invalid input

        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)

    # ---------------- UI ----------------
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

        btn_frame = ctk.CTkFrame(self.tab_main, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkButton(btn_frame, text="Set 'Yes'", command=self.set_yes_location).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(btn_frame, text="Set Box", command=self.set_scan_region).pack(side="right", expand=True, padx=5)

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

        # ---- STATS TAB ----
        self.scroll_frame = ctk.CTkScrollableFrame(self.tab_stats, label_text="Select Wanted Stats")
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
        self.stop6_checkbox = ctk.CTkCheckBox(self.tab_settings, text="Stop macro at 6/7")
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

    # ---------------- UTILS ----------------
    def log(self, msg):
        self.log_box.insert("end", f"> {msg}\n")
        self.log_box.see("end")

    def set_yes_location(self):
        self.log("Hover mouse over 'YES' for 3 seconds...")
        self.after(3000, self._finish_set_yes)

    def _finish_set_yes(self):
        pos = pyautogui.position()
        self.config["yes_pos"] = [pos.x, pos.y]
        self.save_config()
        self.log(f"Yes Position Set: {pos.x}, {pos.y}")

    def set_scan_region(self):
        self.log("Click Top-Left of stats in 3s...")
        self.after(3000, self._step_2_region)

    def _step_2_region(self):
        self.p1 = pyautogui.position()
        self.log("Click Bottom-Right of stats in 3s...")
        self.after(3000, self._finish_region)

    def _finish_region(self):
        p2 = pyautogui.position()
        self.config["scan_region"] = [self.p1.x, self.p1.y, p2.x - self.p1.x, p2.y - self.p1.y]
        self.save_config()
        self.log("Scan Region Saved.")

    def update_preview(self, img_np):
        img = Image.fromarray(img_np)
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(250, 120))
        self.image_label.configure(image=ctk_img, text="")

    # ---------------- WEBHOOK ----------------
    def send_webhook(self, matches, required, img_np, found_stats):
        url = self.config["default_webhook"]
        if not url or "discord.com" not in url:
            self.log("Webhook Error: Geen geldige URL.")
            return

        try:
            img = Image.fromarray(img_np)
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            data = {
                "content": "🐝 **BSS MACRO HIT!** @everyone",
                "embeds": [{
                    "title": "Amulet FOUND!",
                    "description": f"Stats: **{matches}/{required}**\nRolls: **{self.config['total_rolls']}**\n\n**Gevonden Stats:**\n{', '.join(found_stats)}",
                    "color": 0x00ff99,
                    "footer": {"text": "BSM AMULET ROLLER, https://discord.gg/s9jSwPYv"}
                }]
            }

            files = {"file": ("amulet.png", buffer, "image/png")}
            response = requests.post(url, data={"payload_json": json.dumps(data)}, files=files)
            if response.status_code in [200, 204]:
                self.log("Webhook succesvol verzonden!")
            else:
                self.log(f"Webhook Error: {response.status_code}")
        except Exception as e:
            self.log(f"Webhook fout: {e}")

    def test_webhook(self):
        self.save_config()
        url = self.config["default_webhook"]
        if not url:
            self.log("Vul eerst een webhook URL in!")
            return
        try:
            requests.post(url, json={"content": "✅ Webhook test succesvol!"})
            self.log("Testbericht verzonden naar Discord.")
        except Exception as e:
            self.log(f"Test mislukt: {e}")

    # ---------------- MACRO ----------------
    def macro_loop(self):
        targets = []
        for name in self.config["selected_stats"]:
            if name in self.stat_map:
                targets.append(self.stat_map[name])
            else:
                targets.append(name.lower())

        required_count = len(targets)
        if required_count == 0:
            self.log("ERROR: Geen stats geselecteerd!")
            self.running = False
            return

        self.log(f"Zoeken naar {required_count} stats...")

        while self.running:
            self.config["total_rolls"] += 1
            self.roll_label.configure(text=f"Rolls: {self.config['total_rolls']}")

            pydirectinput.press('e')
            time.sleep(self.config.get("delay_after_e_press", 1.0))

            time.sleep(self.config.get("delay_before_click_yes", 2.5))
            pydirectinput.click(self.config["yes_pos"][0], self.config["yes_pos"][1])
            time.sleep(self.config.get("delay_after_click", 2.5))

            try:
                ss = pyautogui.screenshot(region=self.config["scan_region"])
                img_np = np.array(ss)
                self.update_preview(img_np)

                gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
                result = self.reader.readtext(gray, detail=0)
                text_found = " ".join(result).lower()

                matches_found = 0
                found_stats = []
                found_list = []
# --- VERBETERDE MATCHING LOGICA ---
                matches_found = 0
                found_list = []
# --- VERBETERDE MATCHING LOGICA MET VERPLICHTE PASSIVES ---
                matches_found = 0
                found_list = []
                
                # We maken een lijstje van welke passives je ECHT wilde hebben
                wanted_passives = [p for p in self.passives if self.checkboxes[p].get()]
                
                for t in targets:
                    if t == "pollen":
                        # Je 'Pollen' fix van net
                        pattern = r'(?<!white\s)(?<!red\s)(?<!blue\s)\bpollen\b'
                    else:
                        pattern = r'\b' + re.escape(t) + r'\b'
                    
                    if re.search(pattern, text_found):
                        matches_found += 1
                        found_list.append(t)

                # CHECK: Zitten alle geselecteerde passives in de gevonden lijst?
                all_passives_hit = all(p.lower() in found_list for p in wanted_passives)

                self.log(f"Match: {matches_found}/{required_count}, FOUND: {found_list}")

                # De macro stopt nu pas als de passives erbij zitten EN het aantal klopt
                if all_passives_hit and (matches_found >= required_count or (self.config["stop_at_6"] and matches_found >= 6) or matches_found==7):
                    self.log("TARGET BEREIKT! (Passives + Stats OK)")
                    self.send_webhook(matches_found, required_count, img_np, found_list)
                    self.running = False
                    import winsound
                    winsound.Beep(1200, 2500)
                    break
                elif not all_passives_hit and matches_found >= 6:
                    self.log("Skip: enough stats, but missing Passive.")

            except Exception as e:
                self.log(f"OCR Error: {e}")

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
