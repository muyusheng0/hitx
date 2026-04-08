# 小程序功能对齐网页端 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让微信小程序的功能完全对齐网页端，补全所有缺失的功能，包括所有小功能、跳转、提示，确保功能使用一致。

**Architecture:**
- 后端：在现有 `wx_api.py` 中添加缺失的API端点（新闻爬取设置相关），遵循现有的API响应格式和JWT认证模式
- 前端：在小程序中添加新闻爬取设置页面 `admin-news`，在通讯录详情页添加地图展示功能，遵循现有的代码风格和Vant Weapp组件库
- 数据完全共享：使用同一个数据库，与网页端数据完全同步

**Tech Stack:**
- 后端：Python Flask，遵循现有 `wx_api.py` 代码模式
- 前端：微信小程序原生开发，Vant Weapp组件库，使用微信原生地图组件
- 认证：JWT token认证，已有的 `token_required` 装饰器

---

## 文件结构

| 文件 | 操作 | 说明 |
|------|------|------|
| `wx_api.py` | 修改 | 添加新闻爬设置相关API端点（获取配置、更新配置、手动触发爬取） |
| `miniprogram/app.json` | 修改 | 添加新页面 `pages/admin-news/admin-news` 注册 |
| `miniprogram/pages/admin-news/admin-news.js` | 创建 | 新闻爬取设置页面逻辑 |
| `miniprogram/pages/admin-news/admin-news.json` | 创建 | 新闻爬取设置页面配置 |
| `miniprogram/pages/admin-news/admin-news.wxml` | 创建 | 新闻爬取设置页面模板 |
| `miniprogram/pages/admin-news/admin-news.wxss` | 创建 | 新闻爬取设置页面样式 |
| `miniprogram/pages/txl-detail/txl-detail.js` | 修改 | 添加地图相关数据和方法 |
| `miniprogram/pages/txl-detail/txl-detail.wxml` | 修改 | 添加地图组件展示地理位置 |
| `miniprogram/pages/txl-detail/txl-detail.wxss` | 修改 | 添加地图样式 |
| `miniprogram/pages/profile/profile.wxml` | 检查 | 确认跳转入口存在 |

---

## 任务分解

### Task 1: 在 wx_api.py 添加新闻爬取设置相关API端点

**Files:**
- Modify: `wx_api.py` (末尾添加新API)

- [ ] **Step 1: 添加获取新闻配置API**

```python
# ==================== 新闻爬取设置API ====================

@wx_bp.route('/admin/news/config', methods=['GET'])
@token_required
def get_news_config():
    """获取新闻爬取配置（仅管理员）"""
    nickname = request.wx_user['name']
    is_admin, _ = check_admin_status(nickname)
    
    if not is_admin:
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    config = database.get_config()
    return jsonify({
        'success': True,
        'crawl_hour': config.get('crawl_hour', 8),
        'crawl_minute': config.get('crawl_minute', 0),
        'keywords': config.get('keywords', '吉林大学,南岭校区,自动化')
    })
```

- [ ] **Step 2: 添加更新新闻配置API**

```python
@wx_bp.route('/admin/news/config', methods=['POST'])
@token_required
def update_news_config():
    """更新新闻爬取配置（仅管理员）"""
    nickname = request.wx_user['name']
    is_admin, _ = check_admin_status(nickname)
    
    if not is_admin:
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    data = request.get_json()
    crawl_hour = data.get('crawl_hour', 8)
    crawl_minute = data.get('crawl_minute', 0)
    keywords = data.get('keywords', '吉林大学,南岭校区,自动化')
    
    database.set_config('crawl_hour', str(crawl_hour))
    database.set_config('crawl_minute', str(crawl_minute))
    database.set_config('keywords', keywords)
    
    return jsonify({'success': True})
```

- [ ] **Step 3: 添加手动触发新闻爬取API**

```python
@wx_bp.route('/admin/news/crawl', methods=['POST'])
@token_required
def trigger_news_crawl():
    """手动触发新闻爬取（仅管理员）"""
    nickname = request.wx_user['name']
    is_admin, _ = check_admin_status(nickname)
    
    if not is_admin:
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    try:
        import news_crawler
        result = news_crawler.fetch_jlu_news()
        return jsonify({
            'success': True,
            'added': result.get('added', 0),
            'total': result.get('total', 0),
            'message': f'爬取完成，新增{result.get("added", 0)}条新闻'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
```

- [ ] **Step 4: 验证语法检查**

```bash
python3 -m py_compile wx_api.py
```

Expected: no output = success

- [ ] **Step 5: Commit**

