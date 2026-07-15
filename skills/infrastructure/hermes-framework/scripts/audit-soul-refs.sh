#!/usr/bin/env bash
# audit-soul-refs.sh — 检测 SOUL.md 中所有 skill 引用是否指向"活跃"skill
# （非 .archive / 非 .curator_backups）。归档/合并 skill 后必跑，防止铁律
# skill_view() 静默失效。2026-07-13 自检会话沉淀。
#
# 用法: bash ~/.hermes/skills/infrastructure/hermes-framework/scripts/audit-soul-refs.sh
# 退出码: 0 = 无悬空引用; 1 = 存在悬空引用(见输出)

set -uo pipefail
HERMES="${HERMES_HOME:-$HOME/.hermes}"
SOUL="$HERMES/SOUL.md"
SKILLS="$HERMES/skills"

[ -f "$SOUL" ] || { echo "SOUL.md 不存在: $SOUL"; exit 2; }

is_active() {  # $1 = skill name; 活跃=非archive/非backup 下有 name: $1
  find "$SKILLS" -name SKILL.md \
    -not -path '*/.archive/*' -not -path '*/.curator_backups/*' \
    -exec grep -lqx "name: $1" {} \; -print 2>/dev/null | grep -q . 
}

fail=0

echo "=== A. 铁律 skill_view(name='...') 引用（必须真名可加载）==="
grep -oE "skill_view\(name='[^']+'\)" "$SOUL" | sed "s/skill_view(name='//;s/')//" | sort -u |
while read -r n; do
  [ -z "$n" ] && continue
  if is_active "$n"; then echo "  OK   $n"; else echo "  FAIL $n  <- 悬空/已归档"; fi
done

echo ""
echo "=== B. 路由表右栏 \`skill\` 引用（agent 跳转用，必须真名）==="
# 路由表行形如: | 关键词 | `skill-name` |  ；跳过含 § 的合并指向
grep -E '^\|' "$SOUL" | grep -oE '`[a-z][a-z0-9-]+`' | tr -d '`' | sort -u |
while read -r n; do
  [ -z "$n" ] && continue
  if is_active "$n"; then echo "  OK   $n"; else echo "  WARN $n  <- 若为索引段简写(省 hermes- 前缀)可忽略,否则修"; fi
done

echo ""
echo "提示: A 段任何 FAIL 都是真缺陷(铁律细则调不出); B 段 WARN 需人工区分"
echo "      '技能索引速览简写' 与 '真悬空'。修复后跑 build_index(force=True) 重建。"

# 精确退出码只看 A 段
if grep -oE "skill_view\(name='[^']+'\)" "$SOUL" | sed "s/skill_view(name='//;s/')//" | sort -u |
   while read -r n; do [ -z "$n" ] && continue; is_active "$n" || exit 7; done; then
  echo "RESULT: A 段全部可加载 ✅"; exit 0
else
  echo "RESULT: A 段存在悬空铁律引用 ❌"; exit 1
fi
