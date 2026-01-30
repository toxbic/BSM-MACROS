import subprocess
import sys

packages = [
    "customtkinter",
    "easyocr",
    "pydirectinput",
    "pyautogui",
    "opencv-python",
    "numpy",
    "requests",
    "Pillow",
    "torch",        # Explicitly adding the AI engine for EasyOCR
    "torchvision",
    "keyboard"# Needed for image processing in the AI engine
]

def install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

if __name__ == "__main__":
    print("Installing required packages...\n")
    for p in packages:
        try:
            install(p)
            print(f"✓ Installed {p}")
        except Exception as e:
            print(f"✗ Failed to install {p}: {e}")

    print("\nAll done!")

