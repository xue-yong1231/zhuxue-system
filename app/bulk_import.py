"""批量解析学习内容文本，方便房主一次粘贴多条。"""

from __future__ import annotations

import re

from app.content_sync import parse_colon_lines


def parse_learn_items(raw: str) -> list[dict[str, str]]:
    """
    支持两种格式（可混用）：

    1) 竖线分隔，一行一条：
       正文|翻译|解释

    2) 分块（空行或 --- 分隔）：
       正文
       翻译：……
       解释：……
    """
    text = (raw or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []

    items: list[dict[str, str]] = []

    # 「词语：含义」一行一条（与根目录内容文件相同）
    lines_probe = [ln.strip() for ln in text.split("\n") if ln.strip() and not ln.strip().startswith("#")]
    if lines_probe and all(
        (":" in ln or "：" in ln) and "|" not in ln for ln in lines_probe
    ):
        colon_items = parse_colon_lines(text)
        if colon_items:
            return colon_items

    # 若整段都是「一行一条」竖线格式，优先按行解析
    lines_all = [ln.strip() for ln in text.split("\n") if ln.strip()]
    if lines_all and all("|" in ln and not ln.startswith("正文") for ln in lines_all):
        for ln in lines_all:
            if re.match(r"^(翻译|解释|解析|含义|译文)", ln):
                break
            parts = [p.strip() for p in ln.split("|")]
            if parts and parts[0]:
                items.append(
                    {
                        "content": parts[0],
                        "translation": parts[1] if len(parts) > 1 else "",
                        "explanation": parts[2] if len(parts) > 2 else "",
                    }
                )
        if items:
            return items

    # 按 --- 或连续空行切块
    blocks = re.split(r"\n\s*---\s*\n|\n\s*\n+", text)
    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # 单行竖线格式
        if "\n" not in block and "|" in block:
            parts = [p.strip() for p in block.split("|")]
            if parts and parts[0]:
                items.append(
                    {
                        "content": parts[0],
                        "translation": parts[1] if len(parts) > 1 else "",
                        "explanation": parts[2] if len(parts) > 2 else "",
                    }
                )
            continue

        content = ""
        translation = ""
        explanation = ""
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue

        # 带标签
        labeled = False
        buffer_key = "content"
        chunks: dict[str, list[str]] = {
            "content": [],
            "translation": [],
            "explanation": [],
        }
        for ln in lines:
            m = re.match(r"^(正文|内容|名句|成语)\s*[:：]\s*(.*)$", ln)
            if m:
                labeled = True
                buffer_key = "content"
                if m.group(2):
                    chunks["content"].append(m.group(2))
                continue
            m = re.match(r"^(翻译|译文|含义)\s*[:：]\s*(.*)$", ln)
            if m:
                labeled = True
                buffer_key = "translation"
                if m.group(2):
                    chunks["translation"].append(m.group(2))
                continue
            m = re.match(r"^(解释|解析|说明)\s*[:：]\s*(.*)$", ln)
            if m:
                labeled = True
                buffer_key = "explanation"
                if m.group(2):
                    chunks["explanation"].append(m.group(2))
                continue
            if labeled:
                chunks[buffer_key].append(ln)
            else:
                # 无标签：第一行正文，其后若含「翻译/解释」关键字则分流，否则并入解释
                if not content:
                    content = ln
                elif ln.startswith("翻译") or ln.startswith("译文") or ln.startswith("含义"):
                    translation = re.sub(r"^(翻译|译文|含义)\s*[:：]?\s*", "", ln)
                elif ln.startswith("解释") or ln.startswith("解析"):
                    explanation = re.sub(r"^(解释|解析|说明)\s*[:：]?\s*", "", ln)
                elif not translation:
                    translation = ln
                else:
                    explanation = (explanation + "\n" + ln).strip() if explanation else ln

        if labeled:
            content = "\n".join(chunks["content"]).strip()
            translation = "\n".join(chunks["translation"]).strip()
            explanation = "\n".join(chunks["explanation"]).strip()

        if content:
            items.append(
                {
                    "content": content,
                    "translation": translation,
                    "explanation": explanation,
                }
            )

    return items
