import os
import re
from pathlib import Path

import boto3

from rag.index import retrieve


GEN_MODEL = "us.anthropic.claude-haiku-4-5-20251001-v1:0"   # inference profile, not bare ID
THRESHOLDS = {"Silver": 500, "Gold": 2000, "Platinum": 5000}
REGION = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
rt = boto3.client("bedrock-runtime", region_name=REGION)


def _load_template_section(title: str) -> str:
    """Load the first fenced prompt from a named section in the shared Markdown file."""
    path = Path(__file__).resolve().parents[1] / "prompt_templates" / "offer_generation_prompts.md"
    text = path.read_text(encoding="utf-8")
    heading = f"## {title}"
    start = text.find(heading)
    if start < 0:
        raise ValueError(f"Prompt section not found: {heading} in {path}")

    section = text[start:]
    boundary = section.find("\n---\n")
    if boundary >= 0:
        section = section[:boundary]

    blocks = re.findall(r"```[^\n]*\n(.*?)\n```", section, flags=re.DOTALL)
    if not blocks:
        raise ValueError(f"No fenced prompt found in section: {heading}")
    return blocks[0].strip()


SYSTEM_PROMPT = "\n\n".join((
    _load_template_section("Template 1: System Prompt (RAG Context Injection)"),
    _load_template_section("Template 3: Tier-Aware Offer Guidelines"),
    _load_template_section("Template 5: Guardrail Prompt"),
))
USER_PROMPT = _load_template_section("Template 2: User Turn — Offer Generation Request")

def tier_confidence(ltv: float, band=0.10) -> str:
    """Feature-store tier is derived from lifetime value; policy defines tier by
    trailing-12-month spend. Near a threshold the two can disagree."""
    return ("borderline" if any(abs(ltv - t) / t <= band for t in THRESHOLDS.values())
            else "confident")

def interpret(c: dict) -> str:
    channel = ("mostly online" if c["online_to_store_ratio"] > 0.6
               else "mostly in store" if c["online_to_store_ratio"] < 0.4 else "both channels")
    breadth = ("buys across many categories" if c["category_diversity_score"] >= 0.5
               else "concentrated in one or two categories")
    return f"Shops {channel}; {breadth}."

def generate_offer(index, chunks, customer, question, *, strategy="two_pass",
                   signal_mode="interpreted"):
    """Generate one offer using a selectable retriever and profile interpretation.

    ``signal_mode='raw'`` is an evaluation ablation: show the numeric channel and
    category-diversity features instead of the deterministic prose summary.
    """
    contexts = retrieve(index, chunks, customer, strategy=strategy)
    conf = tier_confidence(customer["total_lifetime_value"])
    system = SYSTEM_PROMPT.format(
        retrieved_context="\n\n".join(contexts),
        tier=customer["loyalty_tier"], tier_confidence=conf)
    shopping_pattern = interpret(customer)
    if signal_mode == "raw":
        shopping_pattern = (
            "Raw profile values: "
            f"online_to_store_ratio={customer['online_to_store_ratio']:.3f}; "
            f"category_diversity_score={customer['category_diversity_score']:.3f}."
        )
    elif signal_mode != "interpreted":
        raise ValueError("signal_mode must be 'interpreted' or 'raw'")

    user_values = {
        **customer,
        "interpretation": shopping_pattern,
        "top_categories_str": ", ".join(customer["top_categories"]),
        "question": question,
    }
    user = USER_PROMPT.format(**user_values)
    resp = rt.converse(
        modelId=GEN_MODEL,
        system=[{"text": system}],
        messages=[{"role": "user", "content": [{"text": user}]}],
        inferenceConfig={"maxTokens": 400, "temperature": 0.3},   # temperature only, never with topP
    )
    answer = resp["output"]["message"]["content"][0]["text"]
    return {"answer": answer, "contexts": contexts, "usage": resp["usage"]}
