# RHUL Attendance Bot
[中文](https://github.com/PandaQuQ/RHUL_attendance_bot/blob/main/README_CN.md)
---

The RHUL Attendance Bot automates attendance marking for Royal Holloway students by using web automation. The script checks your calendar events, triggers attendance based on specified conditions, and provides real-time logging using Rich library for better visualization.
![alt text]({8BA55B13-C622-4EB4-93F2-964AF83C7A9E}.png)
## Features

- **Automated Attendance**: Automatically opens the attendance page and marks your attendance based on your calendar events.
- **Manual Trigger**: Allows manual attendance marking via keyboard shortcuts.
- **Real-Time Logging**: Displays logs using Rich library for a better visual experience.
- **Environment and Dependency Checks**: Ensures the script is run in the proper environment and all dependencies are installed.
- **System Time Synchronization Check**: Checks if the system time is synchronized with the NTP server.
- **Auto-Update Feature**: Detects script updates and prompts the user to update.

## Prerequisites

1. **Python 3.9 or above**: Ensure that Python is installed. If not, download and install it from [python.org](https://www.python.org/downloads/).
2. **Google Chrome Browser**: The script uses Chrome for web automation. Make sure it is installed.
3. **Virtual Environment (Recommended)**: Run the script inside a Python virtual environment to avoid dependency conflicts.

## Installation

1. **Clone the Repository**:

    ```bash
    git clone https://github.com/PandaQuQ/RHUL_attendance_bot.git
    cd RHUL_attendance_bot
    ```

2. **Set Up a Virtual Environment** (Recommended):

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use: venv\Scripts\activate
    ```

3. **Install Dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

## Usage

1. **Prepare Your Calendar File**:

   - Place a single `.ics` file containing your event schedule in the `ics` folder located in the script's root directory.

2. **Run the Script**:

   ```bash
   python main.py
   ```

3. **Keyboard Shortcuts**:

   - **Manually Trigger the Next Event**: Press `[`, then `]`.
   - **Exit the Script**: Press `[`, then `q`.

4. **First-Time Login**: The first time you run the script, you may need to manually trigger attendance to log in.

## Important Notes

- **Dependencies**: Make sure all required dependencies are installed by following the instructions in the `requirements.txt` file.
- **Virtual Environment**: Using a virtual environment is highly recommended to avoid conflicts with global packages.
- **System Time**: If the system time is not synchronized with the NTP server, the script will prompt you to synchronize your system clock.
- **Supported Platforms**: The script supports Windows, macOS, and Linux.

## Configuration

To configure the script, modify the relevant parameters inside the code or create a configuration file (not provided in this version). Future versions may include more flexible configuration options.

## Updating

If an update is detected, the script will prompt you to update. You can choose to update by typing `y` or skip it by typing `n`.

## Troubleshooting

1. **Chrome WebDriver Issues**: Make sure that the correct version of the ChromeDriver is being used. The script uses `webdriver-manager` to automatically manage ChromeDriver versions.
2. **Dependency Issues**: If you encounter errors related to missing modules, ensure you have installed all dependencies listed in `requirements.txt`.
3. **Virtual Environment Issues**: If you face issues while running the script, try setting up a fresh virtual environment and reinstalling the dependencies.

## License

This project is licensed under the MIT License with an additional clause. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Thanks to the developers of [Rich](https://github.com/Textualize/rich), [Selenium](https://www.selenium.dev/), and [ics.py](https://github.com/C4ptainCrunch/ics.py) for their amazing libraries.

## Contact

For questions or suggestions, please reach out via the [GitHub repository](https://github.com/PandaQuQ/RHUL_attendance_bot). We welcome feedback and contributions!
