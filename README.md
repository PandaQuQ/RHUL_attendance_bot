
# RHUL Attendance Bot

[中文](https://github.com/PandaQuQ/RHUL_attendance_bot/blob/main/README_CN.md)

## Overview

`RHUL_attendance_bot.py` is an automation script that automatically marks attendance based on events from an `.ics` calendar file for Royal Holloway, University of London (RHUL). The script uses the `webdriver_manager` to automatically manage the Chrome WebDriver, and logs its operations using the `rich` library for live console updates.

The script supports key features like:
- Automatic attendance marking based on your calendar.
- Auto-management of ChromeDriver.
- Real-time log display using `rich`.
- Manual triggering of automation using keyboard shortcuts.

## **Requirements**

1. **Python**: 3.6 or above.
2. **Google Chrome**: The script uses Selenium for browser automation, so Chrome must be installed on your system.

## **Installation and Setup**

### **Step 1: Clone the repository**

```bash
git clone https://github.com/PandaQuQ/RHUL_attendance_bot.git
cd RHUL_attendance_bot
```

### **Step 2: Set up a virtual environment**

```bash
python -m venv venv
venv\Scripts\activate  # On Windows
# OR
source venv/bin/activate  # On macOS/Linux
```

### **Step 3: Install dependencies**

```bash
pip install -r requirements.txt
```

### **Step 4: Place your `.ics` file**

Place your `.ics` calendar file in the `ics` folder inside the project directory.

### **Step 5: Run the script**

```bash
python RHUL_attendance_bot.py
```

### **Step 6: Optional: Build as an executable (for Windows)**

To create an executable version of this script:

```bash
pyinstaller --onefile --noconsole --add-data "ics;ics" RHUL_attendance_bot.py
```

The executable will be available in the `dist` folder.

## **Usage**

- The script automatically detects events in the `.ics` file and performs attendance marking.
- Real-time log messages are displayed in the console.
- You can manually trigger the automation by pressing the `[ ]` keys together.
- The logs will be stored in `automation.log`.

## **Logs**

- The script maintains a log of all operations in `automation.log`.
- The live log display updates every second, showing real-time progress.

## **Important Notes**

- Ensure that Google Chrome is installed and up-to-date.
- The script uses the `webdriver_manager` package to automatically manage the ChromeDriver, so it will download the correct version based on your Chrome browser.
