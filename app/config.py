import json
import os
from pathlib import Path
from typing import Any, Dict

CONFIG_DIR = Path.home() / ".pmfy"
CONFIG_FILE = CONFIG_DIR / "config.json"
LOCAL_CONFIG_FILE = Path(__file__).resolve().parent.parent / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "api": {
        "provider": "openai",  # "openai" or "anthropic"
        "base_url": "https://api.openai.com/v1",
        "api_key": "",
        "model": "gpt-4o-mini",
        "temperature": 0.3,
        "max_tokens": 2048,
        "max_concurrency": 0,  # 0 for unlimited, or 1, 2, 5, 10
        "enable_vision": False,  # Send screenshot for multimodal models
        "prompt_preset": "general",  # "general", "academic", "tech", "game", "literary"
    },
    "modules": {
        "enable_translation": True,  # 译文
        "enable_explanation": True,  # 详细释义与语法分析
        "enable_examples": True,  # 实用例句造句
    },
    "translation": {
        "target_language": "zh-CN",
        "auto_pronounce": False,
        "show_pinyin_ipa": True,
        "full_page_context": True,  # Include full screen text as context
    },
    "selection": {
        "enabled": True,
        "instant_mode": False,  # If True, directly show translation popup skipping the blue bubble
        "hover_delay": 0.15,
        "stay_duration": 4.5,
        "circle_size": 32,
    },
    "hotkeys": {
        "radial_menu": "Ctrl+Win+Alt",  # 快捷轮盘（按住呼出，松开执行）
        "area_snipping": "",           # 选区截屏翻译快捷键（可选）
        "input_translation": "",       # 输入翻译工作台快捷键（可选）
        "fullscreen": "",              # 全屏翻译独立快捷键（可选）
    },
    "fullscreen": {
        "hotkey": "Ctrl+Win+Alt",  # Compatible alias
        "in_place_replace": True,
        "ocr_lang": "ch_ppocr_v4",
    },
    "appearance": {
        "theme": "Auto",  # "Light", "Dark", "Auto"
        "acrylic": True,
    },
    "general": {
        "auto_start": False,
        "minimize_to_tray": True,
    }
}


class ConfigManager:
    """Manages application configuration loading, updating, and saving."""

    def __init__(self):
        self._config: Dict[str, Any] = DEFAULT_CONFIG.copy()
        self._load_config()

    def _load_config(self):
        target_file = LOCAL_CONFIG_FILE if LOCAL_CONFIG_FILE.exists() else CONFIG_FILE
        if target_file.exists():
            try:
                with open(target_file, "r", encoding="utf-8") as f:
                    user_data = json.load(f)
                    self._deep_update(self._config, user_data)
            except Exception as e:
                print(f"[ConfigManager] Failed to load config from {target_file}: {e}")
        else:
            self.save_config()

    def _deep_update(self, target: dict, source: dict):
        for k, v in source.items():
            if isinstance(v, dict) and k in target and isinstance(target[k], dict):
                self._deep_update(target[k], v)
            else:
                target[k] = v

    def get(self, section: str, key: str = None, default: Any = None) -> Any:
        if section not in self._config:
            return default
        if key is None:
            return self._config[section]
        return self._config[section].get(key, default)

    def set(self, section: str, key: str, value: Any):
        if section not in self._config:
            self._config[section] = {}
        self._config[section][key] = value
        self.save_config()

    def update_section(self, section: str, values: Dict[str, Any]):
        if section not in self._config:
            self._config[section] = {}
        self._config[section].update(values)
        self.save_config()

    def save_config(self):
        try:
            with open(LOCAL_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
            
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ConfigManager] Failed to save config: {e}")

    @property
    def raw(self) -> Dict[str, Any]:
        return self._config


config_manager = ConfigManager()