```bash
git add wx_api.py
git commit -m "feat: add news config API for miniprogram admin"
```

---

### Task 2: 创建小程序新闻爬取设置页面

**Files:**
- Create: `miniprogram/pages/admin-news/admin-news.js`
- Create: `miniprogram/pages/admin-news/admin-news.json`
- Create: `miniprogram/pages/admin-news/admin-news.wxml`
- Create: `miniprogram/pages/admin-news/admin-news.wxss`
- Modify: `miniprogram/app.json`

- [ ] **Step 1: 创建页面配置文件 `admin-news.json`**

```json
{
  "usingComponents": {
    "van-cell": "miniprogram_npm/vant-weapp/cell/index",
    "van-cell-group": "miniprogram_npm/vant-weapp/cell-group/index",
    "van-field": "miniprogram_npm/vant-weapp/field/index",
    "van-button": "miniprogram_npm/vant-weapp/button/index",
    "van-loading": "miniprogram_npm/vant-weapp/loading/index",
    "van-toast": "miniprogram_npm/vant-weapp/toast/index"
  }
}
```

- [ ] **Step 2: 创建页面模板 `admin-news.wxml`**

```xml
<view class="container">
  <van-loading wx:if="{{loading}}" />
  
  <block wx:elif="{{config}}">
    <van-cell-group title="爬取时间">
      <van-field label="小时" type="number" value="{{config.crawl_hour}}" placeholder="0-23" bind:change="onCrawlHourChange" />
      <van-field label="分钟" type="number" value="{{config.crawl_minute}}" placeholder="0-59" bind:change="onCrawlMinuteChange" />
    </van-cell-group>

    <van-cell-group title="关键词" style="margin-top: 1rem;">
      <van-field label="关键词" type="textarea" autosize value="{{config.keywords}}" placeholder="逗号分隔" bind:change="onKeywordsChange" />
    </van-cell-group>

    <view class="hint" style="margin-top: 0.5rem; padding: 0 1rem; color: #999; font-size: 12px;">
      关键词用逗号分隔，只有包含关键词的新闻才会被保存
    </view>

    <view class="actions" style="margin-top: 1.5rem; padding: 0 1rem;">
      <van-button type="primary" block loading="{{saving}}" bind:tap="onSave">保存设置</van-button>
      <van-button type="info" block loading="{{crawling}}" bind:tap="onTriggerCrawl" style="margin-top: 1rem;">立即爬取</van-button>
    </view>

    <view wx:if="{{lastResult}}" class="result" style="margin-top: 1rem; padding: 1rem; background: #f5f5f5; border-radius: 8px;">
      <text>{{lastResult}}</text>
    </view>
  </block>

  <van-toast id="van-toast" />
</view>
```

- [ ] **Step 3: 创建页面样式 `admin-news.wxss`**

```css
.container {
  padding: 1rem;
  min-height: 100vh;
  background-color: #f5f5f5;
}

.cell-group {
  margin-bottom: 1rem;
}
```

- [ ] **Step 4: 创建页面逻辑 `admin-news.js`**

```javascript
const { request } = require('../../utils/auth');

Page({
  data: {
    loading: true,
    saving: false,
    crawling: false,
    config: null,
    lastResult: ''
  },

  onLoad() {
    this.loadConfig();
  },

  async loadConfig() {
    try {
      const res = await request('/admin/news/config');
      if (res.success) {
        this.setData({
          config: {
            crawl_hour: res.crawl_hour,
            crawl_minute: res.crawl_minute,
            keywords: res.keywords
          },
          loading: false
        });
      }
    } catch (e) {
      console.error('loadConfig error:', e);
      wx.showToast({ title: '加载失败', icon: 'none' });
      this.setData({ loading: false });
    }
  },

  onCrawlHourChange(e) {
    const value = parseInt(e.detail.value) || 0;
    this.setData({
      'config.crawl_hour': Math.max(0, Math.min(23, value))
    });
  },

  onCrawlMinuteChange(e) {
    const value = parseInt(e.detail.value) || 0;
    this.setData({
      'config.crawl_minute': Math.max(0, Math.min(59, value))
    });
  },

  onKeywordsChange(e) {
    this.setData({
      'config.keywords': e.detail.value
    });
  },

  async onSave() {
    const { config } = this.data;
    this.setData({ saving: true });

    try {
      await request('/admin/news/config', {
        crawl_hour: config.crawl_hour,
        crawl_minute: config.crawl_minute,
        keywords: config.keywords
      }, 'POST');
      wx.showToast({ title: '保存成功' });
    } catch (e) {
      wx.showToast({ title: '保存失败', icon: 'none' });
    } finally {
      this.setData({ saving: false });
    }
  },

  async onTriggerCrawl() {
    this.setData({ crawling: true });

    try {
      const res = await request('/admin/news/crawl', {}, 'POST');
      if (res.success) {
        wx.showToast({ title: res.message });
        this.setData({ lastResult: res.message });
      } else {
        wx.showToast({ title: res.error || '爬取失败', icon: 'none' });
      }
    } catch (e) {
      wx.showToast({ title: '爬取失败', icon: 'none' });
      console.error(e);
    } finally {
      this.setData({ crawling: false });
    }
  }
});
```

