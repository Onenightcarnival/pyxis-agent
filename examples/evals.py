"""跑一个小数据集，记录准确率、延迟、错例和原始调用 log。
组合是 Python list（输入 + 期望）+ 一个 `@step` 出结构化结果 + 一个
`for` 循环。聚合用 `statistics.mean` / `Counter` / 排序取分位，都是
几行 Python。原始调用 log 自己 `json.dumps` 落盘。
A/B 两个模型时，换 `client` / `MODEL` 跑两遍，再比较两份 JSONL。
跑起来：
    OPENROUTER_API_KEY=... uv run --env-file .env python examples/evals.py
    # 跑完会在 runs/ 下生成原始调用 log：
    #   runs/eval_latest.jsonl
"""

from __future__ import annotations

import json
import os
import statistics
import time
from inspect import cleandoc
from pathlib import Path
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, Field

from pyxis import step

MODEL = "openai/gpt-5.4-nano"
LOG_DIR = Path(__file__).parent / "runs"
openrouter = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
)
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
    reasoning: str = Field(description="为什么这样分，一两句")
    label: Literal["spam", "ham"] = Field(description="最终分类")


@step(output=Classification, model=MODEL, client=openrouter, params={"temperature": 0})
def classify(subject: str) -> str:
    return cleandoc(
        f"""
        你是垃圾邮件分类器。先用一两句话说理由，再给最终标签。

        spam：钓鱼、推广奖品、违规广告、荐股等骚扰邮件。
        ham：工作、个人、交易通知等合规邮件。

        邮件主题：{subject}
        """
    )


# ---- eval 主体：跑 + 收指标；失败不中断 ----
def run_eval(
    dataset: list[tuple[str, str, str]],
) -> list[dict]:
    """返回每条的调用记录。失败条 actual=None。"""
    records: list[dict] = []
    for text, expected, note in dataset:
        t0 = time.perf_counter()
        try:
            out = classify(text)
            actual: str | None = out.label
            reasoning = out.reasoning
            err = None
        except Exception as e:
            actual = None
            reasoning = None
            err = f"{e.__class__.__name__}: {e}"
        dt = (time.perf_counter() - t0) * 1000
        records.append(
            {
                "text": text,
                "expected": expected,
                "actual": actual,
                "reasoning": reasoning,
                "note": note,
                "latency_ms": round(dt, 1),
                "error": err,
            }
        )
    return records


def _percentile(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    k = max(0, min(len(s) - 1, round(p / 100 * (len(s) - 1))))
    return s[k]


def main() -> None:
    print(f"跑 {len(DATASET)} 条 eval 样本（模型 {MODEL}）...\n")
    records = run_eval(DATASET)
    # ---- 明细 ----
    print("=== 明细 ===")
    correct = 0
    for r in records:
        ok = r["actual"] == r["expected"]
        correct += int(ok)
        mark = "OK  " if ok else "FAIL"
        actual_s = str(r["actual"] or "(error)")
        print(
            f"  [{mark}] [{r['latency_ms']:6.0f}ms] {r['expected']:4} -> {actual_s:4}  | {r['text'][:30]}"
        )
    # ---- 聚合 ----
    n = len(records)
    latencies = [r["latency_ms"] for r in records]
    errors = [r for r in records if r["error"]]
    print("\n=== 指标 ===")
    print(f"准确率：{correct}/{n} = {correct / n:.1%}")
    print(
        f"延迟：p50={_percentile(latencies, 50):.0f}ms  "
        f"p95={_percentile(latencies, 95):.0f}ms  "
        f"mean={statistics.mean(latencies):.0f}ms"
    )
    print(f"失败（含 schema 校验错）：{len(errors)}")
    mistakes = [r for r in records if not r["error"] and r["actual"] != r["expected"]]
    if mistakes:
        print("\n=== 错例（要人审的地方）===")
        for r in mistakes:
            print(f"  期望 {r['expected']} / 实际 {r['actual']}：{r['text']}")
    # ---- 存 JSONL：普通 Python 一把梭 ----
    LOG_DIR.mkdir(exist_ok=True)
    log_path = LOG_DIR / "eval_latest.jsonl"
    with log_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n=== 原始调用 log ===\n{log_path}")


if __name__ == "__main__":
    main()
