from __future__ import annotations

import random
import string
from typing import Dict, List, Tuple

from security import digest_secret, verify_secret

SCRIBBLE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
EMOJI_PROMPTS: List[Tuple[str, str]] = [
    ("Pick the shield emoji.", "🛡️"),
    ("Pick the laptop emoji.", "💻"),
    ("Pick the lock emoji.", "🔒"),
    ("Pick the warning emoji.", "⚠️"),
    ("Pick the chart emoji.", "📈"),
    ("Pick the server emoji.", "🖥️"),
]
EMOJI_POOL = ["🛡️", "💻", "🔒", "⚠️", "📈", "🖥️", "🔍", "🧠", "🛰️", "🧪"]


def _shuffle_options(answer: str, size: int = 4) -> List[str]:
    distractors = [emoji for emoji in EMOJI_POOL if emoji != answer]
    options = [answer] + random.sample(distractors, k=size - 1)
    random.shuffle(options)
    return options


def make_human_challenge_bundle() -> Dict[str, object]:
    scribble_code = "".join(random.choice(SCRIBBLE_ALPHABET) for _ in range(5))
    prompt, answer = random.choice(EMOJI_PROMPTS)
    emoji_options = _shuffle_options(answer)
    return {
        "payload": {
            "scribble": {"code": scribble_code},
            "emoji": {"prompt": prompt, "options": emoji_options},
        },
        "answers": {
            "scribble": digest_secret(scribble_code.upper()),
            "emoji": digest_secret(answer),
        },
    }


def validate_human_bundle(answers: Dict[str, str], scribble_input: str, emoji_input: str) -> Tuple[bool, str]:
    normalized_scribble = "".join(ch for ch in scribble_input.upper() if ch.isalnum())
    if not verify_secret(answers.get("scribble", ""), normalized_scribble):
        return False, "The scribble code did not match. Try the refreshed card."
    if not verify_secret(answers.get("emoji", ""), emoji_input):
        return False, "The emoji pick was off. Give it another shot."
    return True, "Human verification complete."
