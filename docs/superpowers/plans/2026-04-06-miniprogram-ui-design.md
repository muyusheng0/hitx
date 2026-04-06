# 微信小程序 UI 美化实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将微信小程序UI风格与网站保持一致，使用统一配色和卡片式设计

**Architecture:** 修改全局样式文件和各页面WXSS/WXML文件，采用淡米色背景、白色卡片、暖红渐变按钮的设计规范

**Tech Stack:** 微信小程序原生框架、WXSS、WXML

---

## 文件概览

需要修改的文件：
- `miniprogram/app.wxss` - 全局样式
- `miniprogram/app.json` - 窗口配置（确认配色）
- `miniprogram/pages/index/index.wxss` - 首页样式
- `miniprogram/pages/index/index.wxml` - 首页结构
- `miniprogram/pages/txl/txl.wxss` - 通讯录样式
- `miniprogram/pages/txl-detail/txl-detail.wxss` - 同学详情样式
- `miniprogram/pages/lyb/lyb.wxss` - 留言板样式
- `miniprogram/pages/gallery/gallery.wxss` - 相册样式
- `miniprogram/pages/video/video.wxss` - 视频样式
- `miniprogram/pages/profile/profile.wxss` - 个人中心样式
- `miniprogram/pages/bind/bind.wxss` - 绑定页样式

---

## 任务 1: 更新全局样式 (app.wxss)

**文件:** 修改 `miniprogram/app.wxss`

- [ ] **Step 1: 更新全局样式**

```wxss
/* 全局样式 */
page {
  background-color: #faf8f5;
  font-size: 28rpx;
  color: #333;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
}

.container {
  padding: 30rpx;
}

/* 全局卡片样式 */
.card {
  background: #fff;
  border-radius: 12rpx;
  box-shadow: 0 4rpx 20rpx rgba(0,0,0,0.08);
  padding: 24rpx;
  margin-bottom: 20rpx;
}

/* 全局渐变按钮 */
.btn-primary {
  background: linear-gradient(135deg, #e74c3c, #f39c12);
  color: #fff;
  border: none;
  border-radius: 8rpx;
  padding: 24rpx 32rpx;
  font-size: 28rpx;
  text-align: center;
}

.btn-primary::after {
  border: none;
}

/* 输入框统一样式 */
.input-field {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8rpx;
  padding: 20rpx 24rpx;
  font-size: 28rpx;
}

.input-field:focus {
  border-color: #e74c3c;
  outline: none;
}

/* 头像统一样式 */
.avatar {
  border-radius: 50%;
}

.avatar-sm {
  width: 80rpx;
  height: 80rpx;
}

.avatar-md {
  width: 120rpx;
  height: 120rpx;
}

.avatar-lg {
  width: 150rpx;
  height: 150rpx;
}
```

---

## 任务 2: 确认窗口配置 (app.json)

**文件:** 检查 `miniprogram/app.json`

当前配置：
```json
{
  "window": {
    "navigationBarBackgroundColor": "#2c3e50",
    "navigationBarTextStyle": "white"
  },
  "tabBar": {
    "color": "#666",
    "selectedColor": "#e74c3c",
    "backgroundColor": "#fff"
  }
}
```

配色已符合设计规范，无需修改。

---

## 任务 3: 首页美化 (index)

**文件:** 修改 `miniprogram/pages/index/index.wxss` 和 `miniprogram/pages/index/index.wxml`

- [ ] **Step 1: 更新首页样式**

```wxss
.container {
  padding: 30rpx;
  background: #faf8f5;
  min-height: 100vh;
}

.header {
  background: linear-gradient(135deg, #2c3e50, #34495e);
  padding: 60rpx 30rpx;
  border-radius: 0 0 40rpx 40rpx;
  text-align: center;
  margin: -30rpx -30rpx 30rpx -30rpx;
}

.title {
  font-size: 48rpx;
  color: #fff;
  font-weight: bold;
  letter-spacing: 4rpx;
}

.subtitle {
  font-size: 28rpx;
  color: rgba(255,255,255,0.8);
  margin-top: 10rpx;
}

.stats-card {
  background: #fff;
  border-radius: 12rpx;
  box-shadow: 0 4rpx 20rpx rgba(0,0,0,0.08);
  padding: 40rpx;
  margin-top: 30rpx;
  display: flex;
  justify-content: center;
  align-items: center;
}

.stat-item {
  text-align: center;
}

.stat-icon {
  font-size: 60rpx;
  margin-bottom: 10rpx;
}

.stat-num {
  display: block;
  font-size: 56rpx;
  color: #e74c3c;
  font-weight: bold;
}

.stat-label {
  font-size: 24rpx;
  color: #666;
  margin-top: 8rpx;
}

.section {
  margin-top: 30rpx;
}

.section-title {
  font-size: 32rpx;
  color: #2c3e50;
  font-weight: bold;
  margin-bottom: 20rpx;
  padding-left: 20rpx;
  border-left: 4rpx solid #e74c3c;
}

.message-list {
  margin-top: 20rpx;
}

.message-card {
  background: #fff;
  border-radius: 12rpx;
  box-shadow: 0 4rpx 20rpx rgba(0,0,0,0.08);
  padding: 30rpx;
  margin-bottom: 20rpx;
}

.message-nickname {
  display: block;
  font-size: 28rpx;
  color: #e74c3c;
  font-weight: bold;
}

.message-content {
  display: block;
  font-size: 28rpx;
  color: #333;
  margin-top: 12rpx;
  line-height: 1.6;
}
```

