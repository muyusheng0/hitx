# 🚀 重构执行方案 — HitX 工程化实施指南

> 作者: 小何（执行架构师）
> 日期: 2026-04-23
> 基于: REFACTOR_PLAN.md v1.0（小方架构方案）

---

## 1. 需求分析

### 1.1 核心目标

| 目标 | 说明 |
|------|------|
| **拆单体** | 4000+ 行 app.py → 15 个蓝图模块，每个 <300 行 |
| **零回归** | 所有 111 个路由端点 100% 兼容，前端/小程序无需任何改动 |
| **可维护** | 新人能在 10 分钟内找到任意功能的代码位置 |
| **安全底座** | 统一错误处理、统一装饰器、配置集中化（Phase 0 已部分完成） |

### 1.2 风险边界 — 绝对不能动

| 边界 | 原因 |
|------|------|
| **URL 路径** | 前端硬编码 + 小程序依赖，改一个 404 就是线上事故 |
| **Session 机制** | Flask session + cookie 配置，改动导致所有用户被踢出 |
| **数据库 Schema** | 18 张表结构、字段名、类型，一个都不能改 |
| **文件存储路径** | `DATA_DIR` 下的 photos/videos/avatars 等目录结构 |
| **wx_api 的 Blueprint 名** | 小程序可能依赖 blueprint 名称或 URL 前缀 |
| **SECRET_KEY / JWT_SECRET** | 改了就全部失效 |

### 1.3 成功标准

- [ ] `git diff --stat` 显示 app.py 从 ~4000 行降至 ~120 行（纯工厂代码）
- [ ] 111 个端点逐一通过冒烟测试，返回码与重构前一致
- [ ] 微信小程序 38 个 `/api/wx/*` 端点全部正常
- [ ] 新闻爬取调度器正常运行，无重复启动
- [ ] 管理后台功能（用户管理、日志、新闻、音乐）全部可用
- [ ] `flask routes` 输出与重构前完全一致（可用脚本 diff）

---

## 2. 架构设计评审

### 2.1 REFACTOR_PLAN.md 评审结论

**总体评价：方案合理，方向正确，可以直接执行。** 但有几点需要修正：

#### ✅ 做得好的地方

- Blueprint 按功能域拆分，15 个模块粒度合理
- database 包保持向后兼容（`__init__.py` 导出层），思路正确
- 渐进式迁移策略（一次移一个蓝图）是低风险做法
- 回滚方案基于 Git commit，务实

#### ⚠️ 需要调整的地方

| 问题 | 调整建议 |
|------|----------|
| **Phase 0 已在进行中** | 实际进度：config.py / decorators.py / errors.py / extensions.py / utils.py 已创建且 app.py 已开始导入。执行计划需以此为起点，不要重复做。 |
| **wx_api 中有重复逻辑** | `wx_api.py` 中有与 `app.py` 重复的点赞、评论、媒体上传逻辑。迁移前需确认：哪些是真正独立的，哪些应该复用公共函数。建议：先提取公共函数到 `utils.py`，再分别迁移。 |
| **media 蓝图职责过重** | 11 个路由包含：图片上传、视频上传、头像上传、profile 更新、媒体删除、媒体点赞。建议内部再按子域分组函数，但保持为单个 Blueprint（对外接口不变）。 |
| **admin 蓝图耦合 news/music** | admin 里混入了新闻管理、音乐管理的操作。建议：保留在 admin 蓝图中（因为都是管理员操作），但数据库调用应走 `database.news` / `database.media` 子模块。 |
| **缺少路由一致性验证工具** | 需要一个 `routes_check.py` 脚本，重构前跑一次存基线，重构后每次阶段结束跑一次做 diff。 |

### 2.2 建议的目录结构

基于 REFACTOR_PLAN.md 调整后的最终结构：

