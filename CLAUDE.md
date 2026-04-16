# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

吉大通信八班同学录网站 - Flask Web应用 + 微信小程序，用于班级通讯录管理、留言交流、相册视频分享。

**历史背景**: 初始版本使用CSV存储数据，现已完整迁移到SQLite，扩展了微信小程序、通知系统、点赞、语音喊话、新闻爬虫等功能。

包含：Web网页端 + 微信小程序端 + 自动化新闻爬虫 + 完整管理员功能。

## 快速启动

### 本地开发运行

```bash
cd /home/ubuntu/jlu8
pip install flask pillow apscheduler requests beautifulsoup4 pyjwt
python3 app.py
```

访问 http://localhost:5000

### 使用Gunicorn（生产）

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 完整依赖清单

```
flask>=3.0.0
pillow>=10.0.0
apscheduler>=3.10.0
requests>=2.20.0
beautifulsoup4>=4.14.0
pyjwt>=2.0.0
gunicorn>=20.0.0 (生产推荐)
```

## 架构

### 技术栈
- **后端**: Flask (Python 3.x) + APScheduler (定时任务)
- **前端**: HTML5 + CSS3 + Vanilla JavaScript（无框架，原生开发）
- **移动端**: 微信小程序原生开发 + Vant Weapp + ColorUI
- **数据存储**: SQLite 3 (`alumni.db`)
- **图片处理**: Pillow 生成缩略图
- **认证**: Session（网页）+ JWT Token（小程序）
- **任务调度**: APScheduler 定时新闻爬取

### 系统架构图

```
┌─────────────────────────────────────────────┐
│         浏览器 / 微信小程序                   │
└────────────────┬──────────────────────────────┘
                 │ HTTP/HTTPS requests
                 ▼
┌─────────────────────────────────────────────┐
│          nginx 反向代理                       │
│  ├─ muyusheng.com → 静态文件 + 网页         │
│  └─ jlu8.cn → /api/wx/ → Flask             │
└────────────────┬──────────────────────────────┘
                 ▼
┌─────────────────────────────────────────────┐
│          Flask 应用 (app.py)                 │
│  ├─ 网页路由 (首页/通讯录/留言板/相册/视频)  │
│  ├─ 网页API (验证/编辑/上传/删除)           │
│  ├─ 微信小程序API蓝图 (wx_api.py)           │
│  └─ APScheduler 定时任务 (新闻爬虫)         │
└────────────────┬──────────────────────────────┘
                 ▼
┌─────────────────────────────────────────────┐
│      database.py - 数据库封装层              │
│  封装所有数据库操作，提供线程安全连接         │
└────────────────┬──────────────────────────────┘
                 ▼
┌─────────────────────────────────────────────┐
│      SQLite 数据库 (alumni.db)              │
└────────────────┬──────────────────────────────┘
                 ▼
┌─────────────────────────────────────────────┐
│      静态文件存储                             │
│  ├─ 头像: static/imgs/avatars/             │
│  ├─ 照片: static/imgs/                      │
│  ├─ 缩略图: static/imgs/thumbs/            │
│  ├─ 新闻图片: static/imgs/news/             │
│  ├─ CSS/JS: static/css/js                    │
│  └─ 音乐文件: static/music/                 │
└─────────────────────────────────────────────┘
```

### 核心文件
| 文件 | 行数 | 作用 |
|------|------|------|
| `app.py` | ~2600 | Flask主应用，包含所有网页路由和业务逻辑 |
| `database.py` | ~1800 | SQLite数据库操作封装，提供所有CRUD函数 |
| `news_crawler.py` | ~500 | 吉林大学新闻爬虫，从多个来源抓取新闻 |
| `wx_api.py` | ~1200 | 微信小程序API蓝图（`/api/wx/*`）|
| `start.sh` | - | systemd启动脚本，清理旧进程再启动 |
| `templates/` | - | Jinja2 HTML模板文件 |
| `static/` | - | 静态资源（CSS、JS、上传图片、音乐等）|
| `miniprogram/` | - | 微信小程序源代码（16个页面）|

### 数据库结构
所有数据都通过 `database.py` 中的函数访问，**不要在其他模块直接写SQL查询**。主要表：

