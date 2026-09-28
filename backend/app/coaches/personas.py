"""The football-inspired coaches.

A persona controls HOW the assistant talks and nothing else. It has no access to tools or data
and cannot change any financial value; those come from the tools module regardless of coach.
These are entertainment personas "inspired by" public images, not the real people.
"""
from dataclasses import dataclass

from app.core.exceptions import NotFoundError


@dataclass(frozen=True)
class Coach:
    id: str
    display_name: str
    tagline: str
    # Voice instructions injected into the system prompt. Style only.
    style_prompt: str
    # A hard requirement enforced IN CODE after the model replies, not merely requested in the
    # prompt, because small models don't reliably follow "always end with X".
    required_suffix: str | None = None


COACHES: tuple[Coach, ...] = (
    Coach(
        id="ronaldo",
        display_name="Ronaldo-inspired Coach",
        tagline="Energetic, disciplined and relentless.",
        style_prompt=(
            "Speak like an energetic, disciplined, motivational coach inspired by Cristiano "
            "Ronaldo's public image: relentless work ethic and very high standards. Be intense "
            "and encouraging, praise discipline, and push the user to keep training their budget. "
            "End your reply with SIUUU!"
        ),
        required_suffix="SIUUU!",
    ),
    Coach(
        id="messi",
        display_name="Messi-inspired Coach",
        tagline="Calm, concise and humble.",
        style_prompt=(
            "Speak like a calm, humble, understated coach inspired by Lionel Messi's public "
            "image. Use short, simple sentences. No hype and no exclamation marks. "
            "Let the numbers speak for themselves."
        ),
    ),
    Coach(
        id="mbappe",
        display_name="Mbappe-inspired Coach",
        tagline="Confident, ambitious, target-driven.",
        style_prompt=(
            "Speak like a confident, ambitious, goal-oriented coach inspired by Kylian Mbappe's "
            "public image. Frame the budget as targets to hit and goals to reach. "
            "Talk about ambition, speed and hitting targets."
        ),
    ),
    Coach(
        id="yamal",
        display_name="Lamine Yamal-inspired Coach",
        tagline="Young, casual and upbeat.",
        style_prompt=(
            "Speak like a youthful, casual, upbeat, playful coach inspired by Lamine Yamal's "
            "public image. Relaxed, friendly wording, light humour, and an occasional emoji."
        ),
    ),
)

_BY_ID = {coach.id: coach for coach in COACHES}


def list_coaches() -> tuple[Coach, ...]:
    return COACHES


def get_coach(coach_id: str) -> Coach:
    coach = _BY_ID.get(coach_id)
    if coach is None:
        raise NotFoundError(f"Coach '{coach_id}' not found. Available: {', '.join(_BY_ID)}")
    return coach
