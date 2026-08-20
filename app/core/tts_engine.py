import asyncio
import os
import re
import tempfile
import threading
import unicodedata
from pathlib import Path
from typing import Optional

import edge_tts
import eng_to_ipa as ipa
from pypinyin import pinyin, Style

try:
    import pyttsx3
    _pyttsx3_available = True
except Exception:
    _pyttsx3_available = False

try:
    import winsound
    _winsound_available = True
except Exception:
    _winsound_available = False

import ctypes
winmm = ctypes.windll.winmm


class TTSEngine:
    """Provides TTS speech playback and phonetic/pinyin annotations."""

    def __init__(self):
        self._temp_dir = Path(tempfile.gettempdir()) / "pmfy_tts"
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._engine = None

    def _get_pyttsx3_engine(self):
        if self._engine is None and _pyttsx3_available:
            try:
                self._engine = pyttsx3.init()
                self._engine.setProperty("rate", 160)
            except Exception as e:
                print(f"[TTSEngine] pyttsx3 init error: {e}")
        return self._engine

    def is_chinese(self, text: str) -> bool:
        return any("\u4e00" <= char <= "\u9fff" for char in text)

    def is_english(self, text: str) -> bool:
        # Check if contains ascii letters and no CJK
        has_latin = bool(re.search(r"[a-zA-Z]", text))
        return has_latin and not self.is_chinese(text)

    def get_phonetic_or_pinyin(self, text: str) -> str:
        """Returns IPA for English words/sentences, or Pinyin for Chinese text."""
        text = text.strip()
        if not text:
            return ""

        if self.is_chinese(text):
            # Chinese Pinyin with tones
            py_list = pinyin(text, style=Style.TONE)
            flat_py = [p[0] for p in py_list if p and p[0].strip()]
            return " ".join(flat_py)
        elif self.is_english(text):
            # English IPA
            try:
                # Limit length to avoid slow conversion for long text
                words = text.split()
                if len(words) <= 15:
                    ipa_result = ipa.convert(text)
                    if ipa_result and not ipa_result.endswith("*"):
                        return f"/{ipa_result}/"
            except Exception as e:
                print(f"[TTSEngine] IPA error: {e}")
        return ""

    def speak(self, text: str, voice: Optional[str] = None):
        """Asynchronously plays TTS speech for the given text."""
        if not text or not text.strip():
            return
        
        # Clean text for speech
        clean_text = re.sub(r"[^\w\s\u4e00-\u9fff,.\?!，。？！]", " ", text).strip()
        if not clean_text:
            return

        threading.Thread(target=self._speak_worker, args=(clean_text, voice), daemon=True).start()

    def _speak_worker(self, text: str, voice: Optional[str] = None):
        with self._lock:
            # Stop any playing audio
            try:
                winmm.mciSendStringW("close pmfy_audio", None, 0, 0)
            except Exception:
                pass

            # Determine voice if not specified
            if voice is None:
                if self.is_chinese(text):
                    voice = "zh-CN-XiaoxiaoNeural"
                elif any("\u3040" <= c <= "\u30ff" for c in text):
                    voice = "ja-JP-NanamiNeural"
                elif any("\uac00" <= c <= "\ud7af" for c in text):
                    voice = "ko-KR-SunHiNeural"
                else:
                    voice = "en-US-JennyNeural"

            temp_mp3 = self._temp_dir / f"tts_{os.getpid()}_{threading.get_ident()}.mp3"
            success = False

            # 1. Try edge-tts for high quality neural voice
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                communicate = edge_tts.Communicate(text, voice)
                loop.run_until_complete(communicate.save(str(temp_mp3)))
                loop.close()

                if temp_mp3.exists() and temp_mp3.stat().st_size > 0:
                    # Play MP3 via Windows MCI
                    alias = "pmfy_audio"
                    winmm.mciSendStringW(f'open "{temp_mp3}" type mpegvideo alias {alias}', None, 0, 0)
                    winmm.mciSendStringW(f"play {alias} wait", None, 0, 0)
                    winmm.mciSendStringW(f"close {alias}", None, 0, 0)
                    success = True
            except Exception as e:
                print(f"[TTSEngine] edge-tts error, falling back to pyttsx3: {e}")

            # 2. Fallback to pyttsx3 offline engine
            if not success and _pyttsx3_available:
                try:
                    engine = self._get_pyttsx3_engine()
                    if engine:
                        engine.say(text)
                        engine.runAndWait()
                        success = True
                except Exception as e:
                    print(f"[TTSEngine] pyttsx3 fallback error: {e}")

            # Cleanup temp file
            try:
                if temp_mp3.exists():
                    temp_mp3.unlink()
            except Exception:
                pass


tts_engine = TTSEngine()
