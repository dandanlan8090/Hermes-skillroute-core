---
# This file is absorbed content from: mlops/huggingface-hub
---

# HuggingFace Hub (`hf` CLI) — Full Reference

> Replaces the deprecated `huggingface-cli` command.

## Quick start

```bash
# Install
curl -LsSf https://hf.co/cli/install.sh | bash -s

# Authenticate
export HF_TOKEN=<your-token>  # or hf auth login
```

## Core commands

```bash
hf download <repo_id>                     # Download files from Hub
hf upload <repo_id>                      # Upload (single-commit)
hf upload-large-folder <repo_id> <path>  # Resumable large-directory upload
hf sync                                   # Sync local ↔ Hub

hf auth login/logout                      # Token sessions
hf auth list/switch                       # Multi-account
hf auth whoami                            # Current identity

hf repos create/delete/duplicate          # Repo lifecycle
hf repos move                             # Transfer between namespaces
hf repos branch/tag                       # Git-like refs

hf datasets list/info/parquet              # Dataset metadata + parquet URLs
hf datasets sql <SQL>                      # DuckDB query over parquet URLs
hf models list/info                       # Model metadata

hf papers list                             # Daily papers

hf discussions list/create/comment/close/reopen/rename  # Hub PR lifecycle
hf discussions diff/merge                 # View and merge PRs

hf endpoints deploy/pause/resume/scale-to-zero/catalog  # Inference Endpoints
hf jobs uv                                # Run scripts with inline deps
hf jobs stats                              # Resource monitoring

hf spaces dev-mode/hot-reload              # Space development

hf buckets create/cp/mv/rm/sync            # S3-like bucket management
hf cache list/prune/verify                # Local storage management
hf webhooks create/watch/enable/disable   # Hub event webhooks
hf collections add-item/update/list        # Organize Hub items
```

## Global flags

```bash
--format json    # Machine-readable output for automation
-q / --quiet     # IDs only
```

## Resources

- Tokens: https://huggingface.co/settings/tokens
- Docs: https://huggingface.co/docs/huggingface_hub