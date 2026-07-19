#!/usr/bin/env python3
"""
fertility_final.py -- corrected tokenizer fertility benchmark

Consolidates validated fixes from the audit (see partA/AUDIT.md):
  - grapheme-cluster char counting (fixes codepoint overcount for Indic scripts)
  - .lower() removed (was English-only, asymmetric, and unrepresentative of
    real traffic which isn't pre-lowercased)
  - NFC normalize kept (confirmed harmless / doing its job correctly)
  - unused `random` import/seed removed (dead code)

Adds the two additional denominators required for A3:
  - tokens per UTF-8 byte      (content-fair, script-agnostic)
  - tokens per parallel sentence / parity vs. a reference language

Usage:
    uv run partA/fertility_final.py \
        --corpus eng=partA/corpus/eng.dev \
        --corpus hin=partA/corpus/hin.dev \
        --corpus tam=partA/corpus/tam.dev \
        --corpus kan=partA/corpus/kan.dev \
        --tokenizer gpt2
"""

import argparse
import unicodedata
import regex


def load_tokenizer(spec: str):
    if spec.startswith("hf:"):
        from transformers import AutoTokenizer

        tok = AutoTokenizer.from_pretrained(spec[3:])
        return lambda s: tok.encode(s, add_special_tokens=False)
    else:
        import tiktoken

        enc = tiktoken.get_encoding(spec)
        return enc.encode


def read_lines(path: str):
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            line = unicodedata.normalize("NFC", line)  # confirmed correct
            lines.append(line)
    return lines


def analyze(lines, encode):
    """Return per-metric averages over lines, plus raw per-line token counts
    (needed for the parity/NSL denominator)."""
    per_word, per_char, per_byte, tok_counts = [], [], [], []
    for line in lines:
        tokens = encode(line)
        words = line.split(" ")
        chars = len(regex.findall(r"\X", line))       # grapheme clusters, not codepoints
        byte_len = len(line.encode("utf-8"))

        per_word.append(len(tokens) / len(words))
        per_char.append(len(tokens) / chars)
        per_byte.append(len(tokens) / byte_len)
        tok_counts.append(len(tokens))

    n = len(per_word)
    return {
        "fertility": sum(per_word) / n,
        "tok_per_char": sum(per_char) / n,
        "tok_per_byte": sum(per_byte) / n,
        "mean_toks_per_sentence": sum(tok_counts) / n,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", action="append", required=True, metavar="LANG=PATH")
    ap.add_argument("--tokenizer", default="gpt2")
    args = ap.parse_args()

    encode = load_tokenizer(args.tokenizer)

    print(f"tokenizer: {args.tokenizer}")
    header = f"{'lang':<8}{'fertility':>11}{'tok/char':>11}{'tok/byte':>11}{'tok/sent':>11}"
    print(header)
    print("-" * len(header))

    results = {}
    for spec in args.corpus:
        lang, path = spec.split("=", 1)
        lines = read_lines(path)
        m = analyze(lines, encode)
        results[lang] = m
        print(f"{lang:<8}{m['fertility']:>11.2f}{m['tok_per_char']:>11.3f}"
              f"{m['tok_per_byte']:>11.3f}{m['mean_toks_per_sentence']:>11.2f}")

    if len(results) >= 2:
        langs = list(results)
        base = langs[0]
        print(f"\nRatios vs {base} (this is the parity / NSL comparison):")
        print(f"{'lang':<8}{'word-ratio':>12}{'byte-ratio':>12}{'sent-ratio':>12}")
        for lang in langs[1:]:
            wr = results[lang]["fertility"] / results[base]["fertility"]
            br = results[lang]["tok_per_byte"] / results[base]["tok_per_byte"]
            sr = results[lang]["mean_toks_per_sentence"] / results[base]["mean_toks_per_sentence"]
            print(f"{lang:<8}{wr:>12.2f}{br:>12.2f}{sr:>12.2f}")

if __name__ == "__main__":
    main()