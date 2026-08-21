# Model configuration for a host whose GPU is smaller than the one the repo assumes.
#
#   source infra/model-env.example.sh
#   docker compose --profile gpu up -d vllm
#   docker compose up -d worker
#
# Source it before **every** compose call that touches `vllm` or `worker`. Shell variables
# beat `.env` in compose interpolation, and the two services have to agree: vLLM serves
# `--served-model-name "$VLLM_MODEL"` and the worker asks for `$VLLM_MODEL`. If they drift
# the worker gets a 404 for every decision and every run comes back inconclusive, which
# reads like a broken agent rather than a broken tag.
#
# `.env.example` sizes for a 16GB card. This file exists because the machine this was built
# on has 8GB, and the three obvious ways to shrink the model each fail differently. All
# three were measured, and the failures are recorded here rather than rediscovered.

# --------------------------------------------------------------------------------------
# What works
# --------------------------------------------------------------------------------------
export VLLM_MODEL="cyankiwi/Qwen3-4B-Instruct-2507-AWQ-4bit"
export VLLM_BASE_URL="http://vllm:8000"

# KV cache grows with length x sequences, and this card has a quarter of the headroom.
export VLLM_MAX_MODEL_LEN="8192"
export VLLM_MAX_NUM_SEQS="2"

# 6.87 GiB free of 7.96 on this host: the Windows desktop holds ~1.1 GiB, so 0.92 asked
# for more than exists and vLLM refused at load with the numbers in the message.
export VLLM_GPU_MEMORY_UTILIZATION="0.82"

# Empty: the checkpoint declares its own `quantization_config`, and passing
# `--quantization awq` on top of a pre-quantized checkpoint is a different request.
export VLLM_QUANTIZATION=""

# Empty: CUDA graphs are on. Eager mode saves the memory the capture needs and cost 70s
# per call; 4-bit weights leave enough room that the trade is not worth making.
export VLLM_ENFORCE_EAGER=""

export VLLM_EXTRA_ARGS=""
export VLLM_START_PERIOD="1200s"
export MODEL_MAX_CONCURRENCY="2"

# --------------------------------------------------------------------------------------
# What does not, and why. Each of these cost an hour to find.
# --------------------------------------------------------------------------------------
#
#   Qwen/Qwen3-4B-Instruct-2507            the repo default, bf16
#     ~8GB of weights alone. Does not load on 8GB, and the failure is at load, not at
#     request time.
#
#   Qwen/Qwen3-4B-Instruct-2507-FP8        the same model, half the weights
#     Loads the weights and then dies: the checkpoint carries block-wise FP8 scales and
#     DeepGEMM has no scale-factor layout for sm_120 (consumer Blackwell, RTX 50xx). It
#     aborts with `Unknown SF transformation` before serving a token. Datacenter Blackwell
#     and Hopper are fine; this is specific to the consumer card.
#
#   Qwen/Qwen3-4B-AWQ                      4-bit, fits comfortably
#     Serves, and answers nothing usable. The plain Qwen3 series is hybrid-thinking: it
#     spent all 512 output tokens reasoning and never emitted the JSON, so every call came
#     back `schema_violation`. Use an *Instruct-2507* checkpoint, which does not think.
#     Qwen published no official AWQ for 2507, which is why the working choice above is a
#     third-party quantization of an official model.
#
# Measured on the working configuration: ~0.6s per decision warm, and about 20s on the very
# first call while xgrammar compiles the decision grammar (15 union members, ~11KB of
# schema). The compile is once per schema per server, not per run.
#
# --------------------------------------------------------------------------------------
# On a machine with a 16GB card or larger
# --------------------------------------------------------------------------------------
# Do not source this file. `.env.example` already sizes for that case, and the defaults
# there are the ones the rest of the documentation assumes.