```
hitx/
├── app.py                          # ~120行，应用工厂
├── config.py                       # ✅ 已创建
├── decorators.py                   # ✅ 已创建
├── extensions.py                   # ✅ 已创建
├── utils.py                        # ✅ 已创建
├── errors.py                       # ✅ 已创建
├── models.py                       # [可选] 后期添加
├── routes_check.py                 # [新增] 路由一致性验证脚本
│
├── database/                       # 数据库包（重组后）
│   ├── __init__.py                 # 向后兼容导出
│   ├── connection.py               # 连接管理
│   ├── student.py                  # 学生表
│   ├── message.py                  # 留言表
│   ├── media.py                    # 媒体表
│   ├── voice.py                    # 语音表
│   ├── activity.py                 # 动态表
│   ├── notification.py             # 通知表
│   ├── ai.py                       # AI 表
│   ├── news.py                     # 新闻表
│   ├── config.py                   # 配置表
│   ├── login_log.py                # 登录日志表
│   └── wx_binding.py               # 微信绑定表
│
├── blueprints/                     # 功能模块
│   ├── __init__.py                 # 蓝图注册
│   ├── pages/
│   ├── auth/
│   ├── txl/
│   ├── location/
│   ├── message/
│   ├── media/
│   ├── voice/
│   ├── activity/
│   ├── notification/
│   ├── recycle/
│   ├── ai/
│   ├── admin/
│   ├── stats/
│   ├── news/
│   └── wx_miniapp/
│
├── templates/                      # [不动]
├── static/                         # [不动]
├── news_crawler.py                 # [不动]
├── alumni.db                       # [不动]
└── REFACTOR_PLAN.md                # [参考]
```

### 2.3 关键架构决策确认

| 决策 | 结论 |
|------|------|
| 引入 Flask-RESTful / APIFlask？ | **否**。原生路由最安全，迁移成本最低。 |
| 引入 SQLAlchemy ORM？ | **否**。后期考虑，本次不动数据库层语义。 |
| wx_miniapp 独立蓝图？ | **是**。38 个端点，自成体系。 |
| templates/ 拆分？ | **否**。9 个模板，维持现状。 |
| 配置热加载？ | **否**。Flask 重启即可，无需复杂热加载。 |

---

## 3. 任务拆解

### 3.1 当前实际起点

Phase 0 已部分完成：
- ✅ `config.py` 已创建
- ✅ `decorators.py` 已创建
- ✅ `errors.py` 已创建
- ✅ `extensions.py` 已创建
- ✅ `utils.py` 已创建
- ✅ `app.py` 已导入新模块

**但需要注意**：app.py 中仍然保留了全部 ~4000 行代码，新旧代码共存。最终需要清理。

### 3.2 完整任务依赖图

```
                    ┌─────────────────────────────────┐
                    │  P0: 收尾 Phase 0 (2h)          │
                    │  - 清理 app.py 中的旧代码残留    │
                    │  - 创建 routes_check.py 基线脚本 │
                    │  - 建立数据库/服务备份            │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │  P1: database/ 包重组 (3-4h)    │
                    │  - 创建 database/ 目录结构       │
                    │  - __init__.py 导出层 (兼容)     │
                    │  - 拆分 connection.py            │
                    │  - 逐表拆分子模块                │
                    └──────────────┬──────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
    ┌─────────▼──────┐  ┌─────────▼──────┐  ┌──────────▼─────────┐
    │ P2a: 低依赖模块 │  │ P2b: 中依赖模块 │  │ P2c: 高依赖模块     │
    │ (可并行)       │  │ (可并行)       │  │ (需最后做)          │
    │                │  │                │  │                    │
    │ stats (2路由)  │  │ location (6)   │  │ media (11路由)     │
    │ news (3路由)   │  │ txl (3路由)    │  │ message (7路由)    │
    │ auth (7路由)   │  │ activity (4)   │  │ pages (9路由)      │
    │                │  │ notification   │  │                    │
    │                │  │ recycle        │  │                    │
    └─────────┬──────┘  └─────────┬──────┘  └──────────┬─────────┘
              │                    │                    │
              └────────────────────┼────────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │  P2d: 特殊模块 (串行)            │
                    │  voice (5) → admin (10) →       │
                    │  ai (7) → wx_miniapp (38)       │
                    │  (wx_miniapp 最大，放最后)       │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │  P3: 收尾 (2h)                   │
                    │  - 删除 app.py 旧路由            │
                    │  - 删除 wx_api.py                │
                    │  - 删除 database.py (旧版)       │
                    │  - app.py 精简为工厂             │
                    │  - 全量回归测试                  │
                    └─────────────────────────────────┘
```

