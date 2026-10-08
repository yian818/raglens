"""把实验结果渲染成单文件、离线可开的 HTML 报告。

不依赖任何 CDN（这样报告拷给别人、断网也能看）——这是调试台的基本素养：
你今天生成的报告，三个月后打开仍然应该完整可读。
"""

import datetime
import html
from typing import Dict


def _esc(s) -> str:
    return html.escape(str(s), quote=True)


def _histogram_svg(lengths: list) -> str:
    """分片长度分布直方图（纯 inline SVG，无外部依赖）。"""
    buckets = ["0-100", "100-200", "200-300", "300-400", "400-500", "500+"]
    counts = [0] * 6
    for L in lengths:
        idx = min(5, L // 100)
        counts[idx] += 1
    total = sum(counts) or 1
    max_c = max(counts) or 1

    bar_w, gap, height = 60, 14, 120
    width = len(buckets) * (bar_w + gap) + gap
    bars = []
    for i, c in enumerate(counts):
        h = int(c / max_c * height)
        x = gap + i * (bar_w + gap)
        y = height - h
        bars.append(
            f'<rect x="{x}" y="{y}" width="{bar_w}" height="{h}" fill="#1f6feb" rx="3"></rect>'
            f'<text x="{x + bar_w/2}" y="{y - 5}" text-anchor="middle" font-size="11" fill="#1f2328">{c}</text>'
            f'<text x="{x + bar_w/2}" y="{height + 14}" text-anchor="middle" font-size="10" fill="#57606a">{buckets[i]}</text>'
        )
    return (
        f'<svg width="{width}" height="{height + 26}" viewBox="0 0 {width} {height + 26}" '
        f'style="background:#fff;border:1px solid #d0d7de;border-radius:6px;">'
        + "".join(bars)
        + "</svg>"
    )


def render_html(experiment_name: str, cfg: dict, results: Dict[str, dict], embedder_note: str) -> str:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ---- 策略对比汇总表 ----
    summary_rows = []
    for name, r in results.items():
        agg = r["aggregate"]
        faith = [q["faithfulness"] for q in r["queries"] if q.get("faithfulness") is not None]
        faith_cell = f"{sum(faith)/len(faith):.2f}" if faith else "—"
        summary_rows.append(f"""
        <tr>
          <td class="mono">{_esc(name)}</td>
          <td>{r['n_chunks']}</td>
          <td>{r['avg_chunk_len']}</td>
          <td class="num">{agg['hit_rate@3']:.2f}</td>
          <td class="num strong">{agg['hit_rate@5']:.2f}</td>
          <td class="num">{agg['mrr@5']:.2f}</td>
          <td class="num">{faith_cell}</td>
        </tr>""")

    # ---- 每种策略下的逐 query 明细 ----
    detail_blocks = []
    for name, r in results.items():
        q_blocks = []
        for q in r["queries"]:
            rows = []
            expected = q["expected_doc"]
            for rank, item in enumerate(q["retrieved"], start=1):
                hit_cls = "hit" if item["doc"] == expected else ""
                marks = []
                if item["doc"] == expected:
                    marks.append("✓ 命中文档")
                if item.get("hint_hit"):
                    marks.append("🎯 命中目标片段")
                mark = " ".join(marks)
                rows.append(f"""
                <tr class="{hit_cls}">
                  <td>{rank}</td>
                  <td class="mono">{_esc(item['doc'])} {_esc(mark)}</td>
                  <td class="num">{item['score']}</td>
                  <td class="preview">{_esc(item['preview'])}…</td>
                </tr>""")
            faith_txt = f" · faithfulness={q['faithfulness']}" if q.get("faithfulness") is not None else ""
            q_blocks.append(f"""
            <div class="query">
              <div class="q-head">问：{_esc(q['query'])}{faith_txt}</div>
              <div class="q-meta">期望文档：<span class="mono">{_esc(expected)}</span>
              {('· 期望片段包含：' + _esc(q['expected_chunk_hint'])) if q.get('expected_chunk_hint') else ''}</div>
              <table><thead><tr><th>#</th><th>文档</th><th>得分</th><th>片段预览</th></tr></thead>
              <tbody>{''.join(rows)}</tbody></table>
            </div>""")
        agg = r["aggregate"]
        hist = _histogram_svg(r.get("chunk_lengths", []))
        detail_blocks.append(f"""
        <section>
          <h2>策略：{_esc(name)} <span class="tag">{r['n_chunks']} 个分片 · HitRate@5={agg['hit_rate@5']:.2f}</span></h2>
          <div class="sub">分片长度分布（字符数）：</div>
          {hist}
          {''.join(q_blocks)}
        </section>""")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RagLens 实验报告：{_esc(experiment_name)}</title>
<style>
  body {{ font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; margin: 0; background: #f6f8fa; color: #1f2328; line-height: 1.6; }}
  .wrap {{ max-width: 860px; margin: 0 auto; padding: 24px 16px 48px; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  .sub {{ color: #57606a; font-size: 13px; margin-bottom: 20px; }}
  h2 {{ font-size: 17px; border-left: 4px solid #1f6feb; padding-left: 8px; margin-top: 32px; }}
  table {{ border-collapse: collapse; width: 100%; background: #fff; font-size: 13px; margin: 8px 0 16px; }}
  th, td {{ border: 1px solid #d0d7de; padding: 6px 10px; text-align: left; vertical-align: top; }}
  th {{ background: #f0f3f6; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  td.strong {{ font-weight: 700; color: #1a7f37; }}
  td.preview {{ color: #57606a; }}
  tr.hit td {{ background: #dafbe1; }}
  .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; }}
  .tag {{ font-size: 12px; font-weight: 400; color: #57606a; background: #eef1f4; border-radius: 10px; padding: 2px 10px; margin-left: 8px; }}
  .query {{ background: #fff; border: 1px solid #d0d7de; border-radius: 8px; padding: 12px 14px; margin: 12px 0; }}
  .q-head {{ font-weight: 600; font-size: 14px; }}
  .q-meta {{ font-size: 12px; color: #57606a; margin: 2px 0 8px; }}
  .note {{ background: #fff8c5; border-radius: 6px; padding: 10px 12px; font-size: 12px; color: #4d3800; margin-top: 24px; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>🔬 RagLens 实验报告：{_esc(experiment_name)}</h1>
  <div class="sub">生成时间 {now} · 嵌入器：{_esc(embedder_note)} · top_k={cfg['retrieval'].get('top_k', 5)}</div>

  <h2>切片策略对比</h2>
  <table>
    <thead><tr><th>策略</th><th>分片数</th><th>平均分片长度</th><th>HitRate@3</th><th>HitRate@5</th><th>MRR@5</th><th>Faithfulness</th></tr></thead>
    <tbody>{''.join(summary_rows)}</tbody>
  </table>
  <div class="sub">指标说明：HitRate@k = 正确文档出现在前 k 名的 query 占比；MRR@5 = 正确文档排名倒数的平均；Faithfulness 仅当黄金问答集提供 answer 时计算。</div>

  {''.join(detail_blocks)}

  <div class="note">
    ⚠️ 本报告由 RagLens 生成。若使用默认 local 嵌入器，检索结果仅用于验证流程是否跑通，
    不能作为业务结论——正式评测请在配置中切换到 openai_compatible 接入真实 embedding 模型（如 bge-m3 / m3e）。
  </div>
</div>
</body>
</html>"""


def render_compare_html(left_name: str, left_results: dict, right_name: str, right_results: dict) -> str:
    """两次实验并排对比：同一策略名的指标差异，绿色=变好，红色=变差。"""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    for name in left_results:
        if name not in right_results:
            continue
        la, ra = left_results[name]["aggregate"], right_results[name]["aggregate"]
        for metric in ["hit_rate@3", "hit_rate@5", "mrr@5"]:
            l, r = la[metric], ra[metric]
            delta = r - l
            if abs(delta) < 1e-9:
                arrow, cls = "—", ""
            elif delta > 0:
                arrow, cls = f"▲ +{delta:.2f}", "up"
            else:
                arrow, cls = f"▼ {delta:.2f}", "down"
            rows.append(f"""
            <tr class="{cls}">
              <td class="mono">{_esc(name)}</td>
              <td>{_esc(metric)}</td>
              <td class="num">{l:.2f}</td>
              <td class="num">{r:.2f}</td>
              <td class="num">{arrow}</td>
            </tr>""")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RagLens 对比报告：{_esc(left_name)} → {_esc(right_name)}</title>
<style>
  body {{ font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; margin: 0; background: #f6f8fa; color: #1f2328; line-height: 1.6; }}
  .wrap {{ max-width: 720px; margin: 0 auto; padding: 24px 16px 48px; }}
  h1 {{ font-size: 20px; }}
  table {{ border-collapse: collapse; width: 100%; background: #fff; font-size: 13px; margin: 12px 0; }}
  th, td {{ border: 1px solid #d0d7de; padding: 7px 10px; text-align: left; }}
  th {{ background: #f0f3f6; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  tr.up td:last-child {{ color: #1a7f37; font-weight: 700; }}
  tr.down td:last-child {{ color: #cf222e; font-weight: 700; }}
  .mono {{ font-family: ui-monospace, Menlo, monospace; font-size: 12px; }}
  .sub {{ color: #57606a; font-size: 13px; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>⚖️ RagLens 对比报告</h1>
  <div class="sub">{now} · <b>{_esc(left_name)}</b> → <b>{_esc(right_name)}</b>（同一组黄金问答集）</div>
  <table>
    <thead><tr><th>策略</th><th>指标</th><th>改前</th><th>改后</th><th>变化</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
  <div class="sub">用法：把两次不同配置的实验结果放到一起，直接看出"这次改动到底让 RAG 变好了还是变坏了"。</div>
</div>
</body>
</html>"""
