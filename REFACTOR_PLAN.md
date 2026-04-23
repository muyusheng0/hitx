# 🏗️ 吉大通信八班同学录 — 代码重构方案

> 作者: 小方（方案架构师）
> 日期: 2026-04-23
> 版本: v1.0

---

## 一、现状诊断

### 1.1 代码规模

| 文件 | 行数 | 职责 | 问题 |
|------|------|------|------|
| app.py | 4,076 | 全部路由+工具函数+调度器 | **单文件反模式**，所有东西挤在一起 |
| database.py | 2,022 | 数据库操作 | 功能过多，未按表分组 |
| wx_api.py | 1,447 | 微信小程序 API | 已使用 Blueprint ✅，但包含 admin/media/ai 等功能 |
| news_crawler.py | 706 | 新闻爬取 | 职责单一 ✅ |
| **合计** | **8,251** | | |

### 1.2 路由分布统计

| 模块 | 路由数 | 分布在 |
|------|--------|--------|
| 页面路由 | 9 | app.py |
| 通讯录 API | 3 | app.py |
| 地理位置 API | 6 | app.py |
| 留言/评论 API | 6 | app.py |
| 媒体管理 API | 12 | app.py |
| 喊话 API | 3 | app.py |
| 用户认证 API | 7 | app.py |
| 动态/通知 API | 6 | app.py |
| 管理员 API | 10 | app.py + wx_api.py |
| AI 功能 API | 6 | app.py + wx_api.py |
| 新闻 API | 5 | app.py + wx_api.py |
| 微信小程序 API | 38 | wx_api.py |
| **合计** | **~111** | |

### 1.3 核心问题

1. **单文件 4000+ 行**：滚动找代码、合并冲突地狱、新人无法上手
2. **职责混乱**：wx_api.py 里混入了 admin/music/news 等非小程序功能
3. **重复代码**：app.py 和 wx_api.py 里有多组重复逻辑（点赞、媒体上传、评论等）
4. **无统一错误处理**：每个路由自己 try/except
5. **无统一中间件**：登录检查分散在 `require_login()` 装饰器中
6. **全局变量**：`_news_cache`、`_alumni_cache`、`_ip_location_cache` 直接挂载在模块级

---

## 二、目标架构

### 2.1 设计原则

- **蓝图按功能模块划分**，保持 URL 路由 100% 兼容
- **database.py 保持接口不变**（仅内部重组），不影响 app 层
- **渐进式迁移**：一次迁移一个蓝图，每次迁移后功能完全可用
- **零停机**：利用 Flask 蓝图热替换特性

### 2.2 重构后目录结构