### 3.3 关键路径（串行任务链）

```
P0 收尾 → P1 database 包 → P2d(wx_miniapp) → P3 收尾
```

这是最长路径，**决定了最短完成时间**。wx_miniapp 38 个端点 + 去重逻辑检查是最重的工作量。

### 3.4 可并行任务

P2 阶段中，以下模块可以**完全并行**（无相互依赖）：

| 并行组 | 模块 | 可并行原因 |
|--------|------|------------|
| Group A | stats, news, auth | 路由少、逻辑简单、互不依赖 |
| Group B | location, txl, activity, notification, recycle | 中等复杂度、各自独立 |
| Group C | voice, admin, ai | 有少量跨模块调用，但调用的是 database 层 |
| Group D | media, message | 复杂度最高，建议单独分配 |
| Group E | pages | 依赖 session + 多个 database 调用，需等 P1 完成 |

### 3.5 任务列表与预估

| ID | 任务 | 预估 | 前置 | 优先级 |
|----|------|------|------|--------|
| P0.1 | 建立完整备份 (git tag + db dump) | 15min | — | 🔴 P0 |
| P0.2 | 创建 `routes_check.py` 基线脚本 | 30min | — | 🔴 P0 |
| P0.3 | 跑基线测试，保存 routes 快照 | 15min | P0.2 | 🔴 P0 |
| P0.4 | 清理 app.py 中新模块的重复定义 | 1h | — | 🔴 P0 |
| P1.1 | 创建 database/ 目录 + __init__.py | 30min | P0 | 🔴 P1 |
| P1.2 | 拆分 connection.py | 30min | P1.1 | 🟡 P1 |
| P1.3 | 拆分 student.py | 45min | P1.2 | 🟡 P1 |
| P1.4 | 拆分 message.py | 45min | P1.2 | 🟡 P1 |
| P1.5 | 拆分 media.py | 45min | P1.2 | 🟡 P1 |
| P1.6 | 拆分 voice/activity/notification/ai/news/config/login_log/wx_binding | 2h | P1.2 | 🟡 P1 |
| P1.7 | database/ 全量回归测试 | 30min | P1.3-P1.6 | 🟡 P1 |
| P2.1 | stats 蓝图 | 30min | P1 | 🟢 P2 |
| P2.2 | news 蓝图 | 30min | P1 | 🟢 P2 |
| P2.3 | auth 蓝图 | 1h | P1 | 🟢 P2 |
| P2.4 | location 蓝图 | 1h | P1 | 🟢 P2 |
| P2.5 | txl 蓝图 | 45min | P1 | 🟢 P2 |
| P2.6 | activity 蓝图 | 45min | P1 | 🟢 P2 |
| P2.7 | notification 蓝图 | 30min | P1 | 🟢 P2 |
| P2.8 | recycle 蓝图 | 30min | P1 | 🟢 P2 |
| P2.9 | voice 蓝图 | 45min | P1 | 🟢 P2 |
| P2.10 | admin 蓝图 | 1.5h | P1 | 🟡 P2 |
| P2.11 | ai 蓝图 | 1h | P1 | 🟢 P2 |
| P2.12 | media 蓝图 | 2h | P1 | 🔴 P2 |
| P2.13 | message 蓝图 | 1.5h | P1 | 🔴 P2 |
| P2.14 | pages 蓝图 | 1.5h | P1 | 🟡 P2 |
| P2.15 | wx_miniapp 蓝图 | 3h | P1 | 🔴 P2 |
| P3.1 | 删除 app.py 旧路由 + 精简为工厂 | 30min | P2.1-P2.15 | 🔴 P3 |
| P3.2 | 删除 wx_api.py | 15min | P2.15 | 🟡 P3 |
| P3.3 | 删除 database.py 旧文件 | 15min | P1.7 | 🟡 P3 |
| P3.4 | 全量回归测试 | 1h | P3.1-P3.3 | 🔴 P3 |

