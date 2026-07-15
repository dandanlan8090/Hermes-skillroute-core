# 4 层召回通道仿真脚本

运行方式：
```bash
cd ~/.hermes/vdb && source .venv/bin/activate && python3 /path/to/this/script
```

当前测试结果（2026-07-10）：

```
场景           L1(vdb)           L2(desc)          L3(路由)      L4(铁律)
报错排查       debugging(0.33)   ✅ debugging      ✅              ✅
部署服务       mlops(0.38)       ✅ shipping-verif  ✅              ✅
单元测试       dogfood(0.51)     ✅ tdd-workflow    ✅              —
混合任务       sys-admin(0.49)   ✅ code-output     ✅ 双路由        ✅
日常查询       agent-reach(0.31) ⏭ 不加载           —              ✅
主脑模式       oracle(0.63)      ✅ oracle          ✅              ✅
```

关键发现：
- L1 vdb 单独不可靠(4/6 场景 top 不对)，但 L2+L3+L4 全覆盖
- L2 desc 扫描是核心保障（系统内置 'MUST scan' 指令）
- 无任何场景出现全部四层同时 miss
- AGENTS.md 删除后，L2 替代其 §1 职能
