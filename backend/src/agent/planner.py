"""Multi-model task planner.

For complex tasks, calls Gemini Pro to decompose the task into sub-goals
before handing off to the Gemini Flash–powered step-by-step agent loop.
"""

from __future__ import annotations

import re

from langchain_core.messages import HumanMessage

from src.agent.llm import get_pro_llm
from src.agent.prompts import PLANNING_PROMPT
from src.config import Settings, get_settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Conjunctions / patterns that hint at multi-step tasks
_COMPLEXITY_PATTERNS = re.compile(
    r"\b(and then|after that|first .* then|next|finally|once .* done|step \d)\b",
    re.IGNORECASE,
)


def is_complex_task(task: str, settings: Settings | None = None) -> bool:
    """Heuristic: decide whether a task warrants a planning call to Gemini Pro.

    A task is considered complex if:
    - It has more words than ``settings.complexity_word_threshold``, OR
    - It contains multi-step conjunction patterns.
    """
    s = settings or get_settings()
    word_count = len(task.split())
    if word_count > s.complexity_word_threshold:
        return True
    if _COMPLEXITY_PATTERNS.search(task):
        return True
    return False


async def generate_plan(task: str, context: str | None = None, settings: Settings | None = None) -> str:
    """Call Gemini Pro to produce a numbered plan for *task*.

    Returns the raw plan text (numbered list) which is prepended to the
    agent's task string so Flash can follow it step-by-step.
    """
    s = settings or get_settings()
    pro_llm = get_pro_llm(s)

    context_section = ""
    if context:
        context_section = f"Additional context:\n{context}"

    prompt = PLANNING_PROMPT.format(task=task, context_section=context_section)

    logger.info("generating_plan", task_preview=task[:80])
    response = await pro_llm.ainvoke([HumanMessage(content=prompt)])
    plan_text = response.content if hasattr(response, "content") else str(response)

    logger.info("plan_generated", plan_length=len(plan_text))
    return plan_text


def build_planned_task(original_task: str, plan: str) -> str:
    """Combine the original task with the generated plan into an augmented prompt."""
    return (
        f"TASK: {original_task}\n\n"
        f"PLAN (follow these steps in order):\n{plan}\n\n"
        f"Execute the plan above step by step. After completing all steps, "
        f"provide a final summary of what was accomplished."
    )