---

## 4. 多 Agent 协作分工

### 4.1 分工策略

假设 1 个架构师（我）+ N 个执行 agent，最优分配：

```
架构师 (小何)
├── Agent A: database 包重组
├── Agent B: 低依赖蓝图 (stats, news, auth)
├── Agent C: 中依赖蓝图 (location, txl, activity, notification, recycle)
├── Agent D: 复杂蓝图 (media, message)
├── Agent E: 特殊蓝图 (voice, admin, ai, pages)
└── Agent F: wx_miniapp (最大模块)
```

### 4.2 执行时序

```
时间线 →
┌──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┐
│      │      │      │      │      │      │      │      │      │      │      │
│ P0   │ P1   │      │ P2 并行阶段                                        │ P3 │
│ 收尾 │ 重组 │      │                                                       │ 收尾 │
│ (2h) │ (4h) │      │                                                       │ (2h) │
│      │      │      │      │      │      │      │      │      │      │      │
├──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┤
│ 架构师│ 架构师│      │      │      │      │      │      │      │      │ 架构师│
│ 备份  │ 设计  │ 评审 │ 评审 │ 评审 │ 评审 │ 评审 │ 评审 │ 评审 │ 评审 │ 全量  │
│ 基线  │ 评审  │ A    │ B    │ C    │ D    │ E    │ F    │ 集成 │ 集成 │ 回归  │
│       │       │      │      │      │      │      │      │      │      │       │
├──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┤
│      │ Agent│      │      │      │      │      │      │      │      │       │
│      │ A    │      │      │      │      │      │      │      │      │       │
│      │ database│    │      │      │      │      │      │      │      │       │
│      │ 重组  │      │      │      │      │      │      │      │      │       │
├──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┤
│      │ 等待  │      │ Agent│ Agent│ Agent│ Agent│ Agent│ Agent│      │       │
│      │ P1完  │      │ B    │ C    │ D    │ E    │ F    │      │      │       │
│      │       │      │ 低依赖│ 中依赖│ 复杂  │ 特殊  │ wx   │      │      │       │
│      │       │      │ 蓝图  │ 蓝图  │ 蓝图  │ 蓝图  │ mini │      │      │       │
└──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┘
```

### 4.3 各 Agent 具体职责

| Agent | 负责内容 | 输入 | 输出 | 前置依赖 |
|-------|---------|------|------|----------|
| **架构师 (我)** | P0 收尾、架构设计评审、P1 数据库拆分设计、各阶段 code review、P3 收尾集成 | — | 基线脚本、拆分设计、code review 意见 | — |
| **Agent A** | database/ 包重组（connection → 13 个子模块） | database.py 源码 | database/ 目录，14 个文件 | P0 完成 |
| **Agent B** | stats (2) + news (3) + auth (7) 蓝图 | app.py 中对应路由 | blueprints/{stats,news,auth}/ | P1 完成 |
| **Agent C** | location (6) + txl (3) + activity (4) + notification (3) + recycle (3) 蓝图 | app.py 中对应路由 | blueprints/{location,txl,activity,notification,recycle}/ | P1 完成 |
| **Agent D** | media (11) + message (7) 蓝图 | app.py + wx_api.py 中对应路由 + 去重分析 | blueprints/{media,message}/ | P1 完成 |
| **Agent E** | voice (5) + admin (10) + ai (7) + pages (9) 蓝图 | app.py 中对应路由 | blueprints/{voice,admin,ai,pages}/ | P1 完成 |
| **Agent F** | wx_miniapp (38) 蓝图 | wx_api.py 全部源码 | blueprints/wx_miniapp/ | P1 完成 |

