"""文档切片策略库。

为什么单独成模块：切片策略是 RAG 里最容易被"凭感觉"拍脑袋调的环节，
RagLens 的核心卖点就是把不同策略的结果放到同一张报表上对比。
"""

import re
from dataclasses import dataclass

# 中英文句末标点都作为句子边界
_SENT_SPLIT = re.compile(r"(?<=[。！？；!?;])")
# Markdown 标题行（# 到 ######）
_HEADING = re.compile(r"^#{1,6}\s+.*$", re.M)


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    text: str
    char_len: int


def fixed_split(text: str, chunk_size: int, overlap: int):
    """按字符定长切分，带 overlap 重叠。返回 [(piece, index), ...]。"""
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")
    if overlap >= chunk_size:
        raise ValueError("overlap 必须小于 chunk_size")
    if overlap < 0:
        raise ValueError("overlap 不能为负")

    pieces = []
    i, n, idx = 0, len(text), 0
    while i < n:
        j = min(i + chunk_size, n)
        piece = text[i:j].strip()
        if piece:
            pieces.append((piece, idx))
            idx += 1
        if j >= n:
            break
        i = j - overlap
    return pieces


def sentence_split(text: str, max_len: int):
    """先按句子切，再把短句贪心拼到不超过 max_len。"""
    if max_len <= 0:
        raise ValueError("max_len 必须大于 0")
    raw = _SENT_SPLIT.split(text)
    sents = [s.strip() for s in raw if s and s.strip()]

    pieces, buf, idx = [], "", 0
    for s in sents:
        if not buf or len(buf) + len(s) <= max_len:
            buf += s
        else:
            pieces.append((buf, idx))
            idx += 1
            buf = s
    if buf:
        pieces.append((buf, idx))
    return pieces


def markdown_heading_split(text: str, max_len: int = 0):
    """按 Markdown 标题层级切分：每个章节保留标题本身作为开头，语义最完整。

    max_len > 0 时，超长章节再按句子贪心二次切分（标题会保留在每段前面）。
    """
    matches = list(_HEADING.finditer(text))
    if not matches:
        piece = text.strip()
        return [(piece, 0)] if piece else []

    raw_sections = []
    if matches[0].start() > 0:
        pre = text[: matches[0].start()].strip()
        if pre:
            raw_sections.append(pre)
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sec = text[m.start():end].strip()
        if sec:
            raw_sections.append(sec)

    if max_len <= 0:
        return [(s, idx) for idx, s in enumerate(raw_sections)]

    # 超长章节二次切分，保留标题上下文
    pieces, idx = [], 0
    for sec in raw_sections:
        lines = sec.split("\n", 1)
        heading = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        if len(sec) <= max_len or not body:
            pieces.append((sec, idx))
            idx += 1
            continue
        sents = [s.strip() for s in _SENT_SPLIT.split(body) if s and s.strip()]
        buf = ""
        for s in sents:
            cand = (heading + "\n" + buf) if buf else heading + "\n" + s
            if len(cand) <= max_len:
                buf = (buf + s) if buf else s
            else:
                if buf:
                    pieces.append((heading + "\n" + buf, idx))
                    idx += 1
                buf = s
        if buf:
            pieces.append((heading + "\n" + buf, idx))
            idx += 1
    return pieces


def chunk_document(doc_id: str, text: str, strategy_cfg: dict):
    """按某一种策略切分一篇文档，返回 Chunk 列表。"""
    stype = strategy_cfg["type"]
    name = strategy_cfg["name"]
    if stype == "fixed":
        pieces = fixed_split(
            text,
            chunk_size=int(strategy_cfg["chunk_size"]),
            overlap=int(strategy_cfg.get("overlap", 0)),
        )
    elif stype == "sentence":
        pieces = sentence_split(text, max_len=int(strategy_cfg.get("max_len", 300)))
    elif stype == "markdown_heading":
        pieces = markdown_heading_split(
            text, max_len=int(strategy_cfg.get("max_len", 0))
        )
    else:
        raise ValueError(f"未知切片类型: {stype}（支持 fixed / sentence / markdown_heading）")

    return [
        Chunk(chunk_id=f"{name}:{doc_id}:{i}", doc_id=doc_id, text=piece, char_len=len(piece))
        for piece, i in pieces
    ]
