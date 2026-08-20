import base64
import io
import json
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
import httpx
from PIL import Image

from app.config import config_manager


PROMPT_PRESETS: Dict[str, str] = {
    "general": "你是一个资深翻译官，要求译文地道、自然、通顺，符合目标语言母语者的日常表达习惯。",
    "academic": "你是一个严谨的学术论文翻译专家，要求精准翻译专业术语，保持学术逻辑的严密性与规范性。",
    "tech": "你是一个资深软件工程师与技术文档翻译专家，要求保留所有代码标识符、API 名称及技术名词，语言精炼准确。",
    "game": "你是一个游戏与动漫本地化汉化专家，要求翻译风格生动活泼、口语化，契合角色性格与游戏情境。",
    "literary": "你是一个文学翻译大师，要求译文富有文学美感与韵味，准确传达原文的意境与情感色彩。",
}


class AIClient:
    """Unified client for OpenAI and Anthropic compatible APIs with concurrency control, Vision, and Chat."""

    def __init__(self):
        self._semaphore: Optional[threading.Semaphore] = None
        self._current_max_concurrency: int = 0

    def _get_semaphore(self) -> Optional[threading.Semaphore]:
        max_c = int(config_manager.get("api", "max_concurrency", 0))
        if max_c <= 0:
            return None
        if self._semaphore is None or self._current_max_concurrency != max_c:
            self._current_max_concurrency = max_c
            self._semaphore = threading.Semaphore(max_c)
        return self._semaphore

    def _get_api_config(self) -> Dict[str, Any]:
        return config_manager.get("api", default={})

    def _normalize_openai_url(self, base_url: str) -> str:
        base_url = base_url.strip().rstrip("/")
        if base_url.endswith("/chat/completions"):
            return base_url
        if base_url.endswith("/v1"):
            return f"{base_url}/chat/completions"
        return f"{base_url}/v1/chat/completions"

    def _normalize_anthropic_url(self, base_url: str) -> str:
        base_url = base_url.strip().rstrip("/")
        if base_url.endswith("/messages"):
            return base_url
        if base_url.endswith("/v1"):
            return f"{base_url}/messages"
        return f"{base_url}/v1/messages"

    def test_connection(self) -> Tuple[bool, str, float]:
        """Tests the configured API connection."""
        api_cfg = self._get_api_config()
        provider = api_cfg.get("provider", "openai").lower()
        base_url = api_cfg.get("base_url", "").strip()
        api_key = api_cfg.get("api_key", "").strip()
        model = api_cfg.get("model", "").strip()

        if not base_url:
            return False, "API Base URL 不能为空", 0.0
        if not model:
            return False, "Model 模型名称不能为空", 0.0

        start_time = time.time()
        try:
            if provider == "anthropic":
                url = self._normalize_anthropic_url(base_url)
                headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                }
                payload = {
                    "model": model,
                    "max_tokens": 30,
                    "messages": [{"role": "user", "content": "Respond with 'OK'"}],
                }
            else:  # OpenAI
                url = self._normalize_openai_url(base_url)
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": "Respond with 'OK'"}],
                    "max_tokens": 30,
                }

            with httpx.Client(timeout=15.0) as client:
                resp = client.post(url, headers=headers, json=payload)
                latency = round((time.time() - start_time) * 1000, 1)

                if resp.status_code == 200:
                    return True, f"连接成功！响应耗时: {latency}ms", latency
                else:
                    try:
                        err_json = resp.json()
                        err_msg = err_json.get("error", {}).get("message", resp.text)
                    except Exception:
                        err_msg = resp.text
                    return False, f"API 报错 (HTTP {resp.status_code}): {err_msg[:200]}", latency

        except httpx.ConnectError:
            latency = round((time.time() - start_time) * 1000, 1)
            return False, "网络连接失败，请检查 Base URL 是否正确或网络是否畅通", latency
        except httpx.TimeoutException:
            latency = round((time.time() - start_time) * 1000, 1)
            return False, "请求超时 (15s)，请检查 API 地址或网络", latency
        except Exception as e:
            latency = round((time.time() - start_time) * 1000, 1)
            return False, f"请求异常: {str(e)}", latency

    def translate_selection(self, text: str, target_lang: str = "zh-CN") -> Dict[str, Any]:
        """Translates selected text dynamically based on enabled modules and prompt preset."""
        sem = self._get_semaphore()
        if sem:
            with sem:
                return self._do_translate_selection(text, target_lang)
        return self._do_translate_selection(text, target_lang)

    def _do_translate_selection(self, text: str, target_lang: str) -> Dict[str, Any]:
        api_cfg = self._get_api_config()
        provider = api_cfg.get("provider", "openai").lower()
        base_url = api_cfg.get("base_url", "").strip()
        api_key = api_cfg.get("api_key", "").strip()
        model = api_cfg.get("model", "").strip()

        if not base_url or not model:
            return {
                "error": True,
                "message": "请先在设置中配置 API Base URL 和 Model 模型代号",
                "translation": "（未配置 API，请双击托盘打开设置）",
                "phonetic": "",
                "explanation": "请双击任务栏右下角蓝色托盘图标进入设置，填入您的 API Key 与 Base URL。",
                "examples": [],
            }

        enable_trans = config_manager.get("modules", "enable_translation", True)
        enable_exp = config_manager.get("modules", "enable_explanation", True)
        enable_ex = config_manager.get("modules", "enable_examples", True)

        preset_key = api_cfg.get("prompt_preset", "general")
        preset_desc = PROMPT_PRESETS.get(preset_key, PROMPT_PRESETS["general"])

        json_fields = []
        if enable_trans:
            json_fields.append('  "translation": "准确、地道的目标语言翻译"')
        json_fields.append('  "phonetic": "英文国际音标(如 /həˈloʊ/)或中文带调拼音(如 nǐ hǎo)"')
        if enable_exp:
            json_fields.append('  "explanation": "详细语法分析、词性及重难点释义"')
        if enable_ex:
            json_fields.append('  "examples": [{"src": "原文例句1", "dst": "译文例句1"}, {"src": "原文例句2", "dst": "译文例句2"}]')

        schema_str = "{\n" + ",\n".join(json_fields) + "\n}"

        system_prompt = (
            f"{preset_desc}\n"
            f"请将用户选中的文本翻译为目标语言：{target_lang}。\n"
            "严格按以下 JSON 格式输出，不要附加任何其他前后缀文字：\n"
            "```json\n"
            f"{schema_str}\n"
            "```"
        )

        user_content = f"请翻译并解析：\n\n{text}"

        try:
            if provider == "anthropic":
                url = self._normalize_anthropic_url(base_url)
                headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                }
                payload = {
                    "model": model,
                    "max_tokens": 2048,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_content}],
                }
                with httpx.Client(timeout=25.0) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code != 200:
                        try:
                            err_msg = resp.json().get("error", {}).get("message", resp.text)
                        except Exception:
                            err_msg = resp.text
                        raise Exception(f"HTTP {resp.status_code}: {err_msg}")
                    data = resp.json()
                    raw_text = data["content"][0]["text"]
            else:
                url = self._normalize_openai_url(base_url)
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    "max_tokens": 2048,
                }
                with httpx.Client(timeout=25.0) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code != 200:
                        payload_fallback = {
                            "model": model,
                            "messages": [
                                {"role": "user", "content": f"{system_prompt}\n\n{user_content}"},
                            ],
                            "max_tokens": 2048,
                        }
                        resp2 = client.post(url, headers=headers, json=payload_fallback)
                        if resp2.status_code == 200:
                            data = resp2.json()
                            raw_text = data["choices"][0]["message"]["content"]
                        else:
                            try:
                                err_msg = resp.json().get("error", {}).get("message", resp.text)
                            except Exception:
                                err_msg = resp.text
                            raise Exception(f"HTTP {resp.status_code}: {err_msg}")
                    else:
                        data = resp.json()
                        raw_text = data["choices"][0]["message"]["content"]

            return self._parse_json_result(raw_text, original_text=text)

        except Exception as e:
            return {
                "error": True,
                "message": f"请求失败: {str(e)}",
                "translation": "（翻译请求失败）",
                "phonetic": "",
                "explanation": f"错误详情: {str(e)}",
                "examples": [],
            }

    def translate_batch_texts(
        self,
        texts: List[str],
        target_lang: str = "zh-CN",
        full_context: str = "",
        image_pil: Optional[Image.Image] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> List[str]:
        """Translates a batch of OCR texts with context and optional multimodal Vision screenshot."""
        if not texts:
            return []

        sem = self._get_semaphore()
        if sem:
            with sem:
                return self._do_translate_batch(texts, target_lang, full_context, image_pil, progress_callback)
        return self._do_translate_batch(texts, target_lang, full_context, image_pil, progress_callback)

    def _do_translate_batch(
        self,
        texts: List[str],
        target_lang: str,
        full_context: str,
        image_pil: Optional[Image.Image],
        progress_callback: Optional[Callable[[int, int, str], None]],
    ) -> List[str]:
        api_cfg = self._get_api_config()
        provider = api_cfg.get("provider", "openai").lower()
        base_url = api_cfg.get("base_url", "").strip()
        api_key = api_cfg.get("api_key", "").strip()
        model = api_cfg.get("model", "").strip()
        enable_vision = bool(api_cfg.get("enable_vision", False))
        use_context = bool(config_manager.get("translation", "full_page_context", True))

        if not base_url or not model:
            return texts

        # Convert image to Base64 if vision enabled
        image_b64 = None
        if enable_vision and image_pil is not None:
            try:
                thumb = image_pil.copy()
                thumb.thumbnail((1600, 1600))
                buf = io.BytesIO()
                thumb.save(buf, format="JPEG", quality=80)
                image_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            except Exception as e:
                print(f"[AIClient] Image encode error: {e}")

        chunk_size = 20
        all_results = ["" for _ in range(len(texts))]
        total_chunks = (len(texts) + chunk_size - 1) // chunk_size

        for chunk_idx in range(total_chunks):
            start_i = chunk_idx * chunk_size
            end_i = min(len(texts), start_i + chunk_size)
            chunk_texts = texts[start_i:end_i]

            if progress_callback:
                progress_callback(start_i, len(texts), f"🤖 正在由 AI 翻译文本 ({start_i + 1}/{len(texts)})...")

            indexed_lines = "\n".join([f"[{start_i + i}] {t}" for i, t in enumerate(chunk_texts)])

            system_prompt = (
                "你是一个极度精准的屏幕 OCR 全局翻译引擎。\n"
                f"请将输入的所有文本逐行翻译为目标语言：{target_lang}。\n"
                "【严格翻译准则】：\n"
                "1. 每一个编号项都必须翻译！包括所有单词、短语、按钮名称、菜单、标题、标签与句子，必须全部翻译为目标语言。\n"
                "2. 只有纯阿拉伯数字（如 12345）或纯分割线符号（如 ---）才允许保留原样。\n"
                f"3. 必须保持原有编号不变，严格按 `[索引] 译文` 的格式逐行输出，共 {len(chunk_texts)} 行，必须按序完整输出全部 {len(chunk_texts)} 行！\n"
                "4. 严禁省略、跳过任何一个索引行，严禁输出任何多余的开场白或解释文字。"
            )

            if use_context and full_context:
                system_prompt += f"\n\n【全屏全局语境参考（帮助消除歧义）】：\n{full_context[:1200]}"

            try:
                if provider == "anthropic":
                    url = self._normalize_anthropic_url(base_url)
                    headers = {
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    }
                    content_list = []
                    if image_b64 and chunk_idx == 0:
                        content_list.append({
                            "type": "image",
                            "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64},
                        })
                    content_list.append({"type": "text", "text": indexed_lines})

                    payload = {
                        "model": model,
                        "max_tokens": 4096,
                        "system": system_prompt,
                        "messages": [{"role": "user", "content": content_list}],
                    }
                    with httpx.Client(timeout=35.0) as client:
                        resp = client.post(url, headers=headers, json=payload)
                        resp.raise_for_status()
                        raw_text = resp.json()["content"][0]["text"]
                else:
                    url = self._normalize_openai_url(base_url)
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    }
                    user_content_obj: Any = indexed_lines
                    if image_b64 and chunk_idx == 0:
                        user_content_obj = [
                            {"type": "text", "text": indexed_lines},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                        ]

                    payload = {
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content_obj},
                        ],
                        "max_tokens": 4096,
                    }
                    with httpx.Client(timeout=35.0) as client:
                        resp = client.post(url, headers=headers, json=payload)
                        if resp.status_code != 200:
                            payload_fallback = {
                                "model": model,
                                "messages": [
                                    {"role": "user", "content": f"{system_prompt}\n\n{indexed_lines}"},
                                ],
                                "max_tokens": 4096,
                            }
                            resp2 = client.post(url, headers=headers, json=payload_fallback)
                            resp2.raise_for_status()
                            raw_text = resp2.json()["choices"][0]["message"]["content"]
                        else:
                            raw_text = resp.json()["choices"][0]["message"]["content"]

                # Special case: Single line response
                if len(chunk_texts) == 1:
                    clean_single = raw_text.strip()
                    # Strip any "[0] ", "0. ", or markdown bold
                    clean_single = re.sub(r"^(?:\*\*|)?\[?\s*\d+\s*\]?(?:\*\*|)?[\:\.\-\s]\s*", "", clean_single)
                    clean_single = re.sub(r"^\*\*(.*)\*\*$", r"\1", clean_single).strip()
                    if clean_single:
                        all_results[start_i] = clean_single

                # Multi-line pattern matching
                parsed_count = 0
                for line in raw_text.strip().splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    match = re.match(r"^(?:\*\*|)?\[?\s*(\d+)\s*\]?(?:\*\*|)?[\:\.\-\s]\s*(.*)$", line)
                    if match:
                        idx = int(match.group(1))
                        val = match.group(2).strip()
                        val = re.sub(r"^\*\*(.*)\*\*$", r"\1", val).strip()
                        if 0 <= idx < len(all_results) and val:
                            all_results[idx] = val
                            parsed_count += 1

                # Reliable sequential fallback fill for any missing indices
                if parsed_count < len(chunk_texts):
                    clean_lines = [
                        re.sub(r"^(?:\*\*|)?\[?\s*\d+\s*\]?(?:\*\*|)?[\:\.\-\s]\s*", "", l).strip()
                        for l in raw_text.strip().splitlines() if l.strip()
                    ]
                    for i, cl in enumerate(clean_lines[:len(chunk_texts)]):
                        if not all_results[start_i + i] and cl:
                            all_results[start_i + i] = cl

            except Exception as e:
                print(f"[AIClient] Batch chunk error: {e}")

        # Fill any untranslated gaps with original
        for i in range(len(all_results)):
            if not all_results[i]:
                all_results[i] = texts[i]

        if progress_callback:
            progress_callback(len(texts), len(texts), f"✅ AI 翻译完成 (共 {len(texts)} 处)")

        return all_results

    def chat_with_ai(
        self,
        messages_history: List[Dict[str, str]],
        context: str = "",
        target_lang: str = "zh-CN",
    ) -> str:
        """Multi-turn discussion with AI about translation, grammar, or phrasing."""
        api_cfg = self._get_api_config()
        provider = api_cfg.get("provider", "openai").lower()
        base_url = api_cfg.get("base_url", "").strip()
        api_key = api_cfg.get("api_key", "").strip()
        model = api_cfg.get("model", "").strip()

        if not base_url or not model:
            return "请先在软件设置中配置 API Key 与 Base URL 后再进行提问。"

        system_prompt = (
            "你是一个博学、耐心且专业的 AI 语言助手和翻译导师。\n"
            "用户正在使用 PMFY 翻译工具，并希望与你深度探讨某段文字的翻译细节、语法结构、同义表达或特定语境用法。\n"
            "请用清晰、有条理且亲切的中文回答用户的问题。"
        )
        if context:
            system_prompt += f"\n\n【当前文字背景与参考】：\n{context}"

        try:
            if provider == "anthropic":
                url = self._normalize_anthropic_url(base_url)
                headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                }
                payload = {
                    "model": model,
                    "max_tokens": 3000,
                    "system": system_prompt,
                    "messages": messages_history,
                }
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    resp.raise_for_status()
                    return resp.json()["content"][0]["text"].strip()
            else:
                url = self._normalize_openai_url(base_url)
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                full_messages = [{"role": "system", "content": system_prompt}] + messages_history
                payload = {
                    "model": model,
                    "messages": full_messages,
                    "max_tokens": 3000,
                }
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code != 200:
                        combined_msgs = [{"role": "user", "content": f"系统提示：{system_prompt}"}] + messages_history
                        resp2 = client.post(url, headers=headers, json={"model": model, "messages": combined_msgs})
                        resp2.raise_for_status()
                        return resp2.json()["choices"][0]["message"]["content"].strip()
                    return resp.json()["choices"][0]["message"]["content"].strip()

        except Exception as e:
            return f"❌ 对话请求失败: {str(e)}"

    def _parse_json_result(self, raw: str, original_text: str = "") -> Dict[str, Any]:
        """Resilient multi-stage parser that extracts translation fields even with broken or unescaped JSON."""
        text = raw.strip()
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in text:
            text = text.split("```", 1)[1].split("```", 1)[0].strip()

        try:
            data = json.loads(text)
            return {
                "error": False,
                "original": original_text,
                "translation": str(data.get("translation", "")).strip(),
                "phonetic": str(data.get("phonetic", "")).strip(),
                "explanation": str(data.get("explanation", "")).strip(),
                "examples": data.get("examples", []) if isinstance(data.get("examples"), list) else [],
            }
        except Exception:
            pass

        trans_val = ""
        phon_val = ""
        exp_val = ""
        examples_val = []

        m_trans = re.search(r'["\']translation["\']\s*:\s*"(.*?)(?:"\s*,\s*"\w+"|\s*"\s*\})', text, re.DOTALL)
        if not m_trans:
            m_trans = re.search(r'["\']translation["\']\s*:\s*"(.*)"', text)
        if m_trans:
            trans_val = m_trans.group(1).strip()

        m_phon = re.search(r'["\']phonetic["\']\s*:\s*"(.*?)(?:"\s*,\s*"\w+"|\s*"\s*\})', text, re.DOTALL)
        if m_phon:
            phon_val = m_phon.group(1).strip()

        m_exp = re.search(r'["\']explanation["\']\s*:\s*"(.*?)(?:"\s*,\s*"\w+"|\s*"\s*\})', text, re.DOTALL)
        if not m_exp:
            m_exp = re.search(r'["\']explanation["\']\s*:\s*"(.*?)(?:"\s*,\s*["\']examples["\']|\s*\}\s*$)', text, re.DOTALL)
        if m_exp:
            exp_val = m_exp.group(1).strip()

        m_ex = re.search(r'["\']examples["\']\s*:\s*(\[.*?\])', text, re.DOTALL)
        if m_ex:
            try:
                examples_val = json.loads(m_ex.group(1))
            except Exception:
                item_matches = re.findall(r'\{\s*["\']src["\']\s*:\s*"(.*?)"\s*,\s*["\']dst["\']\s*:\s*"(.*?)"\s*\}', m_ex.group(1), re.DOTALL)
                for src, dst in item_matches:
                    examples_val.append({"src": src.strip(), "dst": dst.strip()})

        if trans_val:
            return {
                "error": False,
                "original": original_text,
                "translation": trans_val,
                "phonetic": phon_val,
                "explanation": exp_val,
                "examples": examples_val,
            }

        clean_text = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
        clean_text = re.sub(r'^\s*\{\s*"translation"\s*:\s*', "", clean_text)
        clean_text = re.sub(r'\s*\}\s*$', "", clean_text).strip()

        return {
            "error": False,
            "original": original_text,
            "translation": clean_text,
            "phonetic": "",
            "explanation": "（AI 已直接返回全文翻译）",
            "examples": [],
        }


ai_client = AIClient()
