# SSA Auto Roller [[Check Releases to Install](https://github.com/spctrl1/SSA-Auto-Roller/releases/latest)]

[![Download](https://img.shields.io/github/v/release/spctrl1/SSA-Auto-Roller?label=Download&style=for-the-badge)](https://github.com/spctrl1/SSA-Auto-Roller/releases/latest)

A custom Python automation tool for rolling Supreme Star Amulets (SSA). I originally built this for personal use and friends, but I am releasing it publicly for anyone who needs it. 

[Note: built for 1080p -> 1440p; you can try using it with 4K but i have not tested it.]

[To roll single passives, simply select no passives or one passive on the target amulet.]

## How to Install & Use
1.  Go to the **Releases** section on the right and download `AutoSsaRoller.exe`.
3.  run `AutoSsaRoller.exe`.
4.  If Windows prevents startup, click **More Info** -> **Run Anyway**.
5


## Important: Virus & Safety Warning
Im not paying to get this certified by Microsoft so you will receive a warning when you unzip/run the program.

* **Windows Defender may flag this file as a virus.** This is a known "false positive" that happens with almost all Python scripts compiled into `.exe` files (PyInstaller).
* **The code is open source.** If you are uncomfortable running the `.exe`, you can view all the source code in this repository and run the raw `AutoSsaRoller.py` file yourself (requires Python 3.11.9 + RapidOCRAuto installed).

## Prerequisites
* **Display Scale:** Windows settings **must** be set to **100%** [If you are on 4K you may need to use different settings].
* **Roblox Settings:**
    * Mode: **Fullscreen** or **Windowed Fullscreen**.
* **In-Game Position:** Stand directly in front of the Supreme Star Amulet generator so the GUI is clearly visible on screen.

### 1. Calibration (First Time Setup)
Expand the **Macro Config** section at the bottom of the tool.

* **Set Click Points:**
    1. Click the **Show Points** button.
    2. Adjust the sliders for `No (10B)` and `Yes (500B)` until the red and green dots align perfectly with the "No" and "Yes" buttons.
* **Set OCR Area:**
    1. Manually generate one amulet so the stats are visible on your screen.
    2. Click the **Show Box** button.
    3. Adjust the `X, Y, W, H` sliders until the **Red Box** perfectly covers the text of the **New Amulet** (the one on the right side).

### 2. Configure Targets
* Click **+ Add Amulet** to add a new target profile (you can have multiple).
* **Passives:** Check the passives you want (Max 2).
* **Stats:** Check the stats you require.
    * Input the **minimum percentage** needed (e.g., enter `45` for 45% minimum stat value; The Entered value is also counted).
    * Leave the value as `0` if you want the stat but don't care about the percentage.

### 3. Test & Run
* **Test OCR (F3):** Press **F3** while an amulet is on screen. Check the "Detected Stats" log at the bottom.
    * *Note:* If the log shows `[None]`, your OCR Area needs to be adjusted.
* **Start (F1):** Press **F1** to begin auto-rolling.
* **Stop (F2):** Press **F2** to stop the macro immediately.

## Why is the file so big?
Unlike simple AutoHotkey (AHK) macros that just check for pixel colors, this tool uses **RapidOCRAuto** (Optical Character Recognition).
* It actually reads the text on your screen to ensure 100% accuracy.
* The large file size is because the entire ONNX engine & Rapid Library is bundled inside the app so you don't have to install it manually.

---

<img width="619" height="955" alt="image" src="https://github.com/user-attachments/assets/d4ab94e6-e3b6-4b11-8d97-4487dd82f330"/>

---

## Support
If you have issues or bugs, DM me on Discord: **spctrl**
