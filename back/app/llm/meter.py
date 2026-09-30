"""Per-process token and failure counts by role, provider and model."""

import threading
from dataclasses import asdict, dataclass

from app.llm.types import Usage


@dataclass
class Tally:
    requests: int = 0
    failures: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


class UsageMeter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tallies: dict[tuple[str, str, str], Tally] = {}

    def _tally(self, role: str, provider: str, model: str) -> Tally:
        return self._tallies.setdefault((role, provider, model), Tally())

    def record(self, role: str, provider: str, model: str, usage: Usage) -> None:
        with self._lock:
            tally = self._tally(role, provider, model)
            tally.requests += 1
            tally.input_tokens += usage.input_tokens
            tally.output_tokens += usage.output_tokens

    def failure(self, role: str, provider: str, model: str) -> None:
        with self._lock:
            self._tally(role, provider, model).failures += 1

    def snapshot(self) -> list[dict[str, object]]:
        with self._lock:
            return [
                {"role": role, "provider": provider, "model": model, **asdict(tally)}
                for (role, provider, model), tally in sorted(self._tallies.items())
            ]
