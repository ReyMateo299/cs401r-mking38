import time, json

ORDERS = {   # simulated order system
    "ORD-2847301": {"status": "In transit", "carrier": "UPS", "eta": "2026-10-09",
                    "items": ["Trail running shoes"], "final_sale": False},
    "ORD-3001122": {"status": "Delivered", "delivered": "2026-09-20",
                    "items": ["Insulated jacket"], "final_sale": True},
}

def lookup_order(order_id: str) -> dict:
    o = ORDERS.get(order_id.strip().upper().lstrip("#"))
    return o or {"error": f"No order found with ID {order_id}. Ask the customer to confirm it."}

def query_policy(question: str) -> dict:
    # Reuse the Track B FAISS retriever (build_index/embed) over northstar-policy-docs.
    _, idx = INDEX.search(embed([question]), 3)
    return {"passages": [CHUNKS[i]["text"] for i in idx[0]]}

def initiate_return(order_id: str) -> dict:
    o = ORDERS.get(order_id)
    # Hard guard in CODE, not just in the prompt: the model cannot talk its way past this.
    if o and o.get("final_sale"):
        return {"error": "Final sale items are non-returnable (POL-RET-004 §4). Not initiated."}
    return {"status": "Return label emailed", "order_id": order_id}

def escalate_to_human(reason: str, summary: str) -> dict:
    return {"status": "Escalated", "ticket": f"ESC-{int(time.time())}", "reason": reason}

TOOL_FUNCS = {f.__name__: f for f in (lookup_order, query_policy, initiate_return, escalate_to_human)}

TOOL_SPECS = [
    {"toolSpec": {"name": "lookup_order",
        "description": "Get status, delivery date, items and final-sale flag for an order ID.",
        "inputSchema": {"json": {"type": "object", "properties": {
            "order_id": {"type": "string"}}, "required": ["order_id"]}}}},
    {"toolSpec": {"name": "query_policy",
        "description": "Search NorthStar's official return, loyalty, and shipping policies. "
                       "Call this BEFORE stating any return window, fee, tier benefit or limit.",
        "inputSchema": {"json": {"type": "object", "properties": {
            "question": {"type": "string"}}, "required": ["question"]}}}},
    {"toolSpec": {"name": "initiate_return",
        "description": "Start a return. Only for orders confirmed inside the customer's window "
                       "and not final sale.",
        "inputSchema": {"json": {"type": "object", "properties": {
            "order_id": {"type": "string"}}, "required": ["order_id"]}}}},
    {"toolSpec": {"name": "escalate_to_human",
        "description": "Hand the conversation to a human agent. Use when the customer requests "
                       "an exception to policy, pushes back after a correct policy answer, or "
                       "the request is outside your authority.",
        "inputSchema": {"json": {"type": "object", "properties": {
            "reason": {"type": "string"}, "summary": {"type": "string"}},
            "required": ["reason", "summary"]}}}},
]