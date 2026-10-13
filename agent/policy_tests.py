"""Exercise the deployed Gateway directly to prove the Cedar $50 policy.

This script makes real Gateway/Lambda requests but does not call a language
model. The simulated credit tool changes only its Lambda-process mock data.
"""

import json
import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

TF_DIR = Path("infrastructure/environments/agent")
OUTPUT = Path("docs/lab3-evidence/policy-tests.json")
TARGET = "northstar-tools"

# Some python.org macOS builds do not locate the system CA bundle. Prefer the
# virtual environment's certifi bundle when available, then use the platform
# trust store elsewhere.
try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()


def _gateway_url() -> str:
    if os.environ.get("GATEWAY_URL"):
        return os.environ["GATEWAY_URL"]
    return subprocess.check_output(["terraform", f"-chdir={TF_DIR}", "output", "-raw", "gateway_url"], text=True).strip()


def call_tool(url: str, tool: str, arguments: dict, request_id: int) -> dict:
    body = json.dumps({"jsonrpc": "2.0", "id": request_id, "method": "tools/call", "params": {"name": f"{TARGET}___{tool}", "arguments": arguments}})
    aws_request = AWSRequest(method="POST", url=url, data=body, headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
    SigV4Auth(boto3.Session().get_credentials(), "bedrock-agentcore", "us-east-1").add_auth(aws_request)
    request = urllib.request.Request(url, data=body.encode(), headers=dict(aws_request.headers), method="POST")
    try:
        with urllib.request.urlopen(request, timeout=60, context=SSL_CONTEXT) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        return {"decision": "HTTP_ERROR", "detail": f"{error.code} {error.read().decode()[:300]}"}
    result = payload.get("result") or payload.get("error") or {}
    if isinstance(result, dict) and result.get("isError") is False:
        return {"decision": "ALLOW", "detail": (result.get("content") or [{}])[0].get("text", "")[:300]}
    message = result.get("message") or (result.get("content") or [{}])[0].get("text", "")
    return {"decision": "DENY" if "Denied" in message else "ERROR", "detail": message[:300]}


def main():
    cases = [
        ("read-only tool", "lookup_order", {"order_id": "ORD-2847301"}, "ALLOW"),
        ("credit under cap", "apply_loyalty_credit", {"customer_id": "CUST-001", "amount": 30, "reason": "policy test"}, "ALLOW"),
        ("credit at cap", "apply_loyalty_credit", {"customer_id": "CUST-001", "amount": 50, "reason": "policy test"}, "ALLOW"),
        ("credit just over cap", "apply_loyalty_credit", {"customer_id": "CUST-001", "amount": 51, "reason": "policy test"}, "DENY"),
        ("credit well over cap", "apply_loyalty_credit", {"customer_id": "CUST-001", "amount": 75, "reason": "policy test"}, "DENY"),
        ("split credit part 1", "apply_loyalty_credit", {"customer_id": "CUST-001", "amount": 40, "reason": "split-credit limitation"}, "ALLOW"),
        ("split credit part 2", "apply_loyalty_credit", {"customer_id": "CUST-001", "amount": 40, "reason": "split-credit limitation"}, "ALLOW"),
    ]
    url, results = _gateway_url(), []
    for request_id, (label, tool, arguments, expected) in enumerate(cases, start=1):
        result = call_tool(url, tool, arguments, request_id)
        result = {"case": label, "tool": tool, "arguments": arguments, "expected": expected, **result}
        result["as_expected"] = result["decision"] == expected
        results.append(result)
        print(f"{'OK' if result['as_expected'] else 'BAD'} {label}: expected {expected}, got {result['decision']}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({"gateway_url": url, "results": results}, indent=2) + "\n", encoding="utf-8")
    if not all(result["as_expected"] for result in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
