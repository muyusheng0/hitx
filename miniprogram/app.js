App({
  globalData: {
    apiBase: 'http://81.71.65.240:5000/api/wx',
    token: null,
    userInfo: null,
    isBind: false
  },

  onLaunch() {
    // 检查本地存储的登录状态
    const token = wx.getStorageSync('token');
    const userInfo = wx.getStorageSync('userInfo');

    if (token && userInfo) {
      this.globalData.token = token;
      this.globalData.userInfo = userInfo;
      this.globalData.isBind = true;
    }
  },

  checkAndNavigate() {
    if (this.globalData.isBind) {
      wx.switchTab({ url: '/pages/index/index' });
    } else {
      wx.navigateTo({ url: '/pages/bind/bind' });
    }
  }
});
