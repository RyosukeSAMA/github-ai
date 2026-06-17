"""Apollo: god of music, poetry, art. Generates images, audio, and creative content."""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from pantheon.core.base import Role, Task, TaskResult, time_ms

log = logging.getLogger(__name__)


APOLLO_SYSTEM_PROMPT = """You are Apollo, the Greek god of music, poetry, art, oracles, light, and knowledge.
You are a creative director and multimedia producer.

Operating principles:
- Default to generating concrete creative artifacts (prompts, lyrics, scene descriptions)
  rather than just describing what *could* be done.
- For image prompts: be vivid and specific (subject, style, lighting, composition).
- For music: write lyrics with verse/chorus structure and tags for genre/mood/instruments.
- For video: write shot-by-shot storyboards.
- Match tone to the request (professional, playful, epic, etc.).
- Quality over quantity.

You focus on: image prompts, music lyrics, video storyboards, creative writing, branding.
You do NOT: do factual research (ask Athena), write production code (ask Hephaestus), or schedule tasks (ask Chronos).
"""


class Apollo(Role):
    name = "apollo"
    description = "Generates images, audio, video; writes lyrics and creative content"
    default_model = "gpt-4o"
    default_provider = "openai"
    default_temperature = 0.7
    tools: List[str] = ["image_gen", "video_gen", "tts"]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("system_prompt", APOLLO_SYSTEM_PROMPT)
        super().__init__(*args, **kwargs)

    def run(self, task: Task, context: Optional[List[dict]] = None) -> TaskResult:
        start = time_ms()
        context_block = self._format_context(context)

        user_prompt = (
            f"Creative request:\n{task.content}\n\n{context_block}"
            if context_block
            else f"Creative request:\n{task.content}"
        )

        try:
            content = self._make_llm_call(
                messages=[{"role": "user", "content": user_prompt}]
            )
            return TaskResult(
                role=self.name,
                content=content,
                success=True,
                duration_ms=time_ms() - start,
                metadata={"model": self.model, "provider": self.default_provider},
            )
        except Exception as e:
            log.exception("Apollo run failed")
            return TaskResult(
                role=self.name,
                content=f"[Apollo] Error: {e}",
                success=False,
                error=str(e),
                duration_ms=time_ms() - start,
            )
