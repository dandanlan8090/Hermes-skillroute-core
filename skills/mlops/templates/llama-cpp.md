---
# This file is absorbed content from: mlops/inference/llama-cpp
# Kept as `templates/llama-cpp.md` for package integrity and reference depth.
# The parent skill mlops-inference SKILL.md provides the workflow summary.
---

# llama.cpp — Full Reference

## Model Discovery (URL-first workflow)

1. **Search**: `https://huggingface.co/models?apps=llama.cpp&sort=trending`
2. **Open**: `https://huggingface.co/<repo>?local-app=llama.cpp` — copy the exact `llama-server` or `llama-cli` command shown
3. **Verify tree API**: `https://huggingface.co/api/models/<repo>/tree/main?recursive=true` — confirm exact filenames and byte sizes; discard README/BF16 shards/mmproj files unless requested
4. **Run**: shorthand `llama-server -hf <repo>:<QUANT>` or exact-file `--hf-repo <repo> --hf-file <filename>`

Search patterns:
```
https://huggingface.co/models?apps=llama.cpp&sort=trending
https://huggingface.co/models?search=<term>&apps=llama.cpp&sort=trending
https://huggingface.co/models?search=<term>&apps=llama.cpp&num_parameters=min:0,max:24B&sort=trending
https://huggingface.co/api/models/<repo>/tree/main?recursive=true
```

## Install llama.cpp

```bash
# macOS / Linux
brew install llama.cpp

# Build from source
git clone https://github.com/ggml-org/llama.cpp && cd llama.cpp && cmake -B build && cmake --build build --config Release
```

## Run from HuggingFace Hub

```bash
llama-cli -hf bartowski/Llama-3.2-3B-Instruct-GGUF:Q8_0
llama-server -hf bartowski/Llama-3.2-3B-Instruct-GGUF:Q8_0
```

## Run exact GGUF file

```bash
llama-server \
    --hf-repo microsoft/Phi-3-mini-4k-instruct-gguf \
    --hf-file Phi-3-mini-4k-instruct-q4.gguf \
    -c 4096
```

## Python (llama-cpp-python)

```python
from llama_cpp import Llama
llm = Llama(model_path="./model-q4_k_m.gguf", n_ctx=4096, n_gpu_layers=35)
out = llm("What is machine learning?", max_tokens=256, temperature=0.7)
print(out["choices"][0]["text"])

# Load from Hub
llm = Llama.from_pretrained(
    repo_id="bartowski/Llama-3.2-3B-Instruct-GGUF",
    filename="*Q4_K_M.gguf",
    n_gpu_layers=35,
)
```

## Choosing a quant

- General chat: `Q4_K_M`
- Code/technical: `Q5_K_M` or `Q6_K` if memory allows
- Tight RAM: `Q3_K_M`, `IQ` variants, or `Q2` only if user explicitly prioritizes fit over quality
- For multimodal repos: mention `mmproj-*.gguf` separately (projector, not main model)

## Output format for discovery requests

```
Repo: <repo>
Recommended quant from HF: <label> (<size>)
llama-server: <command>
Other GGUFs:
- <filename> - <size>
Source URLs:
- <local-app URL>
- <tree API URL>
```

## References

- GitHub: https://github.com/ggml-org/llama.cpp
- HF GGUF docs: https://huggingface.co/docs/hub/gguf-llamacpp
- HF Local Apps: https://huggingface.co/docs/hub/main/local-apps