"""
从项目根目录的内容文件同步到数据库。

用法：在项目根目录新建纯文本文件，文件名 = 分类名，例如：
  成语
  名句
  文学常识

每行一条，推荐格式：
  词语：含义或解释

启动网站时会自动读入并写入对应科目分类（默认语文）。
已存在的相同「正文」不会重复添加；含义有变化时会更新翻译。
"""

from __future__ import annotations

import re
from pathlib import Path

from app import BASE_DIR, db
from app.models import LearnCategory, LearnItem, Subject

# 文件名 → (科目 slug, 分类名)
CONTENT_FILE_MAP = {
    "成语": ("chinese", "成语"),
    "名句": ("chinese", "名句"),
    "文学常识": ("chinese", "文学常识"),
    "文言文": ("chinese", "文言文"),
}


def parse_colon_lines(raw: str) -> list[dict[str, str]]:
    """解析「词语：含义」一行一条。"""
    items: list[dict[str, str]] = []
    text = (raw or "").replace("\r\n", "\n").replace("\r", "\n")
    for ln in text.split("\n"):
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        # 全角/半角冒号
        m = re.match(r"^(.+?)[:：]\s*(.+)$", ln)
        if not m:
            # 没有冒号则整行当正文
            items.append({"content": ln, "translation": "", "explanation": ""})
            continue
        word = m.group(1).strip()
        meaning = m.group(2).strip()
        if not word:
            continue
        items.append(
            {
                "content": word,
                "translation": meaning,
                "explanation": "",
            }
        )
    return items


def sync_content_files() -> dict[str, int]:
    """读取根目录内容文件并写入数据库。返回 {文件名: 新增条数}。"""
    stats: dict[str, int] = {}

    for filename, (subject_slug, category_name) in CONTENT_FILE_MAP.items():
        path = BASE_DIR / filename
        if not path.is_file():
            continue

        subject = Subject.query.filter_by(slug=subject_slug).first()
        if subject is None:
            continue

        category = LearnCategory.query.filter_by(
            subject_id=subject.id, name=category_name
        ).first()
        if category is None:
            category = LearnCategory(
                subject_id=subject.id,
                name=category_name,
                sort_order=50,
            )
            db.session.add(category)
            db.session.flush()

        raw = path.read_text(encoding="utf-8")
        parsed = parse_colon_lines(raw)
        if not parsed:
            stats[filename] = 0
            continue

        existing = {
            item.content: item
            for item in LearnItem.query.filter_by(category_id=category.id).all()
        }
        added = 0
        order_base = len(existing)
        for i, row in enumerate(parsed):
            content = row["content"]
            if content in existing:
                item = existing[content]
                # 更新含义（若文件里改了）
                if row["translation"] and item.translation != row["translation"]:
                    item.translation = row["translation"]
                continue
            db.session.add(
                LearnItem(
                    category_id=category.id,
                    content=content,
                    translation=row["translation"],
                    explanation=row["explanation"],
                    sort_order=order_base + i,
                )
            )
            existing[content] = None  # type: ignore
            added += 1

        stats[filename] = added

    db.session.commit()
    return stats
