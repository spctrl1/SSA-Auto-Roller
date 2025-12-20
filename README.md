# SSA-Auto-Roller

A custom Python automation tool for rolling Supreme Star Amulets (SSA). I originally built this for personal use and friends, but I am releasing it publicly for anyone who needs it.

## ⚠️ Important: Virus & Safety Warning
Because I am an independent developer and not a large company, I cannot afford the expensive digital certificates required by Microsoft.

* **Windows Defender may flag this file as a virus.** This is a known "false positive" that happens with almost all Python scripts compiled into `.exe` files (PyInstaller).
* **The code is open source.** If you are uncomfortable running the `.exe`, you can view all the source code in this repository and run the raw `AutoSsaRoller.py` file yourself (requires Python + Tesseract installed).

## 🛠️ Why is the file so big?
Unlike simple AutoHotkey (AHK) macros that just check for pixel colors, this tool uses **Tesseract OCR** (Optical Character Recognition).
* It actually *reads* the text on your screen to ensure 100% accuracy.
* The large file size is because the entire Tesseract engine is bundled inside the app so you don't have to install it manually.

## 📥 How to Install & Use
1.  Go to the **Releases** section on the right and download `SSA_Roller.zip`.
2.  **CRITICAL:** Right-click the downloaded zip and select **Extract All**.
3.  Open the extracted folder and run `SSA_Roller.exe`.
4.  If Windows prevents startup, click **More Info** -> **Run Anyway**.
5. Make sure you are on 100% Display scale HD or FHD.

## 📞 Support
If you have issues or bugs, DM me on Discord: **spctrl**