- [ ] **Step 2: 更新首页结构**

```wxml
<view class="container">
  <view class="header">
    <text class="title">吉大自动化八班</text>
    <text class="subtitle">同学录 · 时光不老我们不散</text>
  </view>

  <view class="stats-card">
    <view class="stat-item">
      <text class="stat-icon">👥</text>
      <text class="stat-num">{{studentCount}}</text>
      <text class="stat-label">位同学</text>
    </view>
  </view>

  <view class="section">
    <text class="section-title">最新留言</text>
    <view class="message-list">
      <view class="message-card" wx:for="{{recentMessages}}" wx:key="id">
        <text class="message-nickname">{{item.nickname}}</text>
        <text class="message-content">{{item.content}}</text>
      </view>
    </view>
  </view>
</view>
```

---

## 任务 4: 通讯录美化 (txl)

**文件:** 修改 `miniprogram/pages/txl/txl.wxss`

- [ ] **Step 1: 更新通讯录样式**

```wxss
.container {
  padding: 30rpx;
  background: #faf8f5;
  min-height: 100vh;
}

.search-card {
  background: #fff;
  border-radius: 12rpx;
  box-shadow: 0 4rpx 20rpx rgba(0,0,0,0.08);
  padding: 20rpx;
  margin-bottom: 30rpx;
}

.search {
  background: #faf8f5;
  border: 1px solid #e0e0e0;
  border-radius: 8rpx;
  padding: 20rpx 24rpx;
  font-size: 28rpx;
}

.list {
  padding: 0;
}

.student-card {
  background: #fff;
  border-radius: 12rpx;
  box-shadow: 0 4rpx 20rpx rgba(0,0,0,0.08);
  padding: 30rpx;
  margin-bottom: 20rpx;
  display: flex;
  align-items: center;
}

.avatar {
  width: 100rpx;
  height: 100rpx;
  border-radius: 50%;
  margin-right: 30rpx;
  background: linear-gradient(135deg, #2c3e50, #34495e);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 36rpx;
  font-weight: bold;
}

.info {
  flex: 1;
}

.name {
  display: block;
  font-size: 32rpx;
  color: #2c3e50;
  font-weight: bold;
}

.location {
  display: block;
  font-size: 26rpx;
  color: #666;
  margin-top: 10rpx;
}

.arrow {
  color: #ccc;
  font-size: 32rpx;
}
```

---

## 任务 5: 同学详情美化 (txl-detail)

**文件:** 修改 `miniprogram/pages/txl-detail/txl-detail.wxss` 和 WXML

- [ ] **Step 1: 查看现有文件**

```bash
cat miniprogram/pages/txl-detail/txl-detail.wxss
cat miniprogram/pages/txl-detail/txl-detail.wxml
```

- [ ] **Step 2: 更新样式（待确认现有结构）**

根据设计规范，同学详情应包含：
- 大尺寸头像居中显示
- 信息以卡片形式展示
- 底部按钮使用渐变背景

---

## 任务 6: 留言板美化 (lyb)

**文件:** 修改 `miniprogram/pages/lyb/lyb.wxss`

- [ ] **Step 1: 更新留言板样式**

