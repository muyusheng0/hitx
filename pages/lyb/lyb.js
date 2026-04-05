const { request } = require('../../utils/auth');

Page({
  data: {
    messages: [],
    newContent: ''
  },

  onLoad() {
    this.loadMessages();
  },

  async loadMessages() {
    try {
      const res = await request('/messages');
      this.setData({ messages: res.messages });
    } catch (e) {
      wx.showToast({ title: '加载失败', icon: 'none' });
    }
  },

  onContentInput(e) {
    this.setData({ newContent: e.detail.value });
  },

  async onSubmit() {
    const { newContent } = this.data;
    if (!newContent.trim()) {
      wx.showToast({ title: '内容不能为空', icon: 'none' });
      return;
    }

    try {
      await request('/messages', { content: newContent }, 'POST');
      this.setData({ newContent: '' });
      this.loadMessages();
      wx.showToast({ title: '发表成功' });
    } catch (e) {
      wx.showToast({ title: '发表失败', icon: 'none' });
    }
  }
});