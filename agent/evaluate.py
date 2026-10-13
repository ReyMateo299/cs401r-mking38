"""Backward-compatible command for the Track C AgentCore evaluator.

Run ``python -m agent.evaluate`` after deployment. It invokes all five required
scenarios twice and writes artifacts under ``docs/lab3-evidence``.
"""

from agent.evaluate_agentcore import main


if __name__ == "__main__":
    main()
