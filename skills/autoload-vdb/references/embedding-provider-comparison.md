# Embedding Provider 实测对比（2026-07-09）

vdb 选型时做的实测数据，未来选 embedding API 时直接参考。

## 测试环境
- 主机：[HOSTNAME] (Ubuntu 26.04)
- 网络：直连 + 走代理，RTT 到 api.nvidia.com = 1-3ms
- 测试集：8 个 query/description 对，跨语言（中英）+ 中文内场景
- 评估指标：跨语言余弦相似度、单次延迟、稳定性

## 实测数据

| Provider | Model | Dim | 延迟 | 跨语言相似度 | 备注 |
|----------|-------|-----|------|---------------|------|
| **SiliconFlow** | BAAI/bge-m3 | 1024 | **240-280ms** | **0.43-0.67** | 当前在用 ✅ |
| NVIDIA Integrate | baai/bge-m3 | 1024 | - | - | 500 错误 ❌ |
| NVIDIA Integrate | nvidia/nv-embedqa-e5-v5 | 1024 | **5.7-6.7s** | 0.18-0.44 | 太慢 ❌ |
| NVIDIA Integrate | nvidia/nv-embed-v1 | 4096 | 6.7s | 0.18 | 延迟+dim 都不优 ❌ |
| NVIDIA Integrate | snowflake/arctic-embed-l | - | - | - | 404（账户未授权） |
| 本地 fastembed | BAAI/bge-small-zh-v1.5 | 512 | 8ms | **0.10-0.20** | 跨语言为零 ❌ |
| 本地 fastembed | BAAI/bge-m3 | 1024 | - | - | fastembed 0.8 不支持 ❌ |
| 本地 fastembed | jinaai/jina-embeddings-v3 | 1024 | 下载超时 | - | 模型文件太大 |
| 本地 fastembed | jinaai/jina-embeddings-v2-base-zh | 768 | ~1.5s | 待测 | 备选 |

## 跨语言相似度对比（关键）

测试 query：中文用户需求 / 测试 doc：英文技能 description

| Query | Doc | BGE-Small-ZH | BGE-M3 (SiliconFlow) |
|-------|-----|---------------|----------------------|
| 部署 flask 到 ubuntu | System administration tasks: service installation | 0.10 | **0.52** |
| 调试 python 报错 | Skill for configuring Hermes Agent | 0.05 | **0.43** |
| 我想看 Hermes 配置 | Configure Hermes Agent itself | 0.08 | **0.67** |
| 搜索 AI 新闻 | Web search, research, information gathering | 0.12 | **0.60** |

**结论**：BGE-M3 的多语言训练是质变，BGE-Small-ZH 在中英跨语言场景几乎完全失效。

## NVIDIA 6s 延迟根因（已验证）

- 直连 curl POST integrate.api.nvidia.com = 5.76s
- 网络 RTT < 3ms（ping 测试）
- 6s 是 NVIDIA 服务端推理时间，不是网络
- 排除代理问题：测试走默认网络，无 HTTP_PROXY env var

## SiliconFlow 验证

```bash
curl -X POST https://api.siliconflow.cn/v1/embeddings \
  -H "Authorization: Bearer sk-..." \
  -H "Content-Type: application/json" \
  -d '{"model":"BAAI/bge-m3","input":"test","encoding_format":"float"}'
# 200, 240ms
```

- OpenAI 兼容协议
- 需注册 SiliconFlow 账户 → API Key → 充值
- 免费额度足够个人使用

## 决策树

```
需要 embedding API？
  ├─ 离线强制要求？ → 本地 fastembed BGE-Small-ZH（接受跨语言差）
  ├─ 有 NVIDIA API key 且能接受 6s 延迟？ → NVIDIA nv-embedqa-e5-v5
  ├─ 默认推荐（成本敏感 + 跨语言）→ SiliconFlow BGE-M3 ✅
  └─ 想要本地 + BGE-M3 质量？ → 本地 sentence-transformers BGE-M3（2.3GB 下载）
```

## 已知坑

### NVIDIA BAAI/bge-m3 500 错误
- 文档列出但调用返回 500
- 可能是 NVIDIA 端模型未激活或需要特殊权限
- 已用 nv-embedqa-e5-v5 替代

### fastembed 模型支持列表
- 0.8.0 版本不支持 BAAI/bge-m3
- 用 `TextEmbedding.list_supported_models()` 查可用模型
- 多语言备选：intfloat/multilingual-e5-large (1024d, SOTA)

### 切换模型必须重 build
- index.npy dim 不匹配会读不出来
- 总是用 `build(force=True)` 覆盖