| 表名 | 作用 |
|------|------|
| `students` | 同学通讯录（学号、姓名、籍贯、城市、区县、电话、备注、头像、是否管理员）|
| `messages` | 留言板留言（昵称、内容、图片、时间、作者学号）|
| `comments` | 留言评论（所属留言ID、评论者、内容、时间）|
| `message_likes` | 留言点赞记录（留言ID、用户姓名）|
| `photos` | 相册照片元数据（文件名、标题、分类、上传者、时间、赞数）|
| `videos` | 视频链接信息（标题、链接、封面、上传者）|
| `activities` | 动态日志（记录所有用户操作，用于动态流）|
| `notifications` | 用户通知（喊话、点赞等提醒，记录接收者、是否已读）|
| `voice_shouts` | 语音喊话（发送者、接收者、语音URL、时间、是否删除）|
| `media_likes` | 媒体（照片/留言）点赞统一记录表 |
| `viewed_activities` | 用户已浏览活动记录（用于计算未读统计）|
| `login_logs` | 登录日志（IP地址、User-Agent、登录时间、登录用户）|
| `news` | 爬取的新闻（标题、链接、来源、时间、关键词匹配）|
| `config` | 配置表（键值对存储，新闻爬取时间、关键词等）|
| `deleted` | 已删除内容记录（类型、原ID、删除时间、删除者，用于恢复）|
| `wx_bindings` | 微信Openid与学号绑定关系 |

### 设计风格规范（来自 SPEC.md）

| 设计元素 | 规范 |
|----------|------|
| **主题** | 复古胶片 + 现代简约融合风格，温馨怀旧 |
| **主色调** | #2c3e50 (深蓝灰) + #e74c3c (暖红) + #f39c12 (金黄) |
| **背景** | 淡米色纹理背景，模拟老照片质感 |
| **字体** | "ZCOOL XiaoWei" (站酷小薇L) 用于标题，正文用 "Noto Sans SC" |
| **导航栏** | 固定顶部，毛玻璃效果 |
| **音乐播放器** | 右下角悬浮，可展开/收起控制面板 |
| **内容区** | 最大宽度1200px，居中显示 |

### 认证机制

**网页端**:
- 姓名+学号双重验证后设置 `session['verified_student']`
- 验证有效期30分钟，过期需重新验证
- `is_admin(name)` / `is_super_admin(name)` 函数检查管理员权限

**微信小程序端**:
- 微信登录：code → openid 交换
- JWT Token 认证，默认7天过期
- 需要绑定姓名+学号才能使用完整功能
- 数据与网页端完全同步

### 微信小程序API

- 挂载在 `/api/wx/` 蓝图下
- 主要端点：
  - `POST /api/wx/login` - 微信登录，获取JWT token
  - `GET /api/wx/get_student` - 获取当前绑定学生信息
  - `GET /api/wx/get_txl` - 获取通讯录列表
  - `GET /api/wx/get_messages` - 获取留言板列表
  - `POST /api/wx/add_message` - 添加新留言
  - `GET /api/wx/get_photos` - 获取相册照片
  - `POST /api/wx/add_photo` - 上传照片
  - `GET /api/wx/get_videos` - 获取视频列表
  - `GET /api/wx/get_activities` - 获取动态活动
  - `GET /api/wx/get_notifications` - 获取通知列表
  - `POST /api/wx/get_nearest` - 获取附近同学（按地理位置）
  - `POST /api/wx/voice_shout` - 发送语音喊话
- 配置：`WX_APPID` 和 `WX_SECRET` 硬编码在文件头部，`JWT_SECRET` 可通过环境变量覆盖

### 新闻爬虫模块

- 爬取来源：
  1. 吉大新闻网首页 (news.jlu.edu.cn) - 最稳定
  2. 南岭校区东区事务办公室 (dqswb.jlu.edu.cn) - 官方实时
  3. 汽车工程学院 (auto.jlu.edu.cn) - 学院新闻
