# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

吉大通信八班同学录网站 - Flask Web应用，用于班级通讯录管理、留言板、相册视频展示。

## 快速启动

```bash
cd /home/ubuntu/jlu8
pip install flask pillow apscheduler requests
python3 app.py
```

访问 http://localhost:5000

## 架构

### 技术栈
- **后端**: Flask (Python) + APScheduler (定时任务)
- **前端**: HTML5 + CSS3 + Vanilla JavaScript
- **数据存储**: SQLite (`alumni.db`) + CSV备份
- **文件上传**: 本地存储于 `static/imgs/`

### 核心文件
- `app.py` - Flask主应用，包含所有路由和业务逻辑
- `database.py` - SQLite数据库操作封装，提供`get_db()`获取连接
- `news_crawler.py` - 新闻爬虫模块
- `wx_api.py` - 微信小程序API蓝图
- `templates/` - Jinja2 HTML模板
- `static/` - CSS、JS、图片、音视频资源

### 数据库结构
所有数据通过`database.py`中的函数访问，主要表：
- `students` - 同学通讯录
- `messages` - 留言板
- `photos` - 相册照片元数据
- `videos` - 视频
- `activities` - 动态日志
- `notifications` - 通知
- `login_logs` - 登录日志
- `deleted_items` - 已删除内容恢复

### 认证机制
- 姓名+学号验证后设置`session['verified_student']`
- `is_admin(name)` / `is_super_admin(name)` 检查管理员权限
- 验证有效期30分钟

### 新闻爬虫
- `news_crawler.fetch_jlu_news()` - 爬取吉林大学新闻
- APScheduler定时任务，每天指定时间执行`crawl_news_job()`
- 爬取配置存储在数据库`config`表

### 管理功能
- 管理员设置: 修改同学的管理员权限
- 新闻爬取设置: 设置爬取时间和关键词
- 登录日志: 记录用户IP并获取归属地
- 已删除内容恢复

## 常用命令

```bash
# 重启应用
pkill -f "python.*app.py" && nohup python3 app.py > /tmp/jlu8.log 2>&1 &

# 查看应用日志
tail -f /tmp/jlu8.log

# 检查运行状态
ps aux | grep "python.*app.py" | grep -v grep

# 数据库操作
python3 -c "from app import app; from database import get_db; ..."
```

## 模板和静态资源

- 模板中可用`is_admin_user`变量判断当前用户是否是管理员
- `session['verified_student']['name']` 获取当前登录用户名
- `window.currentUser` 在JS中可用，包含`is_admin`和`is_super_admin`属性

## 注意事项

- 数据库文件: `/home/ubuntu/jlu8/alumni.db` (硬编码路径)
- 文件上传限制: 头像500KB，照片无限制，视频100MB
- nginx配置在`/etc/nginx/sites-available/flask`
- 新闻爬虫已移至`static/imgs/news/`目录（gitignore）