### 4.4 Agent 间依赖与协调

```
依赖规则：
1. P0 完成前：任何人不得开始 P1/P2
2. P1 完成后：Agent B-F 可同时开工（无相互依赖）
3. 每个 Agent 完成后：架构师做 code review + 跑 routes_check.py
4. 全部 P2 完成后：架构师执行 P3（收尾集成）

协调机制：
- 每个 Agent 提交前必须：git commit + 跑 routes_check.py 对比基线
- 架构师每完成一个阶段评审，给下一个 Agent 发 "green light"
- 任何 Agent 遇到跨模块调用问题，上报架构师决策
```

### 4.5 我（架构师）的具体工作

1. **P0 阶段**：创建 `routes_check.py` 基线脚本、建立备份、确认 Phase 0 收尾状态
2. **P1 阶段**：设计 database/ 包的 `__init__.py` 导出清单（哪个函数在哪个子模块），给 Agent A 执行
3. **P2 各阶段评审**：每个 Agent 提交后，我跑验证 + 做 code review
4. **P3 阶段**：亲自执行收尾集成——删除旧代码、精简 app.py、全量回归

---

## 5. 质量控制

### 5.1 阶段验收标准

| 阶段 | 验收标准 | 验证方式 |
|------|----------|----------|
| P0 | `routes_check.py` 生成基线快照，包含全部 111 个端点 | 脚本自动验证 |
| P1 | `import database` 正常，所有旧函数名可用，单元测试通过 | Python import + 函数调用测试 |
| P2.x | 迁移的蓝图端点返回码与基线一致，功能手动验证通过 | `routes_check.py` diff + 手动验证 |
| P3 | app.py ≤ 150 行，`flask routes` 与基线 100% 一致 | 脚本自动验证 |

### 5.2 零回归保证策略

#### 策略一：路由基线对比（核心）

创建 `routes_check.py` 脚本：

```python
#!/usr/bin/env python3
"""路由一致性检查工具 — 重构前跑一次保存基线，重构后每次阶段结束跑一次对比。"""

import json
import subprocess
import sys

def get_routes():
    """获取 Flask 应用所有路由，返回排序后的列表。"""
    result = subprocess.run(
        ['python', '-c', 
         'from app import app; '
         'routes = [(r.rule, sorted(r.methods)) for r in app.url_map.iter_rules() '
         'if r.rule != "/static/<filename>"]; '
         'print(json.dumps(sorted(routes)))'],
        capture_output=True, text=True, cwd='/home/admin/.openclaw/workspace/hitx'
    )
    if result.returncode != 0:
        print(f"ERROR: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'check'
    baseline_file = 'docs/routes_baseline.json'
    
    if mode == 'baseline':
        routes = get_routes()
        with open(baseline_file, 'w') as f:
            json.dump(routes, f, indent=2)
        print(f"✅ 基线已保存：{baseline_file}，共 {len(routes)} 个端点")
    
    elif mode == 'check':
        routes = get_routes()
        with open(baseline_file) as f:
            baseline = json.load(f)
        
        current_set = set(r[0] for r in routes)
        baseline_set = set(r[0] for r in baseline)
        
        added = current_set - baseline_set
        removed = baseline_set - current_set
        
        if added:
            print(f"❌ 新增路由 ({len(added)}): {added}")
        if removed:
            print(f"❌ 丢失路由 ({len(removed)}): {removed}")
        if not added and not removed:
            print(f"✅ 路由一致性检查通过：{len(routes)} 个端点全部匹配")
        else:
            sys.exit(1)
```

