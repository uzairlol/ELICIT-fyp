#!/usr/bin/env bash
# Serve any Arm-A model family with vLLM on a Kaggle Tesla T4 x2.
#
# One script, three families, deliberately. The model factor is only interpretable
# as a *model* effect if the serving configuration is held constant: same tensor
# parallelism, same --max-model-len, same --max-num-seqs, same precision policy.
# If any of those differ between families, "sigma^2_model" in the variance
# decomposition is really a serving-configuration effect and the contrast cannot
# be interpreted.
#
# Usage:
#   scripts/serve_arm_model.sh qwen2.5-14b
#   scripts/serve_arm_model.sh llama-3.1-8b
#   scripts/serve_arm_model.sh mistral-7b
#
# The alias printed by this script is what a cell's config must declare as
# `model:` / LLM_MODEL, and it must equal --served-model-name. `elicit doctor
# --model <alias>` checks it, and the exported run_cell.py refuses to start if the
# session's served alias does not match the cell.

set -euo pipefail

ALIAS="${1:-qwen2.5-14b}"
VLLM_BIN="${VLLM_BIN:-vllm}"

# Held identical across families. Changing one of these invalidates the
# cross-model contrast; changing all of them at once is the only way it stays
# honest.
MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-32}"
TENSOR_PARALLEL="${TENSOR_PARALLEL:-2}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.90}"

case "$ALIAS" in
  qwen2.5-14b)
    MODEL="Qwen/Qwen2.5-14B-Instruct-GPTQ-Int4"
    ;;
  llama-3.1-8b)
    MODEL="unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit"
    ;;
  mistral-7b)
    MODEL="TheBloke/Mistral-7B-Instruct-v0.2-AWQ"
    ;;
  *)
    echo "Unknown alias: $ALIAS" >&2
    echo "Known aliases: qwen2.5-14b, llama-3.1-8b, mistral-7b" >&2
    exit 2
    ;;
esac

cat <<EOF
=== ELICIT grid server ===
alias           : $ALIAS
checkpoint      : $MODEL
tensor-parallel : $TENSOR_PARALLEL
max-model-len   : $MAX_MODEL_LEN
max-num-seqs    : $MAX_NUM_SEQS

Cells whose config declares model: $ALIAS can run in this session.
EOF

exec "$VLLM_BIN" serve "$MODEL" \
  --served-model-name "$ALIAS" \
  --tensor-parallel-size "$TENSOR_PARALLEL" \
  --max-model-len "$MAX_MODEL_LEN" \
  --max-num-seqs "$MAX_NUM_SEQS" \
  --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION" \
  --host 0.0.0.0 \
  --port 8000 \
  --enable-prefix-caching