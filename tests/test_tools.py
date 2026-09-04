import unittest

try:
    from aster.tools import Tool, ToolRegistry, TicketBook, build_default_registry
except ImportError:  # pydantic/SDK not installed; offline-only environments skip these
    raise unittest.SkipTest("aster.tools needs pydantic (use .venv for tool tests)")

from pydantic import BaseModel, Field


class DivideArgs(BaseModel):
    dividend: float = Field(description="被除数")
    divisor: float = Field(description="除数，不能为 0")


class ToolTest(unittest.TestCase):
    def test_spec_exposes_name_description_and_schema(self) -> None:
        tool = Tool("divide", "两数相除", DivideArgs, lambda args: args.dividend / args.divisor)

        spec = tool.spec()

        self.assertEqual(spec["name"], "divide")
        self.assertEqual(spec["description"], "两数相除")
        self.assertEqual(spec["input_schema"]["title"], "DivideArgs")
        self.assertIn("divisor", spec["input_schema"]["properties"])

    def test_invalid_arguments_return_error_and_skip_handler(self) -> None:
        calls = []

        def handler(args):
            calls.append(args)
            return "unreachable"

        tool = Tool("divide", "两数相除", DivideArgs, handler)

        result = tool.execute({"dividend": 1.0})

        self.assertIn("error", result)
        self.assertIn("divide", result)
        self.assertEqual(calls, [])

    def test_valid_arguments_run_and_encode_result(self) -> None:
        tool = Tool("divide", "两数相除", DivideArgs, lambda args: {"quotient": args.dividend / args.divisor})

        result = tool.execute({"dividend": 9.0, "divisor": 3.0})

        self.assertEqual(result, '{"quotient": 3.0}')


class ToolRegistryTest(unittest.TestCase):
    def test_unknown_tool_fails_without_raising(self) -> None:
        registry = ToolRegistry([])

        result = registry.execute("missing", {})

        self.assertIn("error", result)
        self.assertIn("missing", result)
        self.assertEqual(len(registry.audit), 1)

    def test_audit_records_both_success_and_failure(self) -> None:
        tool = Tool("divide", "两数相除", DivideArgs, lambda args: {"quotient": 4.0})
        registry = ToolRegistry([tool])

        registry.execute("divide", {"dividend": 8.0, "divisor": 2.0})
        registry.execute("divide", {"divisor": 2.0})

        self.assertEqual(len(registry.audit), 2)
        self.assertTrue(registry.audit[0]["ok"])
        self.assertFalse(registry.audit[1]["ok"])
        self.assertIn('"quotient": 4.0', registry.audit[0]["result"])

    def test_reconcile_flags_claims_without_matching_results(self) -> None:
        tool = Tool(
            "create_ticket",
            "创建工单",
            DivideArgs,
            lambda args: {"created": {"id": 1}},
            claim_pattern=r"工单号\s*(\d+)",
            result_id_pattern=r'"id":\s*(\d+)',
        )
        registry = ToolRegistry([tool])

        self.assertEqual(registry.reconcile("工单号 1 已创建"), ["create_ticket: 1"])
        registry.execute("create_ticket", {"dividend": 1.0, "divisor": 1.0})
        self.assertEqual(registry.reconcile("工单号 1 已创建", since=0), [])
        self.assertEqual(registry.reconcile("工单号 1 已创建", since=1), ["create_ticket: 1"])
        self.assertEqual(
            registry.reconcile("工单号 2 已创建", since=1),
            ["create_ticket: 2"],
        )

    def test_tool_without_patterns_is_not_reconciled(self) -> None:
        registry = ToolRegistry([Tool("divide", "两数相除", DivideArgs, lambda args: 1.0)])

        self.assertEqual(registry.reconcile("随便说什么 42"), [])

    def test_build_default_registry_has_two_ticket_tools(self) -> None:
        registry = build_default_registry()

        self.assertEqual(
            [spec["name"] for spec in registry.specs()],
            ["create_ticket", "list_tickets"],
        )

    def test_ticket_book_create_and_list_flow(self) -> None:
        registry = build_default_registry(TicketBook())

        created = registry.execute(
            "create_ticket",
            {"subject": "打印机坏了", "priority": "high"},
        )
        listed = registry.execute("list_tickets", {"status": "open"})

        self.assertIn('"id": 1', created)
        self.assertIn("打印机坏了", listed)
        self.assertIn('"count": 1', listed)


if __name__ == "__main__":
    unittest.main()