**使用方式**：
```bash
# 重构前：保存基线
python routes_check.py baseline

# 每个阶段后：检查一致性
python routes_check.py check
```

#### 策略二：Git 分步提交

每次阶段完成后立即 commit，格式：

```
refactor(database): create package with connection + student submodules
refactor(blueprint): migrate stats module (2 routes)
refactor(blueprint): migrate news module (3 routes)
refactor(blueprint): migrate auth module (7 routes)
...
```

任何阶段出问题，`git revert HEAD` 即可回退。

#### 策略三：功能验证清单

每个蓝图迁移完成后，手动验证清单（由执行 Agent 勾选）：

```markdown
## [模块名] 迁移验证
- [ ] 所有端点返回 200/302（无 404/500）
- [ ] GET 端点返回数据结构不变
- [ ] POST 端点接受/返回格式不变
- [ ] Session/认证相关端点行为不变
- [ ] 数据库读写无异常
- [ ] routes_check.py 通过
```

### 5.3 自动化测试方案

#### 短期（本次重构期间）

不写完整的 pytest 测试套件（成本太高，且不影响重构质量）。采用：

1. **路由基线对比**（`routes_check.py`）：自动化、每次必跑
2. **关键端点冒烟测试**：写一个 `smoke_test.py`，对每个端点发请求检查返回码
3. **Git hook**（可选）：pre-commit 跑 `routes_check.py check`

#### 中期（重构完成后 1-2 周内）

1. 为每个蓝图写基础 pytest 测试（至少覆盖 GET 端点）
2. 数据库层的 CRUD 函数写单元测试
3. CI/CD 中集成测试

#### 冒烟测试脚本示例

```python
#!/usr/bin/env python3
"""冒烟测试 — 对所有端点发请求，检查返回码。"""
import requests
import json

BASE_URL = 'http://localhost:5000'

# 端点列表 (从 baseline 自动生成或手动维护)
ENDPOINTS = [
    ('GET', '/'),
    ('GET', '/login'),
    ('GET', '/api/stats'),
    ('GET', '/api/news'),
    # ... 111 个端点
]

def smoke_test():
    passed = 0
    failed = 0
    for method, path in ENDPOINTS:
        try:
            resp = requests.request(method, f'{BASE_URL}{path}', timeout=5)
            # 2xx, 3xx, 401(未登录正常) 都算通过
            if resp.status_code < 500:
                passed += 1
            else:
                print(f"❌ {method} {path} → {resp.status_code}")
                failed += 1
        except Exception as e:
            print(f"❌ {method} {path} → ERROR: {e}")
            failed += 1
    
    print(f"\n{'='*40}")
    print(f"通过: {passed}/{passed+failed}")
    if failed:
        print(f"失败: {failed}")
        return False
    return True
```

---

## 6. 迭代节奏

### 6.1 交付策略：多 PR 逐步交付

**不一次性重构完再上线**。理由：

1. 8251 行代码一次性重构 → 单次 PR 太大，review 成本高
2. 如果发现问题，回滚范围太大
3. 分阶段 PR 可以随时暂停，不影响已完成的模块

### 6.2 PR 规划

| PR # | 内容 | 大小 | 风险 |
|------|------|------|------|
| PR 0 | Phase 0 收尾 + routes_check.py + 基线快照 | 小 | 低 |
| PR 1 | database/ 包重组（含 __init__.py 兼容层） | 中 | 中 |
| PR 2 | 低依赖蓝图: stats + news + auth | 小 | 低 |
| PR 3 | 中依赖蓝图: location + txl + activity + notification + recycle | 中 | 低 |
| PR 4 | 复杂蓝图: voice + admin + ai | 中 | 中 |
| PR 5 | 高复杂蓝图: media + message | 中 | 中 |
| PR 6 | pages 蓝图 | 小 | 低 |
| PR 7 | wx_miniapp 蓝图 | 大 | 高 |
| PR 8 | 收尾: 删除旧代码 + app.py 精简 + 全量回归 | 中 | 低 |