- 入口函数：`news_crawler.fetch_jlu_news()` 返回爬取结果
- 定时执行：APScheduler 每天指定时间执行 `crawl_news_job()`
- 可配置：爬取时间、关键词（存储在 `config` 表，`news_keywords` 键）
- 存储：爬取新闻存入 `news` 表，图片下载到 `static/imgs/news/`（gitignore）
- **展示排序规则**（在 `app.py` 和 `news_crawler.py` 中）：
  - 管理员关键词匹配：标题匹配+10分，正文匹配+1分
  - 学生/活动/比赛相关内容：+5分（靠前）
  - 领导相关内容：-8分（靠后）
  - 按总分数降序排列

### 核心功能模块

| 模块 | 功能特点 |
|------|----------|
| **通讯录** | 网格卡片展示，支持搜索/筛选（姓名、籍贯），点击展开详情，地理位置在地图上标注，支持个人信息编辑和头像上传 |
| **留言板** | 时间轴式展示，支持昵称+内容+图片，内置表情选择器，支持点赞和评论，软删除可恢复 |
| **相册** | Masonry瀑布流布局，灯箱放大效果，分类筛选（年份/活动），自动生成缩略图，点赞系统 |
| **视频** | 支持优酷、腾讯、B站等第三方链接嵌入，网格卡片展示，点击弹出模态框播放 |
| **动态通知** | 记录所有用户活动（修改信息、留言、上传等），支持未读统计，对喊话、点赞生成通知推送给相关用户 |
| **语音喊话** | 用户可以给特定同学发送语音留言，仅双方可见，支持删除/恢复 |
| **附近同学** | 小程序功能，基于当前地理位置查找附近的同学 |
| **背景音乐** | 右下角悬浮播放器，内置5首怀旧歌曲，支持播放控制，记忆上次播放状态 |
| **已删除恢复** | 所有删除都是软删除，记录到 `deleted` 表，管理员可在管理界面恢复 |

### 管理功能

- 管理员权限设置：修改任意同学的管理员状态
- 新闻爬取配置：在线设置爬取时间和关键词
- 登录日志查看：显示所有登录记录，包含IP归属地
- 已删除内容浏览和恢复

## 服务管理（重要）

**应用通过 systemd 服务管理，禁止手动启动多个Flask进程，否则会导致端口冲突和异常行为。**

```bash
# 查看服务状态
systemctl status jlu8

# 启动应用
sudo systemctl start jlu8

# 停止应用
sudo systemctl stop jlu8

# 重启应用（修改代码后需要执行）
sudo systemctl restart jlu8

# 查看实时日志
sudo journalctl -u jlu8 -f
```

**启动脚本位置**: `/home/ubuntu/jlu8/start.sh`
**Systemd服务文件**: `/etc/systemd/system/jlu8.service`

**注意**: 如果手动运行了 `python3 app.py`，需要先 `pkill -f "python.*app.py"` 再用 systemd 启动，避免端口冲突。

## 常用命令

```bash
# 检查运行状态（优先使用systemd）
systemctl status jlu8

# 查看应用日志（Flask输出到/tmp/jlu8.log）
tail -f /tmp/jlu8.log

# 直接检查进程
ps aux | grep "python.*app.py" | grep -v grep

# 清理僵尸进程
pkill -f "python.*app.py"

# 数据库交互式调试
python3 -c "from app import app; from database import get_db; conn = get_db(); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM students'); print(cursor.fetchone()); conn.close()"

# 重启nginx（修改配置后）
sudo nginx -t && sudo nginx -s reload
```

### 微信小程序开发

```bash
cd /home/ubuntu/jlu8/miniprogram
npm install
# 使用微信开发者工具打开本目录进行开发
# 命令行上传需要配置miniprogram-ci
```

**依赖**:
- `vant-weapp` - UI组件库
- `ColorUI` - 样式库
- `miniprogram-ci` - 命令行上传工具

## 模板和静态资源

### 前端全局状态
- 模板中可用 `is_admin_user` 变量判断当前用户是否是管理员
- `session['verified_student']['name']` 获取当前登录用户名
- `window.currentUser` 在JS中可用，结构：`{name, student_id, is_admin, is_super_admin}`

