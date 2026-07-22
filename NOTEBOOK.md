# Experiment Log

## Entry 1 — Baseline Reproduction

**Command**

```bash
uv run starter_kit/fertility.py \
  --corpus eng=partA/corpus/eng.dev \
  --corpus hin=partA/corpus/hin.dev \
  --tokenizer gpt2
```

**Result**

```text
tokenizer: gpt2

lang      fertility (tok/word)    tok/char
------------------------------------------
eng                       1.39       0.230
hin                       7.63       1.505

hin is 5.50x the fertility of eng (worse tokenization)
```

**Expectation**

This roughly matches REPORT_v0's ~5.89x claim, confirming the intern's number is reproducible — the bug isn't a fluke, it's structural.

---

## Entry 2 — Baseline Reproduction on Tamil and Kannada (Extended to 4 Languages)

**Command**

```bash
uv run flam-submission/starter_kit/fertility.py \
  --corpus eng=flam-submission/partA/corpus/eng.dev \
  --corpus hin=flam-submission/partA/corpus/hin.dev \
  --corpus tam=flam-submission/partA/corpus/tam.dev \
  --corpus kan=flam-submission/partA/corpus/kan.dev \
  --tokenizer gpt2
```

**Result**

```text
tokenizer: gpt2

lang      fertility (tok/word)    tok/char
------------------------------------------
eng                       1.39       0.230
hin                       7.63       1.505
tam                      23.66       2.677
kan                      19.24       2.584

hin is 5.50x the fertility of eng (worse tokenization)
tam is 17.05x the fertility of eng (worse tokenization)
kan is 13.87x the fertility of eng (worse tokenization)
```

---

## Entry 3 — Experiment 1: Grapheme Cluster Fix (`fertility_v1.py`)

**Change**

```python
chars = len(line)
```

↓

```python
chars = len(regex.findall(r'\X', line))
```

**Result**

```text
lang      fertility (tok/word)    tok/char
------------------------------------------
eng                       1.39       0.230
hin                       7.63       2.266
tam                      23.66       4.160
kan                      19.24       3.963
```

**Observation**

- tok/char rose for all Indic languages:
  - hin: **1.505 → 2.266**
  - tam: **2.677 → 4.160**
  - kan: **2.584 → 3.963**
- English remained unchanged (no combining characters).

**Conclusion**

`len(line)` overcounts codepoints for Indic scripts, which had been **deflating** the reported tok/char cost for Hindi, Tamil, and Kannada. The true cost is worse than REPORT_v0 reported, not better.

---

## Entry 4 — Experiment 2: Remove `.lower()` (`fertility_v2.py`)

**Result**

```text
lang      fertility (tok/word)    tok/char
------------------------------------------
eng                       1.32       0.219
hin                       7.63       1.505
tam                      23.66       2.677
kan                      19.24       2.584
```

**Observation**

- English fertility: **1.39 → 1.32**
- Hindi/Tamil/Kannada: **no change**

**Conclusion**

`.lower()` only affects English, and it was slightly **narrowing** the reported Hindi/English gap (5.50× → 5.76× once removed). This is a small, one-sided bias.

---

## Entry 5 — Experiment 3: Remove NFC Normalization (`fertility_v3.py`)

**Result**

```text
lang      fertility (tok/word)    tok/char
------------------------------------------
eng                       1.39       0.230
hin                       7.62       1.505
tam                      23.66       2.677
kan                      19.26       2.585
```

**Observation**

Maximum difference was approximately **0.1–0.2** across all languages—an order of magnitude smaller than Experiments 1 and 2.

**Conclusion**

`normalize()` is not a bug.

---

## Entry 6 — Remove `random.seed()`

Removed `random.seed()` because it is never used.

---

## Entry 7 — Test with a Multilingual Tokenizer (`hf:microsoft/Phi-4-mini-instruct`)

Reference: [Multilingual Tokenizer Leaderboard](https://huggingface.co/spaces/eduagarcia/multilingual-tokenizer-leaderboard)

**Result**

```text
tokenizer: hf:microsoft/Phi-4-mini-instruct

lang      fertility (tok/word)    tok/char
------------------------------------------
eng                       1.37       0.227
hin                       1.72       0.341
tam                       3.27       0.373
kan                       2.93       0.399

hin is 1.26x the fertility of eng (worse tokenization)
tam is 2.39x the fertility of eng (worse tokenization)
kan is 2.14x the fertility of eng (worse tokenization)
```

Compared to GPT-2:

- Hindi: **5.50×**
- Tamil: **17.05×**
- Kannada: **13.87×**

**Big finding**

Most of the "fertility gap" reported in REPORT_v0 is a property of GPT-2's vocabulary (which had near-zero Indic training data), not an inherent property of the languages. This directly changes the A4 recommendation.

---

## Entry 8 — Corrected Denominators (`fertility_final.py`)

### GPT-2

```text
tokenizer: gpt2

lang      fertility   tok/char   tok/byte   tok/sent
----------------------------------------------------
eng            1.32      0.219      0.219      25.53
hin            7.63      2.266      0.592     187.93
tam           23.66      4.159      0.993     384.90
kan           19.24      3.962      0.973     348.10
```

### Phi-4 Mini Instruct

```text
tokenizer: hf:microsoft/Phi-4-mini-instruct

lang      fertility   tok/char   tok/byte   tok/sent
----------------------------------------------------
eng            1.35      0.224      0.224      26.07
hin            1.73      0.513      0.135      41.43
tam            3.27      0.579      0.139      53.23
kan            2.93      0.610      0.151      53.13
```

### Ratios vs. English

| Tokenizer | Language | Word Ratio | Byte Ratio | Sentence Ratio (NSL/parity) |
|-----------|----------|-----------:|-----------:|----------------------------:|
| Phi-4 | hin | 1.28 | 0.60 | 1.59 |
| Phi-4 | tam | 2.42 | 0.62 | 2.04 |
| Phi-4 | kan | 2.17 | 0.67 | 2.04 |
| GPT-2 | hin | 5.78 | 2.70 | 7.36 |
| GPT-2 | tam | 17.92 | 4.53 | 15.08 |
| GPT-2 | kan | 14.58 | 4.44 | 13.64 |

**Surprise**

Byte-ratio is **lower** than both word-ratio and sentence-ratio for every language/tokenizer—including values **below 1.0** for Phi-4, where Indic languages actually outperform English on tok/byte.

**Reason**

Devanagari, Tamil, and Kannada codepoints occupy **3 bytes** each in UTF-8, while Latin characters typically occupy **1 byte**. As a result, byte count is not a script-agnostic proxy for the amount of content. It systematically inflates the denominator for Indic scripts, masking the true disparity instead of correcting it.

**Revised conclusion**

Byte-based normalization is not the fairest denominator after all. Sentence-ratio (NSL/parity) is more appropriate because FLORES provides literal same-content parallel sentences. It is the only denominator that keeps the **amount of communicated content** constant, rather than fixing a script-dependent unit such as words or bytes.
