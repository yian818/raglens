"""加载与校验 RagLens 配置文件（YAML）。"""

from pathlib import Path

import yaml

REQUIRED_SECTIONS = ["data", "chunker", "embedding", "retrieval"]


def load_config(path: str) -> dict:
    """读取 YAML 配置并做最小校验。

    相对路径一律相对于配置文件所在目录解析，保证 `raglens run --config xxx.yaml`
    在任何工作目录下结果一致——这是评测可复现性的前提之一。
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}")
    with open(p, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    for key in REQUIRED_SECTIONS:
        if key not in cfg:
            raise ValueError(f"配置缺少必填段: {key}")
    if not cfg["chunker"].get("strategies"):
        raise ValueError("chunker.strategies 至少要配一种切片策略")

    cfg.setdefault("experiment", {"name": "未命名实验"})
    cfg.setdefault("rerank", {"enabled": False})
    cfg.setdefault("eval", {"metrics": ["hit_rate@3", "hit_rate@5", "mrr@5"]})
    # 记录基准目录，供后续把相对路径锚定到配置文件旁边
    cfg["_base_dir"] = str(p.parent)
    return cfg


def resolve_path(cfg: dict, rel: str) -> str:
    """把配置里的相对路径解析为绝对路径（相对配置文件所在目录）。"""
    p = Path(rel)
    if not p.is_absolute():
        p = Path(cfg["_base_dir"]) / p
    return str(p)
