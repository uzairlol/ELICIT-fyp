# Serve Qwen2.5-14B (GPTQ int4, ~9 GB) with vLLM on a Windows workstation
# with a single T4 / RTX-class GPU (or local test box). Linux twin, see
# scripts/serve_vllm.gptq_tp2.sh for the Kaggle T4 x2 (tensor-parallel) variant.
#
# Notes:
# - Drop --tensor-parallel-size if you have one GPU.
# - --swap-space 0 keeps the KV cache in VRAM (no spill to system RAM).
# - --served-model-name must match parameters.LLM_MODEL ("qwen2.5-14b").
# - Requires: pip install vllm  (Python 3.11+, CUDA toolkit, xformers)
#
# KV budget (Qwen2.5-14B, single GPU): 384 KiB/token. With 0.90*16 GiB usable,
# ~9 GiB weights => ~4.7 GiB KV => 12,800 tokens => ~16 seqs @ ~800 tokens.

python -m vllm.entrypoints.openai.api_server `
  --model "Qwen/Qwen2.5-14B-Instruct-GPTQ-Int4" `
  --served-model-name "qwen2.5-14b" `
  --max-model-len 8192 `
  --max-num-seqs 16 `
  --gpu-memory-utilization 0.90 `
  --swap-space 0 `
  --host 0.0.0.0 `
  --port 8000 `
  --enable-prefix-caching