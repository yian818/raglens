"""样例语料与黄金问答集加载。"""

import json
from pathlib import Path

from .config import resolve_path

DOC_SUFFIX = (".md", ".txt")


def load_docs(cfg: dict) -> dict:
    """读取 docs_dir 下所有 .md/.txt，返回 {doc_id: text}。"""
    docs_dir = Path(resolve_path(cfg, cfg["data"]["docs_dir"]))
    if not docs_dir.exists():
        raise FileNotFoundError(f"文档目录不存在: {docs_dir}")

    docs = {}
    for f in sorted(docs_dir.iterdir()):
        if f.suffix.lower() in DOC_SUFFIX:
            docs[f.name] = f.read_text(encoding="utf-8")
    if not docs:
        raise ValueError(f"文档目录里没有 .md/.txt 文件: {docs_dir}")
    return docs


def load_golden_qa(cfg: dict) -> list:
    """读取 golden_qa.jsonl，每行 {"query": ..., "expected_doc": ...}。"""
    path = Path(resolve_path(cfg, cfg["data"]["golden_qa"]))
    if not path.exists():
        raise FileNotFoundError(f"黄金问答集不存在: {path}")

    items = []
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if "query" not in obj or "expected_doc" not in obj:
                raise ValueError(f"golden_qa 第 {lineno} 行缺少 query/expected_doc")
            items.append(obj)
    if not items:
        raise ValueError("golden_qa 为空，至少需要一条问答")
    return items
