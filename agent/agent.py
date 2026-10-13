"""Compatibility entry point for the Track C AgentCore Harness.

The previous implementation kept a client-side ReAct loop here. Track C now
uses the deployed Harness, Gateway, and Cedar policy engine instead.
"""

from agent.harness_client import HarnessAgent

_agent = None


def chat(message: str, session_id: str):
    global _agent
    if _agent is None:
        _agent = HarnessAgent(run_label="manual")
    return _agent.invoke(message, session_id)
