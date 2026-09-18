# SetuBid Deduplication Audit Report

## 1. Executive Summary

SetuBid currently contains a working prototype for reducing duplicate procurement notices from 12,000 notices across 260 portals. The prototype uses normalized text, MinHash, locality-sensitive hashing (LSH), SQLite persistence, hot-bucket mitigation, and persistent bidder-facing card IDs.

The design is substantially faster than pairwise comparison and the indexed database lookup is much faster than a forced table scan. However, the current evidence also exposes a serious quality problem: suppressing hot buckets reduces labelled same-pair candidate recall from 57.71% to 46.59%. This mitigation should not be accepted for production without a better hot-bucket strategy.

The evidence file was generated before the final MinHash correction. It reports a 64-component sampled sketch, while the current code uses a complete 256-component sketch. Therefore, the current evidence numbers must be regenerated before they are presented as final results.

## 2. Business Scenario

A single procurement opportunity can appear on several portals, receive a corrigendum, or be reformatted by a nodal agency. Copies may differ in:

- Portal reference number
- Publication date
- Money formatting
- Capitalization
- Wording and boilerplate
- Added corrigendum text
- Truncation of long notices

The product requirement is one opportunity card per real tender. The two errors have different costs:

- False merge: two different tenders become one card. This can cause a bidder to miss a deadline.
- False duplicate: one tender remains as multiple cards. This creates a poor product experience and duplicate subscription value.

The current explicit cost ratio is:

> False merge cost = 20 times false duplicate cost.

This ratio drives a conservative final merge decision. LSH is used only to retrieve candidates; exact Jaccard similarity is required before merging.

The second business requirement is stable bookmarks. A bidder's card ID must remain stable across reruns and newly discovered copies.

## 3. Current Design

### 3.1 Text representation

The pipeline combines the notice title and body, converts text to lowercase, and extracts word trigrams: consecutive groups of three words.

Examples of deliberately normalized noise:

- Reference numbers become `REF`.
- Dates become `DATE`.
- Monetary amounts become `MONEY`.
- Known portal preambles and boilerplate are removed.

Three-word shingles were selected because individual words are too broad for procurement language, while longer shingles are more sensitive to small wording changes.

The exact feature set remains available for final Jaccard scoring. The current reduced representation is a 256-component MinHash signature, approximately 2,048 bytes per notice. The earlier 64-component sketch used a reservoir sample and did not support the claimed complete-set error interpretation; that implementation has been corrected in the Python source.

### 3.2 Similarity

For two normalized feature sets A and B, exact similarity is Jaccard similarity:

`J(A,B) = |A intersect B| / |A union B|`

A pair is eligible for merging only when exact Jaccard similarity is at least 0.75.

MinHash estimates Jaccard similarity for compact comparison and candidate retrieval. It is not used as the final merge decision.

### 3.3 Candidate retrieval

The signature is divided into 16 bands of 4 rows. Two notices become candidates if at least one band is identical.

For true similarity `s`, the theoretical candidate survival probability is:

`P(candidate) = 1 - (1 - s^4)^16`

The current curve includes these reference points:

| True similarity | Candidate survival probability |
|---:|---:|
| 0.30 | 0.122 |
| 0.50 | 0.644 |
| 0.75 | 0.998 |
| 0.90 | approximately 1.000 |

The selected exact merge threshold is 0.75, where the theoretical candidate survival probability is approximately 0.998.

### 3.4 Persistence and stable IDs

SQLite stores:

- `notice`: notice metadata, feature count, and persistent `card_id`
- `lsh_band`: band/key/notice lookup rows
- `hot_bucket`: buckets suppressed by the mitigation

The card ID is deterministic for a new component and reuses an existing card ID when a previously known notice is encountered again. This is intended to preserve bookmarks across reruns.

## 4. Evidence Currently Available

The existing evidence snapshot contains the following results:

| Measurement | Result |
|---|---:|
| Notices processed | 12,000 |
| Labelled pairs | 900 |
| Labelled same pairs | 279 |
| Labelled different pairs | 621 |
| MinHash mean absolute error | 0.0755 |
| MinHash 95th-percentile absolute error | 0.1965 |
| Candidate recall before hot-bucket mitigation | 57.71% |
| Candidate recall after hot-bucket mitigation | 46.59% |
| Candidate pairs before mitigation | 11,581,083 |
| Candidate pairs after mitigation | 579,803 |
| Mean candidates per notice before mitigation | 1,930.18 |
| Mean candidates per notice after mitigation | 96.63 |
| Maximum candidates before mitigation | 5,178 |
| Maximum candidates after mitigation | 287 |
| Hot buckets | 477 |
| Rows in hot buckets | 69,134 |
| Recorded runtime | 56.5 seconds |
| Indexed lookup mean | 0.0764 ms |
| Forced scan mean | 4.0268 ms |
| Persisted cards | 8,265 |

