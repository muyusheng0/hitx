const app = getApp();

function login() {
  return new Promise((resolve, reject) => {
    wx.login({
      success: async (res) => {
        if (!res.code) {
          reject(new Error('No code'));
          return;
        }

        try {
          const response = await request('/login', {
            code: res.code
          }, 'POST');

          if (response.need_bind) {
            app.globalData.isBind = false;
            resolve({ needBind: true, openid: response.openid });
          } else {
            app.globalData.token = response.token;
            app.globalData.userInfo = response.user;
            app.globalData.isBind = true;
            wx.setStorageSync('token', response.token);
            wx.setStorageSync('userInfo', response.user);
            resolve({ needBind: false, user: response.user });
          }
        } catch (e) {
          reject(e);
        }
      },
      fail: reject
    });
  });
}

function bind(openid, name, studentId) {
  return new Promise((resolve, reject) => {
    request('/bind', {
      openid,
      name,
      student_id: studentId
    }, 'POST').then(response => {
      app.globalData.token = response.token;
      app.globalData.userInfo = response.user;
      app.globalData.isBind = true;
      wx.setStorageSync('token', response.token);
      wx.setStorageSync('userInfo', response.user);
      resolve(response.user);
    }).catch(reject);
  });
}

function request(url, data, method = 'GET') {
  const app = getApp();
  return new Promise((resolve, reject) => {
    wx.showLoading({ title: '加载中...' });

    wx.request({
      url: app.globalData.apiBase + url,
      data,
      method,
      header: {
        'Content-Type': 'application/json',
        'Authorization': app.globalData.token ? `Bearer ${app.globalData.token}` : ''
      },
      success: (res) => {
        wx.hideLoading();
        if (res.data.success) {
          resolve(res.data);
        } else {
          reject(new Error(res.data.error || 'Request failed'));
        }
      },
      fail: (err) => {
        wx.hideLoading();
        reject(err);
      }
    });
  });
}

module.exports = { login, bind, request };
