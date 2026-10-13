# Lab 3 Track B — examples, evaluation analysis, and failure cases

## Evidence status and provenance

The repeated RAGAS data in `rag_eval.csv` is complete: four supplied cases,
two repeats in each of two conditions, with 16 valid rows. The judge was
`us.anthropic.claude-haiku-4-5-20251001-v1:0` (Claude Haiku 4.5).

The saved generated answers are in `docs/lab3-rag-comparison-examples.json`
and the earlier five-output capture is in `docs/lab3-rag-examples.json`. Those
earlier outputs remain useful failure evidence: they included filler, invented
campaign terms, an assumed unused credit, and unsupported tier-up language.

The five answers below are the current generated capture in
`track-b-generated-examples.json`. Each was generated with
`us.anthropic.claude-haiku-4-5-20251001-v1:0`, returned eight retrieved policy
chunks, and had no automated review flags. I then manually checked the profile,
the stated tier benefit, category, and source chunks. All five are accepted as
policy-safe examples; they are reproduced verbatim rather than edited.

## Five policy-reviewed, generated input/output pairs

Each profile below is taken from the supplied harness except the fifth, which
is the documented local case. The bullet for each example identifies the
retrieved context sections that support its stated benefit. The full eight
retrieved contexts per capture, including their document-and-section headers,
are preserved verbatim in `track-b-generated-examples.json`.

### 1. Gold online Outdoor/Footwear customer — `CUST-10000317`

- Input: 81% churn probability; feature-store tier Gold; 47 days since last
  purchase; top categories Outdoor and Footwear; mostly online.
- Supporting retrieved context: `POL-LOY-011 | 4. Tier Benefits` (Gold free
  return shipping).
- Generated offer (accepted):

  > Subject: Your Gold benefits are waiting
  >
  > Body: Your account currently shows Gold status, including free return
  > shipping on all your online orders. Explore outdoor gear and footwear on
  > your next visit and use the benefits available to you.

- Review: accepted. It names only Gold status, a documented Gold benefit, and
  supplied categories. “Free return shipping” is not a promise that every
  order is returnable; eligibility remains governed by the return policy.

### 2. Bronze in-store Apparel customer — `CUST-10000904`

- Input: 74% churn probability; feature-store tier Bronze; 68 days since last
  purchase; Apparel only; mostly in store.
- Supporting retrieved contexts: `POL-LOY-011 | 4. Tier Benefits` and
  `POL-SHP-007 | 2. Free Shipping Thresholds` (Bronze $75 free-standard-
  shipping threshold); `KB-FAQ-022 | Returns` (400 locations).
- Generated offer (accepted):

  > Subject: Your Bronze member benefits are waiting
  >
  > Body: Your account currently shows Bronze status, including free standard
  > shipping on orders of $75 or more. Explore apparel on your next visit to any
  > of our 400 stores or online, and use the benefits available to you as a
  > Bronze member.

- Review: accepted. Bronze's $75 free-standard-shipping threshold is in
  `POL-SHP-007`; the 400-location operational fact appears in the retrieved
  FAQ. It does not promise free return shipping, a discount, or a reward
  balance.

### 3. Platinum multi-category customer — `CUST-10000122`

- Input: 66% churn probability; feature-store tier Platinum; average order
  value $447; categories Outdoor, Electronics, and Home; both channels.
- Supporting retrieved context: `POL-LOY-011 | 4. Tier Benefits` (unlimited
  Platinum gear repair). The capture also retrieved `POL-LOY-011 | 4.1 Annual
  Gear Credit`, which is why the review explicitly checks that the answer does
  not claim the credit is available.
- Generated offer (accepted):

  > Subject: Your Platinum benefits are waiting
  >
  > Body: Your account currently shows Platinum status, including unlimited
  > free gear repair on eligible items. Explore outdoor gear and electronics on
  > your next visit and use the benefits available to you as a Platinum member.

- Review: accepted. It uses the documented Platinum gear-repair benefit and
  supplied categories; it does not assume the annual $100 gear credit is
  unredeemed or available in the customer's account.

### 4. Near-threshold feature-store Silver customer — `CUST-10000588`

- Input: 70% churn probability; feature-store tier Silver; lifetime value
  $1,985; categories Home and Beauty; mostly online.
- Supporting retrieved contexts: `POL-LOY-011 | 4. Tier Benefits` and
  `POL-SHP-007 | 2. Free Shipping Thresholds` (Silver benefits and the $50
  free-standard-shipping threshold).
- Generated offer (accepted):

  > Subject: Your Silver Member Benefits Are Ready to Use
  >
  > Body: Your account currently shows Silver status, including free standard
  > shipping on orders of $50 or more and 1.25× points on every purchase.
  > Explore Home and Beauty on your next visit and use the benefits available to
  > you as a Silver member.

- Review: accepted. It uses conditional account-status wording and only Silver
  benefits. It does not infer that the $1,985 lifetime value places the
  customer near Gold or that Gold benefits are active.

### 5. Local Bronze Grocery/Apparel customer — `LOCAL-TRACKB-005`

- Input: at-risk Bronze member; shops in store; top categories Grocery and
  Apparel.
