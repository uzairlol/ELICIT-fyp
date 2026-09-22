#!/usr/bin/env bash
# Serve Qwen2.5-14B (GGUF Q4_K_M, ~9 GB) with vLLM on a Kaggle Tesla T4 x2.
#
# This is the drop-in path for the exact ~9 GB Q4_K_M model used with Ollama
# (the bartowski repo is the single-file mirror; the official Qwen GGUF repo
# only ships sharded parts, which vLLM cannot load). vLLM executes GGUF through
# llama.cpp kernels (Turing sm75 = supported) but GGUF does NOT support tensor
# parallelism, so this uses ONE T4 and leaves the second GPU idle. Use
# serve_vllm.gptq_tp2.sh instead if you want both GPUs.
#
# WHY THESE FLAGS (Qwen2.5-14B: 48 layers, 8 KV heads, head_dim 128):
#   KV bytes/token = 2 (K+V) * 48 layers * 8 kv_heads * 128 head_dim * 2 B fp16
#                  = 393,216 B = 384 KiB / token
#   T4 x1 budget = 0.92 * 16 GiB = 14.72 GiB usable
#   weights (~9.6 GB) + CUDA graphs/activations (~1 GB) => ~10.6 GiB resident
#   leftover for KV cache = ~4.1 GiB = ~10,900 tokens
#   --max-model-len 8192 covers the worst-case call (punishment prompt ~2.5k
#   tokens + max_tokens 3000 => ~5.5k), with headroom.
#   --max-num-seqs 16: full 16 concurrent short calls (~400-700 tokens each)
#   fit comfortably; anything beyond that vLLM preempts (recompute), it never
#   spills KV to CPU RAM (swap/CPU-offload default is off in current vLLM, and
#   the flag that used to control it, --swap-space, has been removed).
#
# --gpu-memory-utilization 0.92 keeps ~1 GB headroom for the T4's small heap.
# --tokenizer must be passed when serving a raw .gguf (GGUF carries no HF
#   tokenizer), which is why we also add it here.
# --served-model-name must match parameters.LLM_MODEL ("qwen2.5-14b").

set -e

vllm serve \
  "bartowski/Qwen2.5-14B-Instruct-GGUF:Qwen2.5-14B-Instruct-Q4_K_M.gguf" \
  --served-model-name "qwen2.5-14b" \
  --tokenizer "Qwen/Qwen2.5-14B-Instruct" \
  --max-model-len 8192 \
  --max-num-seqs 16 \
  --gpu-memory-utilization 0.92 \
  --host 0.0.0.0 \
  --port 8000 \
  --enable-prefix-caching