import threading
from typing import Dict, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    CardWidget,
    ComboBox,
    FluentIcon as FIF,
    IconWidget,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    PasswordLineEdit,
    PrimaryPushButton,
    PushButton,
    SegmentedWidget,
    DoubleSpinBox,
    SpinBox,
    SwitchButton,
    TitleLabel,
    SubtitleLabel,
    BodyLabel,
    CaptionLabel,
    StrongBodyLabel,
    Theme,
    setTheme,
    setThemeColor,
)

from app.config import config_manager
from app.core.ai_client import ai_client, PROMPT_PRESETS
from app.utils.autostart import is_autostart_enabled, set_autostart


class FluentSettingCard(CardWidget):
    """A resilient Fluent Design card with title, subtitle on the left and control on the right."""

    def __init__(self, title: str, subtitle: str = "", control: Optional[QWidget] = None, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(50)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(12)

        # Left Text Column
        text_vbox = QVBoxLayout()
        text_vbox.setSpacing(2)
        text_vbox.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.title_lbl = StrongBodyLabel(title, self)
        self.title_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #201F1E;")
        text_vbox.addWidget(self.title_lbl)

        if subtitle:
            self.sub_lbl = CaptionLabel(subtitle, self)
            self.sub_lbl.setStyleSheet("font-size: 11px; color: #605E5C;")
            self.sub_lbl.setWordWrap(True)
            text_vbox.addWidget(self.sub_lbl)

        layout.addLayout(text_vbox, stretch=1)

        # Right Control
        if control is not None:
            layout.addWidget(control, stretch=0, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)


class SettingsWindow(QWidget):
    """Windows 11 Fluent Design Main Settings Window."""

    settings_saved = pyqtSignal()
    test_result_signal = pyqtSignal(bool, str, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PMFY 全局翻译 - 软件设置")
        self.setMinimumSize(580, 480)
        self.resize(660, 540)

        # Apply Fluent Theme
        setThemeColor("#0078D4")
        setTheme(Theme.LIGHT)

        self._init_ui()
        self._load_values()

        self.test_result_signal.connect(self._on_test_result)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 14, 18, 12)
        main_layout.setSpacing(10)

        # 1. Top Header Title
        header_layout = QHBoxLayout()
        icon = IconWidget(FIF.LANGUAGE, self)
        icon.setFixedSize(28, 28)
        title_label = TitleLabel("PMFY 软件设置中心", self)
        header_layout.addWidget(icon)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # 2. Navigation Tabs (SegmentedWidget)
        self.pivot = SegmentedWidget(self)
        self.pivot.addItem("api_tab", "API 接口配置", icon=FIF.GLOBE)
        self.pivot.addItem("trans_tab", "翻译与模块", icon=FIF.LANGUAGE)
        self.pivot.addItem("hotkey_tab", "快捷键与划词", icon=FIF.MOVE)
        self.pivot.addItem("about_tab", "关于与外观", icon=FIF.INFO)
        main_layout.addWidget(self.pivot)

        # 3. Stacked Pages
        self.stacked_widget = QStackedWidget(self)
        main_layout.addWidget(self.stacked_widget, stretch=1)

        self._init_api_page()
        self._init_trans_page()
        self._init_hotkey_page()
        self._init_about_page()

        self.pivot.currentItemChanged.connect(self._on_tab_changed)
        self.pivot.setCurrentItem("api_tab")

        # 4. Bottom Save Bar
        bottom_frame = QFrame(self)
        bottom_frame.setStyleSheet("border-top: 1px solid rgba(0, 0, 0, 0.08); padding-top: 8px;")
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(0, 8, 0, 0)

        status_tip = CaptionLabel("设置修改后点击保存即可全局实时生效", bottom_frame)
        status_tip.setStyleSheet("color: #8A8886;")
        bottom_layout.addWidget(status_tip)
        bottom_layout.addStretch()

        self.btn_save = PrimaryPushButton("💾 保存并应用设置", bottom_frame, FIF.SAVE)
        self.btn_save.setFixedWidth(180)
        self.btn_save.clicked.connect(self._on_save_clicked)
        bottom_layout.addWidget(self.btn_save)

        main_layout.addWidget(bottom_frame)

    def _create_scrollable_page(self) -> tuple[QScrollArea, QVBoxLayout]:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 8, 12, 8)
        layout.setSpacing(12)
        scroll.setWidget(content)
        return scroll, layout

    # -------------------------------------------------------------
    # Page 1: API Configuration
    # -------------------------------------------------------------
    def _init_api_page(self):
        scroll, layout = self._create_scrollable_page()

        group_title = SubtitleLabel("AI 大模型 API 接入与高级参数", scroll.widget())
        layout.addWidget(group_title)

        # 1. Preset / Provider
        self.provider_combo = ComboBox()
        self.provider_combo.addItems([
            "OpenAI 官方兼容格式 (/v1/chat/completions)",
            "Anthropic Claude 格式 (/v1/messages)",
            "DeepSeek (深度求索官方)",
            "Moonshot / Kimi (月之暗面)",
            "SiliconFlow (硅基流动)",
            "Ollama (本地私有模型)",
        ])
        self.provider_combo.setFixedWidth(280)
        self.provider_combo.currentIndexChanged.connect(self._on_provider_preset_changed)
        card_p = FluentSettingCard(
            "API 协议与服务商预设",
            "选择标准 OpenAI 兼容协议或 Anthropic 格式，或一键选用常用服务商预设",
            self.provider_combo,
            scroll.widget(),
        )
        layout.addWidget(card_p)

        # 2. Base URL
        self.url_edit = LineEdit()
        self.url_edit.setPlaceholderText("https://api.openai.com/v1")
        self.url_edit.setFixedWidth(320)
        card_u = FluentSettingCard(
            "API Base URL (接口基地址)",
            "支持任意兼容 OpenAI 或 Anthropic 协议的中转或官方 API 接口地址",
            self.url_edit,
            scroll.widget(),
        )
        layout.addWidget(card_u)

        # 3. API Key
        self.key_edit = PasswordLineEdit()
        self.key_edit.setPlaceholderText("sk-...")
        self.key_edit.setFixedWidth(320)
        card_k = FluentSettingCard(
            "API Key (密钥)",
            "填入大模型服务商提供的密钥，保存在本地安全配置中",
            self.key_edit,
            scroll.widget(),
        )
        layout.addWidget(card_k)

        # 4. Model Name
        self.model_edit = LineEdit()
        self.model_edit.setPlaceholderText("gpt-4o-mini")
        self.model_edit.setFixedWidth(320)
        card_m = FluentSettingCard(
            "Model (模型代号)",
            "指定调用的模型名称，如 gpt-4o-mini, deepseek-chat, claude-3-5-sonnet",
            self.model_edit,
            scroll.widget(),
        )
        layout.addWidget(card_m)

        # 5. Max Concurrency Control
        self.spin_concurrency = SpinBox()
        self.spin_concurrency.setRange(0, 50)
        self.spin_concurrency.setValue(0)
        self.spin_concurrency.setFixedWidth(120)
        card_conc = FluentSettingCard(
            "最大请求并发数限制",
            "设置 API 调用的最大并行请求数（0 为不作限制，设置如 2 或 5 可有效防 429 频控报错）",
            self.spin_concurrency,
            scroll.widget(),
        )
        layout.addWidget(card_conc)

        # 6. Prompt Style Preset
        self.prompt_combo = ComboBox()
        self.prompt_map = {
            "通用日常精译 (自然地道)": "general",
            "学术论文精读 (严谨规范)": "academic",
            "计算机与代码开发 (保留代码与术语)": "tech",
            "游戏与动漫汉化 (生动口语化)": "game",
            "文学与古典诗词 (优美韵味)": "literary",
        }
        self.prompt_combo.addItems(list(self.prompt_map.keys()))
        self.prompt_combo.setFixedWidth(280)
        card_prompt = FluentSettingCard(
            "专业领域提示词风格模板",
            "根据当前工作领域选择专属提示词调优，让 AI 输出更具针对性",
            self.prompt_combo,
            scroll.widget(),
        )
        layout.addWidget(card_prompt)

        # 7. Multimodal Vision Switch
        self.switch_vision = SwitchButton()
        card_vis = FluentSettingCard(
            "【多模态】翻译时附带屏幕截图",
            "将截屏画面作为多模态图像输入给视觉大模型（适用于 GPT-4o / Claude 3.5 Sonnet 等）",
            self.switch_vision,
            scroll.widget(),
        )
        layout.addWidget(card_vis)

        # 8. Test Connection Button
        self.btn_test_api = PushButton("⚡ 测试 API 连接", None, FIF.SEND)
        self.btn_test_api.setFixedWidth(150)
        self.btn_test_api.clicked.connect(self._on_test_api_clicked)
        card_t = FluentSettingCard(
            "API 连通性测试",
            "向配置的大模型发送一条快速测试请求，验证 API 密钥与网络延时（成功后自动保存配置）",
            self.btn_test_api,
            scroll.widget(),
        )
        layout.addWidget(card_t)

        layout.addStretch()
        self.stacked_widget.addWidget(scroll)

    # -------------------------------------------------------------
    # Page 2: Translation Settings & Modules
    # -------------------------------------------------------------
    def _init_trans_page(self):
        scroll, layout = self._create_scrollable_page()

        group_title = SubtitleLabel("翻译偏好与功能模块开关", scroll.widget())
        layout.addWidget(group_title)

        # 1. Target Language
        self.lang_map: Dict[str, str] = {
            "简体中文 (zh-CN)": "zh-CN",
            "繁體中文 (zh-TW)": "zh-TW",
            "English (en)": "en",
            "日本語 (ja)": "ja",
            "한국어 (ko)": "ko",
            "Français (fr)": "fr",
            "Deutsch (de)": "de",
            "Español (es)": "es",
            "Русский (ru)": "ru",
        }
        self.lang_combo = ComboBox()
        self.lang_combo.addItems(list(self.lang_map.keys()))
        self.lang_combo.setFixedWidth(220)
        card_l = FluentSettingCard(
            "默认目标语言",
            "框选划词与全屏 OCR 翻译默认输出的目标语言",
            self.lang_combo,
            scroll.widget(),
        )
        layout.addWidget(card_l)

        # 2. Module 1: Enable Translation
        self.switch_mod_trans = SwitchButton()
        card_mt = FluentSettingCard(
            "启用基础译文 (Translation)",
            "在划词弹窗与卡片中展示精准目标语言翻译",
            self.switch_mod_trans,
            scroll.widget(),
        )
        layout.addWidget(card_mt)

        # 3. Module 2: Enable Explanation
        self.switch_mod_exp = SwitchButton()
        card_me = FluentSettingCard(
            "启用详细解释与语法分析 (Explanation)",
            "在划词弹窗中展示词性、长难句结构与重点语法说明（关闭可大幅提升响应速度）",
            self.switch_mod_exp,
            scroll.widget(),
        )
        layout.addWidget(card_me)

        # 4. Module 3: Enable Examples
        self.switch_mod_ex = SwitchButton()
        card_mex = FluentSettingCard(
            "启用实用例句造句 (Example Sentences)",
            "在划词弹窗中提供典型双语造句与例句拓展",
            self.switch_mod_ex,
            scroll.widget(),
        )
        layout.addWidget(card_mex)

        # 5. Full page context
        self.switch_full_context = SwitchButton()
        card_fctx = FluentSettingCard(
            "全屏翻译整页上下文关联",
            "将整屏文本作为全局背景注入给大模型，提供上下文连贯的高质量翻译",
            self.switch_full_context,
            scroll.widget(),
        )
        layout.addWidget(card_fctx)

        # 6. Auto TTS
        self.switch_auto_tts = SwitchButton()
        card_tts = FluentSettingCard(
            "自动语音朗读 (TTS)",
            "划词悬停翻译触发后，自动播放所选单词或语句的发音",
            self.switch_auto_tts,
            scroll.widget(),
        )
        layout.addWidget(card_tts)

        # 7. Phonetic / Pinyin
        self.switch_phonetic = SwitchButton()
        card_ph = FluentSettingCard(
            "显示音标与拼音注音",
            "英文标注国际音标 (IPA)，中文标注带调汉语拼音",
            self.switch_phonetic,
            scroll.widget(),
        )
        layout.addWidget(card_ph)

        layout.addStretch()
        self.stacked_widget.addWidget(scroll)

    # -------------------------------------------------------------
    # Page 3: Hotkeys & Selection
    # -------------------------------------------------------------
    def _init_hotkey_page(self):
        scroll, layout = self._create_scrollable_page()

        group_title = SubtitleLabel("全局快捷键与划词交互", scroll.widget())
        layout.addWidget(group_title)

        # 1. Radial Menu Hotkey
        self.radial_hk_edit = LineEdit()
        self.radial_hk_edit.setText("Ctrl+Win+Alt")
        self.radial_hk_edit.setFixedWidth(200)
        card_rhk = FluentSettingCard(
            "快捷轮盘按键 (Radial Menu)",
            "长按该快捷键在光标处呼出 5 方位轮盘，鼠标移动指向对应方位后松开即刻执行（默认：Ctrl+Win+Alt）",
            self.radial_hk_edit,
            scroll.widget(),
        )
        layout.addWidget(card_rhk)

        # 2. Area Snipping Hotkey
        self.area_hk_edit = LineEdit()
        self.area_hk_edit.setPlaceholderText("例如: Alt+Q (可选)")
        self.area_hk_edit.setFixedWidth(200)
        card_ahk = FluentSettingCard(
            "选区截屏翻译独立快捷键",
            "按下后直接激活全屏十字准心框选截图翻译（左键框选即翻，右键框选弹出确认卡片）",
            self.area_hk_edit,
            scroll.widget(),
        )
        layout.addWidget(card_ahk)

        # 3. Input Translation Hotkey
        self.input_hk_edit = LineEdit()
        self.input_hk_edit.setPlaceholderText("例如: Alt+W (可选)")
        self.input_hk_edit.setFixedWidth(200)
        card_ihk = FluentSettingCard(
            "输入翻译工作台独立快捷键",
            "按下后直接呼出独立双语输入翻译工作台（支持输入 500ms 实时防抖翻译与深度解析）",
            self.input_hk_edit,
            scroll.widget(),
        )
        layout.addWidget(card_ihk)

        # 4. Instant Translation Mode Switch
        self.switch_instant = SwitchButton()
        card_inst = FluentSettingCard(
            "划词立即弹出翻译卡片",
            "开启后，长按/拖拽选中文本释放后跳过蓝色小圆圈，直接秒级弹出详细翻译卡片",
            self.switch_instant,
            scroll.widget(),
        )
        layout.addWidget(card_inst)

        # 5. Selection Translation Switch
        self.switch_selection = SwitchButton()
        card_sel = FluentSettingCard(
            "开启鼠标划词翻译功能",
            "总开关：控制是否启用屏幕划词检测与自动翻译",
            self.switch_selection,
            scroll.widget(),
        )
        layout.addWidget(card_sel)

        # 6. Bubble Size Setting
        self.spin_bubble_size = SpinBox()
        self.spin_bubble_size.setRange(20, 64)
        self.spin_bubble_size.setValue(32)
        self.spin_bubble_size.setFixedWidth(140)
        card_bsize = FluentSettingCard(
            "划词悬浮球尺寸 (Circle Size)",
            "调整鼠标选区释放后显示的蓝色小圆圈直径大小（单位: px，默认：32 px）",
            self.spin_bubble_size,
            scroll.widget(),
        )
        layout.addWidget(card_bsize)

        # 7. Hover Delay Setting
        self.spin_hover_delay = DoubleSpinBox()
        self.spin_hover_delay.setRange(0.05, 1.50)
        self.spin_hover_delay.setSingleStep(0.05)
        self.spin_hover_delay.setValue(0.15)
        self.spin_hover_delay.setFixedWidth(140)
        card_hdelay = FluentSettingCard(
            "悬浮球鼠标悬停触发延时 (Hover Delay)",
            "鼠标移动到蓝色小圆圈上停留多长时间后自动触发翻译（单位: 秒，默认：0.15 秒）",
            self.spin_hover_delay,
            scroll.widget(),
        )
        layout.addWidget(card_hdelay)

        layout.addStretch()
        self.stacked_widget.addWidget(scroll)

    # -------------------------------------------------------------
    # Page 4: About & Theme
    # -------------------------------------------------------------
    def _init_about_page(self):
        scroll, layout = self._create_scrollable_page()

        group_title = SubtitleLabel("常规设置与界面外观", scroll.widget())
        layout.addWidget(group_title)

        # 1. Autostart Switch
        self.switch_autostart = SwitchButton()
        card_auto = FluentSettingCard(
            "开机自动启动 (Auto Start)",
            "系统开机登录时自动在后台静默启动 PMFY 并常驻任务栏托盘",
            self.switch_autostart,
            scroll.widget(),
        )
        layout.addWidget(card_auto)

        # 2. Theme
        self.theme_combo = ComboBox()
        self.theme_combo.addItems(["浅色 (Light)", "深色 (Dark)", "跟随系统 (Auto)"])
        self.theme_combo.setFixedWidth(180)
        card_theme = FluentSettingCard(
            "界面色彩主题",
            "支持浅色、深色模式或自动跟随 Windows 11 系统主题切换",
            self.theme_combo,
            scroll.widget(),
        )
        layout.addWidget(card_theme)

        # 3. Version Card
        ver_badge = PushButton("v1.3.0 专业版")
        ver_badge.setEnabled(False)
        ver_badge.setFixedWidth(120)
        card_ver = FluentSettingCard(
            "PMFY 全局智能翻译桌面应用",
            "集成 OpenAI/Claude 多协议、快捷轮盘、选区原位重绘、全屏沉浸翻译与问 AI 深度对话系统",
            ver_badge,
            scroll.widget(),
        )
        layout.addWidget(card_ver)

        layout.addStretch()
        self.stacked_widget.addWidget(scroll)

    # -------------------------------------------------------------
    # Handlers & Logic
    # -------------------------------------------------------------
    def _on_tab_changed(self, route_key: str):
        mapping = {
            "api_tab": 0,
            "trans_tab": 1,
            "hotkey_tab": 2,
            "about_tab": 3,
        }
        idx = mapping.get(route_key, 0)
        self.stacked_widget.setCurrentIndex(idx)

    def _on_provider_preset_changed(self, index: int):
        presets = {
            0: ("openai", "https://api.openai.com/v1", "gpt-4o-mini"),
            1: ("anthropic", "https://api.anthropic.com/v1", "claude-3-5-sonnet-20241022"),
            2: ("openai", "https://api.deepseek.com/v1", "deepseek-chat"),
            3: ("openai", "https://api.moonshot.cn/v1", "moonshot-v1-8k"),
            4: ("openai", "https://api.siliconflow.cn/v1", "deepseek-ai/DeepSeek-V3"),
            5: ("openai", "http://localhost:11434/v1", "qwen2.5:7b"),
        }
        if index in presets:
            prov, url, model = presets[index]
            self.url_edit.setText(url)
            self.model_edit.setText(model)

    def _load_values(self):
        # API
        api_cfg = config_manager.get("api", default={})
        prov = api_cfg.get("provider", "openai")
        self.url_edit.setText(api_cfg.get("base_url", "https://api.openai.com/v1"))
        self.key_edit.setText(api_cfg.get("api_key", ""))
        self.model_edit.setText(api_cfg.get("model", "gpt-4o-mini"))
        self.spin_concurrency.setValue(int(api_cfg.get("max_concurrency", 0)))
        self.switch_vision.setChecked(bool(api_cfg.get("enable_vision", False)))

        # Prompt preset
        preset = api_cfg.get("prompt_preset", "general")
        for name, key in self.prompt_map.items():
            if key == preset:
                self.prompt_combo.setCurrentText(name)
                break

        if prov == "anthropic":
            self.provider_combo.setCurrentIndex(1)
        elif "deepseek" in api_cfg.get("base_url", ""):
            self.provider_combo.setCurrentIndex(2)
        elif "moonshot" in api_cfg.get("base_url", ""):
            self.provider_combo.setCurrentIndex(3)
        elif "siliconflow" in api_cfg.get("base_url", ""):
            self.provider_combo.setCurrentIndex(4)
        elif "localhost:11434" in api_cfg.get("base_url", ""):
            self.provider_combo.setCurrentIndex(5)
        else:
            self.provider_combo.setCurrentIndex(0)

        # Translation & Modules
        trans_cfg = config_manager.get("translation", default={})
        t_lang = trans_cfg.get("target_language", "zh-CN")
        for text, code in self.lang_map.items():
            if code == t_lang:
                self.lang_combo.setCurrentText(text)
                break

        mod_cfg = config_manager.get("modules", default={})
        self.switch_mod_trans.setChecked(bool(mod_cfg.get("enable_translation", True)))
        self.switch_mod_exp.setChecked(bool(mod_cfg.get("enable_explanation", True)))
        self.switch_mod_ex.setChecked(bool(mod_cfg.get("enable_examples", True)))
        self.switch_full_context.setChecked(bool(trans_cfg.get("full_page_context", True)))

        self.switch_auto_tts.setChecked(trans_cfg.get("auto_pronounce", False))
        self.switch_phonetic.setChecked(trans_cfg.get("show_pinyin_ipa", True))

        # Hotkeys & Selection
        hk_cfg = config_manager.get("hotkeys", default={})
        self.radial_hk_edit.setText(hk_cfg.get("radial_menu", "Ctrl+Win+Alt"))
        self.area_hk_edit.setText(hk_cfg.get("area_snipping", ""))
        self.input_hk_edit.setText(hk_cfg.get("input_translation", ""))

        sel_cfg = config_manager.get("selection", default={})
        self.switch_instant.setChecked(bool(sel_cfg.get("instant_mode", False)))
        self.switch_selection.setChecked(bool(sel_cfg.get("enabled", True)))
        self.spin_bubble_size.setValue(int(sel_cfg.get("circle_size", 32)))
        self.spin_hover_delay.setValue(float(sel_cfg.get("hover_delay", 0.15)))

        # General & Autostart
        self.switch_autostart.setChecked(is_autostart_enabled())

    def _on_test_api_clicked(self):
        prov_idx = self.provider_combo.currentIndex()
        provider = "anthropic" if prov_idx == 1 else "openai"
        base_url = self.url_edit.text().strip()
        api_key = self.key_edit.text().strip()
        model = self.model_edit.text().strip()
        max_c = self.spin_concurrency.value()
        vision = self.switch_vision.isChecked()
        preset = self.prompt_map.get(self.prompt_combo.currentText(), "general")

        config_manager.update_section("api", {
            "provider": provider,
            "base_url": base_url,
            "api_key": api_key,
            "model": model,
            "max_concurrency": max_c,
            "enable_vision": vision,
            "prompt_preset": preset,
        })

        self.btn_test_api.setEnabled(False)
        self.btn_test_api.setText("正在测试...")

        def _worker():
            success, msg, latency = ai_client.test_connection()
            self.test_result_signal.emit(success, msg, latency)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_test_result(self, success: bool, msg: str, latency: float):
        self.btn_test_api.setEnabled(True)
        self.btn_test_api.setText("⚡ 测试 API 连接")

        if success:
            config_manager.save_config()
            InfoBar.success(
                title="API 连接测试成功",
                content=f"{msg} (模型: {self.model_edit.text()}) - 已自动保存配置",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self,
            )
        else:
            InfoBar.error(
                title="API 连接失败",
                content=msg,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=6000,
                parent=self,
            )

    def _on_save_clicked(self):
        prov_idx = self.provider_combo.currentIndex()
        provider = "anthropic" if prov_idx == 1 else "openai"
        base_url = self.url_edit.text().strip()
        api_key = self.key_edit.text().strip()
        model = self.model_edit.text().strip()
        max_c = self.spin_concurrency.value()
        vision = self.switch_vision.isChecked()
        preset = self.prompt_map.get(self.prompt_combo.currentText(), "general")

        selected_lang_text = self.lang_combo.currentText()
        target_lang = self.lang_map.get(selected_lang_text, "zh-CN")

        radial_hk = self.radial_hk_edit.text().strip() or "Ctrl+Win+Alt"
        area_hk = self.area_hk_edit.text().strip()
        input_hk = self.input_hk_edit.text().strip()

        config_manager.update_section("api", {
            "provider": provider,
            "base_url": base_url,
            "api_key": api_key,
            "model": model,
            "max_concurrency": max_c,
            "enable_vision": vision,
            "prompt_preset": preset,
        })

        config_manager.update_section("modules", {
            "enable_translation": self.switch_mod_trans.isChecked(),
            "enable_explanation": self.switch_mod_exp.isChecked(),
            "enable_examples": self.switch_mod_ex.isChecked(),
        })

        config_manager.update_section("translation", {
            "target_language": target_lang,
            "auto_pronounce": self.switch_auto_tts.isChecked(),
            "show_pinyin_ipa": self.switch_phonetic.isChecked(),
            "full_page_context": self.switch_full_context.isChecked(),
        })

        config_manager.update_section("hotkeys", {
            "radial_menu": radial_hk,
            "area_snipping": area_hk,
            "input_translation": input_hk,
        })

        config_manager.update_section("fullscreen", {
            "hotkey": radial_hk,
        })

        config_manager.update_section("selection", {
            "enabled": self.switch_selection.isChecked(),
            "instant_mode": self.switch_instant.isChecked(),
            "circle_size": self.spin_bubble_size.value(),
            "hover_delay": round(self.spin_hover_delay.value(), 2),
        })

        # Autostart Windows Registry
        autostart_on = self.switch_autostart.isChecked()
        set_autostart(autostart_on)
        config_manager.update_section("general", {
            "auto_start": autostart_on,
        })

        config_manager.save_config()
        self.settings_saved.emit()

        InfoBar.success(
            title="设置已保存",
            content="您的配置已成功保存并立即生效！",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self,
        )
