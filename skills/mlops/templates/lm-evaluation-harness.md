---
# This file is absorbed content from: mlops/evaluation/lm-evaluation-harness
---

# lm-evaluation-harness — Full Reference

## What it does

Evaluates LLMs across 60+ academic benchmarks using standardized prompts and metrics. Industry standard used by EleutherAI, HuggingFace, and major labs.

## Quick start

```bash
pip install lm-eval

lm_eval --model hf \
  --model_args pretrained=meta-llama/Llama-2-7b-hf \
  --tasks mmlu,gsm8k,hellaswag \
  --device cuda:0 \
  --batch_size auto \
  --num_fewshot 5
```

## Core benchmarks

| Benchmark | What it measures | Standard fewshot |
|-----------|-----------------|------------------|
| MMLU | 57-subject multitask (multiple choice) | 5-shot |
| GSM8K | Grade school math word problems | 5-shot |
| HellaSwag | Common sense reasoning | 10-shot |
| TruthfulQA | Truthfulness and factuality | 0-shot |
| HumanEval | Python code generation (164 problems) | 0-shot |
| ARC | AI2 Reasoning Challenge (science) | 25-shot |

**Standard suite**: `mmlu,gsm8k,hellaswag,truthfulqa,arc_challenge`

## Model backends

```bash
# HuggingFace (default)
lm_eval --model hf --model_args pretrained=model-name

# vLLM (5-10x faster)
lm_eval --model vllm \
  --model_args pretrained=model-name,tensor_parallel_size=2 \
  --tasks mmlu --batch_size auto

# Quantized
lm_eval --model hf \
  --model_args pretrained=model-name,load_in_4bit=True \
  --tasks mmlu
```

## Running specific subsets

```bash
# Only STEM MMLU
--tasks mmlu_stem

# HumanEval with code execution
--tasks humaneval --allow_code_execution
```

## Model comparison script

```python
import json, pandas as pd

models = ["meta-llama-Llama-2-7b-hf", "meta-llama-Llama-2-13b-hf"]
tasks = ["mmlu", "gsm8k", "hellaswag", "truthfulqa"]

results = []
for model in models:
    with open(f"results/{model}.json") as f:
        data = json.load(f)
    row = {"Model": model.replace("-", "/")}
    for task in tasks:
        metrics = data["results"][task]
        key = "acc" if "acc" in metrics else "exact_match"
        row[task.upper()] = f"{metrics[key]:.3f}"
    results.append(row)

df = pd.DataFrame(results)
print(df.to_markdown(index=False))
```

## Tracking training progress

```bash
lm_eval --model hf \
  --model_args pretrained=checkpoints/step-$N \
  --tasks gsm8k,hellaswag \
  --num_fewshot 0 \
  --output_path results/step-$N.json
```

## Common issues

| Issue | Fix |
|-------|-----|
| Too slow | Use vLLM backend or `--num_fewshot 0` |
| OOM | `--batch_size 1` or `load_in_8bit=True` |
| Different from reported | Check `--num_fewshot 5` (most papers use 5-shot) |
| HumanEval no execution | `pip install human-eval` + `--allow_code_execution` |

## Hardware requirements (7B model, single A100)

- HellaSwag: ~10 min
- GSM8K: ~5 min
- MMLU (full): ~2 hours
- HumanEval: ~20 min

## Resources

- GitHub: https://github.com/EleutherAI/lm-evaluation-harness
- Task library: 60+ tasks
- HF Leaderboard: https://huggingface.co/spaces/HuggingFaceH4/open_llm_leaderboard