```
hitx/
├── app.py                          # [~120行] 应用工厂 + 入口
├── extensions.py                   # [~60行]  扩展初始化 (scheduler, etc)
├── database.py                     # [重组]   数据库层（向后兼容）
├── wx_api.py                       # [废弃]   内容迁移到 blueprints/wx_miniapp.py
├── news_crawler.py                 # [保留]   职责单一，不动
├── config.py                       # [新增]   配置集中管理
├── decorators.py                   # [新增]   通用装饰器 (登录检查、管理员检查)
├── utils.py                        # [新增]   通用工具函数 (压缩、IP、缓存)
├── models.py                       # [新增]   数据模型类（可选，替代纯 dict）
├── errors.py                       # [新增]   统一错误处理
│
├── blueprints/                     # [新增]   功能模块蓝图
│   ├── __init__.py                 # 蓝图注册
│   ├── pages/                      # 页面渲染
│   │   ├── __init__.py
│   │   └── views.py                # /, /login, /txl, /lyb, /gallery, /video, /media, /about, /ai-chat
│   ├── auth/                       # 认证模块
│   │   ├── __init__.py
│   │   └── views.py                # /api/verify, /api/user/*, /api/logout
│   ├── txl/                        # 通讯录模块
│   │   ├── __init__.py
│   │   └── views.py                # /api/txl/list, /api/txl/map, /api/get_student
│   ├── location/                   # 地理位置模块
│   │   ├── __init__.py
│   │   └── views.py                # /api/location/*, /api/update_coords, /api/update_gps_coords
│   ├── message/                    # 留言模块
│   │   ├── __init__.py
│   │   └── views.py                # /api/add_message, /api/delete_message,
│   │                               #            /api/like_message, /api/unlike_message,
│   │                               #            /api/get_message_likes/*,
│   │                               #            /api/add_comment, /api/get_comments/*,
│   │                               #            /api/delete_comment
│   ├── media/                      # 媒体模块
│   │   ├── __init__.py
│   │   └── views.py                # /api/upload_image, /api/upload_video, /api/add_video,
│   │                               #            /api/upload_avatar, /upload_avatar,
│   │                               #            /update_profile, /api/update_profile,
│   │                               #            /api/delete_photo, /api/delete_video,
│   │                               #            /api/like_media, /api/unlike_media,
│   │                               #            /api/get_media_likes/*
│   ├── voice/                      # 喊话模块
│   │   ├── __init__.py
│   │   └── views.py                # /api/add_voice_message, /api/upload_voice_shout,
│   │                               #            /api/get_voice_shouts/*,
│   │                               #            /api/voice_shout/delete, /api/voice_shout/restore
│   ├── activity/                   # 动态模块
│   │   ├── __init__.py
│   │   └── views.py                # /api/get_activities, /api/get_unread_activity_count,
│   │                               #            /api/mark_activities_viewed,
│   │                               #            /api/delete_activity
│   ├── notification/               # 通知模块
│   │   ├── __init__.py
│   │   └── views.py                # /api/notifications, /api/notifications/count,
│   │                               #            /api/notifications/mark_read
│   ├── recycle/                    # 回收站模块
│   │   ├── __init__.py
│   │   └── views.py                # /api/get_deleted, /api/restore_deleted,
│   │                               #            /api/permanent_delete
│   ├── ai/                         # AI 模块
│   │   ├── __init__.py
│   │   └── views.py                # /api/openclaw/chat, /api/openclaw/queue_status,
│   │                               #            /api/openclaw/mark_connected,
│   │                               #            /api/openclaw/mark_disconnected,
│   │                               #            /api/openclaw/history, /api/openclaw/history/users,
│   │                               #            /api/ai_image/generate
│   ├── admin/                      # 管理模块
│   │   ├── __init__.py
│   │   └── views.py                # /api/super_admin/set_admin,
│   │                               #            /api/admin/login_logs/delete,
│   │                               #            /api/get_login_logs,
│   │                               #            /api/admin/news/*, /api/admin/music/*
│   ├── stats/                      # 统计模块
│   │   ├── __init__.py
│   │   └── views.py                # /api/stats, /api/check_verify
│   ├── news/                       # 新闻/校友模块
│   │   ├── __init__.py
│   │   └── views.py                # /api/news, /api/alumni, /api/captcha
│   └── wx_miniapp/                 # 微信小程序 API（原 wx_api.py 迁移）
│       ├── __init__.py
│       └── views.py                # /api/wx/* (全部 38 个端点)
│
├── templates/                      # [保留]   Jinja2 模板（不动）
├── static/                         # [保留]   静态资源（不动）
└── REFACTOR_PLAN.md                # [本文件]
```

---

## 三、文件职责说明

### 3.1 核心文件

#### `app.py`（应用工厂，~120 行）

```python
from flask import Flask
from config import AppConfig
from extensions import init_extensions
from blueprints import register_blueprints
from errors import register_error_handlers

def create_app(config_class=AppConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    init_extensions(app)          # scheduler, db init
    register_blueprints(app)      # 注册所有蓝图
    register_error_handlers(app)  # 统一错误处理
    
    return app

# 入口
app = create_app()
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
```

职责：应用工厂模式，纯胶水代码，不包含任何业务逻辑。

#### `config.py`（配置集中化）

| 内容 | 说明 |
|------|------|
| `AppConfig` | Flask 配置（secret_key, upload, session cookie） |
| `DATA_DIR` | 数据目录 `/home/ubuntu/jlu8` |
| `ADMIN_USERS` | 管理员名单 |
| `WX_APPID / WX_SECRET` | 微信配置 |
| `JWT_SECRET` | JWT 密钥 |

#### `extensions.py`（扩展初始化）

| 内容 | 说明 |
|------|------|
| `init_scheduler()` | APScheduler 新闻爬取调度器 |
| `init_extensions(app)` | 统一初始化入口 |