- [ ] **Step 5: 在 `app.json` 中注册新页面**

找到 `pages` 数组，在 `admin-settings` 之后添加：

```json
"pages": [
  ... existing pages ...
  "pages/admin-news/admin-news"
]
```

并在 `profile` 页面跳转入口确认存在。

- [ ] **Step 6: Commit**

```bash
git add \
  miniprogram/app.json \
  miniprogram/pages/admin-news/admin-news.js \
  miniprogram/pages/admin-news/admin-news.json \
  miniprogram/pages/admin-news/admin-news.wxml \
  miniprogram/pages/admin-news/admin-news.wxss
git commit -m "feat: add admin news config page for miniprogram"
```

---

### Task 3: 在个人中心（profile）页面添加新闻设置入口跳转

**Files:**
- Modify: `miniprogram/pages/profile/profile.wxml`
- Modify: `miniprogram/pages/profile/profile.js`

- [ ] **Step 1: 在 `profile.wxml` 添加跳转按钮**

在 `goToAdminSettings` 按钮之后（管理员区域内）添加：

```wxml
<van-button bindtap="goToNewsConfig" type="default" size="small" style="margin-top: 10px;">新闻爬取设置</van-button>
```

位置应该在管理员功能按钮区域，与其他管理按钮放在一起。

- [ ] **Step 2: 在 `profile.js` 添加跳转方法**

在 `goToAdminSettings` 方法之后添加：

```javascript
goToNewsConfig() {
  wx.navigateTo({ url: '/pages/admin-news/admin-news' });
}
```

- [ ] **Step 3: Commit**

```bash
git add miniprogram/pages/profile/profile.wxml miniprogram/pages/profile/profile.js
git commit -m "feat: add news config entry in profile page"
```

---

### Task 4: 在通讯录详情页添加地图展示地理位置

**Files:**
- Modify: `miniprogram/pages/txl-detail/txl-detail.wxml`
- Modify: `miniprogram/pages/txl-detail/txl-detail.wxss`
- Modify: `miniprogram/pages/txl-detail/txl-detail.js`

- [ ] **Step 1: 在 `txl-detail.wxml` 添加地图组件**

在喊话区域之前，添加地图 section：

```xml
<!-- 地图展示 -->
<view class="section" wx:if="{{student.gps_coords}}">
  <van-cell-group title="地理位置">
    <map
      latitude="{{map.latitude}}"
      longitude="{{map.longitude}}"
      scale="{{map.scale}}"
      show-location
      style="width: 100%; height: 300px; border-radius: 8px;"
      markers="{{map.markers}}"
    />
  </van-cell-group>
</view>
```

- [ ] **Step 2: 在 `txl-detail.wxss` 添加地图间距样式**

确保 section 有适当的 margin：

```css
.section {
  margin-top: 1rem;
}
```

（如果已经存在则无需重复添加）

- [ ] **Step 3: 在 `txl-detail.js` 添加地图数据初始化**

在 `loadStudentDetail` 成功后，解析 GPS 坐标并初始化地图：

```javascript
// 解析GPS坐标初始化地图
if (student.gps_coords) {
  try {
    const parts = student.gps_coords.split(',');
    const lat = parseFloat(parts[0].trim());
    const lon = parseFloat(parts[1].trim());
    this.setData({
      map: {
        latitude: lat,
        longitude: lon,
        scale: 15,
        markers: [{
          id: 1,
          latitude: lat,
          longitude: lon,
          title: student.name,
          iconPath: '/static/images/marker.png',
          width: 30,
          height: 30
        }]
      }
    });
  } catch (e) {
    console.error('parse gps error:', e);
  }
}
```

添加 `map` 到 data 默认值：

```javascript
data: {
  student: null,
  loading: true,
  showPhoneSheet: false,
  showVoiceSheet: false,
  voiceShouts: [],
  recording: false,
  recordingTime: 0,
  map: null,  // 添加这行
  ...
}
```

- [ ] **Step 4: 验证代码语法**

