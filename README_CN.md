
# RHUL 签到机器人

[English](https://github.com/PandaQuQ/RHUL_attendance_bot/blob/main/README.md)

## 概述

`RHUL_attendance_bot.py` 是一个用于英国皇家霍洛威大学 (RHUL) 的自动签到脚本，该脚本基于 `.ics` 日历文件中的事件进行自动签到。脚本使用 `webdriver_manager` 自动管理 Chrome WebDriver，并通过 `rich` 库实时记录日志信息。

脚本的主要功能包括：
- 基于您的日历自动签到。
- 自动管理 ChromeDriver。
- 使用 `rich` 实时显示日志信息。
- 通过键盘快捷键手动触发自动化操作。

## **运行环境要求**

1. **Python**：版本 3.6 或更高。
2. **Google Chrome**：脚本使用 Selenium 进行浏览器自动化操作，因此需要在系统中安装 Chrome。

## **安装与配置**

### **步骤 1: 克隆仓库**

```bash
git clone https://github.com/PandaQuQ/RHUL_attendance_bot.git
cd RHUL_attendance_bot
```

### **步骤 2: 设置虚拟环境**

```bash
python -m venv venv
venv\Scripts\activate  # Windows
# 或
source venv/bin/activate  # macOS/Linux
```

### **步骤 3: 安装依赖包**

```bash
pip install -r requirements.txt
```

### **步骤 4: 放置您的 `.ics` 文件**

将您的 `.ics` 日历文件放置在项目目录下的 `ics` 文件夹内。

### **步骤 5: 运行脚本**

```bash
python RHUL_attendance_bot.py
```

### **步骤 6: 可选：生成可执行文件（适用于 Windows）**

如果想将脚本打包为可执行文件：

```bash
pyinstaller --onefile --noconsole --add-data "ics;ics" RHUL_attendance_bot.py
```

生成的可执行文件会保存在 `dist` 文件夹中。

## **使用说明**

- 脚本会自动检测 `.ics` 文件中的事件，并进行签到。
- 实时的日志信息会显示在控制台中。
- 您可以通过同时按下 `[ ]` 键手动触发签到操作。
- 所有日志会保存在 `automation.log` 文件中。

## **日志记录**

- 脚本会将所有操作日志保存在 `automation.log` 文件中。
- 实时日志显示每秒更新一次，提供当前操作进度。

## **重要注意事项**

- 确保已安装并更新 Google Chrome 浏览器。
- 脚本使用 `webdriver_manager` 包自动管理 ChromeDriver，会根据您系统中的 Chrome 浏览器版本自动下载相应的驱动程序。