#### `decorators.py`（通用装饰器）

| 装饰器 | 说明 |
|--------|------|
| `@login_required` | 登录检查（替代 `require_login()`） |
| `@admin_required` | 管理员检查（替代 `is_admin()`） |
| `@super_admin_required` | 超级管理员检查 |
| `@wx_token_required` | 微信小程序 Token 验证 |

#### `utils.py`（通用工具）

| 函数 | 说明 |
|------|------|
| `compress_avatar()` | 头像压缩 |
| `compress_image()` | 图片压缩 |
| `create_thumbnail()` | 缩略图生成 |
| `get_ip_location()` | IP 归属地查询 + 缓存 |
| `get_real_ip()` | 获取真实客户端 IP |
| `allowed_file()` | 文件扩展名检查 |
| `sanitize_input()` | 输入清洗 |
| `haversine_distance()` | 地理距离计算 |
| `get_city_name()` / `get_province_name()` | 地名映射 |
| `is_public_path()` | 公开路径判断 |
| `_news_cache` / `_alumni_cache` | 缓存管理 |

#### `errors.py`（统一错误处理）

```python
def register_error_handlers(app):
    @app.errorhandler(413)
    def request_entity_too_large(e): ...
    
    @app.errorhandler(401)
    def unauthorized(e): ...
    
    @app.errorhandler(500)
    def internal_error(e): ...
```

#### `models.py`（可选，数据模型类）

将数据库返回的 dict 包装为轻量数据类，提升代码可读性。

```python
from dataclasses import dataclass

@dataclass
class Student:
    id: int
    name: str
    hometown_name: str
    coords: str
    # ...

# 或使用 TypedDict 保持零改动
from typing import TypedDict

class StudentDict(TypedDict):
    id: int
    name: str
    # ...
```

### 3.2 蓝图模块

每个蓝图模块结构统一：

```
blueprints/<module>/
├── __init__.py      # 创建 Blueprint 对象，导入 views
└── views.py         # 路由处理函数
```

#### 蓝图职责映射表

| 蓝图 | URL 前缀 | 路由数 | 核心职责 |
|------|----------|--------|----------|
| `pages` | 无 | 9 | 页面渲染（HTML 模板） |
| `auth` | `/api` | 7 | 学生验证、密码管理、登出 |
| `txl` | `/api` | 3 | 通讯录列表、地图数据 |
| `location` | `/api` | 6 | 省市区查询、坐标更新 |
| `message` | `/api` | 7 | 留言 CRUD、评论、点赞 |
| `media` | `/api` | 11 | 图片/视频/头像上传、管理、点赞 |
| `voice` | `/api` | 5 | 语音喊话上传、查询、删除、恢复 |
| `activity` | `/api` | 4 | 动态查询、已读标记、删除 |
| `notification` | `/api` | 3 | 通知查询、计数、已读标记 |
| `recycle` | `/api` | 3 | 回收站查询、恢复、彻底删除 |
| `ai` | `/api` | 7 | OpenClaw 聊天、AI 图片生成 |
| `admin` | `/api` | 10 | 管理员设置、登录日志、新闻管理、音乐管理 |
| `stats` | `/api` | 2 | 统计数据、验证状态检查 |
| `news` | `/api` | 3 | 新闻查询、校友会、验证码 |
| `wx_miniapp` | `/api/wx` | 38 | 微信小程序全部 API |

---

## 四、database.py 重组方案

### 4.1 原则

**保持所有函数签名不变**，仅内部重组文件结构。确保 app 层 `import database` + `database.func()` 调用零改动。

### 4.2 重组后的 database 包

```
database/
├── __init__.py          # 导出所有公共函数（保持向后兼容）
├── connection.py        # 连接管理 (get_db, close_db, init_db)
├── student.py           # 学生表操作 (read_txl, write_txl, update_*)
├── message.py           # 留言表操作 (read_lyb, add_comment, delete_comment, ...)
├── media.py             # 媒体表操作 (read_videos, read_photos, delete_*, likes)
├── voice.py             # 语音喊话 (read_voice_shouts, add_voice_shout, ...)
├── activity.py          # 动态表操作 (read_activities, write_activity, ...)
├── notification.py      # 通知表操作 (create_notification, get_notifications, ...)
├── ai.py                # AI 聊天历史 (save_ai_chat, get_ai_chat_history, ...)
├── news.py              # 新闻表操作 (get_news, save_news, clear_news, ...)
├── config.py            # 配置表操作 (get_config, set_config, ...)
├── login_log.py         # 登录日志 (write_login_log, read_login_logs, ...)
└── wx_binding.py        # 微信绑定 (bind_wx_openid, get_binding_by_openid, ...)
```

