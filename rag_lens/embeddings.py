"""Embedding 提供商：默认纯本地、零依赖、零网络。

设计取舍：很多"评测台"项目要求你先配 API Key 才能跑通 demo，冷启动门槛
直接劝退一批人。RagLens 默认带 LocalHashEmbedder——基于字符 n-gram 的
确定性哈希向量，不是真正的语义向量，但足以让整条链路在无 Key 环境下
跑通、看懂报表结构。正式评测时在配置里切到 OpenAI 兼容接口即可。
"""

import hashlib
import math
import os
from typing import List


# 常用 embedding 服务的"一键预设"：填一行 preset 就有默认 base_url/model，
# 配置里显式写的字段仍会覆盖预设值。解决的是"换个模型要翻文档抄地址"的摩擦。
EMBEDDING_PRESETS = {
    "bge-m3": {"provider": "openai_compatible", "base_url": "http://localhost:11434/v1", "model": "bge-m3"},
    "bge-large-zh": {"provider": "openai_compatible", "base_url": "http://localhost:11434/v1", "model": "bge-large-zh-v1.5"},
    "m3e": {"provider": "openai_compatible", "base_url": "http://localhost:11434/v1", "model": "m3e"},
    "openai": {"provider": "openai_compatible", "base_url": "https://api.openai.com/v1", "model": "text-embedding-3-small", "api_key_env": "OPENAI_API_KEY"},
}


def apply_presets(embedding_cfg: dict) -> dict:
    """把 preset 展开成完整配置：预设为默认值，显式字段优先。"""
    out = dict(embedding_cfg or {})
    preset = out.pop("preset", None)
    if preset:
        if preset not in EMBEDDING_PRESETS:
            raise ValueError(
                f"未知 embedding preset: {preset}（支持: {', '.join(EMBEDDING_PRESETS)}）"
            )
        merged = dict(EMBEDDING_PRESETS[preset])
        merged.update(out)  # 配置里显式写的覆盖预设
        return merged
    return out


def cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class LocalHashEmbedder:
    """字符 unigram + bigram 哈希到固定维向量，L2 归一化。"""

    def __init__(self, dim: int = 256):
        self.dim = dim

    def tokens(self, text: str):
        text = (text or "").lower()
        chars = [c for c in text.strip() if not c.isspace()]
        grams = set(chars)
        for i in range(len(chars) - 1):
            grams.add(chars[i] + chars[i + 1])
        return grams

    def encode(self, texts: List[str]) -> List[List[float]]:
        out = []
        for t in texts:
            vec = [0.0] * self.dim
            for g in self.tokens(t):
                h = int(hashlib.md5(g.encode("utf-8")).hexdigest(), 16)
                idx = h % self.dim
                sign = 1.0 if (h >> 8) % 2 == 0 else -1.0
                vec[idx] += sign
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            out.append([v / norm for v in vec])
        return out


class OpenAICompatibleEmbedder:
    """OpenAI 兼容的 /v1/embeddings 客户端（Ollama / DeepSeek / vLLM 等均可）。"""

    def __init__(self, base_url: str, model: str, api_key: str):
        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError(
                "远程 embedding 需要额外依赖：pip install openai"
            ) from e
        self.client = OpenAI(base_url=base_url, api_key=api_key or "not-needed")
        self.model = model

    def encode(self, texts: List[str]) -> List[List[float]]:
        resp = self.client.embeddings.create(model=self.model, input=texts)
        return [d.embedding for d in resp.data]


def build_embedder(cfg: dict):
    """根据配置构造嵌入器（支持 embedding.preset 一键预设）。"""
    e = apply_presets(cfg["embedding"])
    provider = e.get("provider", "local")
    if provider == "local":
        return LocalHashEmbedder(dim=int(e.get("dim", 256)))
    if provider == "openai_compatible":
        api_key = os.environ.get(e.get("api_key_env", "OPENAI_API_KEY"), "")
        return OpenAICompatibleEmbedder(
            base_url=e["base_url"], model=e["model"], api_key=api_key
        )
    raise ValueError(f"未知 embedding provider: {provider}（支持 local / openai_compatible）")