### 主要模板文件
| 文件 | 说明 |
|------|------|
| `templates/index.html` | 首页 |
| `templates/txl.html` | 通讯录页面 |
| `templates/lyb.html` | 留言板页面 |
| `templates/gallery.html` | 相册页面 |
| `templates/video.html` | 视频页面 |
| `templates/about.html` | 个人中心/关于页面 **包含大量内联JavaScript，修改后需重启Flask** |
| `templates/media.html` | 媒体整合页面 |

### static目录结构
```
static/
├── css/style.css          - 全站样式表 (65KB)
├── js/
│   ├── main.js            - 主要前端逻辑 (71KB)
│   └── province_data.js   - 中国省份城市坐标数据（用于地图标注）
├── imgs/
│   ├── avatars/           - 同学头像
│   ├── messages/          - 留言附带图片
│   ├── thumbs/            - 缩略图（自动生成）
│   └── news/              - 爬虫抓取的新闻图片（gitignore）
└── music/                 - 背景音乐音频文件（不在git中）
```

## nginx配置说明

| 配置文件 | 作用 | 域名 |
|----------|------|------|
| `/etc/nginx/sites-available/muyusheng.com` | 网页主站 + HTTPS API | www.muyusheng.com |
| `/etc/nginx/sites-available/flask` | Flask API代理 | jlu8.cn |

- **muyusheng.com**: 提供网页访问，同时为微信小程序提供HTTPS API（小程序要求必须HTTPS）
- **flask**: 直接代理到 127.0.0.1:5000

**修改配置后必须执行**:
```bash
sudo nginx -t && sudo nginx -s reload
```

## 文件上传限制

| 类型 | 大小限制 |
|------|----------|
| 头像 | 500KB |
| 照片 | 无限制 |
| 视频 | 100MB |
| 语音 | 无限制（小程序端限制） |

## 开发注意事项

### 开发前检查清单

1. 确认没有僵尸进程：`ps aux | grep "python.*app.py" | grep -v grep`
2. 如果有，先清理：`pkill -f "python.*app.py"`
3. 修改代码后需要重启systemd：`sudo systemctl restart jlu8`
4. 检查日志确认启动成功：`journalctl -u jlu8 -f`
5. 关于页面 `about.html` 有大量内联JS，修改后**必须重启**才能生效

### 代码开发规范

1. **所有数据库操作必须通过 `database.py` 中的函数**，不要在 `app.py` 或 `wx_api.py` 中直接写SQL
2. 遵循现有的错误处理模式：返回JSON `{"code": 0, "message": "...", "data": ...}`
3. 前端使用原生JavaScript，不要引入框架除非必要
4. 添加新功能后保持整体怀旧温馨的设计风格，与现有设计协调

### 调试技巧

1. **查看Flask日志**: `tail -f /tmp/jlu8.log`
2. **查看systemd日志**: `sudo journalctl -u jlu8 -f`
3. **数据库查询调试**: 使用 `python3 -c "..."` 交互式测试
4. **前端调试**: 浏览器开发者工具 → Console查看JS错误
5. **小程序调试**: 使用微信开发者工具调试，查看Network请求

### 常见问题排查

| 问题 | 原因 | 解决方法 |
|------|------|----------|
| 502 Bad Gateway | Flask进程未启动 | `sudo systemctl start jlu8`，检查日志 |
| 端口占用 | 有多个Flask进程在运行 | `pkill -f "python.*app.py"` 然后重启服务 |
| 修改代码不生效 | about.html有内联JS，没重启 | `sudo systemctl restart jlu8` |
| 图片不显示 | 权限问题或路径错误 | 检查 `static/imgs/` 目录权限：`chmod 755` |
| 新闻不更新 | 定时任务未触发 | 检查APScheduler日志，手动测试 `fetch_jlu_news()` |

### Git使用注意事项

- `.gitignore` 排除了 `static/imgs/` 下的用户上传内容（头像、照片、新闻图片）
- `.gitignore` 排除了 `static/music/` 音频文件
- 但数据库文件 `alumni.db` **被跟踪**，提交会保存当前数据库状态
- 微信小程序编译生成的 `miniprogram/node_modules/` 被排除
- 每次提交前确认没有包含敏感信息（API密钥等）

## 安全注意事项