#### `__init__.py` 示例

```python
# database/__init__.py
# 保持向后兼容：所有旧函数名仍然可用

from database.connection import get_db, close_db, init_db
from database.student import read_txl, write_txl, update_student_gps_coords, update_student_admin
from database.message import read_lyb, write_lyb, get_next_lyb_id, add_comment, get_comments_by_message, \
    delete_comment, get_message_likes, has_liked_message, like_message, unlike_message, \
    delete_message_by_time_nickname, delete_message
from database.media import read_videos, write_videos, get_next_video_id, read_photos, write_photos, \
    get_next_photo_id, delete_photo, delete_video, get_media_likes, has_liked_media, \
    like_media, unlike_media, get_all_likes_for_media, get_all_liked_for_user
from database.voice import read_voice_shouts, get_voice_shouts_by_target, add_voice_shout, \
    delete_voice_shout, restore_voice_shout
# ... 所有导出
```

### 4.3 迁移策略

1. 先创建 `database/` 目录和 `__init__.py`
2. 将 `database.py` 重命名为 `database/_legacy.py`
3. `__init__.py` 从 `_legacy.py` 导入所有函数
4. 逐步将函数迁移到对应子模块
5. 全部迁移完成后删除 `_legacy.py`

---

## 五、渐进式迁移步骤（不停机）

### Phase 0：准备（1-2 小时）

| 步骤 | 操作 | 风险 |
|------|------|------|
| 0.1 | 完整备份项目目录和数据库 | 无 |
| 0.2 | 创建 `config.py`，将硬编码配置提取出来 | 极低 |
| 0.3 | 创建 `extensions.py`，提取调度器代码 | 极低 |
| 0.4 | 创建 `utils.py`，提取工具函数 | 极低 |
| 0.5 | 创建 `decorators.py`，提取装饰器 | 极低 |
| 0.6 | 创建 `errors.py`，注册统一错误处理 | 极低 |
| 0.7 | 在 `app.py` 顶部 import 新模块，但不改动路由 | 无 |

### Phase 1：database.py 重组（2-3 小时）

| 步骤 | 操作 | 风险 |
|------|------|------|
| 1.1 | 创建 `database/` 包结构 | 无 |
| 1.2 | 创建 `__init__.py` 从旧文件导出所有函数 | 极低 |
| 1.3 | 重命名 `database.py` → `database/_legacy.py` | 低 |
| 1.4 | 测试：确保所有 `database.func()` 调用正常 | — |
| 1.5 | 逐个子模块迁移函数 | 中 |
| 1.6 | 全部迁移后删除 `_legacy.py` | 低 |

### Phase 2：独立蓝图迁移（按优先级，每个 1-2 小时）

> **每个阶段完成后必须：重启服务 → 功能验证 → 确认正常再进入下一阶段**

| 阶段 | 模块 | 路由来源 | 验证点 |
|------|------|----------|--------|
| 2.1 | `stats` | `/api/stats`, `/api/check_verify` | 统计数据页正常 |
| 2.2 | `news` | `/api/news`, `/api/alumni`, `/api/captcha` | 新闻页、验证码正常 |
| 2.3 | `location` | 6 个 `/api/location/*` 端点 | 地图功能正常 |
| 2.4 | `auth` | 7 个 `/api/user/*` + 验证端点 | 登录/验证正常 |
| 2.5 | `pages` | 9 个页面路由 | 所有页面可访问 |
| 2.6 | `txl` | 3 个通讯录端点 | 通讯录列表/地图正常 |
| 2.7 | `message` | 7 个留言端点 | 留言/评论/点赞正常 |
| 2.8 | `media` | 11 个媒体端点 | 上传/展示/点赞正常 |
| 2.9 | `voice` | 5 个喊话端点 | 语音喊话正常 |
| 2.10 | `activity` | 4 个动态端点 | 动态流正常 |
| 2.11 | `notification` | 3 个通知端点 | 通知正常 |
| 2.12 | `recycle` | 3 个回收站端点 | 恢复/删除正常 |
| 2.13 | `ai` | 7 个 AI 端点 | AI 聊天/图片生成正常 |
| 2.14 | `admin` | 10 个管理端点 | 管理员功能正常 |
| 2.15 | `wx_miniapp` | 38 个微信小程序端点 | 小程序全面验证 |