```bash
# 微信开发者工具会验证，这里检查文件编码换行符
head -n 30 miniprogram/pages/txl-detail/txl-detail.js | tail -n 10
```

- [ ] **Step 5: Commit**

```bash
git add \
  miniprogram/pages/txl-detail/txl-detail.js \
  miniprogram/pages/txl-detail/txl-detail.wxml \
  miniprogram/pages/txl-detail/txl-detail.wxss
git commit -m "feat: add map display in txl detail page"
```

---

### Task 5: 功能完整性检查与优化

**Files:**
- Check: 所有已修改文件对齐网页功能
- Verify: 所有跳转路径正常
- Test: API端点返回格式正确

- [ ] **Step 1: 检查所有功能点对比**

| 功能 | 网页端 | 小程序 | 状态 |
|------|--------|--------|------|
| 首页统计 | ✅ | ✅ | 已完成 |
| 班级时光 | ✅ | ✅ | 已完成（首页已有） |
| 通讯录搜索筛选 | ✅ | ✅ | 已完成 |
| 附近同学 | ✅ | ✅ | 已完成 |
| 通讯录详情查看 | ✅ | ✅ | 已完成 |
| 通讯录地图展示 | ✅ | ❌ | **本任务补全** |
| 联系同学（拨号/复制） | ✅ | ✅ | 已完成 |
| 语音喊话 | ✅ | ✅ | 已完成 |
| 留言板列表 | ✅ | ✅ | 已完成 |
| 发表留言（文字/图片/语音） | ✅ | ✅ | 已完成 |
| 留言点赞 | ✅ | ✅ | 已完成 |
| 留言评论 | ✅ | ✅ | 已完成 |
| 删除留言 | ✅ | ✅ | 已完成 |
| 相册列表 | ✅ | ✅ | 已完成 |
| 相册点赞 | ✅ | ✅ | 已完成 |
| 上传照片 | ✅ | ✅ | 已完成 |
| 删除照片 | ✅ | ✅ | 已完成 |
| 保存图片到相册 | ✅ | ✅ | 已完成 |
| 视频列表 | ✅ | ✅ | 已完成 |
| 视频点赞 | ✅ | ✅ | 已完成 |
| 上传视频 | ✅ | ✅ | 已完成 |
| 删除视频 | ✅ | ✅ | 已完成 |
| 播放视频 | ✅ | ✅ | 已完成 |
| 个人资料编辑 | ✅ | ✅ | 已完成 |
| 头像上传 | ✅ | ✅ | 已完成 |
| 通知列表 | ✅ | ✅ | 已完成 |
| 标记通知已读 | ✅ | ✅ | 已完成 |
| 已删除恢复 | ✅ | ✅ | 已完成 |
| 动态列表 | ✅ | ✅ | 已完成 |
| 删除动态（管理员） | ✅ | ✅ | 已完成 |
| 登录日志查看（管理员） | ✅ | ✅ | 已完成 |
| 权限管理（超管） | ✅ | ✅ | 已完成 |
| 新闻爬取设置（管理员） | ✅ | ❌ | **本任务补全** |

确认所有功能现在都已覆盖。

- [ ] **Step 2: 检查所有跳转路径**

验证所有页面跳转链：
- `profile → admin-settings` - 权限管理 ✓
- `profile → admin-news` - 新闻设置 ✓ (新建)
- `profile → login-logs` - 登录日志 ✓
- `profile → deleted` - 已删除恢复 ✓
- `profile → notifications` - 通知 ✓

所有跳转路径完整。

- [ ] **Step 3: 检查API端点完整性**

确认所有新增API在 `wx_api.py` 中：
- `GET /admin/news/config` - 获取配置 ✓
- `POST /admin/news/config` - 保存配置 ✓
- `POST /admin/news/crawl` - 手动爬取 ✓

- [ ] **Step 4: 检查database.py是否有需要的函数**

确认 `get_config()` 和 `set_config()` 存在：

```python
python3 -c "import database; print('get_config exists:', callable(getattr(database, 'get_config', None))); print('set_config exists:', callable(getattr(database, 'set_config', None)))"
```

Expected output:
```
get_config exists: True
set_config exists: True
```

- [ ] **Step 5: Commit (if any fixes needed)**

如果没有需要修改，此步骤跳过。

---

## 完成后最终验证

- 所有API遵循统一响应格式 `{"success": true/false, ...}` ✓
- 所有认证使用 `token_required` 装饰器 ✓
- 所有权限检查调用 `check_admin_status` 函数 ✓
- 遵循现有的代码风格和命名规范 ✓
- 所有页面都能通过跳转到达 ✓

