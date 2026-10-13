"""Policy-grounded mock tools used by the Track C AgentCore Lambda target.

The Lambda package includes this module and the repository policy corpus. The
tools simulate backing services deliberately: no external customer or order
data is changed during the demonstration.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

ORDERS = {
    "ORD-2847301": {
        "order_id": "ORD-2847301", "customer_id": "CUST-001", "status": "In transit",
        "carrier": "UPS", "tracking_number": "1Z999AA10198765432",
        "estimated_delivery": (date.today() + timedelta(days=3)).isoformat(),
        "items": [{"name": "Trail running shoes", "final_sale": False}],
    },
    "ORD-3001122": {
        "order_id": "ORD-3001122", "customer_id": "CUST-002", "status": "Delivered",
        "carrier": "UPS", "estimated_delivery": (date.today() - timedelta(days=14)).isoformat(),
        "items": [{"name": "Insulated jacket", "final_sale": True}],
    },
}

CUSTOMERS = {
    "CUST-001": {"name": "Jordan Martinez", "tier": "Gold", "points": 2847},
    "CUST-002": {"name": "Alex Chen", "tier": "Platinum", "points": 7420},
    "CUST-003": {"name": "Sam Williams", "tier": "Bronze", "points": 312},
}


def _policy_docs() -> Path:
    """Locate documents in the Lambda zip first, then in a local checkout."""
    here = Path(__file__).resolve().parent
    for candidate in (here / "policy_docs", here.parent / "northstar-policy-docs"):
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError("No bundled NorthStar policy documents were found.")


def _policy_sections() -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    for file in sorted(_policy_docs().glob("*.md")):
        text = file.read_text(encoding="utf-8")
        identifier = re.search(r"\*\*Document ID:\*\*\s*(\S+)", text)
        document_id = identifier.group(1) if identifier else file.stem
        pieces = re.split(r"(?m)^(#{2,3} .+)$", text)
        for index in range(1, len(pieces), 2):
            heading, body = pieces[index].lstrip("#").strip(), pieces[index + 1].strip()
            number = re.match(r"(\d+(?:\.\d+)?)\.?(?:\s|$)", heading)
            source = f"{document_id} §{number.group(1)}" if number else document_id
            sections.append({"source": source, "heading": heading, "text": body})
    return sections


_STOPWORDS = {"a", "an", "and", "are", "can", "do", "for", "from", "i", "in", "is", "it", "my", "of", "on", "or", "the", "to", "we", "what", "with", "you", "your"}


def _terms(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z0-9]+", text.lower()) if len(word) > 2 and word not in _STOPWORDS}


def lookup_order(order_id: str) -> dict:
    """Return a simulated order record; no external service is called."""
    order_id = order_id.strip().upper().lstrip("#")
    order = ORDERS.get(order_id)
    if order is None:
        return {"error": "ORDER_NOT_FOUND", "message": f"No order was found for {order_id}."}
    return dict(order)


def query_policy(question: str) -> dict:
    """Retrieve up to three text passages from the bundled policy corpus."""
    query_terms = _terms(question)
    ranked: list[tuple[int, dict[str, str]]] = []
    for section in _policy_sections():
        score = len(query_terms & _terms(f"{section['heading']} {section['text']}"))
        if score:
            ranked.append((score, section))
    ranked.sort(key=lambda item: item[0], reverse=True)
    passages = ranked[:3]
    if not passages:
        return {"answer": "No matching NorthStar policy text was found. Do not infer an answer; escalate.", "source_documents": [], "confidence": "low"}
    return {
        "answer": "\n\n".join(f"[{section['source']} — {section['heading']}]\n{section['text']}" for _, section in passages),
        "source_documents": [section["source"] for _, section in passages],
        "confidence": "high" if passages[0][0] >= 2 else "medium",
    }


def initiate_return(order_id: str, reason: str) -> dict:
    """Simulate only policy-eligible returns; final sale is a hard stop."""
    order = lookup_order(order_id)
    if "error" in order:
        return order
    if any(item.get("final_sale") for item in order["items"]):
        return {"error": "FINAL_SALE", "message": "POL-RET-004 §4: final-sale merchandise cannot be returned or exchanged at any tier."}
    return {"return_id": f"RTN-{uuid4().hex[:8].upper()}", "status": "Initiated", "message": f"Return initiated for {order['order_id']}; reason recorded: {reason}."}


def apply_loyalty_credit(customer_id: str, amount: float, reason: str) -> dict:
    """Simulate a loyalty credit; Cedar is the platform enforcement for the cap."""
    customer_id = customer_id.strip().upper()
    customer = CUSTOMERS.get(customer_id)
    if customer is None:
        return {"error": "CUSTOMER_NOT_FOUND", "message": f"No customer was found for {customer_id}."}
    if amount <= 0:
        return {"error": "INVALID_AMOUNT", "message": "Credit amount must be positive."}
    # Defence in depth; Gateway/Cedar must deny this before Lambda is invoked.
    if amount > 50:
        return {"error": "CREDIT_CAP", "message": "Credits above $50 require a manager and were not applied."}
    points = int(round(amount * 100))
    customer["points"] += points
    return {"success": True, "customer_id": customer_id, "amount_credited": amount, "points_added": points, "reason_recorded": reason, "message": f"Applied ${amount:.2f} ({points} points) to the customer's account."}


def escalate_to_human(customer_id: str, issue_summary: str, priority: str = "normal") -> dict:
    """Record a mock handoff. It does not grant or promise a policy exception."""
    return {"ticket_id": f"TKT-{uuid4().hex[:8].upper()}", "priority": "urgent" if priority.lower() == "urgent" else "normal", "message": "A customer-service specialist has been notified. This handoff does not change any policy decision.", "customer_id": customer_id or "UNKNOWN", "issue_summary": issue_summary}
