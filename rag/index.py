# rag/index.py
import json, re, pathlib, boto3, numpy as np, faiss

REGION = "us-east-1"
EMBED_MODEL = "amazon.titan-embed-text-v2:0"
rt = boto3.client("bedrock-runtime", region_name=REGION)

def chunk_markdown(path: pathlib.Path, max_chars=1200, overlap=150):
    """Split on ## / ### headings; a section is the natural unit of a policy rule.
    Oversized sections are split with overlap so a rule never loses its context."""
    text = path.read_text()
    doc_id = (re.search(r"\*\*Document ID:\*\*\s*(\S+)", text) or
              re.search(r"(KB-[A-Z]+-\d+)", text))
    doc_id = doc_id.group(1) if doc_id else path.stem
    chunks = []
    for sec in re.split(r"\n(?=#{2,3} )", text):
        heading = sec.strip().splitlines()[0].lstrip("# ").strip()
        start = 0
        while start < len(sec):
            body = sec[start:start + max_chars]
            chunks.append({"doc_id": doc_id, "section": heading,
                           # Prefix with provenance so the model can cite it and
                           # the chunk still makes sense when read on its own.
                           "text": f"[{doc_id} | {heading}]\n{body.strip()}"})
            start += max_chars - overlap
    return chunks

def embed(texts):
    out = []
    for t in texts:
        r = rt.invoke_model(modelId=EMBED_MODEL, body=json.dumps(
            {"inputText": t, "dimensions": 1024, "normalize": True}))
        out.append(json.loads(r["body"].read())["embedding"])
    return np.array(out, dtype="float32")

def build_index(corpus_dir="northstar-policy-docs"):
    chunks = [c for p in sorted(pathlib.Path(corpus_dir).glob("*.md"))
              for c in chunk_markdown(p)]
    vecs = embed([c["text"] for c in chunks])
    index = faiss.IndexFlatIP(vecs.shape[1])   # inner product on normalized vectors = cosine
    index.add(vecs)
    return index, chunks


def _retrieval_passes(customer, strategy):
    """Return (query, optional allowed doc IDs) passes for a retrieval strategy."""
    tier = customer.get("loyalty_tier")
    if not tier:
        raise ValueError("customer must include 'loyalty_tier' for policy retrieval")

    entitlement_query = (
        f"{tier} tier benefits points earn rate free shipping threshold return window "
        "birthday reward early access gear repair gear credit"
    )
    constraint_query = (
        "final sale non-returnable retention offer validity single use combinability "
        "no free expedited shipping any tier"
    )

    if strategy in ("option_a", "A"):
        return [(entitlement_query, None)]
    if strategy in ("option_b", "B"):
        return [(constraint_query, None)]
    if strategy in ("option_c", "C"):
        ratio = customer.get("online_to_store_ratio", 0.5)
        ratio = 0.5 if ratio is None else float(ratio)
        channel = ("online" if ratio > 0.5 else "in store")
        hybrid_query = (
            f"{tier} tier benefits and shipping thresholds for a customer who shops "
            f"mostly {channel}; final sale exclusions, retention offer validity, "
            "single use, combinability, no free expedited shipping"
        )
        # This strategy is meant to retrieve entitlement and offer-constraint
        # rules, so retain the three policy sources that govern those facts.
        policy_doc_ids = {"POL-LOY-011", "POL-SHP-007", "POL-RET-004"}
        return [(hybrid_query, policy_doc_ids)]
    if strategy == "two_pass":
        return [(entitlement_query, None), (constraint_query, None)]

    raise ValueError(
        "strategy must be one of 'option_a', 'option_b', 'option_c', or 'two_pass'"
    )


def retrieve(index, chunks, customer, k=4, strategy="two_pass"):
    """Retrieve policy context with a single strategy or two complementary passes.

    `option_a` retrieves tier entitlements, `option_b` retrieves offer
    constraints, and `option_c` uses a customer-aware query filtered to policy
    documents. The default `two_pass` merges the top k entitlement and
    constraint chunks, preserving query order and removing duplicate chunks.

    Returns the chunk text strings expected by the offer-generation prompt.
    """
    if k < 1:
        raise ValueError("k must be at least 1")
    if index.ntotal != len(chunks):
        raise ValueError(
            f"FAISS index has {index.ntotal} vectors but received {len(chunks)} chunks"
        )
    if index.ntotal == 0:
        return []

    selected = []
    seen = set()
    for query, allowed_doc_ids in _retrieval_passes(customer, strategy):
        # For metadata-filtered Option C, scan the small local index in score
        # order and retain the first k chunks from the allowed policy documents.
        # The corpus is only about 50 chunks, so this exact filtering is cheap.
        search_k = index.ntotal if allowed_doc_ids else min(k, index.ntotal)
        _, indices = index.search(embed([query]), search_k)
        pass_count = 0
        for raw_idx in indices[0]:
            chunk_idx = int(raw_idx)
            if chunk_idx < 0 or chunk_idx in seen:
                continue
            chunk = chunks[chunk_idx]
            if allowed_doc_ids and chunk.get("doc_id") not in allowed_doc_ids:
                continue
            selected.append(chunk["text"])
            seen.add(chunk_idx)
            pass_count += 1
            if pass_count >= k:
                break
    return selected
