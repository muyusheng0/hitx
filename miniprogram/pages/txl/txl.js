const { request } = require('../../utils/auth');

Page({
  data: {
    students: []
  },

  onLoad() {
    this.loadStudents();
  },

  async loadStudents() {
    try {
      const res = await request('/txl');
      this.setData({ students: res.students });
    } catch (e) {
      wx.showToast({ title: '加载失败', icon: 'none' });
    }
  },

  onSearch(e) {
    // 简化：前端过滤
  },

  goDetail(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: `/pages/txl-detail/txl-detail?id=${id}` });
  }
});