"""
页面渲染路由
迁移自 app.py
"""

import os
import json
from datetime import datetime, timedelta
import random
import time
import hashlib
from flask import render_template, session, request, redirect, url_for, send_from_directory
import database
import config
import utils

from blueprints.pages import pages_bp


@pages_bp.route('/login')
def login_page():
    """登录页"""
    if 'verified_student' in session:
        # 已登录，跳转到原页面或留言页
        redirect_url = request.args.get('redirect', '/lyb')
        return redirect(redirect_url)
    return render_template('login.html')


@pages_bp.route('/')
def index():
    """首页"""
    students = database.read_txl()
    messages = database.read_lyb()

    # 过去一周内的留言数量
    one_week_ago = datetime.now() - timedelta(days=7)
    week_messages = [m for m in messages
                      if datetime.strptime(m['time'], '%Y-%m-%d %H:%M:%S') > one_week_ago]
    week_message_count = len(week_messages)

    # 按时间倒序获取最新留言(最多12条)
    sorted_messages = sorted(messages, key=lambda x: x['time'], reverse=True)
    recent_messages = sorted_messages[:1]  # 只显示一条最新留言

    activities = get_activities()

    # 获取照片,按年份分组,每年最多3张
    img_files = get_gallery_images()
    photos_by_year = {}
    for img in img_files:
        year = img.get('year', 2020)
        if year not in photos_by_year:
            photos_by_year[year] = []
        if len(photos_by_year[year]) < 4:
            photos_by_year[year].append(img)

    # 获取省份统计
    province_stats = {}
    for s in students:
        p = s['hometown_name']
        if p:
            if p not in province_stats:
                province_stats[p] = {'count': 0, 'students': [], 'coords': s['coords']}
            province_stats[p]['count'] += 1
            province_stats[p]['students'].append({'name': s['name'], 'id': s['id']})

    return render_template('index.html',
                           student_count=len(students),
                           recent_messages=recent_messages,
                           week_message_count=week_message_count,
                           activities=activities[:9],  # 传递最新9条动态
                           photos_by_year=photos_by_year,
                           province_stats=province_stats,
                           logged_in='verified_student' in session)


@pages_bp.route('/txl')
def txl():
    """通讯录页面"""
    is_logged = 'verified_student' in session

    # 未登录用户:不能查看同学通讯录
    if not is_logged:
        students = []
    else:
        students = database.read_txl()

    # 为每个学生添加拼音用于排序
    try:
        from pypinyin import lazy_pinyin
        for s in students:
            s['pinyin'] = ''.join(lazy_pinyin(s.get('name', '')))
    except:
        for s in students:
            s['pinyin'] = s.get('name', '')

    # 为没有坐标的学生填充坐标(根据城市名和区)
    for s in students:
        if not s.get('coords'):
            city = s.get('city', '') or s.get('hometown_name', '')
            district = s.get('district', '')
            if city:
                coords = database.get_coords_by_city(city, district)
                if coords:
                    s['coords'] = coords

    voice_shouts = database.read_voice_shouts()

    # 计算离我最近的同学(仅登录用户)
    nearest_classmates = []
    if is_logged:
        current_user = session['verified_student']
        # 优先使用GPS坐标,其次使用session中的城市坐标,最后根据当前用户的城市查找
        current_coords = current_user.get('coords', '')
        current_name = current_user.get('name', '')
        current_id = current_user.get('id', '')

        # 查找当前用户的GPS坐标(优先使用)
        for s in students:
            if s.get('name') == current_name and s.get('id') == current_id:
                gps = s.get('gps_coords', '')
                if gps:
                    current_coords = gps
                break

        # 如果没有GPS坐标也没有session坐标,根据城市获取
        if not current_coords:
            for s in students:
                if s.get('name') == current_name and s.get('id') == current_id:
                    current_coords = s.get('coords', '')
                    break

        if current_coords:
            try:
                lat1, lon1 = map(float, current_coords.split(','))
                distances = []
                for s in students:
                    if s.get('name') == current_name:
                        continue
                    # 优先使用同学的GPS坐标,其次使用城市坐标
                    s_coords = s.get('gps_coords', '') or s.get('coords', '')
                    if s_coords:
                        try:
                            lat2, lon2 = map(float, s_coords.split(','))
                            dist = haversine_distance(lat1, lon1, lat2, lon2)
                            distances.append((s['name'], dist, s))
                        except:
                            continue
                distances.sort(key=lambda x: x[1])
                nearest_classmates = [(d[2], int(d[1])) for d in distances[:2]]
            except:
                pass

    return render_template('txl.html', students=students, voice_shouts=voice_shouts, nearest_classmates=nearest_classmates, logged_in=is_logged)


@pages_bp.route('/lyb')
def lyb():
    """留言板页面"""
    logged_in = 'verified_student' in session
    messages = database.read_lyb()
    messages.reverse()
    # 为每条留言添加头像信息
    students = database.read_txl()
    for msg in messages:
        msg['avatar'] = ''
        for s in students:
            if s.get('name') == msg.get('nickname'):
                msg['avatar'] = s.get('avatar', '')
                break
    return render_template('lyb.html', messages=messages, logged_in=logged_in)


@pages_bp.route('/gallery')
def gallery():
    """相册页面 - 重定向到媒体中心"""
    return redirect('/media')


@pages_bp.route('/video')
def video_page():
    """视频页面 - 重定向到媒体中心"""
    return redirect('/media')


@pages_bp.route('/media')
def media():
    """媒体中心 - 相册和视频合并页面"""
    from datetime import datetime

    # 检查登录状态
    logged_in = 'verified_student' in session

    img_files = get_gallery_images()
    videos = get_videos()
    news = database.get_news(100)

    # 过滤掉旧新闻,只展示今年的新闻
    current_year = datetime.now().year
    news = [n for n in news if int(n['published_time'][:4]) >= current_year]

    # 只排除校友会相关内容(留给校友会tab展示)
    alumni_keywords = ['校友会', '校友总会', '北京校友会', '上海校友会', '深圳校友会', '广州校友会',
                       '成都校友会', '武汉校友会', '北美校友会', '校友大会', '校友联谊', '校友活动',
                       '校友交流', '校友企业', '校友返校']
    news = [n for n in news if not any(kw in (n.get('title', '') + ' ' + n.get('content', '')).lower() for kw in alumni_keywords)]

    # 按日期+图片排序(最新优先,有图片的放前面)
    def news_sort_key(n):
        pub_time = n.get('published_time', '')
        if pub_time:
            try:
                date = datetime.strptime(pub_time[:10], '%Y-%m-%d')
            except:
                date = datetime.min
        else:
            date = datetime.min
        has_image = 1 if n.get('image_url') else 0
        # 日期降序(最新优先),图片优先(有图片=1 > 无图片=0)
        return (date, has_image)
    news.sort(key=news_sort_key, reverse=True)
    news = news[:20]  # 最多渲染20条新闻

    # 检查当前用户是否是管理员
    is_admin_user = False
    if 'verified_student' in session:
        current_name = session['verified_student']['name']
        is_admin_user = is_admin(current_name)

    return render_template('media.html', images=img_files, videos=videos, news=news, is_admin_user=is_admin_user, logged_in=logged_in)


@pages_bp.route('/about')
def about():
    """个人中心页面"""
    return render_template('about.html')


@pages_bp.route('/ai-chat')
def ai_chat():
    """AI 聊天助手页面（仅管理员）"""
    return render_template('ai-chat.html')

