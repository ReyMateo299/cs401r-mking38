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