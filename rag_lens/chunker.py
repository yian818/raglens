"""文档切片策略库。

为什么单独成模块：切片策略是 RAG 里最容易被"凭感觉"拍脑袋调的环节，
RagLens 的核心卖点就是把不同策略的结果放到同一张报表上对比。
"""

import re
from dataclasses import dataclass

# 中英文句末标点都作为句子边界
_SENT_SPLIT = re.compile(r"(?<=[。！？；!?;])")


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
    else:
        raise ValueError(f"未知切片类型: {stype}（支持 fixed / sentence）")

    return [
        Chunk(chunk_id=f"{name}:{doc_id}:{i}", doc_id=doc_id, text=piece, char_len=len(piece))
        for piece, i in pieces
    ]
