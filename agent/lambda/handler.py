"""Dispatch an AgentCore Gateway Lambda tool call to the local mock tools."""

import logging
import tools

LOG = logging.getLogger()
LOG.setLevel(logging.INFO)


def _name(event, context):
    custom = getattr(getattr(context, "client_context", None), "custom", {}) or {}
    raw = custom.get("bedrockAgentCoreToolName") or event.get("toolName") or event.get("name") or ""
    return raw.split("___")[-1]


def handler(event, context):
    name = _name(event, context)
    args = event.get("arguments", event) if isinstance(event, dict) else {}
    dispatch = {
        "lookup_order": lambda: tools.lookup_order(args["order_id"]),
        "query_policy": lambda: tools.query_policy(args["question"]),
        "initiate_return": lambda: tools.initiate_return(args["order_id"], args["reason"]),
        "apply_loyalty_credit": lambda: tools.apply_loyalty_credit(args["customer_id"], args["amount"], args["reason"]),
        "escalate_to_human": lambda: tools.escalate_to_human(args.get("customer_id", "UNKNOWN"), args["issue_summary"], args.get("priority", "normal")),
    }
    if name not in dispatch:
        return {"error": "UNKNOWN_TOOL", "message": f"Tool {name!r} is not available."}
    try:
        return dispatch[name]()
    except KeyError as error:
        return {"error": "MISSING_ARGUMENT", "message": f"Missing argument: {error.args[0]}"}
