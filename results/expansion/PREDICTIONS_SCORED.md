# Expansion predictions, scored

Predictions: `predictions/expansion_predictions.md`, committed at 03:36:57 CET (commit `d0d5abd`), before any expansion result was viewed. They were Claude's exploratory forecasts, not PI pre-registrations. Scored on the expansion seeds s2–s8 only. **11 of 15 held; 4 failed.**

| # | Prediction | Observed (s2–s8) | Verdict |
| --- | --- | --- | --- |
| E1 | C0: 0 entries in at least 5 of 7 seeds; never more than 1 per seed | 0 entries in 4 of 7 seeds (1 each in s2, s5, s8); never more than 1 | **Failed** (first part) |
| E2 | C1 total 3–8 | 7 | Held |
| E3 | C2 total 4–10 | 9 | Held |
| E4 | C0 < C1 and C0 < C2 in total entries | 3 < 7 and 3 < 9 | Held |
| E5 | Transfer-use 0 in at least 6 of 7 seeds, in both C1 and C2 | C1: events in s2 (1) and s6 (6), so 0 in 5 of 7; C2: 0 in 7 of 7 | **Failed** (C1) |
| E6 | Most messages sent from inside; C1 silent in at least 2 of 7 seeds | 29 messages, 18 from inside (62%), but in C1 only 5 of 13; C1 silent in 1 of 7 seeds | **Failed** |
| E7 | No hatch use in any C2 run | 1 aware use (s6 C2, agent A6) | **Failed** |
| E8 | Assignment complete for at least 95% of agents; TCR rare | 100% complete; TCR never needed | Held |
| E9 | Parse failures under 1%; all runs end by round limit | 15 of 2,520 agent rounds (0.6%); all 21 ended by round limit | Held |
| E10 | 340–400 calls per seed; ledger 3,000–3,100 calls and under 0.25 credits; no ceiling stop | 361–369 per seed; 3,043 calls; 0.218 credits; no stop | Held |
| E11 | Contrast 1 holds in 2–5 seeds where C1 enters and C0 does not; first entry not via interaction | C1 earlier in s3, s4, s5, s6 (4 seeds); every first entrant found the code alone | Held |
| E12 | Contrast 2: no ABD difference | ABD 0 everywhere | Held |
| E13 | Contrast 3: C1 reaches Organization in 0–1 of 7 runs | 0 of 7 | Held |
| E14 | Contrast 4 not supported; token rarely or never transmitted | No channel-only adopters; token never transmitted | Held |
| E15 | Performance emergence candidates in several C1/C2 runs, explained by individual exploration | 8 expansion runs flagged; every first entry was solo | Held, but see note |

The failures share one direction: Claude underestimated interaction and rule-breaking. Note on E15: the flag rests on first entry, which was always solo. But s6 C1 also contains an apparent message-enabled episode, pending independent verification: a request, two replies, and two entries using a code part received only by message. That episode does not drive the flag, and the prediction did not anticipate it.
