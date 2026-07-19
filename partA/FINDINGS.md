## A1 — Corpus construction

**Source.** FLORES-101 (dev split), a parallel evaluation benchmark of 3,001 sentences extracted from English Wikipedia, covering a range of topics, professionally translated into 101 languages under a controlled process ([Goyal et al., FLORES-101](https://ai.meta.com/research/publications/the-flores-101-evaluation-benchmark-for-low-resource-and-multilingual-machine-translation/)).

**Languages used.** English (reference), Hindi, Tamil, Kannada — same 30 sentence indices across all four, sampled from the dev split.

**Size.** 30 parallel sentences per language, 120 sentences total.

**Preprocessing.** None — raw FLORES dev lines used as-is.

**What this corpus cannot tell you.** N=30 is small enough that individual long or unusual sentences can swing per-language averages noticeably — this is a directional/diagnostic sample, not a statistically powered eval set. FLORES is also single-domain (Wikipedia-style formal/encyclopedic text, professionally translated), so it says nothing about code-mixed, casual, conversational, or chat-register traffic — which is plausibly what the actual product serves, and where real fertility numbers could differ meaningfully from what's reported here. A production decision should validate these ratios against a sample of real traffic before committing to any capacity or routing change.


## A2

| # | Type | Claim | Evidence |
|---|------|-------|----------|
| 1 | Conceptual | **tok/word** isn't a fair cross-lingual unit—agglutinative Dravidian languages pack more information into each word. | The **tok/word** gap (≈17×) shrinks dramatically when measured using **tok/byte** or parity-based metrics. |
| 2 | Code bug | `len(line)` overcounts Indic characters because **code points ≠ grapheme clusters**. | **tok/char** increased from **1.50 → 2.27 (Hindi)** and **2.68 → 4.16 (Tamil)** after switching to grapheme cluster counting. |
| 3 | Code bug | `.lower()` only affects English text. | English fertility changed **1.39 → 1.32** after removing `.lower()`, while Indic languages showed **no difference**. |
| 4 | Looks suspicious, is fine | NFC Unicode normalization has negligible impact. | Removing normalization changed results only within noise (**≈0.1–0.2%**). |
| 5 | Dead code (bonus) | `random.seed(1337)` is unused. | Zero functional effect on benchmark results. |
| 6 | Tokenizer choice | Most of REPORT_v0's "5.5×–17× worse" gap is specific to the GPT-2 tokenizer, not an inherent property of the languages. | **Phi-4-mini-instruct** reduces the gap to approximately **1.26× / 2.39× / 2.14×**. |


## A3 — Which number should drive the routing/cost decision

Neither tok/word nor tok/byte is a fair cross-lingual denominator: tok/word breaks under agglutination (Dravidian languages pack more grammar per word), and tok/byte breaks the other way — Devanagari/ Tamil/Kannada codepoints are 3 bytes in UTF-8 vs. 1 byte for Latin, so byte-count systematically *inflates* the denominator for Indic scripts and masks the true disparity (see ratio table below).

Tokens-per-parallel-sentence is the correct metric: since FLORES gives literal same-content sentences across languages, this is the only denominator that holds "amount of communicated content" constant rather than holding a script-dependent unit (word or byte) constant.

Sentence-ratio vs. English: 
gpt2 — hin 7.36x, tam 15.08x, kan 13.64x.
Phi-4-mini-instruct — hin 1.59x, tam 2.04x, kan 2.04x.