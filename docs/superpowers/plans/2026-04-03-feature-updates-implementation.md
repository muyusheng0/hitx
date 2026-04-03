# 同学录网站功能改进实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 对同学录网站实施5项功能改进

**Architecture:**
- 采用模块化修改，优先改动小、风险低的文件
- 系统消息功能需要新增数据库表和API
- 遵循现有代码风格和模式

**Tech Stack:** Python/Flask, JavaScript, SQLite, HTML/CSS

---

## 实施顺序

1. 首页改版
2. 评论区默认展开
3. 留言板照片点击放大
4. 页面底部提示 + 返回顶部按钮
5. 系统消息通知功能（最复杂）

---

## 任务 1: 首页改版

**Files:**
- Modify: `templates/index.html:1-160`
- Modify: `static/css/style.css` (样式加强)

**Changes:**
- 移除顶部欢迎横幅（class: hero-banner）
- 移除统计模块（class: stats-section）
- 加强最新动态模块样式（class: latest-activities）
- 最新动态模块添加更醒目的边框和阴影

---

## 任务 2: 评论区默认展开

**Files:**
- Modify: `templates/lyb.html:100-130`
- Modify: `static/js/main.js:270-290`

**Changes:**
- 修改 lyb.html 中评论区的默认 display 状态
- 在 main.js 的 submitMessage 函数中，新留言的评论区默认展开

---

## 任务 3: 留言板照片点击放大

**Files:**
- Modify: `templates/lyb.html:95-105`
- Modify: `static/js/main.js:360-400`

**Changes:**
- 修改 lyb.html 中留言图片，添加 onclick 事件触发 showLightbox
- 确保 showLightbox 函数已存在于 main.js（应该已存在）

---

## 任务 4: 页面底部提示 + 返回顶部按钮

**Files:**
- Create: `static/css/back-to-top.css` (返回顶部按钮样式)
- Modify: `static/js/main.js` (添加滚动检测和返回顶部逻辑)
- Modify: `templates/index.html` (添加按钮HTML)
- Modify: `templates/txl.html` (添加按钮HTML)
- Modify: `templates/lyb.html` (添加按钮HTML)
- Modify: `templates/media.html` (添加按钮HTML)

**Changes:**
- 添加 back-to-top 样式（固定右下角，圆形按钮）
- 添加 scrollToTop() 函数到 main.js
- 添加滚动检测，超过300px显示按钮
- 在四个页面添加按钮HTML和初始化代码

---

## 任务 5: 系统消息通知功能（新增）

**Files:**
- Modify: `database.py` (新增 notifications 表和CRUD函数)
- Modify: `app.py` (新增通知API，修改点赞/评论/喊话接口创建通知)
- Modify: `templates/about.html` (添加通知图标和下拉列表)
- Modify: `static/css/style.css` (通知下拉列表样式)
- Modify: `static/js/main.js` (添加获取通知、显示下拉列表逻辑)

### 5.1 数据库层

**Files:**
- Modify: `database.py`

**Changes:**
在 database.py 中添加:
```python
def init_notifications_table():
    """初始化 notifications 表"""

def create_notification(recipient, sender, notif_type, ref_id, content):
    """创建通知"""

def get_notifications(recipient, limit=20):
    """获取用户通知列表"""

def get_unread_notification_count(recipient):
    """获取未读通知数量"""

def mark_notification_read(notification_id, recipient):
    """标记通知为已读"""

def mark_all_notifications_read(recipient):
    """标记所有通知为已读"""
```

### 5.2 API层

**Files:**
- Modify: `app.py`

**New Routes:**
- `GET /api/notifications` - 获取通知列表
- `GET /api/notifications/count` - 获取未读数量
- `POST /api/notifications/mark_read` - 标记已读

**Modified Routes (添加创建通知逻辑):**
- `/api/add_comment` - 评论时创建通知
- `/api/like_message` - 点赞留言时创建通知
- `/api/upload_image` - 上传照片时创建通知
- `/api/add_video` - 添加视频时创建通知
- `/api/shout` - 喊话时创建通知

### 5.3 前端UI

**Files:**
- Modify: `templates/about.html` (在用户状态区域添加通知图标)
- Modify: `static/css/style.css` (通知下拉列表样式)
- Modify: `static/js/main.js` (通知相关JS逻辑)

**通知图标HTML:**
```html
<div class="notification-bell" onclick="toggleNotificationDropdown()">
    <span class="bell-icon">🔔</span>
    <span class="notification-badge" id="notificationBadge">0</span>
</div>
<div class="notification-dropdown" id="notificationDropdown">
    <!-- 通知列表 -->
</div>
```

---

## 实施检查清单

- [ ] 任务1: 首页改版完成，最新动态模块醒目显示
- [ ] 任务2: 评论区默认展开
- [ ] 任务3: 留言板照片可点击放大
- [ ] 任务4: 返回顶部按钮功能正常
- [ ] 任务5: 系统消息通知功能完整可用
  - [ ] 数据库表创建成功
  - [ ] 通知API正常返回数据
  - [ ] 点赞/评论/喊话正确创建通知
  - [ ] 右上角通知图标显示
  - [ ] 下拉列表正常显示通知
  - [ ] 点击通知可跳转到对应内容
