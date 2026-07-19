# A4 — Tokenizer Fertility: Corrected Recommendation

**Corrected headline numbers.** REPORT_v0's claimed 5.5x-17x "Hindi/Tamil/Kannada is worse" figures were computed as tokens-per-whitespace-word, using gpt2 (a tokenizer with near-zero Indic training data) and a codepoint-based character count that overcounts Indic combining characters. On a proper parallel corpus (FLORES-101, 4 languages), with the content-fair denominator (tokens per parallel sentence), the picture changes substantially:
- With gpt2: hin 7.4x, tam 15.1x, kan 13.6x vs. English.
- With an Indic-aware model (Phi-4-mini-instruct): hin 1.6x, tam 2.0x, kan 2.0x.

**Routing recommendation.** Do not commit to REPORT_v0's ~6x capacity/cost multiplier or a hard routing split by language. Most of the disparity is a property of tokenizer choice, not an inherent property of these languages —switching to an Indic-aware tokenizer/model recovers most of the gap(6-15x down to ~2x). Recommend evaluating serving with an Indic-aware tokenizer before allocating extra capacity, rather than budgeting for the original multiplier.

**Biggest caveat.** FLORES is a small (N=30), single-domain (formal/Wikipedia-style) parallel corpus. It says nothing about code-mixed, casual, or chat-register traffic, which is what the product likely serves in practice — real-world fertility could differ in either direction.

**Metric to monitor in production.** Tokens-per-request by language (not tokens-per-word), tracked over time — a sustained upward drift would catch this analysis being wrong (e.g., if real traffic's register differs from FLORES's formal domain in a way that changes fertility).