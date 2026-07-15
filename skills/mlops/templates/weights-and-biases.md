---
# This file is absorbed content from: mlops/evaluation/weights-and-biases
---

# Weights & Biases — Full Reference

## Quick start

```python
import wandb
wandb.init(project="my-project", name="run-001")
wandb.log({"loss": 0.5, "accuracy": 0.8})
```

## Common patterns

### Training loop logging

```python
for step, (x, y) in enumerate(dataloader):
    loss = train(x, y)
    wandb.log({
        "train/loss": loss.item(),
        "train/lr": optimizer.param_groups[0]["lr"],
        "train/grad_norm": grad_norm,
    }, step=step)
```

### Auto-log PyTorch

```python
wandb.watch(model, log_freq=100)          # Logs gradients + parameters
wandb.log({"epoch": epoch}, step=step)
```

### Tables and artifacts

```python
# Log predictions table
wandb.log({
    "predictions": wandb.Table(
        columns=["id", "text", "pred", "label", "prob"],
        data=[[i, text, pred, label, prob] for i, (text, pred, label, prob) in enumerate(results)]
    )
})

# Artifacts
artifact = wandb.Artifact("model-checkpoint", type="model")
artifact.add_file("model.pt")
run.log_artifact(artifact)
```

### Sweeps (hyperparameter search)

YAML sweep config:
```yaml
method: random
metric:
  name: val/accuracy
  goal: maximize
parameters:
  lr:
    values: [1e-4, 5e-4, 1e-3]
  batch_size:
    values: [16, 32, 64]
```

```bash
wandb sweep sweep.yaml
wandb agent <sweep_id>
```

Or programmatic:
```python
sweep_id = wandb.sweep(sweep_config, project="my-project")
wandb.agent(sweep_id, function=train)
```

### Resume a run

```python
# By ID
wandb.init(id=run_id, resume="must", project="my-project")

# Auto-resume most recent
wandb.init(project="my-project", resume="allow")
```

### Multi-run comparison

```python
runs = wandb.Api().runs("user/project", filters={"state": "finished"})
for run in runs:
    print(run.name, run.summary_metrics.get("accuracy"))
```

## Integration with common frameworks

```python
# PyTorch Lightning
from pytorch_lightning import Callback
class WandbCallback(Callback):
    def on_validation_epoch_end(self, trainer, pl_module):
        wandb.log({"val/acc": trainer.callback_metrics.get("val/acc")})
```

## Resources

- Docs: https://docs.wandb.ai
- Quickstart: https://docs.wandb.ai/quickstart