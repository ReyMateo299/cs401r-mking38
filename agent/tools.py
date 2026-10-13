"""Local customer-service tools used by the Track C ReAct agent."""

import time
from functools import lru_cache

from rag.index import build_index, embed


# Deliberately small mock order system for the lab scenarios.
ORDERS = {
    "ORD-2847301": {
        "status": "In transit",
        "carrier": "UPS",
        "eta": "2026-10-13",
        "items": ["Trail running shoes"],
        "final_sale": False,
    },
    "ORD-3001122": {
        "status": "Delivered",
        "delivered": "2026-09-20",
        "items": ["Insulated jacket"],
        "final_sale": True,
    },
}


@lru_cache(maxsize=1)
def _policy_index():
    """Build the local FAISS policy index once, on first policy lookup."""
    from pathlib import Path

    corpus = Path(__file__).resolve().parents[1] / "northstar-policy-docs"
    return build_index(str(corpus))


def lookup_order(order_id: str) -> dict:
    normalized_id = order_id.strip().upper().lstrip("#")
    order = ORDERS.get(normalized_id)
    if order is None:
        return {"error": f"No order found with ID {order_id}. Ask the customer to confirm it."}
    return {"order_id": normalized_id, **order}


def query_policy(question: str) -> dict:
    """Retrieve the three closest passages from the official policy corpus."""
    index, chunks = _policy_index()
    scores, indices = index.search(embed([question]), min(3, index.ntotal))
    passages = []
    for score, chunk_index in zip(scores[0], indices[0]):
        if chunk_index >= 0:
            chunk = chunks[int(chunk_index)]
            passages.append({
                "doc_id": chunk["doc_id"],
                "section": chunk["section"],
                "score": float(score),
                "text": chunk["text"],
            })
    return {"passages": passages}


def initiate_return(order_id: str) -> dict:
    """Simulate a return; final-sale and unknown orders are rejected in code."""
    normalized_id = order_id.strip().upper().lstrip("#")
    order = ORDERS.get(normalized_id)
    if order is None:
        return {"error": f"No order found with ID {order_id}. Return not initiated."}
    if order.get("final_sale"):
        return {
            "error": "Final sale items are non-returnable (POL-RET-004 §4). Not initiated."
        }
    return {"status": "Return label emailed", "order_id": normalized_id}


def escalate_to_human(reason: str, summary: str) -> dict:
    """Record a simulated handoff; no external ticketing system is connected."""
    return {
        "status": "Escalated",
        "ticket": f"ESC-{int(time.time())}",
        "reason": reason,
        "summary": summary,
    }


TOOL_FUNCS = {
    fn.__name__: fn
    for fn in (lookup_order, query_policy, initiate_return, escalate_to_human)
}

TOOL_SPECS = [
    {"toolSpec": {
        "name": "lookup_order",
        "description": "Get status, delivery date, items and final-sale flag for an order ID.",
        "inputSchema": {"json": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        }},
    }},
    {"toolSpec": {
        "name": "query_policy",
        "description": (
            "Search NorthStar's official return, loyalty, and shipping policies. "
            "Call this BEFORE stating any return window, fee, tier benefit or limit."
        ),
        "inputSchema": {"json": {
            "type": "object",
            "properties": {"question": {"type": "string"}},
            "required": ["question"],
        }},
    }},
    {"toolSpec": {
        "name": "initiate_return",
        "description": (
            "Start a return only after policy confirms the order is inside the customer's "
            "window and lookup_order confirms it is not final sale. The tool rejects "
            "unknown and final-sale orders."
        ),
        "inputSchema": {"json": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        }},
    }},
    {"toolSpec": {
        "name": "escalate_to_human",
        "description": (
            "Hand the conversation to a human agent when the customer requests an "
            "exception, pushes back after a correct policy answer, or the request is "
            "outside your authority. For final-sale cases, the handoff cannot authorize "
            "an exception or return."
        ),
        "inputSchema": {"json": {
            "type": "object",
            "properties": {
                "reason": {"type": "string"},
                "summary": {"type": "string"},
            },
            "required": ["reason", "summary"],
        }},
    }},
]