- `SECRET_KEY` 在 `app.py` 中硬编码：`jlu_tongxin_8_class_2024_secret_key`，生产环境应改为环境变量
- 微信 `APPID` 和 `SECRET` 在 `wx_api.py` 中硬编码，生产环境建议通过环境变量注入
- `JWT_SECRET` 默认值在代码中，可通过环境变量 `JWT_SECRET` 覆盖
- IP归属地查询使用 http://ip-api.com 免费API，缓存1小时，避免频繁请求
- 所有上传文件会检查扩展名，禁止可执行文件上传

## 重要文件

- `templates/about.html` - "个人中心"页面，包含大量内联JavaScript，修改后需重启Flask
- `static/js/main.js` - 主要前端逻辑
- `wx_api.py` - 微信小程序API，APPID和SECRET直接写入代码中
- `database.py` - 所有数据库操作都在这里，添加新表先在这里加函数
- `app.py` - Flask主应用，路由和业务逻辑
- `news_crawler.py` - 新闻爬虫
- `SPEC.md` - 原始完整设计规格说明书，包含视觉设计规范
- `alumni.db` - SQLite数据库文件，跟踪在git中
- `/etc/systemd/system/jlu8.service` - systemd服务配置文件
- `/home/ubuntu/jlu8/start.sh` - 启动脚本

## 配置和路径硬编码

| 配置项 | 值 | 位置 |
|--------|-----|------|
| 数据库路径 | `/home/ubuntu/jlu8/alumni.db` | `database.py` |
| SECRET_KEY | `jlu_tongxin_8_class_2024_secret_key` | `app.py` |
| 微信APPID | `wx747fe17f7c7b65e8` | `wx_api.py` |
| 默认JWT_SECRET | `jlu8_wx_secret_key_2024` | `wx_api.py` |
| 会话有效期 | 30分钟 | `app.py` |
| JWT有效期 | 7天 | `wx_api.py` |
| 图片存储根目录 | `static/imgs/` | 多处 |
| 日志文件 | `/tmp/jlu8.log` | `start.sh` |

## 标准开发工作流

修改功能或添加新功能的完整步骤：

```bash
# 1. 拉取最新代码
git pull origin master

# 2. 检查当前是否有运行中的Flask进程
ps aux | grep "python.*app.py" | grep -v grep

# 3. 如果有，清理僵尸进程
pkill -f "python.*app.py"

# 4. 修改代码...（编辑相应文件）

# 5. 本地测试（可选）
python3 app.py
# 访问 http://localhost:5000 测试功能

# 6. 测试完成后，用systemd重启
sudo systemctl restart jlu8

# 7. 检查启动状态
systemctl status jlu8

# 8. 查看日志确认无错误
journalctl -u jlu8 -n 50

# 9. 提交代码
git add <修改的文件>
git commit -m "feat/fix: 描述你的修改"

# 10. 如果需要推送到远程
git push origin master
```

**重要提醒**: 修改 `templates/about.html` 后**必须重启服务**，因为它包含大量内联JavaScript，Flask不会自动重载模板缓存。

## systemd启动流程详解

`start.sh` 启动脚本的执行流程：

1. 切换到工作目录 `/home/ubuntu/jlu8`
2. **强制清理所有旧的Flask进程** - `pkill -f "python.*app.py"`
3. 等待1秒让进程完全退出
4. 使用 `exec` 启动Flask，替换当前shell进程，让systemd能够直接管理
5. 所有输出重定向到 `/tmp/jlu8.log`

systemd配置：
- 自动重启：进程退出后会在5秒后自动重启
- 用户：root（需要绑定端口和读写文件）
- 随系统启动：开机自动启动

## 数据库变更工作流

如果需要添加新表或修改现有表结构：

### 添加新表步骤

1. **在 `database.py` 中**:
   - 添加创建表的SQL语句到 `init_db()` 函数
   - 添加对应的CRUD操作函数（`get_xxx()`, `add_xxx()`, `update_xxx()`, `delete_xxx()`）

2. **在代码中使用**:
   - 只通过 `database.py` 中的函数访问数据库
   - 在 `app.py` 或 `wx_api.py` 中导入并使用这些函数

3. **执行建表**（SQLite会自动创建）:
   ```python
   python3 -c "from database import init_db; init_db()"
   ```

4. **测试功能**后重启服务

### 修改现有表步骤