### Phase 3：收尾（1-2 小时）

| 步骤 | 操作 |
|------|------|
| 3.1 | 删除原始 `app.py` 中已迁移的路由 |
| 3.2 | 删除原始 `wx_api.py`（内容已迁移到 `blueprints/wx_miniapp/`） |
| 3.3 | 删除原始 `database.py`（内容已迁移到 `database/` 包） |
| 3.4 | 更新 `app.py` 为纯应用工厂 |
| 3.5 | 编写 `README.md` 说明新架构 |
| 3.6 | 集成测试：全量功能回归 |

### 预计总工时

| 阶段 | 工时 | 累计 |
|------|------|------|
| Phase 0 | 1-2h | 2h |
| Phase 1 | 2-3h | 5h |
| Phase 2 | 15-20h | 25h |
| Phase 3 | 1-2h | 27h |
| **总计** | **20-27 小时** | |

---

## 六、风险评估与回滚方案

### 6.1 风险矩阵

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 迁移过程中路由丢失 | 中 | 高 | 每次迁移后全量路由测试 |
| 数据库函数签名不匹配 | 低 | 高 | Phase 1 先做 `__init__.py` 导出层，零改动 |
| Session 跨蓝图失效 | 低 | 高 | Flask session 是全局的，蓝图不隔离 session |
| 调度器重复启动 | 低 | 中 | 确保 `init_news_scheduler` 只调用一次 |
| 微信 Token 验证失败 | 低 | 高 | 保持 JWT_SECRET 不变，迁移后立即验证 |
| 文件上传路径错误 | 中 | 中 | 保持 `DATA_DIR` 常量不变 |
| 缩略图生成失败 | 低 | 低 | 保持 `compress_image` / `create_thumbnail` 函数不变 |

### 6.2 回滚方案

**策略：每次阶段迁移后提交 Git commit，回滚只需 `git revert`**

```bash
# 每次阶段完成后的标准流程
git add -A
git commit -m "refactor: migrate <module> to blueprint"
git push origin main

# 如果出问题，回滚到上一次正常提交
git revert HEAD          # 撤销最近一次提交
# 或
git reset --hard <commit-hash>  # 回退到指定提交
```

**紧急回滚脚本**（提前准备）：

```bash
#!/bin/bash
# rollback.sh - 紧急回滚到旧版
cd /home/admin/.openclaw/workspace/hitx
git stash                    # 保存当前工作
git checkout main~N          # 回退 N 个提交
systemctl restart hitx       # 重启服务
```

### 6.3 测试清单

每个阶段完成后必须验证：

- [ ] 所有路由 `200` 响应（用 `curl` 或脚本批量检查）
- [ ] 登录功能正常（session 未丢失）
- [ ] 文件上传功能正常（头像、图片、视频）
- [ ] 数据库读写正常
- [ ] 微信小程序 API 正常（如迁移了 wx 模块）
- [ ] 调度器正常运行（新闻爬取）
- [ ] 管理员权限正常

---

## 七、关键设计决策

### 7.1 为什么不重构为 Flask-RESTful / APIFlask？

- 当前使用 Flask 原生路由，改动成本大
- 76+ 端点逐个重写风险高
- 蓝图拆分是**最小风险、最大收益**的方案

### 7.2 为什么不引入 SQLAlchemy ORM？

- 现有 database.py 使用原生 SQLite + 手动 SQL，2000+ 行
- ORM 迁移需要重写所有查询，工作量大
- 当前项目数据量小（18 张表，同学录规模），原生 SQL 性能足够
- 后续如果需要，可以先用 `database/` 包作为过渡层

### 7.3 为什么 wx_miniapp 保留为独立蓝图？

- 已有 Blueprint 结构，迁移成本最低
- 38 个端点构成完整的 API 子系统
- 小程序前端依赖 `/api/wx/*` 路径不变

