# RHUL 自动签到脚本
[English](https://github.com/PandaQuQ/RHUL_attendance_bot/blob/main/README.md)
---
RHUL 自动签到脚本通过使用网页自动化来为 Royal Holloway 学生自动签到。该脚本根据日历事件检查并触发签到操作，并使用 Rich 库进行实时日志记录，提供更好的可视化体验。

## 功能

- **自动签到**：根据日历事件自动打开签到页面并进行签到。
- **手动触发**：允许通过快捷键手动触发签到操作。
- **实时日志记录**：使用 Rich 库显示日志，提供更好的视觉效果。
- **环境和依赖检查**：确保脚本在正确的环境中运行并安装了所有依赖项。
- **系统时间同步检查**：检查系统时间是否与 NTP 服务器同步。
- **自动更新功能**：检测脚本更新并提示用户更新。

## 前提条件

1. **Python 3.9 或以上**：确保已安装 Python。如果没有，请从 [python.org](https://www.python.org/downloads/) 下载并安装。
2. **Google Chrome 浏览器**：脚本使用 Chrome 进行网页自动化，请确保已安装 Chrome 浏览器。
3. **虚拟环境（推荐）**：在 Python 虚拟环境中运行脚本以避免依赖冲突。

## 安装

1. **克隆代码仓库**：

    ```bash
    git clone https://github.com/PandaQuQ/RHUL_attendance_bot.git
    cd RHUL_attendance_bot
    ```

2. **设置虚拟环境**（推荐）：

    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows 系统使用: venv\Scripts\activate
    ```

3. **安装依赖项**：

    ```bash
    pip install -r requirements.txt
    ```

## 使用说明

1. **准备您的日历文件**：

   - 将包含日程安排的 `.ics` 文件放置在脚本根目录的 `ics` 文件夹中。

2. **运行脚本**：

   ```bash
   python main.py
   ```

3. **快捷键说明**：

   - **手动触发下一个事件**：按下 `[`, 然后按 `]`。
   - **退出脚本**：按下 `[`, 然后按 `q`。

4. **首次登录**：首次运行脚本时，可能需要手动触发签到以完成登录。

## 注意事项

- **依赖项**：确保已根据 `requirements.txt` 文件的说明安装所有必需的依赖项。
- **虚拟环境**：强烈建议使用虚拟环境，以避免与全局包产生冲突。
- **系统时间**：如果系统时间与 NTP 服务器不同步，脚本会提示您同步系统时钟。
- **支持平台**：脚本支持 Windows、macOS 和 Linux 系统。

## 配置

要配置脚本，可以修改代码中的相关参数，或者创建配置文件（当前版本不提供）。未来版本可能会增加更灵活的配置选项。

## 更新

如果检测到更新，脚本会提示您是否更新。可以输入 `y` 更新，也可以输入 `n` 跳过更新。

## 常见问题

1. **Chrome WebDriver 问题**：确保使用的是正确版本的 ChromeDriver。脚本使用 `webdriver-manager` 自动管理 ChromeDriver 版本。
2. **依赖问题**：如果遇到缺少模块的错误，请确保已安装 `requirements.txt` 中列出的所有依赖项。
3. **虚拟环境问题**：如果运行脚本时出现问题，请尝试重新设置虚拟环境并重新安装依赖项。

## 许可证

本项目采用 MIT 许可证。有关详细信息，请参阅 [LICENSE](LICENSE) 文件。

## 鸣谢

- 感谢 [Rich](https://github.com/Textualize/rich)、[Selenium](https://www.selenium.dev/) 和 [ics.py](https://github.com/C4ptainCrunch/ics.py) 库的开发者。

## 联系方式

如有问题或建议，请通过 [GitHub 仓库](https://github.com/PandaQuQ/RHUL_attendance_bot) 联系我们。欢迎反馈和贡献！
