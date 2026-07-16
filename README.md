# README — Hermes-skillroute-core

Hermes Agent 微内核架构的配置模板仓库。包含极致拆解后的 `SOUL.md`、按分类组织的技能集和 `vdb` 检索工具链。

> ⚠️ 本仓库**只含元数据资产与源码**，不含任何个人路径、token、hostname 或私人模型名。部署时由 `install.sh` 在用户本地生成运行时状态（向量索引、`.venv`、`.env`）。

## 架构分界（成熟 Agent 框架标准）

| 类型 | 入库 | 生成方式 |
|------|------|---------|
| 代码（`vdb/*.py`, `scripts/*`） | ✅ | 仓库提供 |
| 元数据（`skills/**` 的 frontmatter） | ✅ | 仓库提供 |
| 索引（Chroma） | ❌ | `install.sh` 本地构建 |
| 运行时状态（`.venv`, `.env`, `*.db`） | ❌ | 用户本地生成 |

## 目录结构

```
hermes-skillroute-core/
├── install.sh                 # 一键部署（新装全量 / 存量补充 / --profile）
├── README.md                  # 本文件
├── LICENSE                   # MIT
├── TROUBLESHOOTING.md       # 故障排查指南
├── CONTRIBUTING.md          # 贡献规范
│
├── SOUL.md                    # → ~/.hermes/SOUL.md（存量不覆盖）
├── .env.example               # → ~/.hermes/.env（仅当不存在时复制）
│
├── memories/
│   ├── USER.md                # 用户画像模板（通用占位，非私人版）
│   └── FRAMEWORK_EVOLUTION.md # 框架演进钩子
│
├── vdb/                       # 技能检索工具链
│   ├── sparse.py              # 词法权重（纯 Python）
│   ├── embed.py               # 云端嵌入（BGE-M3）
│   ├── indexer.py             # Chroma 索引构建
│   ├── matcher.py             # dcg-inspired 三层: query 分类短路 → 白名单直达 → RRF(K=60) + trigger 加成
│   ├── routing.py             # 专名门禁路由层
│   └── __init__.py
│
├── scripts/
│   ├── init-vdb.sh            # .venv + pip + build_index
│   └── vdb-autoload.py      # 预热 + 索引过期检测 + 自动重建
│
└── skills/                    # 元数据资产（全量同步本地真实结构）
    ├── core/                  # 铁律细则
    ├── workflow/              # 高频工作流
    ├── methodology/           # 思维框架
    ├── infrastructure/        # 框架机制
    ├── integration/           # 外部集成
    ├── media/ research/ mlops/ smart-home/ social-media/ email/ apple/
    └── templates/             # NEW_SKILL_TEMPLATE.md
```

## 技能分类职责

| 分类 | 加载特点 | Token 预算 |
|------|---------|----------|
| `core/` | 检测到铁律违规时触发对应微技能 | 150-200 |
| `workflow/` | 用户触发场景关键词时加载 | 400-800 |
| `methodology/` | vdb 语义匹配或用户明确要求 | 300-600 |
| `infrastructure/` | 框架故障排查时低频加载 | 300-600 |
| `integration/` | 涉及外部系统交互时加载 | 400-800 |
| `templates/` | 创建新技能时人工查阅 | — |

## 快速部署

```bash
# 全新安装（会创建 ~/.hermes 或合并到现有）
bash install.sh

# 存量补充（只补缺失，不覆盖现有个性化配置）
bash install.sh --profile

# 装到独立 profile（测试用，零污染）
bash install.sh --profile installtest
# 验证完删除：
rm -rf ~/.hermes/profiles/installtest
```

## 源文件映射

| 本仓库路径 | 目标 | 备注 |
|-----------|------|------|
| `SOUL.md` | `~/.hermes/SOUL.md` | 存量用户不自动覆盖 |
| `memories/USER.md` | `~/.hermes/memories/USER.md` | 模板，存量不覆盖 |
| `.env.example` | `~/.hermes/.env` | 仅当目标不存在时复制 |
| `vdb/*.py` | `~/.hermes/vdb/*.py` | 安全覆盖 |
| `scripts/init-vdb.sh` | `~/.hermes/scripts/init-vdb.sh` | 全量覆盖 |
| `skills/*` | `~/.hermes/skills/` | 存量只补充不覆盖 |

**不发布：** `~/.hermes/memories/MEMORY.md`（隐私）、任何含个人路径/hostname/token 的内容。

## 铁律概要（详见 SOUL.md）

1. **信息真实** — 不编造，不确定直说，高危二次确认
2. **代码输出** — 完整代码块，禁省略关键行
3. **验证前置** — 结论前 IDENTIFY→RUN→READ→VERIFY
4. **安全约束** — 禁恶意脚本，密钥仅模板，开源必脱敏
5. **改进优先** — 先 patch 现有，变更必验证，限 `~/.hermes/` 边界
6. **思考范围** — 仅本轮，禁预判/过度推演
7. **长对话上下文** — 会话 >50 条且用户回指历史时才查压缩记忆

## 检索工具链（vdb/）

```bash
cd ~/.hermes/vdb
./init-vdb.sh        # 建 .venv + 装依赖 + 构建索引
# 检索
python -c "from matcher import search; print(search('飞书文档', top_k=5))"
```

检索流程 = query 分类短路(问候/空query) → 白名单直达(精确命中技能名/trigger) → 稠密(BGE-M3) → 稀疏(BM25) → disable过滤 → RRF K=60 + trigger加成 → 路由门禁。详见 `vdb/matcher.py` 顶部 docstring。
