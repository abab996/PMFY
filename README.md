# PMFY - 全局 AI 智能桌面翻译工具

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white" alt="Python Version" />
  <img src="https://img.shields.io/badge/UI-Windows%2011%20Fluent%20Design-0078D4?style=flat&logo=windows11&logoColor=white" alt="UI" />
  <img src="https://img.shields.io/badge/OCR-RapidOCR%20ONNX-FF6F00?style=flat" alt="OCR" />
  <img src="https://img.shields.io/badge/LLM-OpenAI%20%7C%20Anthropic%20Compatible-412991?style=flat&logo=openai&logoColor=white" alt="LLM" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg?style=flat" alt="License" />
</p>

> **PMFY** 是一款专为 Windows 11 深度定制的现代化、高颜值全局 AI 智能翻译桌面应用。融合 Fluent Design 原生视觉风格与 RapidOCR 离线文字识别引擎，支持**光标快捷轮盘**、**选区截屏原位重绘**、**全屏原位翻译**、**划词立即翻译**、**独立输入翻译工作台**与**问 AI 智能答疑**。

---

## ✨ 核心特性矩阵

### 1. 🎛️ 光标 5 方位快捷轮盘 (Radial / Pie Menu)
- **按住呼出，松开即刻执行**：在任意界面长按快捷键（默认 `Ctrl+Win+Alt`），光标所在处瞬间弹出半透明 Fluent 亚克力圆盘。
- **5 方位功能布局**：
  - ⬆️ **上方**：**🖥️ 全屏翻译**（全屏原位 OCR 重绘翻译）
  - ⬇️ **下方**：**✂️ 选区翻译**（十字准心选区截图原位翻译）
  - ⬅️ **左侧**：**⚡ 立即翻译模式切换**（一键切换划词立即弹窗 / 显示悬浮球）
  - ➡️ **右侧**：**✍️ 输入翻译工作台**（呼出独立双语输入翻译窗口）
  - ⏺️ **中心**：**✕ 取消操作**（不执行任何操作直接隐匿）
- 移动鼠标指向对应方位，扇区高亮反馈，**松开快捷键即秒级执行**。

---

### 2. ✂️ 选区截屏原位重绘翻译 (Area Snipping Translation)
- **十字准心框选**：支持全屏冻结并精准截取屏幕任意区域；
- **左键框选**：松开左键立即自动截取区域进行 RapidOCR 识别与 AI 原位重绘替换；
- **右键框选**：松开右键在选区边缘弹出确认卡片（`✨ 确认翻译此选区？`），确认后执行；
- **动态胶囊进度条 (Pill Progress HUD)**：展示 OCR 识别、AI 批量翻译与原位重绘的实时动态进度；
- **二次划词与浮动微导航栏**：翻译完成后可直接在译图上框选文字，进行 **📋 复制**、**🔍 详细翻译** 或 **🤖 问 AI**。

---

### 3. 🖥️ 全屏沉浸式原位图像翻译 (Fullscreen Viewer)
- 一键捕获当前全屏画面，调用 RapidOCR 离线提取所有文字坐标；
- AI 智能上下文连贯翻译，自动进行原背景智能修补（Inpainting）与高对比度文字原位重绘；
- 支持 **按住空格对比原图**、**鼠标滚轮缩放与右键拖拽平移**、**左键框选文字查询** 与 **顶部即时目标语言切换**。

---

### 4. ⚡ 划词“立即翻译”与“悬停翻译”双模式
- **智能防误触过滤**：基于 Windows UI Automation 原生选区嗅探与位移矢量门禁，彻底过滤原地长按与非选区手抖；
- **默认模式**：划词释放后在边缘弹出蓝色防遮挡小圆圈，鼠标悬停时弹出三合一翻译卡片；
- **立即翻译模式**：划词释放后跳过悬浮球，直接秒级弹出三合一详细翻译卡片。

---

### 5. ✍️ 独立双语输入翻译工作台 (Input Translation Studio)
- 类似 Google 翻译 / DeepL 桌面端独立工作台；
- **双向语言管理**：源语言自动识别、目标语言下拉选择与一键互换语言（`⇄`）；
- **实时 500ms 防抖翻译**：输入或修改文本时停顿 500ms 即自动发起翻译，杜绝频繁输入时的冲突；
- **多维解析联动**：同步展示【📝 译文】、【🔊 语音发音与音标/拼音】、【💡 详细释义与语法分析】、【📖 实用造句】及【🤖 问 AI】。

---

### 6. 🤖 “问 AI” 智能讨论与答疑系统 (Ask AI)
- 携带当前划词或全屏选区原文、译文与全局上下文，呼出置顶智能对话窗口；
- 支持语法难点剖析、近义表达辨析、母语级润色及多轮自由追问。

---

## 🛠️ 技术架构与依赖

| 模块 | 核心技术 | 功能说明 |
| :--- | :--- | :--- |
| **GUI 框架** | `PyQt6` + `QFluentWidgets` | 深度集成 Windows 11 Fluent Design 与亚克力磨砂半透明特效 |
| **离线 OCR** | `rapidocr-onnxruntime` | 超轻量、高速度离线文字检测与四角坐标回归 |
| **大模型客户端** | `httpx` (异步并发 / 信号量限流) | 兼容 OpenAI / Anthropic / DeepSeek / Ollama 等全系 API |
| **图像渲染** | `Pillow (PIL)` | 背景颜色主色嗅探、原位色块擦除覆盖与自适应换行排版 |
| **系统底层钩子** | `pynput` + `ctypes (Win32 API)` | 全局热键状态双向监听、UIA 选区探测与窗口强制置顶 |
| **语音与注音** | `edge-tts` / `pypinyin` / `eng-to-ipa` | 纯离线音标拼音注音与神经网络自然语音朗读 |

---

## 🚀 快速开始与使用

### 环境要求
- **操作系统**：Windows 10 / 11 (64-bit)
- **Python 版本**：Python 3.10 或更高版本

### 安装步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/your-username/PMFY.git
   cd PMFY
   ```

2. **创建并激活虚拟环境**
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **启动应用**
   - 方式一：直接双击项目根目录下的 **`启动软件.bat`**（推荐，静默常驻托盘）；
   - 方式二：双击 **`启动软件(带控制台日志).bat`**（调试模式）；
   - 方式三：命令行启动：
     ```bash
     python run.py
     ```

5. **首次配置**
   - 首次启动会自动弹出设置中心，填入您的 **API Base URL**（如 `https://api.openai.com/v1`）与 **API Key**，点击 **测试 API 连接** 并保存即可！

---

## ⌨️ 快捷键速查

| 功能 | 默认快捷键 | 说明 |
| :--- | :--- | :--- |
| **快捷轮盘** | `Ctrl+Win+Alt` | **按住不放**在光标处呼出 5 方位轮盘，指向方位后**松开执行** |
| **选区截屏翻译** | 通过轮盘下方呼出（可在设置中自定义） | 十字准心框选（左键松开即翻，右键松开弹出确认卡片） |
| **输入翻译工作台** | 通过轮盘右侧呼出（可在设置中自定义） | 打开独立双语输入翻译工作台 |
| **全屏原位翻译** | 通过轮盘上方呼出 | 全屏捕获、OCR 与原位文本重绘替换 |
| **退出全屏/选区** | `ESC` | 立即退出全屏查看器或选区截屏 |
| **全屏对比原图** | `空格键 (Space)` | 按住显示原图，松开恢复译图 |

---

## 📄 开源许可证

本项目基于 [MIT License](LICENSE) 开源发布。
