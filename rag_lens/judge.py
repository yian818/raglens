"""答案层评测：faithfulness（答案是否忠于检索上下文）。

v0.2 默认只提供 lexical mock：答案词面有多少比例能在上下文里找到。
它不是真的 LLM 裁判，但能让"faithfulness"这一列在无 Key 环境下先跑通流程；
正式使用时切到 openai_compatible，接 DeepSeek / GPT 等做裁判。
"""

from .embeddings import LocalHashEmbedder

_lex = LocalHashEmbedder()


def mock_faithfulness(answer: str, contexts: list) -> float:
    """答案的字符 n-gram 中有多少比例出现在上下文里（0~1）。"""
    if not answer or not contexts:
        return 0.0
    answer_tokens = _lex.tokens(answer)
    if not answer_tokens:
        return 0.0
    ctx_tokens = set()
    for c in contexts:
        ctx_tokens |= _lex.tokens(c)
    return round(len(answer_tokens & ctx_tokens) / len(answer_tokens), 4)


def llm_faithfulness(answer: str, contexts: list, question: str, cfg: dict) -> float:
    """OpenAI 兼容接口做 LLM 裁判。需要 pip install openai。"""
    import os

    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError("LLM 裁判需要额外依赖：pip install openai") from e

    j = cfg.get("eval", {}).get("judge", {})
    api_key = os.environ.get(j.get("api_key_env", "OPENAI_API_KEY"), "")
    client = OpenAI(
        base_url=j.get("base_url", "http://localhost:11434/v1"),
        api_key=api_key or "not-needed",
    )
    prompt = (
        "请判断下面这个答案是否完全基于给定上下文，不得使用外部知识。"
        "只回答一个数字 0 或 1：1=完全忠于上下文，0=有编造。\n\n"
        f"问题：{question}\n上下文：{''.join(contexts)}\n答案：{answer}\n分数："
    )
    resp = client.chat.completions.create(
        model=j.get("model", "qwen2.5"), messages=[{"role": "user", "content": prompt}]
    )
    text = resp.choices[0].message.content.strip()
    return 1.0 if text.startswith("1") else 0.0


def judge_faithfulness(answer: str, contexts: list, question: str, cfg: dict) -> float:
    provider = cfg.get("eval", {}).get("judge", {}).get("provider", "none")
    if provider == "none" or not answer:
        return None
    if provider == "mock":
        return mock_faithfulness(answer, contexts)
    if provider == "openai_compatible":
        return llm_faithfulness(answer, contexts, question, cfg)
    raise ValueError(f"未知 judge provider: {provider}")
