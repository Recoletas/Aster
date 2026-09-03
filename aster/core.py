"""Deterministic response strategy for offline runs and tests."""


def echo_reply(history: list[tuple[str, str]]) -> str:
    """Reply deterministically from the alternating conversation history.

    ``history`` entries are ``(role, text)`` pairs ending with the current
    user message; the strategy only counts the user turns.
    """

    turn = sum(1 for role, _ in history if role == "user")
    return f"echo #{turn}: {history[-1][1]}"
