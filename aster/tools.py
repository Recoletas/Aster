"""Customer-service tools: pydantic schemas, validation, and an audit log.

The registry is the permission boundary: only registered tools exist for
the model. Validation failures return an error string so the model can
correct itself via the next tool_result instead of breaking the loop.
"""

import json

from pydantic import BaseModel, Field, ValidationError

AUDIT_LIMIT = 200


class Tool:
    """One callable capability with a pydantic-validated argument model."""

    def __init__(
        self,
        name: str,
        description: str,
        model: type[BaseModel],
        handler,
    ) -> None:
        self.name = name
        self.description = description
        self.model = model
        self.handler = handler

    def spec(self) -> dict:
        """Tool definition in Messages API shape."""

        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.model.model_json_schema(),
        }

    def execute(self, arguments: dict) -> str:
        try:
            args = self.model.model_validate(arguments)
        except ValidationError as error:
            return f"error: invalid arguments for {self.name}: {error.json()}"

        result = self.handler(args)
        if isinstance(result, str):
            return result
        return json.dumps(result, ensure_ascii=False)


class ToolRegistry:
    """The registered tools are exactly the ones the model may call."""

    def __init__(self, tools: list[Tool]) -> None:
        self._tools = {tool.name: tool for tool in tools}
        self.audit: list[str] = []

    def specs(self) -> list[dict]:
        return [tool.spec() for tool in self._tools.values()]

    def execute(self, name: str, arguments: dict) -> str:
        """Run one tool and record it; unknown tools fail without raising."""

        tool = self._tools.get(name)
        if tool is None:
            result = f"error: unknown tool {name}"
        else:
            result = tool.execute(arguments)

        entry = f"{name} {json.dumps(arguments, ensure_ascii=False)} -> {result}"
        self.audit.append(entry[:AUDIT_LIMIT])
        return result


class TicketBook:
    """In-memory ticket store for the M5 experiment (not persisted)."""

    def __init__(self) -> None:
        self._tickets: dict[int, dict] = {}
        self._next_id = 1

    def create(self, subject: str, priority: str) -> dict:
        ticket = {
            "id": self._next_id,
            "subject": subject,
            "priority": priority,
            "status": "open",
        }
        self._tickets[ticket["id"]] = ticket
        self._next_id += 1
        return {"created": ticket}

    def list_tickets(self, status: str) -> dict:
        matches = [t for t in self._tickets.values() if t["status"] == status]
        return {"tickets": matches, "count": len(matches)}


class CreateTicketArgs(BaseModel):
    subject: str = Field(min_length=1, description="问题摘要，一句话")
    priority: str = Field(
        default="normal",
        pattern="^(low|normal|high)$",
        description="优先级：low/normal/high",
    )


class ListTicketsArgs(BaseModel):
    status: str = Field(
        default="open",
        pattern="^(open|closed)$",
        description="按状态过滤：open/closed",
    )


def build_default_registry(book: TicketBook | None = None) -> ToolRegistry:
    """The two safe built-in customer-service tools."""

    book = book or TicketBook()
    return ToolRegistry(
        [
            Tool(
                "create_ticket",
                "创建一条客服工单，返回工单号",
                CreateTicketArgs,
                lambda args: book.create(args.subject, args.priority),
            ),
            Tool(
                "list_tickets",
                "按状态列出客服工单",
                ListTicketsArgs,
                lambda args: book.list_tickets(args.status),
            ),
        ]
    )
