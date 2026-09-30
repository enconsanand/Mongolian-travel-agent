"""Check the configured providers with real calls: ``make llm-smoke`` (or ``python -m app.llm.smoke "text"``).

Runs a planner tool call, a structured-output call and a writer reply, then prints usage. Spends a little of
the Workers AI free allocation.
"""

import sys

from pydantic import BaseModel, Field

from app.llm import LLMError, Message, ToolSpec, configured_gateway

DEFAULT_PROMPT = "Тэрэлжид 10-р сарын 5-наас 2 шөнө 2 хүн байх гэр буудал хайж байна."

FIND_STAYS = ToolSpec(
    name="find_stays_near",
    description="Find places to stay near a Mongolian destination for given dates and guests.",
    parameters={
        "type": "object",
        "properties": {
            "place": {"type": "string", "description": "Destination name, e.g. Terelj"},
            "check_in": {"type": "string", "description": "YYYY-MM-DD"},
            "nights": {"type": "integer", "minimum": 1},
            "guests": {"type": "integer", "minimum": 1},
        },
        "required": ["place", "nights", "guests"],
    },
)


class TripIntent(BaseModel):
    destination: str = Field(description="Destination in English")
    nights: int = Field(ge=1)
    guests: int = Field(ge=1)
    language: str = Field(description="Language of the request: mn or en")


def main(prompt: str) -> int:
    gateway = configured_gateway()
    failed = False

    print("== planner: tool call")
    try:
        result = gateway.complete(
            "planner",
            [Message.system("You plan trips in Mongolia. Use the tools."), Message.user(prompt)],
            tools=[FIND_STAYS],
        )
        print(f"{result.provider}/{result.model}")
        print("text:", result.text[:300] or "-")
        for call in result.tool_calls:
            print("tool:", call.name, call.arguments)
    except LLMError as exc:
        failed = True
        print("FAILED:", exc.code, exc)

    print("\n== planner: structured output")
    try:
        intent = gateway.structured("planner", [Message.user(prompt)], TripIntent)
        print(intent.model_dump())
    except LLMError as exc:
        failed = True
        print("FAILED:", exc.code, exc)

    print("\n== writer: Mongolian reply")
    try:
        reply = gateway.complete(
            "writer",
            [Message.system("Хэрэглэгчид монгол хэлээр товч, эелдэг хариулна уу."), Message.user(prompt)],
        )
        print(f"{reply.provider}/{reply.model}")
        print(reply.text[:500])
    except LLMError as exc:
        failed = True
        print("FAILED:", exc.code, exc)

    print("\n== usage")
    for row in gateway.meter.snapshot():
        print(row)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(" ".join(sys.argv[1:]) or DEFAULT_PROMPT))
