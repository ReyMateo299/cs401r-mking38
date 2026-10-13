"""Client-side ReAct loop over Amazon Bedrock's Converse API."""

import json
import logging
import os
import time
from pathlib import Path

import boto3

from agent.tools import TOOL_FUNCS, TOOL_SPECS


ROOT = Path(__file__).resolve().parents[1]
SYSTEM_PROMPT = (ROOT / "agent" / "system_prompt.txt").read_text(encoding="utf-8")
MODEL = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
REGION = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
# Current list rates for the US inference profile, USD per token.
PRICE_IN, PRICE_OUT = 1.10 / 1_000_000, 5.50 / 1_000_000

rt = boto3.client("bedrock-runtime", region_name=REGION)
log = logging.getLogger("agent")
SESSIONS: dict[str, list] = {}
TURN_SUMMARIES: list[dict] = []


def _log(event: str, **fields):
    log.info(json.dumps({"event": event, **fields}, ensure_ascii=False, default=str))


def chat(message: str, session_id: str, max_steps: int = 6):
    """Handle one user turn; return (reply text, tool names called in order)."""
    messages = SESSIONS.setdefault(session_id, [])
    messages.append({"role": "user", "content": [{"text": message}]})
    tools_called, tokens_in, tokens_out = [], 0, 0
    started = time.perf_counter()
    _log("turn_start", session_id=session_id, user_message=message)

    def finish(reply: str, stop_reason: str):
        cost = tokens_in * PRICE_IN + tokens_out * PRICE_OUT
        summary = {
            "session_id": session_id,
            "tools_called": list(tools_called),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "estimated_haiku_cost_usd": round(cost, 8),
            "duration_ms": round((time.perf_counter() - started) * 1000, 1),
            "stop_reason": stop_reason,
            "reply": reply,
        }
        TURN_SUMMARIES.append(summary)
        _log("turn_end", **summary)
        return reply, tools_called

    for step in range(1, max_steps + 1):
        response = rt.converse(
            modelId=MODEL,
            system=[{"text": SYSTEM_PROMPT}],
            messages=messages,
            toolConfig={"tools": TOOL_SPECS},
            inferenceConfig={"maxTokens": 800, "temperature": 0},
        )
        usage = response.get("usage", {})
        tokens_in += usage.get("inputTokens", 0)
        tokens_out += usage.get("outputTokens", 0)
        message_block = response["output"]["message"]
        messages.append(message_block)
        stop_reason = response.get("stopReason", "unknown")
        _log(
            "model_step",
            session_id=session_id,
            step=step,
            stop_reason=stop_reason,
            usage=usage,
            message=message_block,
        )

        if stop_reason != "tool_use":
            reply = "".join(
                block.get("text", "")
                for block in message_block.get("content", [])
                if isinstance(block, dict)
            )
            return finish(reply, stop_reason)

        tool_results = []
        for block in message_block.get("content", []):
            if "toolUse" not in block:
                continue
            tool_use = block["toolUse"]
            tool_name = tool_use["name"]
            tool_input = tool_use.get("input", {})
            tool_started = time.perf_counter()
            try:
                result = TOOL_FUNCS[tool_name](**tool_input)
                status = "success"
            except Exception as exc:  # Return tool failures to the model for recovery.
                result = {"error": f"{type(exc).__name__}: {exc}"}
                status = "error"
            latency_ms = round((time.perf_counter() - tool_started) * 1000, 1)
            tools_called.append(tool_name)
            _log(
                "tool_call",
                session_id=session_id,
                step=step,
                tool=tool_name,
                input=tool_input,
                output=result,
                status=status,
                latency_ms=latency_ms,
            )
            tool_results.append({
                "toolResult": {
                    "toolUseId": tool_use["toolUseId"],
                    "content": [{"json": result}],
                    "status": status,
                }
            })
        messages.append({"role": "user", "content": tool_results})

    fallback = "I'm sorry, I couldn't complete that. Let me connect you with a specialist."
    return finish(fallback, "max_steps_reached")
