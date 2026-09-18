# SetuBid deduplication engine

Run: python setubid/dedupe_pipeline.py

Outputs: setubid.db is the persistent SQLite retrieval structure. lsh_band is
the lookup table, indexed by (band, band_key); hot_bucket records suppressed
hot LSH buckets. notice.card_id is the persistent bidder-facing opportunity ID.
evidence.json contains labelled-pair separation, MinHash error, candidate recall,
work before/after mitigation, and indexed-vs-scan query plans/timings.
retrieval_curve.csv and retrieval_curve.svg contain the LSH survival curve and
the selected operating point.

Similarity is Jaccard over normalised word 3-shingles. Three words preserve
tender phrases while generic individual words are too broad. Preamble,
references, dates and money are replaced by placeholders. A 256-component
MinHash uses 2048 bytes per notice and has a 95 percent sampling error bound
of approximately plus/minus 0.0613. The sketch is computed over the complete
shingle set, not a reservoir sample. It retrieves candidates only; merging
needs exact Jaccard at least 0.75.

LSH uses 16 bands of four rows. Survival is 1-(1-s^4)^16. The explicit cost
setting is false merge = 20 times a false duplicate, so retrieval prioritises
candidate recall and exact scoring makes the final conservative decision.
The B-tree on (band, band_key) probes 16 exact keys, unlike a corpus scan.
The benchmark in evidence.json forces the rejected full-table scan with
SQLite's NOT INDEXED clause. SQLite does not expose physical row-visit counts,
so the report records planner paths and returned-row counts rather than
inventing a row-examination number. Hot buckets are deliberately suppressed;
their recall cost is reported and must be accepted or improved before a
production rollout.
