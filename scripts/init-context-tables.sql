-- SpanKind 上下文分类标签表
-- 来源: 借鉴 dcg 的 SpanKind 命令上下文分类范式, 迁移到 Agent 长对话治理
-- 真实数据支撑(~/.hermes/state.db 两个长 session):
--   Data(工具原始输出) 占 75-85% token; Executed(执行上下文) 仅 10-20%
--   分类压缩可省 75-83% token 且执行上下文零损失
--
-- 设计原则:
--   * 私有 side table, 不侵入 hermes-agent 核心(state.db / hermes_state.py)
--   * message_tags 通过 message rowid 关联 state.db.messages.id
--   * 分类用规则即可(role=tool->DATA, assistant 带 tool_calls->EXECUTED)

CREATE TABLE IF NOT EXISTS message_tags (
    message_id      INTEGER PRIMARY KEY,   -- 对应 state.db messages.id
    span_kind       TEXT NOT NULL,          -- EXECUTED | ARGUMENT | DATA | COMMENT
    confidence      REAL DEFAULT 1.0,       -- 规则分类置信度 (1.0=精确, <1=启发式)
    compress_ratio  REAL DEFAULT 1.0,       -- 压缩时保留比例 (EXECUTED=1.0, DATA=0.08)
    reason          TEXT,                   -- 分类依据 (可解释)
    processed_at    REAL NOT NULL,          -- 处理时间戳
    FOREIGN KEY (message_id) REFERENCES messages(id)
);

CREATE INDEX IF NOT EXISTS idx_span_kind ON message_tags(span_kind);

-- 分类统计视图: 实时看三类分布 (对应真实数据验证的产出)
CREATE VIEW IF NOT EXISTS span_kind_stats AS
SELECT
    span_kind,
    COUNT(*)                          AS msg_count,
    ROUND(AVG(compress_ratio), 3)     AS avg_compress_ratio
FROM message_tags
GROUP BY span_kind
ORDER BY msg_count DESC;
