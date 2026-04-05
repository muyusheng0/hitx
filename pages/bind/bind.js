const app = getApp();
const { login, bind } = require('../../utils/auth');

Page({
  data: {
    openid: '',
    name: '',
    studentId: '',
    loading: false
  },

  onLoad() {
    this.doLogin();
  },

  async doLogin() {
    try {
      const result = await login();
      if (!result.needBind) {
        wx.switchTab({ url: '/pages/index/index' });
      } else {
        this.setData({ openid: result.openid });
      }
    } catch (e) {
      wx.showToast({ title: '登录失败', icon: 'none' });
    }
  },

  onNameInput(e) {
    this.setData({ name: e.detail.value });
  },

  onStudentIdInput(e) {
    this.setData({ studentId: e.detail.value });
  },

  async onBind() {
    const { openid, name, studentId } = this.data;

    if (!name || !studentId) {
      wx.showToast({ title: '请填写完整', icon: 'none' });
      return;
    }

    this.setData({ loading: true });

    try {
      await bind(openid, name, studentId);
      wx.showToast({ title: '绑定成功' });
      setTimeout(() => {
        wx.switchTab({ url: '/pages/index/index' });
      }, 1500);
    } catch (e) {
      wx.showToast({ title: e.message || '绑定失败', icon: 'none' });
    } finally {
      this.setData({ loading: false });
    }
  }
});
