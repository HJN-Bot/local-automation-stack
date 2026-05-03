from dataclasses import dataclass, field
from typing import Iterator, Protocol, Optional


@dataclass
class Task:
    id: str
    type: str
    content: str
    context: dict = field(default_factory=dict)


@dataclass
class Step:
    action: str
    summary: str
    raw: Optional[dict] = None


class Executor(Protocol):
    bot_name: str

    def execute(self, task: Task) -> Iterator[Step]:
        ...