- Supporting retrieved contexts: `POL-LOY-011 | 4. Tier Benefits` and
  `POL-SHP-007 | 2. Free Shipping Thresholds` (Bronze $75 free-standard-
  shipping threshold).
- Generated offer (accepted):

  > Subject: Your Bronze Member Benefits Are Ready to Use
  >
  > Body: Your account currently shows Bronze status, including free standard
  > shipping on orders of $75 or more. Explore Apparel on your next visit to
  > our store or online, and take advantage of the benefits available to you as
  > a Bronze member. We're here to help you find what you need.

- Review: accepted. Apparel is one of the supplied categories; the $75
  shipping threshold is documented. The neutral final sentence does not add a
  policy, account-state, campaign, or deadline claim.

## RAGAS evaluation: observed scores and limits

The pipeline change was **adding the supplied customer profile as an explicit
judge context**. The generator, retriever, four cases, two repeats, and judge
model otherwise stayed the same.

| Condition | Faithfulness mean (range) | Answer relevancy mean (range) | Context recall mean (range) |
|---|---:|---:|---:|
| Before profile context | 0.158 (0.000–0.333) | 0.419 (0.111–0.586) | 0.608 (0.333–1.000) |
| After profile context | 0.414 (0.222–0.615) | 0.347 (0.259–0.547) | 0.640 (0.333–1.000) |
| Difference, after − before | +0.256 | −0.071 | +0.031 |

Per-case means and repeat ranges are in `docs/lab3-ragas-summary.csv`; every
aggregate has 8 valid values (`valid_n=8`, `expected_n=8`). The raw per-run
scores are in `rag_eval.csv`.

### Faithfulness limitation — profile facts are invisible without profile context

Before the change, the judge saw only retrieved policy chunks. A correct
profile-based statement such as the Gold customer's Outdoor/Footwear preference
or the Platinum customer's average order value has no supporting policy text.
For `CUST-10000904`, mean faithfulness rose from 0.063 to 0.439 after the
profile was added; for `CUST-10000122`, it rose from 0.267 to 0.558. The change
helped, but a score still does not establish policy compliance: the saved
answers can phrase existing benefits as a newly granted offer or assume an
unused credit. This is why the policy review above is separate from the score.

### Answer-relevancy limitation — the metric evaluates a poor task fit

The inputs are instructions such as “Generate a retention offer,” while the
outputs are short marketing emails, not direct answers to a customer question.
The repeated scores demonstrate instability and task mismatch: Gold
(`CUST-10000317`) was a plausible category-specific offer but after-condition
answer relevancy ranged from 0.312 to 0.547. Adding profile context is not a
generation improvement, so the observed −0.071 aggregate change cannot show
that the offer became less relevant to its intended customer.

### Context-recall limitation — ground truth contains non-corpus claims

The `CUST-10000122` ground truth asks for a margin judgment about a “heavy
percentage discount” on a $447 average order. That commentary is not a policy
claim retrievable from `northstar-policy-docs/`; its context recall stayed
0.333 in both repeats and both conditions. The provided instructor notes also
identify that the ground truths include material absent from the corpus. A low
context-recall score can therefore diagnose a harness mismatch rather than a
retrieval failure. Conversely, a high score does not validate every generated
claim.

## Documented failure cases and concrete fixes

### Failure 1 — unsupported campaign terms and unsupported account state

Observed Platinum outputs said that a $100 annual gear credit was “waiting” or
“unused,” and several outputs used warm-up claims such as “we've noticed it's
been a while.” The policy says that Platinum receives an annual credit, but the
customer profile does not prove its present balance or whether it is unused.
The profile also supplies days since last purchase, not evidence that the
customer wants to be welcomed back.

**Fix:** keep account-state fields distinct from policy text. Add a deterministic
pre-send validator that rejects terms such as `unused`, `waiting`, `balance`,
or a campaign amount unless the profile has an explicit supporting field. Use
only existing tier benefits when no campaign entitlement is supplied. This is a
prompt and validation fix, not a retrieval-only fix.

### Failure 2 — fabricated deadline or operational detail

Observed raw outputs say “within the next 45 days” and an older local capture
said “any of our 400 locations.” The policy supports a retention offer being
valid for 45 days **from issue** and separately states that store pickup is
available at 400 locations. Neither profile supplies an offer issue timestamp
or makes store count relevant to an individualized offer. Presenting either as
a concrete personalized fact is therefore avoidable and can be misleading.

**Fix:** permit the phrase “valid for 45 days from issue” only when a retrieved
retention-offer chunk supports it; never manufacture a calendar deadline. Omit
the store-count claim unless it answers a location/pickup question and its
source is retrieved. Add a post-generation rule to reject date-like strings
unless an issue date is provided.

### Failure 3 — tier source mismatch near a threshold

`CUST-10000588` is Silver by the feature-store field and has lifetime value
$1,985. Policy eligibility, however, is based on trailing-12-month spend.
The raw output's “stack those rewards toward your next gear upgrade” may imply
a proximity to Gold that the supplied profile cannot establish.

**Fix:** use the loyalty system of record at generation time. Until then, the
pipeline should render borderline tier benefits conditionally and prohibit
claims about distance to the next tier based on lifetime value.
