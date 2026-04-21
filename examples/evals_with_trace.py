"""用 Trace 做 evals——没有新原语，只是把 Trace 当 eval log 用。

行业里 "evals"（LLM evaluation）常被做成一个独立框架：dataset 对象、runner
对象、scorer 对象、leaderboard……pyxis 里**不需要这一套**。evals 就是：

- 一个 Python dataset（list of 输入 + 期望）。
- 一个 `@step`，产结构化输出。
- 一个 `for` 循环跑完——失败不中断。
- 一个 `trace()` 捕获每次调用的 prompt / 输出 / usage / 延迟。
- 一些纯 Python 聚合：准确率、token 成本、p50/p95 延迟、错例清单。
- `Trace.to_jsonl(...)` 把原始 log 存盘——回放、diff、人审抽检都走它。

回归：**eval 不是框架，是 Python + trace 数据**。你要 A/B 不同模型？换个
`set_default_client(...)` 跑两遍就好。你要比两次 commit 的质量漂移？存两份
JSONL diff 即可。

跑起来：
    OPENROUTER_API_KEY=... uv run --env-file .env python examples/evals_with_trace.py

    # 跑完会在 runs/ 下生成 eval log：
    #   runs/eval_latest.jsonl   ← 原始调用，可回放 / 审计 / diff
"""

from __future__ import annotations

import os
import statistics
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from pyxis import flow, set_default_client, step, trace
from pyxis.providers import openrouter_client

MODEL = "openai/gpt-5.4-nano"
LOG_DIR = Path(__file__).parent / "runs"


# ---- Eval dataset：输入 + 期望 label + 可选备注 ----

DATASET: list[tuple[str, Literal["spam", "ham"], str]] = [
    ("【紧急】您的账户已被冻结，请点击下方链接立即核实身份", "spam", "钓鱼典型"),
    ("本周技术分享会周四下午 3 点，会议室 3B，主题 LLM 评测", "ham", "公司日常"),
    ("恭喜您获得 iPhone 15 抽奖资格，仅剩 3 小时点此领取", "spam", "奖品诱饵"),
    ("Hi 我是隔壁小王，周末有空一起打球吗？", "ham", "私人邀约"),
    ("信用卡账单已出：应还 ¥2,134，到期日 4 月 28 日", "ham", "账单提醒不是推销"),
    ("代开发票可抵税，联系微信 abc123，当天到账", "spam", "违规广告"),
    ("你的快递已到丰巢 A-3 格，取件码 9472", "ham", "物流通知"),
    ("独家内幕：三支股票下周必涨，加入群免费领", "spam", "荐股群"),
]


# ---- Schema：先给理由再给标签（防止"先定结论再编理由"） ----


class Classification(BaseModel):
    reasoning: str = Field(description="为什么这样分——一两句")
    label: Literal["spam", "ham"] = Field(description="最终分类")


@step(output=Classification, model=MODEL)
def classify(subject: str) -> str:
    """你是垃圾邮件分类器。先用一两句话说理由，再给最终标签。
    spam：钓鱼、推广奖品、违规广告、荐股等骚扰邮件。
    ham：工作、个人、交易通知等合规邮件。"""
    return f"邮件主题：{subject}"


# ---- eval 主体：跑 + 收指标；失败不中断 ----


@flow
def run_eval(dataset: list[tuple[str, str, str]]) -> list[tuple[str, str, str | None, float]]:
    """返回每条的 (expected, actual, error, latency_ms)。失败条 actual=None。"""
    records: list[tuple[str, str, str | None, float]] = []
    for text, expected, _ in dataset:
        t0 = time.perf_counter()
        try:
            out = classify(text)
            actual: str | None = out.label
            err = None
        except Exception as e:
            actual = None
            err = f"{e.__class__.__name__}: {e}"
        dt = (time.perf_counter() - t0) * 1000
        records.append((expected, actual or "(error)", err, dt))
    return records


def _percentile(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    k = max(0, min(len(s) - 1, round(p / 100 * (len(s) - 1))))
    return s[k]


def main() -> None:
    set_default_client(openrouter_client(api_key=os.environ["OPENROUTER_API_KEY"]))

    print(f"跑 {len(DATASET)} 条 eval 样本（模型 {MODEL}）...\n")
    with trace() as t:
        records = run_eval(DATASET)

    # ---- 明细 ----
    print("=== 明细 ===")
    correct = 0
    mistakes: list[tuple[str, str, str]] = []
    for (text, expected, _note), (_, actual, _err, dt) in zip(DATASET, records, strict=True):
        ok = actual == expected
        correct += int(ok)
        mark = "OK  " if ok else "FAIL"
        print(f"  [{mark}] [{dt:6.0f}ms] {expected:4} -> {actual:4}  | {text[:30]}")
        if not ok:
            mistakes.append((text, expected, actual))

    # ---- 聚合 ----
    n = len(records)
    latencies = [dt for _, _, _, dt in records]
    usage = t.total_usage()
    print("\n=== 指标 ===")
    print(f"准确率：{correct}/{n} = {correct / n:.1%}")
    print(f"总 tokens：{usage.total_tokens}（avg {usage.total_tokens / max(n, 1):.0f}/条）")
    print(
        f"延迟：p50={_percentile(latencies, 50):.0f}ms  "
        f"p95={_percentile(latencies, 95):.0f}ms  "
        f"mean={statistics.mean(latencies):.0f}ms"
    )
    print(f"失败（含 schema 校验错）：{len(t.errors())}")

    if mistakes:
        print("\n=== 错例（要人审的地方）===")
        for text, exp, act in mistakes:
            print(f"  期望 {exp} / 实际 {act}：{text}")

    # ---- 存 JSONL：原始调用全记录，用于回放 / diff ----
    LOG_DIR.mkdir(exist_ok=True)
    log_path = LOG_DIR / "eval_latest.jsonl"
    t.to_jsonl(log_path)
    print(f"\n=== 原始调用 log ===\n{log_path}")
    print("（用这个做 A/B：换 set_default_client(...) 再跑一次，diff 两个 jsonl）")


if __name__ == "__main__":
    main()