1. 在 `database.py` 中修改创建表SQL
2. 如果已有数据，需要写ALTER语句迁移数据
3. 备份数据库：`cp alumni.db alumni.db.backup`
4. 执行迁移
5. 验证数据完整性后重启服务

## API响应格式规范

所有API（网页API和小程序API）都遵循统一的响应格式：

**成功响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

**错误响应**:
```json
{
  "code": 1,
  "message": "错误信息描述",
  "data": null
}
```

**需要登录/认证错误**:
```json
{
  "code": 401,
  "message": "需要先登录",
  "data": null
}
```

**权限不足错误**:
```json
{
  "code": 403,
  "message": "没有权限执行此操作",
  "data": null
}
```

遵循这个格式保持一致性，前端代码可以统一处理。

## 添加新API端点步骤

### 网页端API（在 `app.py` 中）

1. 添加路由装饰器 `@app.route('/api/your_endpoint', methods=['POST'])`
2. 验证会话登录状态：`if 'verified_student' not in session: return jsonify(...)`
3. 验证权限（如果需要）：`if not is_admin(...): return jsonify(...)`
4. 获取POST参数：`request.json.get('xxx')`
5. 调用 `database.py` 中的函数执行业务逻辑
6. 返回统一格式的JSON响应
7. 重启服务测试

### 小程序API（在 `wx_api.py` 中）

1. 添加路由装饰器 `@wx_api.route('/your_endpoint', methods=['POST'])`
2. 添加JWT认证装饰器 `@token_required`
3. 从`g.student_id`获取当前用户学号
4. 获取POST参数：`request.json.get('xxx')`
5. 调用 `database.py` 中的函数执行业务逻辑
6. 返回统一格式的JSON响应
7. 重启服务测试

## 微信小程序页面结构

`miniprogram/` 目录包含完整的微信小程序源代码：

**主要页面**:
- `pages/index/index` - 首页
- `pages/txl/txl` - 通讯录列表
- `pages/txl-detail/txl-detail` - 通讯录详情
- `pages/lyb/lyb` - 留言板
- `pages/media/media` - 媒体（相册+视频）
- `pages/gallery/gallery` - 相册
- `pages/video/video` - 视频
- `pages/mine/mine` - 个人中心
- `pages/bind/bind` - 绑定姓名学号
- `pages/recovery/recovery` - 已删除恢复
- `pages/notifications/notifications` - 通知列表
- `pages/activity/activity` - 动态活动
- `pages/admin/admin` - 管理首页
- `pages/admin-loginlogs/admin-loginlogs` - 登录日志
- `pages/admin-permission/admin-permission` - 权限管理
- `pages/admin-news/admin-news` - 新闻爬取设置

所有页面数据都调用 `wx_api.py` 中的API，与网页端共享同一数据库，数据完全同步。

## 最近功能更新历史

| 提交 | 功能 |
|------|------|
| f2df31d | 按内容类型排序新闻：学生/活动优先，领导靠后 |
| a89cc46 | 按关键词匹配度排序展示新闻 |
| 4d27d82 | 修复新闻published_time字段缺失问题 |
| 79e7575 | 增加新闻获取数量(5→50)，修复中文日期解析 |
| b436a10 | 新增南岭校区新闻源(dqswb.jlu.edu.cn) |
| 138fec2 | 修复新闻详情页内容提取，下载配图 |
| 4e57d7e | 附近同学API返回avatar头像字段 |

项目在持续迭代中，最近重点是完善新闻爬虫和展示排序功能。

## 后端交互流程图

```
用户请求
    ↓
nginx接收请求
    ↓
判断域名 → muyusheng.com → 静态文件 → 返回
             ↓
          jlu8.cn → 转发给Flask (127.0.0.1:5000)
             ↓
Flask路由分发
    ↓
┌───────────────┐
│   网页路由     │ → 渲染Jinja2模板 → 返回HTML
│   API路由     │ → 执行业务逻辑 → 返回JSON
│ 小程序API蓝图 │ → JWT认证 → 执行业务 → 返回JSON
└───────────────┘
    ↓
所有数据库操作 → database.py封装
    ↓
SQLite存储数据
    ↓
返回响应给用户
```
