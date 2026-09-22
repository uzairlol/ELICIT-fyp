#!/usr/bin/env bash
# Serve Qwen2.5-14B (GPTQ int4, ~9 GB) with vLLM on a Kaggle Tesla T4 x2.
#
# Fastest path: uses BOTH T4s via tensor parallelism. GPTQ (non-Marlin path)
# is officially supported on Turing sm75 (vLLM hardware matrix: GPTQ [x] on
# Volta+Turing; Marlin kernels are sm80+ only, vLLM falls back for sm75).
#
# WHY THESE FLAGS (Qwen2.5-14B: 48 layers, 8 KV heads, head_dim 128):
#   KV bytes/token full model  = 2 * 48 * 8 * 128 * 2 B = 384 KiB
#   KV bytes/token per GPU TP2 = 192 KiB (24 layers each)
#   Per-GPU budget = 0.90 * 16 GiB = 14.4 GiB
#   weights ~9.0 GB split TP2 => ~4.5 GiB per GPU
#   leftover KV per GPU = ~9.4 GiB = ~49,000 tokens/kernel
#   --max-num-seqs 32 with a typical mix (~400-1,800 tokens/call) needs
#     ~32 * 1,200 * 192 KiB = ~7.2 GiB/GPU < 9.4 GiB. No spill, no preemption.
#   Worst-case burst (all 32 at 8192 tokens) exceeds the pool, in which case
#   vLLM preempts/recomputes short prefills -- it NEVER drops KV to CPU RAM
#   (swap/CPU-offload default is off in current vLLM, and the flag that used
#   to control it, --swap-space, has been removed).
#
# --served-model-name must match parameters.LLM_MODEL ("qwen2.5-14b").
#
# ALTERNATIVE: if you see AWQ prefer this repo instead of GPTQ:
#   --model "Qwen/Qwen2.5-14B-Instruct-AWQ" --quantization awq
#   (also supported on Turing, but routes through non-Marlin kernels there.)

set -e

vllm serve \
  --model "Qwen/Qwen2.5-14B-Instruct-GPTQ-Int4" \
  --served-model-name "qwen2.5-14b" \
  --tensor-parallel-size 2 \
  --max-model-len 8192 \
  --max-num-seqs 32 \
  --gpu-memory-utilization 0.90 \
  --host 0.0.0.0 \
  --port 8000 \
  --enable-prefix-caching