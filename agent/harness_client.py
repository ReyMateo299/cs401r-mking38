"""Invoke the Track C AgentCore Harness and append raw evidence.

The client is intentionally separate from the older local-agent path. It reads
the deployed harness ARN from Terraform (or HARNESS_ARN) and writes the rubric
artifact names under ``docs/lab3-evidence``.
"""

import csv
import json
import os
import subprocess
import time
import uuid
from pathlib import Path

import boto3

EVIDENCE = Path("docs/lab3-evidence")
TF_DIR = Path("infrastructure/environments/agent")
INPUT_TOKEN_COST = 1.10 / 1_000_000
OUTPUT_TOKEN_COST = 5.50 / 1_000_000
RUNTIME_SESSION_COST_ESTIMATE = 0.0033


def _harness_arn() -> str:
    if os.environ.get("HARNESS_ARN"):
        return os.environ["HARNESS_ARN"]
    result = subprocess.run(
        ["terraform", f"-chdir={TF_DIR}", "output", "-raw", "harness_arn"],
        capture_output=True,
        text=True,
    )
    if result.returncode or not result.stdout.strip().startswith("arn:"):
        raise RuntimeError("Set HARNESS_ARN or run this from the repository root after terraform apply. " + result.stderr[-400:])
    return result.stdout.strip()


class HarnessAgent:
    def __init__(self, harness_arn: str | None = None, region: str = "us-east-1", record: bool = True, run_label: str = "eval"):
        self.arn = harness_arn or _harness_arn()
        self.client = boto3.client("bedrock-agentcore", region_name=region)
        self.record = record
        self.run_label = run_label
        if record:
            EVIDENCE.mkdir(parents=True, exist_ok=True)

    def invoke(self, message: str, session_id: str | None = None) -> tuple[str, list[str]]:
        """Start a fresh runtime session and return the reply and tool names."""
        runtime_session_id = f"{session_id or 'session'}-{uuid.uuid4()}"
        started = time.time()
        response = self.client.invoke_harness(
            harnessArn=self.arn,
            runtimeSessionId=runtime_session_id,
            messages=[{"role": "user", "content": [{"text": message}]}],
        )
        reply_parts: list[str] = []
        calls: list[dict] = []
        current_call = None
        usage = {"inputTokens": 0, "outputTokens": 0}
        stop_reason = None
        for event in response["stream"]:
            now = time.time()
            if "contentBlockStart" in event:
                start = event["contentBlockStart"].get("start", {})
                if "toolUse" in start:
                    current_call = {"tool": start["toolUse"].get("name", "").split("___")[-1], "input": "", "output": "", "started": now}
                    calls.append(current_call)
                elif "toolResult" in start and calls:
                    calls[-1]["status"] = start["toolResult"].get("status", "success")
                    calls[-1]["latency_ms"] = round((now - calls[-1]["started"]) * 1000, 1)
            elif "contentBlockDelta" in event:
                delta = event["contentBlockDelta"].get("delta", {})
                if "text" in delta:
                    reply_parts.append(delta["text"])
                elif "toolUse" in delta and current_call is not None:
                    current_call["input"] += delta["toolUse"].get("input", "")
                elif "toolResult" in delta and calls:
                    for block in delta["toolResult"]:
                        calls[-1]["output"] += block.get("text", "") if isinstance(block, dict) else str(block)
            elif "messageStop" in event:
                stop_reason = event["messageStop"].get("stopReason")
            elif "metadata" in event:
                event_usage = event["metadata"].get("usage", {})
                usage["inputTokens"] += event_usage.get("inputTokens", 0)
                usage["outputTokens"] += event_usage.get("outputTokens", 0)
            else:
                for error_key in ("validationException", "internalServerException", "runtimeClientError"):
                    if error_key in event:
                        raise RuntimeError(f"{error_key}: {event[error_key]}")
        reply = "".join(reply_parts)
        if self.record:
            self._record(runtime_session_id, calls, usage, stop_reason, time.time() - started)
        return reply, [call["tool"] for call in calls]

    def _record(self, runtime_session_id, calls, usage, stop_reason, seconds):
        trace_path = EVIDENCE / "agent-traces.jsonl"
        with trace_path.open("a", encoding="utf-8") as trace:
            for call in calls:
                try:
                    tool_input = json.loads(call["input"]) if call["input"] else {}
                except json.JSONDecodeError:
                    tool_input = call["input"]
                trace.write(json.dumps({
                    "session_id": runtime_session_id, "tool": call["tool"], "input": tool_input,
                    "output": call["output"][:4000], "status": call.get("status"),
                    # ``latency_ms`` is the documented field. ``latency`` is a
                    # compatibility alias for the supplied evidence collector.
                    "latency_ms": call.get("latency_ms"), "latency": call.get("latency_ms"),
                }) + "\n")
        cost_path = EVIDENCE / "agent-cost.csv"
        model_cost = usage["inputTokens"] * INPUT_TOKEN_COST + usage["outputTokens"] * OUTPUT_TOKEN_COST
        write_header = not cost_path.exists()
        with cost_path.open("a", newline="", encoding="utf-8") as cost_file:
            writer = csv.writer(cost_file)
            if write_header:
                writer.writerow(["run", "session_id", "input_tokens", "output_tokens", "model_cost_usd", "runtime_cost_est_usd", "total_est_usd", "tool_calls", "stop_reason", "seconds"])
            writer.writerow([self.run_label, runtime_session_id, usage["inputTokens"], usage["outputTokens"], round(model_cost, 6), RUNTIME_SESSION_COST_ESTIMATE, round(model_cost + RUNTIME_SESSION_COST_ESTIMATE, 6), len(calls), stop_reason, round(seconds, 1)])