### 7.4 为什么不拆分 templates/？

- 模板文件数量少（9 个）、职责清晰
- 拆分模板目录对维护成本帮助有限
- 保持与路由的一对一映射关系即可

---

## 八、未来演进建议

1. **引入 SQLAlchemy**：在 `database/` 包稳定后，逐步用 ORM 替代原生 SQL
2. **引入迁移工具**：使用 Flask-Migrate (Alembic) 管理数据库 schema 变更
3. **API 版本化**：在路由前加 `/api/v1/` 前缀，方便未来迭代
4. **单元测试**：为每个蓝图添加 pytest 测试
5. **Docker 化**：将 Flask + SQLite + Scheduler 容器化部署
6. **监控告警**：添加 Sentry 或类似工具监控错误

---

## 附录 A：完整路由映射表

### app.py 原始路由 → 目标蓝图

| 原始路由 | 路由方法 | 目标蓝图 |
|----------|----------|----------|
| `/login` | GET | pages |
| `/` | GET | pages |
| `/txl` | GET | pages |
| `/lyb` | GET | pages |
| `/gallery` | GET | pages |
| `/video` | GET | pages |
| `/media` | GET | pages |
| `/about` | GET | pages |
| `/ai-chat` | GET | pages |
| `/api/verify` | POST | auth |
| `/api/check_verify` | GET | stats |
| `/api/captcha` | GET | news |
| `/api/user/set_password` | POST | auth |
| `/api/check_user_login_password` | POST | auth |
| `/api/user/verify_password` | POST | auth |
| `/api/user/check_password_verified` | GET | auth |
| `/api/user/get_password_prompt` | GET | auth |
| `/api/user/set_password_prompt` | POST | auth |
| `/api/logout` | POST | auth |
| `/api/stats` | GET | stats |
| `/api/txl/list` | GET | txl |
| `/api/txl/map` | GET | txl |
| `/api/get_student` | GET | txl |
| `/api/location/codes_to_names` | GET | location |
| `/api/location/provinces` | GET | location |
| `/api/location/cities/<province_code>` | GET | location |
| `/api/location/districts/<city_code>` | GET | location |
| `/api/location/lookup` | GET | location |
| `/api/update_coords` | POST | location |
| `/api/update_gps_coords` | POST | location |
| `/api/add_message` | POST | message |
| `/api/delete_message` | POST | message |
| `/api/like_message` | POST | message |
| `/api/unlike_message` | POST | message |
| `/api/get_message_likes/<id>` | GET | message |
| `/api/add_comment` | POST | message |
| `/api/get_comments/<id>` | GET | message |
| `/api/delete_comment` | POST | message |
| `/api/upload_image` | POST | media |
| `/api/upload_video` | POST | media |
| `/api/add_video` | POST | media |
| `/api/upload_avatar` | POST | media |
| `/upload_avatar` | POST | media |
| `/update_profile` | POST | media |
| `/api/update_profile` | POST | media |
| `/api/delete_photo` | POST | media |
| `/api/delete_video` | POST | media |
| `/api/like_media` | POST | media |
| `/api/unlike_media` | POST | media |
| `/api/get_media_likes/<type>/<id>` | GET | media |
| `/api/add_voice_message` | POST | voice |
| `/api/upload_voice_shout` | POST | voice |
| `/api/get_voice_shouts/<name>` | GET | voice |
| `/api/voice_shout/delete` | POST | voice |
| `/api/voice_shout/restore` | POST | voice |
| `/api/get_activities` | GET | activity |
| `/api/get_unread_activity_count` | GET | activity |
| `/api/mark_activities_viewed` | POST | activity |
| `/api/delete_activity` | POST | activity |
| `/api/notifications` | GET | notification |
| `/api/notifications/count` | GET | notification |
| `/api/notifications/mark_read` | POST | notification |
| `/api/get_deleted` | GET | recycle |
| `/api/restore_deleted` | POST | recycle |
| `/api/permanent_delete` | POST | recycle |
| `/api/news` | GET | news |
| `/api/alumni` | GET | news |
| `/api/openclaw/chat` | POST | ai |
| `/api/openclaw/queue_status` | GET | ai |
| `/api/openclaw/mark_connected` | POST | ai |
| `/api/openclaw/mark_disconnected` | POST | ai |
| `/api/openclaw/history` | GET/DEL | ai |
| `/api/openclaw/history/users` | GET | ai |
| `/api/ai_image/generate` | POST | ai |
| `/api/super_admin/set_admin` | POST | admin |
| `/api/get_login_logs` | GET | admin |
| `/api/admin/login_logs/delete` | POST | admin |
| `/api/admin/news/crawl` | POST | admin |
| `/api/admin/news/schedule` | GET/POST | admin |
| `/api/admin/news/keywords` | GET/POST | admin |
| `/api/admin/music/generate` | POST | admin |
| `/api/admin/music/list` | GET | admin |
| `/api/admin/music/delete` | POST | admin |
| `/api/admin/music/apikey` | GET/POST | admin |
| `/api/admin/music/setting` | GET/POST | admin |

