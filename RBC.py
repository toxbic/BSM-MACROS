import customtkinter as ctk
import threading
import easyocr
import pydirectinput
import time
import numpy as np
import math
import webbrowser
from PIL import ImageGrab

# Set a tiny pause to prevent "doubled" inputs, but keep it fast
pydirectinput.PAUSE = 0.01 

class RoboBearDefinitive(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.reader = easyocr.Reader(['en'])
        self.running = False
        self.digital_bee = 0
        self.round_counter = 0  # Track rounds
        self.drives_bought = 0
        # YOUR EXACT LIST
        self.fixed_clicks = [
            (1004, 142), (933, 748), (933, 748),
            (933, 748), (933, 748), (933, 748), (1083, 459)
        ]
        
        self.drive_buy_xy = (897, 836)      
        self.drive_next_xy = (1106, 820)    
        
        self.setup_ui()

    def setup_ui(self):
        self.title("RBC Macro - Made by Toxbic")
        self.geometry("300x600")
        self.attributes("-topmost", True)

        ctk.CTkLabel(self, text="ROBO BEAR MACRO By Toxbic", font=("Arial", 20, "bold")).pack(pady=(20, 5))
        
        selection_frame = ctk.CTkFrame(self)
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
        
        self.log_box = ctk.CTkTextbox(self, height=200)
        self.log_box.pack(pady=10, padx=20, fill="both")

        ctk.CTkButton(self, text="START Macro", fg_color="green", height=45, font=("Arial", 14, "bold"), command=self.start).pack(pady=5, fill="x", padx=20)
        ctk.CTkButton(self, text="STOP", fg_color="red", height=40, command=self.stop).pack(pady=5, fill="x", padx=20)
        ctk.CTkButton(self, text="JOIN DISCORD", fg_color="#7289da", command=self.open_discord).pack(pady=10, fill="x", padx=20)

    def log(self, msg):
        self.log_box.insert("end", f"> {msg}\n"); self.log_box.see("end")

    def open_discord(self):
        webbrowser.open("https://discord.gg/s9jSwPYv")

    def stop(self): self.running = False

    def start(self):
        if not self.running:
            self.running = True
            self.log("Starting sequence...")
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
        pydirectinput.moveRel(1, 0)
        pydirectinput.moveRel(-1, 0)
        time.sleep(0.1) 
        pydirectinput.mouseDown()
        time.sleep(0.05)
        pydirectinput.mouseUp()
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
        self.log("Jumping in corner...")
        pydirectinput.keyDown('space'); time.sleep(0.1); pydirectinput.keyUp('space')
        pydirectinput.keyDown('w'); time.sleep(1.8); pydirectinput.keyUp('w')
        pydirectinput.keyDown('d'); time.sleep(1); pydirectinput.keyUp('d')
        pydirectinput.keyDown('space'); time.sleep(0.1); pydirectinput.keyUp('space')
        pydirectinput.keyDown('d'); time.sleep(0.3); pydirectinput.keyUp('d')
        time.sleep(1)
        pydirectinput.keyDown('e'); time.sleep(1); pydirectinput.keyUp('e')

    def buy_4_different_drives(self):

        self.drives_bought = self.drives_bought +1
        time.sleep(1)
        self.action_smooth(1855, 601, post_pause=0.5)
        self.action_smooth(841, 587, post_pause=0.5)



        pydirectinput.keyDown('e'); time.sleep(1); pydirectinput.keyUp('e')

        time.sleep(1)

        drive_selection = [
            ("Red", self.buy_red.get()), ("White", self.buy_white.get()),
            ("Blue", self.buy_blue.get()), ("Glitched", self.buy_glitched.get())
        ]
        items_bought = 0
        self.log("Round 1: Priority buying...")
        for i, (name, active) in enumerate(drive_selection):
            if not self.running: return
            if active:
                self.action_smooth(self.drive_buy_xy[0], self.drive_buy_xy[1], post_pause=0.4)
                items_bought += 1
            self.action_smooth(self.drive_next_xy[0], self.drive_next_xy[1], post_pause=0.3)
        self.action_smooth(self.drive_next_xy[0], self.drive_next_xy[1], post_pause=0.3)
        if items_bought < 4 and self.running:
            for i, (name, active) in enumerate(drive_selection):
                if items_bought >= 4 or not self.running: break
                if not active:
                    self.action_smooth(self.drive_buy_xy[0], self.drive_buy_xy[1], post_pause=0.4)
                    items_bought += 1
                self.action_smooth(self.drive_next_xy[0], self.drive_next_xy[1], post_pause=0.3)
        pydirectinput.keyDown('e'); time.sleep(1); pydirectinput.keyUp('e')
        pydirectinput.keyDown('a'); time.sleep(0.5); pydirectinput.keyUp('a')
        pydirectinput.keyDown('d'); time.sleep(0.5); pydirectinput.keyUp('d')

    def use_drives(self):
                
                if self.digital_bee == 1 and self.running:
                 for key in ['4', '5', '6', '7']:
                    for _ in range(6):
                        if not self.running: break
                        pydirectinput.press(key); time.sleep(1)
                self.digital_bee= 0
                        
    def scan_bee(self):
        region = (632, 351, 625, 326)
        bbox = (region[0], region[1], region[0] + region[2], region[1] + region[3])
        try:
            screenshot = np.array(ImageGrab.grab(bbox=bbox))
            results = self.reader.readtext(screenshot)
            for (bbox_int, text, prob) in results:
                if "digital" in text.lower():
                    mx = region[0] + (bbox_int[0][0] + bbox_int[2][0]) / 2
                    my = region[1] + (bbox_int[0][1] + bbox_int[2][1]) / 2
                    self.digital_bee = 1
                    return int(mx), int(my) # Gevonden!
        except: pass
        
        # DE FIX: Als hij niks vindt, geef de standaard klikplek terug
        # Zo krijgt bx, by altijd cijfers en crasht je script niet.
        return 0,0

    def main_loop(self):
        self.log("Ready. Start in 3s...")
        time.sleep(3)
        
        while self.running:
            # 1. EERSTE KEER LOPEN (gebeurt alleen bij start of na een echte win)
            self.walk_to_bear_original()

            # --- DIT IS DE INNER LOOP ---
            # Deze loop blijft bij de beer zolang je in searching_mode zit
            while self.running:
                searching_mode = (self.round_counter >= 10)

                # A. Menu openen (Fixed clicks)
                if self.running:
                    for x, y in self.fixed_clicks:
                        self.action_smooth(x, y, post_pause=0.3)
                
                # B. Scannen en refreshen
                if self.running and searching_mode:
                    for i in range(3):
                        if not self.running: break
                        
                        # We slaan de resultaten van de scan op in 'coords'
                        bx, by = self.scan_bee() 
                        
                        if bx> 0: # Als coords niet None is (Digital Bee gevonden)
                            self.log("Digital Bee detected! Clicking now...")
                            # KLIK DIRECT op de coördinaten van de bij
                            self.action_smooth(bx, by, post_pause=0.5)
                            
                            # Zet de flag zodat we weten dat we hem hebben
                            self.digital_bee = 1 
                            search_mode = 0
                            self.round_counter = -1
                            break
                           
                        else:
                            if i < 2:
                                self.log(f"Refreshing... ({i+1}/5)")
                                self.action_smooth(814, 827, post_pause=0.6)
                
                time.sleep(0.5)

                # C. Bijen kiezen (altijd de 2 bovenste slots als fallback/flow)
                if self.running:
                    self.log("Selecting 2 top bees...")
                    self.action_smooth(638, 500, post_pause=0.5)
                    self.action_smooth(956, 399, post_pause=0.5)
                    if self.digital_bee ==0:
                     bx, by = self.scan_bee()
                     if bx > 0:
                         self.action_smooth(bx,by, post_pause=0.5)
                         self.digital_bee = 1
                         searching_mode = 0

                         
                         

                     else:
                      self.action_smooth(956, 399, post_pause=0.5)
                    
                    # D. Accepteren
                    self.action_smooth(1094, 827, post_pause=0.8) 

                # E. SKIP LOGIC: Moeten we resetten en opnieuw?
                if self.running and self.round_counter >=10:
                    self.log("Resetting via UI clicks...")
                    self.action_smooth(1855, 601, post_pause=0.5)
                    self.action_smooth(841, 587, post_pause=0.5)
                    
                    # HIER IS DE FIX: In plaats van de loop te eindigen, 
                    # drukken we op E en blijven we in deze 'while' loop.
                    self.log("Skipping walk, talking to bear again...")
                    time.sleep(3)
                    pydirectinput.press('e')
                    time.sleep(1.5)
                    continue # Gaat direct terug naar 'A. Menu openen'
                
                # Als searching_mode uit is, breekt hij uit de inner loop om te gaan lopen/shoppen
                break 


            # 2. SHOPPEN EN LOPEN (gebeurt alleen als searching_mode klaar of uit is)
            if self.running and not (self.round_counter >= 10):
                self.log(self.drives_bought)
                self.use_drives()
                self.walk_to_drive_reversed()
                self.buy_4_different_drives()
                self.round_counter += 1
                self.log(f"Round {self.round_counter} done.")
                time.sleep(5)

if __name__ == "__main__":
    app = RoboBearDefinitive(); app.mainloop()
