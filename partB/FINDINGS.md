# Part B — Capacity Reconciliation

Model: FLM-4B-Instruct (dense), 28 layers, 8 KV heads, head_dim 128, fp16.
Hardware: 1× L4 (24 GB), `gpu_memory_utilization=0.92`, `max_model_len=4096`,
~1.6 GB non-KV overhead.

## B1 — KV-cache bytes/token and max concurrent sequences

**KV-cache bytes per token:**

```
bytes/token = 2 (K and V) × kv_heads × head_dim × precision_bytes × layers
            = 2 × 8 × 128 × 2 × 28
            = 114,688 bytes/token  (= 112 KiB/token exactly)
```

**Memory available for KV cache** (treating GPU memory as GiB, the
conventional unit for reported VRAM sizes):

```
Total usable   = 24 GiB × 0.92                         = 22.08 GiB
Weights        = 4.2e9 params × 2 bytes (fp16)          ≈ 7.82 GiB
Overhead       = 1.6 GiB (given)
Remaining for KV cache = 22.08 − 7.82 − 1.6             ≈ 12.66 GiB
                                                         ≈ 13.59 × 10^9 bytes
```

**Max total tokens storable:**

```
13.59e9 bytes / 114,688 bytes/token ≈ 118,500 tokens
```

**Max concurrent 4096-token sequences:**

```
118,500 / 4096 ≈ 28.9  →  ~28-29 sequences
```

**Check against the log.** At batch 24 (`prompt_len=3584 + gen_len=512 =
4096`, i.e. exactly `max_model_len`), `kv_cache_util=0.93` and
`preempted_seqs=0` — still fits cleanly. At batch 32, `kv_cache_util=0.97`
and `preempted_seqs=7` — capacity has been exceeded. The predicted
ceiling (~28-29) falls right between the last clean batch (24) and the
first batch showing preemption (32), which is a good match given the
approximations involved (block-level memory allocation granularity,
rounding in the stated overhead figure).

## B2 — the batch-32/48 throughput anomaly

`reported_tok_s` for `prompt_len=3584` across batch size:

| batch | reported_tok_s | preempted_seqs | kv_cache_util |
|---|---|---|---|
| 4  | 565.4  | 0  | 0.16 |
| 8  | 902.6  | 0  | 0.31 |
| 16 | 1311.4 | 0  | 0.62 |
| 24 | 1607.4 | 0  | 0.93 |
| 32 | 1384.0 | 7  | 0.97 |
| 48 | 1298.5 | 23 | 0.97 |

Throughput rises through batch 24, then **falls** at batch 32 and falls
further at batch 48 — despite batch size still increasing. This inverts
naive "more batch → more throughput" scaling.

**Mechanism.** The drop begins exactly where B1 predicts it should: once
concurrent KV-cache demand exceeds the GPU's ~28-29-sequence capacity, the
scheduler must **preempt** sequences — evicting their KV cache and later
re-running prefill to resume them. That reprocessing is pure wasted
compute, so effective throughput falls even though nominal batch size
rises. `kv_cache_util` saturating at 0.97 (not 1.00) at both batch 32 and
48 is consistent with the scheduler actively fighting to stay within a
hard memory ceiling rather than the model doing more useful work.

**Proposed change.** Cap concurrent long-context batch at ~24 (below the
ceiling) — or quantize the KV cache to int8, which roughly halves
bytes/token and should roughly double the ceiling to ~56-58 sequences,
letting batch 48 run without preemption. Predicted effect: with int8 KV
cache, batch 48 should show `preempted_seqs=0` and reported_tok_s close
to the batch-24 per-sequence rate (1607.4/24 ≈ 67 tok/s/seq) × 48 ≈
3200 tok/s — i.e. only under a fixed KV-cache-capacity constraint does the
report's optimistic number become plausible, not by assumption.

## B3 — the misreading behind Section 2's conclusions

**What `reported_tok_s` actually counts.** Testing on the prompt=3584,
batch=16 row (`num_requests=16`, `wall_clock_s=49.97`):

```
Gen tokens only:      16 × 512 / 49.97            = 163.9 tok/s   (doesn't match)
Prompt + gen tokens:  16 × (3584 + 512) / 49.97    = 1311.6 tok/s  (matches reported 1311.4)
```

The same check on the short-prompt batch-16 row confirms it:
`16 × (512 + 256) / 13.91 = 883.2` — an exact match to the logged value.

**Conclusion:** `reported_tok_s = (prompt tokens + generated tokens) /
wall-clock time.` Prefill (prompt) tokens are processed in one parallel
forward pass and aren't a sustained per-token rate the way decode is.
Counting them inflates the metric — and inflates it more, the longer the
prompt — which is exactly why REPORT_v0's Section 2 sees "longer prompts →
better throughput." It's an artifact of what the column counts, not a
real capacity gain. This single misreading is the source of both
Section 2 conclusions the report draws.

**Honest goodput at batch 24, long prompt** (`num_requests=24`,
`gen_len=512`, `wall_clock_s=61.16`, `itl_ms_p50=96.07`, `preempted_seqs=0`
— clean row, no wasted recompute):

```
Way 1 — gen tokens / wall-clock:
  24 × 512 / 61.16                    ≈ 200.9 tok/s

Way 2 — per-sequence decode rate × concurrent batch:
  (1000 / 96.07) × 24                 ≈ 249.9 tok/s
```

Both independent derivations land in the ~200-250 tok/s range — nowhere
near the logged 1607.4 tok/s, and nowhere near the report's ~3200 tok/s
extrapolation for batch 48.

**What the report should have said.** Prefill throughput and decode
("goodput") throughput are different things and must be reported
separately. True sustained generation throughput at the best clean
operating point (batch 24) is ~200-250 tok/s, not ~1600 tok/s. Batch 48
should never have been extrapolated linearly — per B1/B2, capacity is
already exceeded well before batch 48, so real goodput there is *worse*
than at batch 24, not ~2x better.

## B4 — the counter to confirm the B2 mechanism

Pull **`preempted_seqs`** (or, if available at the serving-stack level,
the scheduler's raw preemption/recompute-event counter) per batch size at
`prompt_len=3584`. Expected value: 0 for batch ≤24, then a sharp jump to a
non-zero count starting at batch 32 (7) and growing further at batch 48
(23) — exactly the transition already visible in the log, occurring right
at the ~28-29-sequence ceiling computed in B1. A clean confirmation would
be re-running batch 28 and 30 specifically, expecting the jump to appear
right at that boundary rather than gradually.