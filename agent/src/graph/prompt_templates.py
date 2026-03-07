from __future__ import annotations

from typing import Optional


INTENT_GUIDANCE: dict[str, str] = {
    "recommend": "优先给出候选目的地对比（适合人群、季节、预算级别）。",
    "attractions": "优先给出景点清单、开放时间、建议游玩时长与动线。",
    "itinerary": "优先给出按天行程，含上午/下午/晚间安排与交通建议。",
    "budget": "优先给出分项预算（住宿、交通、门票、餐饮）与总预算范围。",
    "tips": "优先给出风险提醒、出行准备清单和可执行注意事项。",
    "general": "优先直接回答并在信息不足时补充1-2个澄清问题。",
    "unclear": "先简短确认需求，再给出可选方向。",
}


def build_system_prompt(base_prompt: str, intent: Optional[str]) -> str:
    guidance = INTENT_GUIDANCE.get((intent or "general").lower(), INTENT_GUIDANCE["general"])
    return f"{base_prompt}\n\n任务策略:\n{guidance}"


def build_answer_prompt(
    user_question: str,
    context: str,
    tools_used: list[str],
    intent: Optional[str],
) -> str:
    guidance = INTENT_GUIDANCE.get((intent or "general").lower(), INTENT_GUIDANCE["general"])
    if tools_used:
        return (
            f"用户问题: {user_question}\n\n"
            f"{context}\n\n"
            f"任务类型: {intent or 'general'}\n"
            f"回答要求: {guidance}\n"
            "请基于工具结果回答，优先引用 source/fetched_at，涉及时效信息时明确时间。"
        )
    return (
        f"用户问题: {user_question}\n\n"
        f"任务类型: {intent or 'general'}\n"
        f"回答要求: {guidance}\n"
        "请直接给出清晰、可执行的建议。"
    )


def build_direct_prompt(user_question: str, intent: Optional[str]) -> str:
    guidance = INTENT_GUIDANCE.get((intent or "general").lower(), INTENT_GUIDANCE["general"])
    return (
        f"用户问题: {user_question}\n\n"
        f"任务类型: {intent or 'general'}\n"
        f"回答要求: {guidance}\n"
        "若关键信息不足，请在结尾提出最多2个澄清问题。"
    )