```wxss
.container {
  padding: 30rpx;
  background: #faf8f5;
  min-height: 100vh;
}

.input-card {
  background: #fff;
  border-radius: 12rpx;
  box-shadow: 0 4rpx 20rpx rgba(0,0,0,0.08);
  padding: 30rpx;
  margin-bottom: 30rpx;
}

.textarea {
  width: 100%;
  height: 160rpx;
  border: 1px solid #e0e0e0;
  border-radius: 8rpx;
  padding: 20rpx;
  box-sizing: border-box;
  font-size: 28rpx;
  background: #faf8f5;
}

.textarea:focus {
  border-color: #e74c3c;
  outline: none;
}

.submit-btn {
  background: linear-gradient(135deg, #e74c3c, #f39c12);
  color: #fff;
  border: none;
  border-radius: 8rpx;
  padding: 24rpx;
  font-size: 28rpx;
  margin-top: 20rpx;
  width: 100%;
}

.submit-btn::after {
  border: none;
}

.messages {
  padding: 0;
}

.message-card {
  background: #fff;
  border-radius: 12rpx;
  box-shadow: 0 4rpx 20rpx rgba(0,0,0,0.08);
  padding: 30rpx;
  margin-bottom: 20rpx;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15rpx;
}

.nickname {
  font-size: 28rpx;
  color: #e74c3c;
  font-weight: bold;
}

.time {
  font-size: 22rpx;
  color: #999;
}

.content {
  font-size: 28rpx;
  color: #333;
  line-height: 1.6;
}
```

---

## 任务 7: 相册美化 (gallery)

**文件:** 修改 `miniprogram/pages/gallery/gallery.wxss`

- [ ] **Step 1: 查看现有文件**

```bash
cat miniprogram/pages/gallery/gallery.wxss
```

- [ ] **Step 2: 更新样式（待确认结构）**

根据设计规范，相册应使用：
- 2列瀑布流布局
- 图片圆角 8px
- 点击效果阴影加深

---

## 任务 8: 视频页面美化 (video)

**文件:** 修改 `miniprogram/pages/video/video.wxss`

- [ ] **Step 1: 查看现有文件**

```bash
cat miniprogram/pages/video/video.wxss
```

- [ ] **Step 2: 更新样式（待确认结构）**

根据设计规范，视频卡片应使用白色背景 + 封面图 + 标题

---

## 任务 9: 个人中心美化 (profile)

**文件:** 修改 `miniprogram/pages/profile/profile.wxss`

- [ ] **Step 1: 查看现有文件**

```bash
cat miniprogram/pages/profile/profile.wxss
```

- [ ] **Step 2: 更新样式（待确认结构）**

根据设计规范：
- 头像 + 姓名居中卡片顶部（渐变背景）
- 信息列表卡片式
- 退出按钮渐变背景

---

## 任务 10: 绑定页美化 (bind)

**文件:** 修改 `miniprogram/pages/bind/bind.wxss`

- [ ] **Step 1: 更新绑定页样式**

```wxss
.container {
  padding: 100rpx 50rpx;
  background: #faf8f5;
  min-height: 100vh;
}

.header {
  text-align: center;
  margin-bottom: 80rpx;
}

.title {
  display: block;
  font-size: 44rpx;
  color: #2c3e50;
  font-weight: bold;
}

.subtitle {
  display: block;
  font-size: 26rpx;
  color: #666;
  margin-top: 16rpx;
}

.form-card {
  background: #fff;
  border-radius: 16rpx;
  box-shadow: 0 4rpx 20rpx rgba(0,0,0,0.08);
  padding: 50rpx 30rpx;
}

.input {
  background: #faf8f5;
  border: 1px solid #e0e0e0;
  border-radius: 8rpx;
  padding: 24rpx;
  margin-bottom: 30rpx;
  font-size: 28rpx;
}

.input:focus {
  border-color: #e74c3c;
  outline: none;
}

.btn {
  background: linear-gradient(135deg, #e74c3c, #f39c12);
  color: #fff;
  border-radius: 8rpx;
  padding: 26rpx;
  font-size: 28rpx;
  margin-top: 20rpx;
  border: none;
}

.btn::after {
  border: none;
}
```

---

## 任务 11: 提交代码

- [ ] **Step 1: 提交所有修改**

```bash
cd miniprogram
git add .
git commit -m "feat: 微信小程序UI美化，与网站风格统一

- 全局样式更新：淡米色背景、卡片阴影、渐变按钮
- 首页：渐变头部、统计卡片、留言卡片
- 通讯录：搜索框样式、列表卡片
- 留言板：输入卡片、提交按钮样式
- 绑定页：统一样式卡片

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
git push origin main
```

---

## 自检清单

- [ ] 全局背景色是否为 #faf8f5 (淡米色)
- [ ] 卡片是否使用 border-radius: 12rpx
- [ ] 卡片是否有 box-shadow 阴影
- [ ] 按钮是否使用渐变 background: linear-gradient(135deg, #e74c3c, #f39c12)
- [ ] 头像是否为圆形
- [ ] 输入框聚焦时边框颜色是否为 #e74c3c

---

## 执行选项

**1. Subagent-Driven (recommended)** - 每个任务分配给独立子agent执行
**2. Inline Execution** - 在当前会话中执行任务，带检查点

**选择哪个方式？**
