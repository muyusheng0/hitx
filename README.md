# 吉大通信八班 同学录网站

一个温馨、个性的同学录网站，记录青春回忆。

## 功能特点

- **通讯录**：展示全班同学的个人信息
- **留言板**：写下想说的话，与大家分享
- **相册**：上传和浏览照片回忆
- **视频**：分享珍贵的视频资料
- **背景音乐**：内置5首青春怀旧歌曲

## 个人信息保护

修改个人信息和上传内容需要验证身份（姓名+学号），确保信息安全。

## 技术栈

- 后端：Flask (Python)
- 前端：HTML5 + CSS3 + Vanilla JavaScript
- 数据存储：CSV文件

## 运行方式

```bash
cd /home/ubuntu/jlu8
pip install flask
python3 app.py
```

访问 http://localhost:5000

## 部署到公网

使用生产级WSGI服务器（如Gunicorn）配合nginx部署：

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 文件说明

- `app.py` - Flask主应用
- `txl.csv` - 同学通讯录数据
- `lyb.csv` - 留言板数据
- `videos.csv` - 视频链接数据
- `templates/` - HTML模板
- `static/` - 静态资源（CSS、JS、图片）
