from __future__ import annotations

import re
from typing import Any

from app.skills.base import BaseSkill

FACT_PAIRS = [
    (("已完成", "完成验收", "已验收", "验收通过"), ("正在", "未完成", "进行中", "尚未")),
    (("通过", "成功"), ("失败", "未通过", "驳回")),
    (("同意", "批准"), ("否决", "拒绝", "不同意")),
    (("增加", "上升", "提高", "提升"), ("减少", "下降", "降低")),
    (("是", "属于"), ("不是", "不属于", "非")),
]

NEGATION = re.compile(r"(不|未|无|非|没有|禁止)")


class FactSkill(BaseSkill):
    name = "fact_analysis"
    version = "1.0.0"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        before = context.get("before", "")
        after = context.get("after", "")
        return {
            "is_fact_change": self.is_fact_change(before, after),
            "looks_factual": self.looks_factual(before) or self.looks_factual(after),
        }

    def looks_factual(self, text: str) -> bool:
        keys = ["完成", "验收", "通过", "失败", "批准", "否决", "正在", "未", "已"]
        return any(k in text for k in keys)

    def is_fact_change(self, before: str, after: str) -> bool:
        b, a = before.strip(), after.strip()
        if not b or not a or b == a:
            return False
        for pos_group, neg_group in FACT_PAIRS:
            b_pos = any(x in b for x in pos_group)
            a_neg = any(x in a for x in neg_group)
            b_neg = any(x in b for x in neg_group)
            a_pos = any(x in a for x in pos_group)
            if (b_pos and a_neg) or (b_neg and a_pos):
                return True
        # negation flip on overlapping stem
        if bool(NEGATION.search(b)) != bool(NEGATION.search(a)):
            # only if shared content words
            shared = set(re.findall(r"[\u4e00-\u9fff]{2,}", b)) & set(
                re.findall(r"[\u4e00-\u9fff]{2,}", a)
            )
            if shared:
                return True
        return False
