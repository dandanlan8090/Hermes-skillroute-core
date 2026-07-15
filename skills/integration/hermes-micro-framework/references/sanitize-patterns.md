# Sanitize Patterns — 推送到 hermes-micro-framework 的脱敏映射

推送前必须清洗个人标识符。本文件是可复用的替换映射 + 安全例外清单。

## 必须替换（个人/环境信息）

| 原值 | 替换为 | 出现在 |
|------|--------|--------|
| `~` | `~` | 路径、命令示例、日志 |
| `[HOSTNAME]` | `[HOSTNAME]` | hostname、日志头 |
| `Hermes` | `Hermes` | author 字段、报告署名 |
| `hermes` | `hermes` | 小写变体 |

**清洗脚本**（在 repo 根目录运行）：
```python
from pathlib import Path
repl = [("~","~"),("[HOSTNAME]","[HOSTNAME]"),("Hermes","Hermes"),("hermes","hermes")]
for p in Path("skills").rglob("**/*.md"):
    t = p.read_text()
    for o,n in repl: t = t.replace(o,n)
    p.write_text(t)
```
> 仅扫描 `grep` 不够——`references/*.md` 历史报告里常含这些标识符，必须批量替换后复查。

## 安全保留（非隐私，不要误删）

| 值 | 为什么安全 |
|----|-----------|
| `dandanlan8090` | 公开 GitHub 仓库路径 `github.com/dandanlan8090/hermes-micro-framework`，是 repo 身份不是个人隐私 |
| `ghp_xx...xxxx` / `sk-xxx...xxxx` | 文档中的 token **占位符**（脱敏规范本身示例），非真实密钥 |
| `sk-your-key` | `.env.example` 的占位符 |
| `BAAI/bge-m3` / `siliconflow.cn` | 公开模型名/服务商 |

## 硬红线（永远不入库）

- `~/.hermes/memories/MEMORY.md` — 隐私
- `~/.hermes/.env` — 真实 token
- `~/.hermes/vdb/chroma/` — 向量索引（install.sh 本地重建）
- `~/.hermes/vdb/.venv/` — 运行时
- 任何含个人路径、真实用户名、真实 token、真实 hostname 的内容