The indexed lookup is approximately 52.7 times faster than the forced scan in this benchmark: `4.0268 / 0.0764`.

The indexed query plan uses a covering B-tree index on `(band, band_key)`. The rejected alternative is a forced full-table scan using SQLite's `NOT INDEXED` clause. SQLite does not expose exact physical B-tree row-visit counts through this interface, so the evidence records planner paths, returned rows, and wall-clock time instead of inventing a row-examination value.

## 5. Scenario Interpretation

### Scenario A: Same tender, different portal copies

Expected behavior:

1. Reference numbers, dates, money formats, and boilerplate are normalized.
2. Shared tender language produces overlapping trigrams.
3. MinHash makes the representation compact.
4. LSH retrieves likely copies.
5. Exact Jaccard prevents an approximate sketch from directly causing a merge.
6. The copies receive the same persistent card ID.

Current result: the system has the required conservative architecture, but the hot-bucket mitigation loses too many labelled same pairs. A true duplicate that lands in a suppressed bucket may never reach exact scoring.

### Scenario B: Different tenders with similar procurement language

Expected behavior:

1. Generic words such as `construction`, `work`, and `tender` may overlap.
2. Three-word shingles provide more context than individual-word matching.
3. Exact Jaccard at 0.75 is the final protection against false merges.
4. The 20:1 cost ratio favors avoiding accidental merges.

Current result: the evidence shows separation between labelled same and different groups, but the report lacks the required worked examples showing one concrete same pair and one concrete different pair under two tokenization choices. Those examples still need to be added from `labelled_pairs.csv`.

### Scenario C: Re-running the pipeline

Expected behavior:

1. The same notice keeps its `card_id`.
2. A new copy that joins an existing component reuses that component's card ID.
3. New independent components receive deterministic IDs based on the minimum notice ID.
4. The SQLite database remains available after the process exits.

Current result: the database schema and code support this behavior. A dedicated two-run test should still be added to prove that IDs remain unchanged after inserting a new copy and rerunning the pipeline.

### Scenario D: Hot portal or boilerplate-heavy notices

The portal profile explains why the distribution is uneven. P001-P006 are nodal aggregators and attach large common preambles. Short notices may contain more boilerplate than tender-specific content. This creates large LSH buckets because many notices share the same normalized structure.

The hot-bucket mitigation reduces work substantially, from 11.58 million to 0.58 million candidate pairs, but its quality cost is large. This is the main unresolved engineering issue.

## 6. Requirement Audit

| Requirement | Status | Explanation |
|---|---|---|
| Define mechanical similarity | Mostly complete | Trigram Jaccard and normalization are implemented. Worked pair examples are missing. |
| Defend tokenization/noise decisions from corpus | Partly complete | Portal profile supports the decisions, but the report needs concrete labelled examples. |
| Trade exactness for space | In progress | Current code uses 256 full-set MinHash; old evidence is stale and must be regenerated. |
| Measure estimator error | Present but stale | Existing error numbers belong to the old 64-component implementation. |
| Build sublinear retrieval | Complete in prototype | 16-band LSH is implemented and persisted. |
| Show survival probability curve | Implemented | `retrieval_curve.csv` and `retrieval_curve.svg` are generated by the current code. |
| Include asymmetric error cost | Complete | False merge cost is set to 20 times false duplicate cost. |
| Store retrieval structure relationally | Complete | SQLite stores LSH rows and hot buckets. |
| Justify access path with measurements | Mostly complete | Query plans and timings are present; exact physical row visits are unavailable in SQLite. |
| Locate skew empirically | Complete in prototype | Hot buckets and their row counts are recorded; portal profile explains the cause. |
| Measure mitigation cost | Complete but failing quality review | Work falls sharply, but same-pair recall falls to 46.59%. |
| Stable bidder card IDs | Implemented, test still needed | `notice.card_id` is persisted, but a two-run regression test is not yet included. |
| Finish under 20 minutes | Current snapshot passes | Recorded runtime is 56.5 seconds, but long-term growth projection is absent. |

## 7. Recommended Next Steps

1. Regenerate `evidence.json` using the current 256-component implementation.
2. Add two worked labelled-pair examples using unigram versus trigram features.
3. Add a two-run stable-card regression test.
4. Replace unconditional hot-bucket suppression with a targeted strategy, such as portal-aware blocking, a second independent signature, or bounded sampling from hot buckets.
5. Measure recall and runtime again after that mitigation.
6. Add a growth benchmark or projection to support the phrase "on one machine forever."

## 8. Reproduction

Run from the repository root:

```powershell
python .\setubid\dedupe_pipeline.py
```

Expected generated artifacts:

- `setubid/setubid.db`
- `setubid/evidence.json`
- `setubid/bucket_distribution.csv`
- `setubid/retrieval_curve.csv`
- `setubid/retrieval_curve.svg`

The report should be updated after the pipeline successfully regenerates the evidence using the current code.
