---
# This file is absorbed content from: mlops/inference/vllm
# Kept as `templates/vllm.md` for package integrity and reference depth.
---

# vLLM — Full Reference

## When to use vs llama.cpp

- **Use vLLM**: production APIs (100+ req/sec), OpenAI compat, multi-user, low latency + high throughput
- **Use llama.cpp**: CPU/edge, single-user, custom quants

## Quick start

```bash
pip install vllm
vllm serve meta-llama/Llama-3-8B-Instruct
```

## OpenAI-compatible query

```python
from openai import OpenAI
c = OpenAI(base_url='http://localhost:8000/v1', api_key='EMPTY')
print(c.chat.completions.create(
    model='meta-llama/Llama-3-8B-Instruct',
    messages=[{'role': 'user', 'content': 'Hello!'}]
).choices[0].message.content)
```

## Common server flags

| Flag | Use case |
|------|---------|
| `--tensor-parallel-size N` | 30B+ on multi-GPU (power of 2) |
| `--gpu-memory-utilization 0.9` | Most configs; 0.7 if OOM |
| `--max-model-len 8192` | Reduce if OOM |
| `--enable-prefix-caching` | Repeated prompt patterns |
| `--enable-chunked-prefill` | Long prompts |
| `--enable-metrics --metrics-port 9090` | Prometheus monitoring |
| `--speculative-model DRAFT` | Speculative decoding |
| `--quantization awq` | AWQ-quantized models |
| `--trust-remote-code` | Custom models |

## Docker

```bash
docker run --gpus all -p 8000:8000 \
  vllm/vllm-openai:latest \
  --model meta-llama/Llama-3-8B-Instruct \
  --gpu-memory-utilization 0.9 \
  --enable-prefix-caching
```

## Quantized serving (fit 70B on single GPU)

```bash
vllm serve TheBloke/Llama-2-70B-AWQ \
  --quantization awq \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.95
```

## Common issues

| Issue | Fix |
|-------|-----|
| OOM | `--gpu-memory-utilization 0.7` or use quantization |
| Slow TTFT | `--enable-prefix-caching` + `--enable-chunked-prefill` |
| Model not found | `--trust-remote-code` |
| Low throughput (<50 req/sec) | Increase `--max-num-seqs 512`, check GPU util >80% |
| Speculative decoding | `--speculative-model DRAFT_MODEL` |

## Resources

- Docs: https://docs.vllm.ai
- GitHub: https://github.com/vllm-project/vllm
- Paper: "Efficient Memory Management for Large Language Model Serving with PagedAttention" (SOSP 2023)