**共 9 个 PR，每个可独立 review 和回滚。**

### 6.3 里程碑与交付物

| 里程碑 | 交付物 | 质量标准 |
|--------|--------|----------|
| M0: 基线 | `docs/routes_baseline.json` + 备份 tag | 111 个端点全覆盖 |
| M1: 数据库层 | `database/` 包（14 个文件） | 所有旧函数名可用 |
| M2: 低依赖模块完成 | 3 个蓝图模块 | routes_check 通过 |
| M3: 中依赖模块完成 | 5 个蓝图模块 | routes_check 通过 |
| M4: 特殊模块完成 | 4 个蓝图模块 | routes_check 通过 |
| M5: 复杂模块完成 | media + message | routes_check 通过 |
| M6: pages 完成 | pages 蓝图 | 所有页面可访问 |
| M7: wx_miniapp 完成 | wx_miniapp 蓝图 | 小程序验证通过 |
| M8: 收尾 | app.py ≤ 150 行，旧文件删除 | routes_check 100% 一致 |

### 6.4 工时与时间线

| 阶段 | 工时 | 完成节点 | 说明 |
|------|------|----------|------|
| P0 收尾 | 2h | M0 | 基线、备份、确认 Phase 0 状态 |
| P1 数据库重组 | 4h | M1 | 需要谨慎，函数签名零改动 |
| P2 蓝图迁移 | 15h | M2-M7 | 核心工作量，可并行 |
| P3 收尾集成 | 2h | M8 | 删除旧代码、精简、全量测试 |
| **总计** | **~23 小时** | | 单 agent 串行约 3 个工作日 |

**多 Agent 并行时间线**：

| 时间 | 工作 |
|------|------|
| Day 1 AM (2h) | P0 收尾（架构师） |
| Day 1 AM-PM (4h) | P1 数据库重组（Agent A），架构师做设计评审 |
| Day 2 (6-8h) | P2 蓝图迁移（Agent B-F 并行），架构师逐个评审 |
| Day 3 AM (2h) | P3 收尾集成（架构师），全量回归 |

**并行模式：2-3 天可完成。串行模式：约 3 个工作日。**

---

## 7. 风险应对速查

| 风险 | 信号 | 应对 |
|------|------|------|
| 路由丢失 | `routes_check.py check` 报 removed | `git revert HEAD`，重新检查迁移 |
| Session 失效 | 登录后立即被踢出 | 检查 `app.secret_key` 和 session cookie 配置是否与重构前一致 |
| 数据库函数找不到 | `ImportError` 或 `AttributeError` | 检查 `database/__init__.py` 导出列表是否遗漏 |
| 调度器重复启动 | 新闻爬取重复执行 | 确认 `init_news_scheduler` 只在 `create_app()` 中调用一次 |
| 文件上传 500 | 上传端点报错 | 检查 `UPLOAD_FOLDER` 和 `DATA_DIR` 路径常量是否一致 |
| wx_miniapp 报错 | 小程序 API 返回异常 | 检查 blueprint URL 前缀是否为 `/api/wx`，与原 wx_api.py 一致 |

---

## 附录：执行检查清单

重构开始前逐项确认：

- [ ] Git 仓库干净（无未提交变更）
- [ ] `git tag v1.0-pre-refactor` 已创建
- [ ] 数据库 `alumni.db` 已备份
- [ ] `routes_check.py baseline` 已跑，基线已保存
- [ ] 开发环境可正常启动（`python app.py` 或 `./start.sh`）
- [ ] 所有端点冒烟测试通过
- [ ] 小程序开发工具可正常连接
- [ ] 团队成员/Agent 分工已确认

---

_方案结束。核心原则：先验后动、小步快跑、随时可退。_
