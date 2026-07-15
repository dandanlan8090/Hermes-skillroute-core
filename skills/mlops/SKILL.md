---
name: mlops
description: >-
  MLOps class-level umbrella: local & production LLM inference (llama.cpp/GGUF,
  vLLM, HuggingFace Hub discovery) plus model benchmarking (lm-eval-harness) and
  experiment tracking (W&B). Use when running models locally, deploying production
  LLM APIs, choosing quant methods, searching HuggingFace, benchmarking model
  quality, comparing models, or tracking training experiments.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms:
- linux
- macos
- windows
metadata:
  hermes:
    tags:
      trigger:
        - 推理
        - llm部署
        - 模型推理
        - vllm
        - llama
        - 跑模型
        - inference
        - 评测
        - benchmark
        - ML评估
        - 模型评估
        - llm评测
        - benchmark测试
        - 评估指标
      disable:
        - long_context
        - read_only
        - deep_review
    category: mlops
    related_skills: []
---

# MLOps — Local/Production Inference & Model Evaluation

Class-level umbrella for the model lifecycle: **run models** (inference) and
**measure models** (evaluation). Branch-specific reference lives in `templates/`
and is pulled in only when that branch is active.

## Branch A — Inference (serving)

Three inference modes and their trade-offs, plus HuggingFace Hub discovery:

| Mode | Use when | Key tools |
|------|----------|-----------|
| **llama.cpp / GGUF** | CPU/Apple Silicon/edge, custom quants, local-first | `llama-server`, `llama-cli`, HF Hub search |
| **vLLM** | Production API serving, high throughput, OpenAI compat | `vllm serve`, OpenAI SDK |
| **HuggingFace Hub** | Model discovery, download, upload | `hf` CLI (`hf download`, `hf upload`, `hf models list`) |

### Quick starts

**llama.cpp (URL-first)**
1. Search: `https://huggingface.co/models?apps=llama.cpp&sort=trending`
2. Open: `https://huggingface.co/<repo>?local-app=llama.cpp` — copy exact command
3. Run: `llama-server -hf <repo>:<QUANT>` or `--hf-repo <repo> --hf-file <file>`

Quant selection: general chat `Q4_K_M`; code/technical `Q5_K_M`/`Q6_K`; tight RAM
`Q3_K_M`/IQ; audio/video add `mmproj-*.gguf`.

**vLLM**
```bash
pip install vllm
vllm serve meta-llama/Llama-3-8B-Instruct
# query via OpenAI SDK: base_url='http://localhost:8000/v1', api_key='EMPTY'
```
Quantization: `--quantization awq` (or gptq/fp8) + `--tensor-parallel-size`.

**HuggingFace Hub**
```bash
hf download <repo_id>            # download files
hf upload <repo_id>              # upload (single-commit)
hf models list --search <term>   # search
hf endpoints deploy/pause/resume # Inference Endpoints
```

### Hardware requirements

| Model size | llama.cpp (CPU/GPU) | vLLM (GPU) |
|-----------|---------------------|-----------|
| 7B-13B | 8-16GB | 1x A10 (24GB) or A100 (40GB) |
| 30B-40B | 24-32GB | 2x A100 (tensor parallel) |
| 70B+ | 48GB+ | 4x A100 or 2x A100-80GB + AWQ |

Full reference: `templates/llama-cpp.md`, `templates/vllm.md`,
`templates/huggingface-hub.md`.

## Branch B — Evaluation (benchmarking & tracking)

| Workflow | Tool | Use when |
|----------|------|----------|
| **Academic benchmarks** | `lm-eval` (EleutherAI harness) | Standardized metrics, comparing models, tracking training |
| **Experiment tracking** | W&B | Logging training runs, sweeping hyperparameters, sharing results |

```bash
# lm-eval standard suite
pip install lm-eval
lm_eval --model hf --model_args pretrained=meta-llama/Llama-2-7b-hf \
  --tasks mmlu,gsm8k,hellaswag,truthfulqa,arc_challenge \
  --device cuda:0 --batch_size auto --num_fewshot 5
# vLLM backend (5-10x faster)
lm_eval --model vllm --model_args pretrained=model,tensor_parallel_size=2 --tasks mmlu

# W&B
import wandb
wandb.init(project="my-project", name="run-001")
wandb.log({"loss": 0.5, "accuracy": 0.8})
wandb.agent(sweep_id, function=train)   # sweeps
```

When to use each: academic paper/model release → `lm-eval`; training iteration /
hyperparameter search → W&B sweeps; both → run `lm-eval` on checkpoints and log
to W&B.

Full reference: `templates/lm-evaluation-harness.md` (60+ tasks, vLLM backend,
model comparison, custom tasks, API eval, distributed) and
`templates/weights-and-biases.md` (logging, artifacts, sweeps, resuming,
integration patterns).

## When to use which

- Need to **run** a model locally or as an API → Branch A.
- Need to **measure/compare** a model or track experiments → Branch B.
- Both: serve with vLLM, benchmark checkpoints with lm-eval, log to W&B.
