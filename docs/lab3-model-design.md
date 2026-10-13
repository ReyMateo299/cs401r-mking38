# Lab 3 — Model Design Justification

**Tracks completed:** Track A (Churn Prediction) and Track B (Offer Generation RAG)

## Churn model choice

I used XGBoost for this task because the input is a small, structured tabular
dataset: 9,999 customers and 11 model features derived from purchase history.
The retention team also needs a model whose aggregate drivers can be inspected
and whose performance can be compared meaningfully with a simple recency rule.
Gradient-boosted trees capture non-linear relationships and interactions (for
example, recency together with purchase frequency and basket value) without
requiring feature scaling or a much larger training set. They also provide a
useful, though not causal, gain-based feature-importance view.

A logistic-regression baseline would be easier to explain but assumes a mostly
linear relationship between the predictors and churn unless I manually add
interactions. A neural network would add tuning and reproducibility overhead
for roughly ten thousand rows and a small number of numeric features, with no
unstructured input that would justify the cost. I would reconsider XGBoost if
NorthStar added a much larger sequence of purchase events, product text or
images, or if it needed calibrated uncertainty rather than a ranking score. In
that situation I would compare a temporal model or an ensemble, while retaining
a transparent tabular baseline.

## What the features bought us

The final Athena-backed local run used a stratified 70/30 split (6,999 training
and 3,000 validation customers), XGBoost 3.4.1, `max_depth=6`, `eta=0.03`,
`num_round=600`, and a training-split-derived `scale_pos_weight=3.5448`. Its
held-out AUC-ROC was 0.7835, precision at the global top 10% was 0.7100, and
recall at the global top 10% was 0.3227.

The recency-only baseline AUC was 0.7232. The full model therefore had a
0.0603 AUC lift, with a paired-bootstrap 95% confidence interval of
[0.0407, 0.0798]. Because the interval excludes zero, this is evidence that
the additional features added predictive signal on this held-out split. It is
also an honest reminder that recency remains a strong baseline: the extra
features improve ranking, but they do not make recency unimportant.

Gain importance ranked `days_since_last_purchase` first, followed by 180-day
and 30-day purchase frequency. Average order value and average basket size
were the next strongest contributors. Tenure, online-to-store ratio, and
category diversity had less gain in this fitted model; I would not call them
useless from this result alone, but they are less clearly valuable here. The
largest reliable slice concern is Silver: its AUC was 0.7204 and recall at the
global contact cutoff was 0.2035. Platinum's AUC was higher (0.8856), but it
has only 21 churn positives, so that estimate is borderline rather than a
reason to declare the model fairer for Platinum members.

## Offer-generation system choice

I chose retrieval-augmented generation rather than fine-tuning because the
claims an offer may make are controlled by policy documents that can change.
With RAG, I can update the local policy corpus and rebuild the FAISS index
without retraining a model. Titan Text Embeddings v2 keeps embedding in
Bedrock and the local FAISS index is sufficient for this small policy corpus.
The pipeline uses a two-pass retriever: one query targets tier benefits and a
second targets constraints such as return windows, retention-offer rules, and
shipping restrictions. I did not add a re-ranker because the corpus is small;
I would measure a re-ranker before accepting its complexity and latency.

Claude Haiku 4.5 generates the short constrained offer and also serves as the
RAGAS judge in the recorded comparison. The primary production risk is
plausible but unsupported marketing copy: a model can turn a standing benefit
into a new incentive, invent a deadline, or use the feature-store tier as if
it were the policy system of record. The latter matters because the feature
store derives tier from lifetime value while policy tiers use trailing
12-month spend. The system therefore labels near-threshold tiers as borderline
and the prompt instructs conditional phrasing rather than a claim that a
customer is close to, or entitled to, another tier.

The RAGAS evidence also shows why its scores are diagnostics rather than a
deployment gate. I ran all four supplied cases twice before and twice after
adding the supplied customer profile to the judge contexts. Adding the profile
increased mean faithfulness from 0.158 to 0.414 and context recall from 0.608
to 0.640, but answer relevancy fell from 0.419 to 0.347. This helped the judge
verify profile facts, but did not unambiguously improve the system. Context
recall remains limited by ground-truth claims that the policy corpus does not
contain, and answer relevancy is ill-matched to an instruction-to-generate an
offer rather than a customer question. The detailed evidence and limitations
are in `docs/lab3-evidence/track-b-examples.md`.

## With 10× more time or data

For the churn model, I would evaluate a true temporal split using event dates,
calibrate probability estimates, and investigate the weaker Silver recall with
an appropriate business threshold rather than assuming the global top-10%
allocation is equitable. I would also add per-customer explanations before an
offer is sent.

For the RAG system, I would use the loyalty system of record instead of the
feature-store approximation, attach claim-level policy citations to each
offer, and add deterministic validation that blocks unsupported tier benefits,
campaign terms, and return-window claims. Finally, I would test offers in a
shadow campaign with human review and measure redemption and complaints—not
just LLM-judge metrics—before production use.
