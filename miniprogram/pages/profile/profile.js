const { request } = require('../../utils/auth');

Page({
  data: {
    profile: null
  },

  onLoad() {
    this.loadProfile();
  },

  async loadProfile() {
    try {
      const res = await request('/profile');
      this.setData({ profile: res.profile });
    } catch (e) {
      wx.showToast({ title: '加载失败', icon: 'none' });
    }
  },

  onLogout() {
    wx.showModal({
      title: '提示',
      content: '确定要退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          // 只清除认证相关信息，保留其他缓存
          try {
            wx.removeStorageSync('token');
            wx.removeStorageSync('userInfo');
          } catch (e) {}
          getApp().globalData.isBind = false;
          getApp().globalData.token = null;
          getApp().globalData.userInfo = null;
          wx.reLaunch({ url: '/pages/bind/bind' });
        }
      }
    });
  }
});