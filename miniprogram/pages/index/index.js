const { request } = require('../../utils/auth');

Page({
  data: {
    studentCount: 0,
    recentMessages: [],
    activities: []
  },

  onLoad() {
    this.checkBind();
  },

  onShow() {
    this.checkBind();
  },

  checkBind() {
    const app = getApp();
    if (!app.globalData.isBind) {
      wx.navigateTo({ url: '/pages/bind/bind' });
      return;
    }
    this.loadData();
  },

  async loadData() {
    try {
      const [txlRes, msgRes] = await Promise.all([
        request('/txl'),
        request('/messages')
      ]);

      this.setData({
        studentCount: txlRes.students.length,
        recentMessages: msgRes.messages.slice(0, 3)
      });
    } catch (e) {
      wx.showToast({ title: '加载失败', icon: 'none' });
    }
  }
});