### wx_api.py 路由 → 目标蓝图

| 原始路由 | 目标蓝图 |
|----------|----------|
| `/api/wx/login` | wx_miniapp |
| `/api/wx/bind` | wx_miniapp |
| `/api/wx/check_bind` | wx_miniapp |
| `/api/wx/txl` | wx_miniapp |
| `/api/wx/txl/<id>` | wx_miniapp |
| `/api/wx/messages` | wx_miniapp |
| `/api/wx/photos` | wx_miniapp |
| `/api/wx/videos` | wx_miniapp |
| `/api/wx/profile` | wx_miniapp |
| `/api/wx/avatar` | wx_miniapp |
| `/api/wx/comments/*` | wx_miniapp |
| `/api/wx/messages/*/like` | wx_miniapp |
| `/api/wx/media/*/like` | wx_miniapp |
| `/api/wx/deleted` | wx_miniapp |
| `/api/wx/notifications` | wx_miniapp |
| `/api/wx/activities` | wx_miniapp |
| `/api/wx/nearest` | wx_miniapp |
| `/api/wx/voice_shout` | wx_miniapp |
| `/api/wx/timeline` | wx_miniapp |
| `/api/wx/admin/*` | wx_miniapp |
| `/api/wx/media/*` | wx_miniapp |
| `/api/wx/messages/*` | wx_miniapp |
| `/api/wx/ai/image/generate` | wx_miniapp |
| `/api/wx/alumni` | wx_miniapp |
| `/api/wx/admin/news/*` | wx_miniapp |

---

## 附录 B：Blueprint 注册代码示例

```python
# blueprints/__init__.py
from blueprints.pages import pages_bp
from blueprints.auth import auth_bp
from blueprints.txl import txl_bp
from blueprints.location import location_bp
from blueprints.message import message_bp
from blueprints.media import media_bp
from blueprints.voice import voice_bp
from blueprints.activity import activity_bp
from blueprints.notification import notification_bp
from blueprints.recycle import recycle_bp
from blueprints.ai import ai_bp
from blueprints.admin import admin_bp
from blueprints.stats import stats_bp
from blueprints.news import news_bp
from blueprints.wx_miniapp import wx_miniapp_bp

BLUEPRINTS = [
    pages_bp,
    auth_bp,
    txl_bp,
    location_bp,
    message_bp,
    media_bp,
    voice_bp,
    activity_bp,
    notification_bp,
    recycle_bp,
    ai_bp,
    admin_bp,
    stats_bp,
    news_bp,
    wx_miniapp_bp,
]

def register_blueprints(app):
    for bp in BLUEPRINTS:
        app.register_blueprint(bp)
```

```python
# blueprints/pages/__init__.py
from flask import Blueprint

pages_bp = Blueprint('pages', __name__)

from blueprints.pages import views  # noqa: F401
```

```python
# blueprints/pages/views.py
from flask import render_template, session, redirect, url_for
from blueprints.pages import pages_bp
import database

@pages_bp.route('/login')
def login_page():
    if 'verified_student' in session:
        redirect_url = request.args.get('redirect', '/lyb')
        return redirect(redirect_url)
    return render_template('login.html')

@pages_bp.route('/')
def index():
    # ... 原有逻辑
    return render_template('index.html', ...)
```

---

_方案结束。按此方案执行可在 20-27 小时内完成重构，过程中保持服务 100% 可用。_
