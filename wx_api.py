"""
微信小程序API模块
提供 /api/wx/* 端点
"""

from flask import Blueprint, request, jsonify, session
import jwt
import datetime
import requests
from functools import wraps
import os
import database

wx_bp = Blueprint('wx', __name__, url_prefix='/api/wx')

# JWT配置
JWT_SECRET = os.environ.get('JWT_SECRET', 'jlu_wx_miniprogram_2024_dev_key')
JWT_EXPIRE_DAYS = 7

# 微信API配置
WX_APPID = 'wx747fe17f7c7b65e8'
WX_SECRET = '8b9b397efa48f2ab2b3d3d0e4c7ef61a'


def generate_token(openid, student_id, name):
    """生成JWT Token"""
    payload = {
        'openid': openid,
        'student_id': student_id,
        'name': name,
        'iat': datetime.datetime.utcnow(),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=JWT_EXPIRE_DAYS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256').decode('utf-8')


def verify_token(token):
    """验证JWT Token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def token_required(f):
    """Token验证装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header[7:]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        request.wx_user = payload
        return f(*args, **kwargs)
    return decorated


def get_openid_from_code(code):
    """通过code换取openid"""
    url = 'https://api.weixin.qq.com/sns/jscode2session'
    params = {
        'appid': WX_APPID,
        'secret': WX_SECRET,
        'js_code': code,
        'grant_type': 'authorization_code'
    }
    try:
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()
        return data.get('openid'), data
    except Exception as e:
        return None, {'error': str(e)}


@wx_bp.route('/login', methods=['POST'])
def wx_login():
    """微信登录"""
    data = request.get_json()
    code = data.get('code')

    if not code:
        return jsonify({'success': False, 'error': 'Missing code'})

    openid, wx_data = get_openid_from_code(code)

    if not openid:
        return jsonify({'success': False, 'error': 'Invalid code', 'detail': wx_data})

    # 检查是否已绑定
    binding = database.get_binding_by_openid(openid)
    if binding:
        # 已绑定，直接登录
        token = generate_token(openid, binding['student_id'], binding['name'])
        return jsonify({
            'success': True,
            'token': token,
            'need_bind': False,
            'user': {
                'student_id': binding['student_id'],
                'name': binding['name']
            }
        })

    # 未绑定
    return jsonify({
        'success': True,
        'need_bind': True,
        'openid': openid
    })


@wx_bp.route('/bind', methods=['POST'])
def wx_bind():
    """绑定openid与学生账号"""
    data = request.get_json()
    openid = data.get('openid')
    name = data.get('name')
    student_id = data.get('student_id')

    if not all([openid, name, student_id]):
        return jsonify({'success': False, 'error': 'Missing parameters'})

    # 验证姓名+学号有效性
    students = database.read_txl()
    valid_student = None
    for s in students:
        if s['name'] == name and s['id'] == student_id:
            valid_student = s
            break

    if not valid_student:
        return jsonify({'success': False, 'error': 'Invalid name or student_id'})

    # 执行绑定
    success = database.bind_wx_openid(openid, student_id, name)
    if not success:
        return jsonify({'success': False, 'error': 'Bind failed'})

    token = generate_token(openid, student_id, name)
    return jsonify({
        'success': True,
        'token': token,
        'user': {
            'student_id': student_id,
            'name': name
        }
    })


@wx_bp.route('/check_bind', methods=['GET'])
def check_bind():
    """检查openid是否已绑定"""
    openid = request.args.get('openid')
    if not openid:
        return jsonify({'success': False, 'error': 'Missing openid'})

    binding = database.get_binding_by_openid(openid)
    return jsonify({
        'success': True,
        'bound': binding is not None
    })


@wx_bp.route('/txl', methods=['GET'])
@token_required
def get_txl():
    """获取通讯录列表"""
    students = database.read_txl()
    result = []
    for s in students:
        result.append({
            'id': s['id'],
            'name': s['name'],
            'hometown': s.get('hometown_name', ''),
            'city': s.get('city', ''),
            'avatar': s.get('avatar', ''),
            'phone': s.get('phone', ''),
            'work': s.get('work', ''),
            'company': s.get('company', '')
        })
    return jsonify({'success': True, 'students': result})


@wx_bp.route('/txl/<student_id>', methods=['GET'])
@token_required
def get_student_detail(student_id):
    """获取同学详细信息"""
    students = database.read_txl()
    for s in students:
        if s['id'] == student_id:
            return jsonify({'success': True, 'student': dict(s)})
    return jsonify({'success': False, 'error': 'Student not found'})


@wx_bp.route('/messages', methods=['GET'])
@token_required
def get_messages():
    """获取留言列表"""
    messages = database.read_lyb()
    messages.reverse()  # 最新在前
    students = database.read_txl()
    student_avatar = {s['name']: s.get('avatar', '') for s in students}
    result = []
    for m in messages:
        nickname = m['nickname']
        result.append({
            'id': m['id'],
            'nickname': nickname,
            'avatar': student_avatar.get(nickname, ''),
            'content': m['content'],
            'time': m['time'],
            'image': m.get('image', ''),
            'voice': m.get('voice', '')
        })
    return jsonify({'success': True, 'messages': result})


@wx_bp.route('/messages', methods=['POST'])
@token_required
def add_message():
    """发表留言"""
    from datetime import datetime
    data = request.get_json()
    content = data.get('content', '').strip()
    image = data.get('image', '').strip()

    if not content:
        return jsonify({'success': False, 'error': 'Empty content'})

    if len(content) > 500:
        return jsonify({'success': False, 'error': 'Content too long'})

    nickname = request.wx_user['name']

    message = {
        'id': database.get_next_lyb_id(),
        'nickname': nickname,
        'content': content,
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'image': image,
        'voice': ''
    }

    messages = database.read_lyb()
    messages.append(message)
    database.write_lyb(messages)

    return jsonify({'success': True, 'message': message})


@wx_bp.route('/photos', methods=['GET'])
@token_required
def get_photos():
    """获取相册列表"""
    photos = database.read_photos()
    result = []
    for p in photos:
        result.append({
            'id': p['id'],
            'filename': p['filename'],
            'owner': p.get('owner', ''),
            'time': p.get('time', ''),
            'year': p.get('year', 2020)
        })
    return jsonify({'success': True, 'photos': result})


@wx_bp.route('/videos', methods=['GET'])
@token_required
def get_videos():
    """获取视频列表"""
    videos = database.read_videos()
    result = []
    for v in videos:
        result.append({
            'id': v['id'],
            'title': v['title'],
            'url': v['url'],
            'cover': v.get('cover', ''),
            'owner': v.get('owner', '')
        })
    return jsonify({'success': True, 'videos': result})


@wx_bp.route('/profile', methods=['GET'])
@token_required
def get_profile():
    """获取个人资料"""
    student_id = request.wx_user['student_id']
    students = database.read_txl()
    for s in students:
        if s['id'] == student_id:
            profile = dict(s)
            # 添加管理员权限信息
            profile['is_admin'] = s.get('is_admin', False) or s.get('name') == '穆玉升'
            profile['is_super_admin'] = s.get('super_admin', False) or s.get('name') == '穆玉升'
            return jsonify({'success': True, 'profile': profile})
    return jsonify({'success': False, 'error': 'Profile not found'})


@wx_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile():
    """更新个人资料"""
    student_id = request.wx_user['student_id']
    data = request.get_json()

    students = database.read_txl()
    for s in students:
        if s['id'] == student_id:
            # 更新允许的字段
            allowed_fields = ['phone', 'work', 'position',
                             'hobby', 'dream', 'company', 'industry', 'gender', 'birthday',
                             'github', 'douyin', 'xiaohongshu', 'custom_intro', 'avatar',
                             'city', 'hometown', 'hometown_name', 'gps_coords']
            for field in allowed_fields:
                if field in data:
                    s[field] = data[field]

            database.write_txl(students)
            return jsonify({'success': True})

    return jsonify({'success': False, 'error': 'Profile not found'})


@wx_bp.route('/avatar', methods=['POST'])
@token_required
def upload_avatar():
    """上传头像"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file'})

    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'error': 'No file selected'})

    # 保存文件
    import uuid
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
    filename = f"avatar_{uuid.uuid4().hex}.{ext}"
    avatar_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static/imgs/avatars')
    os.makedirs(avatar_dir, exist_ok=True)
    filepath = os.path.join(avatar_dir, filename)
    file.save(filepath)

    avatar_url = f'/static/imgs/avatars/{filename}'

    # 更新用户头像
    student_id = request.wx_user['student_id']
    students = database.read_txl()
    for s in students:
        if s['id'] == student_id:
            s['avatar'] = avatar_url
            database.write_txl(students)
            break

    return jsonify({'success': True, 'url': avatar_url})


# ==================== 评论API ====================

@wx_bp.route('/comments/<int:message_id>', methods=['GET'])
@token_required
def get_comments(message_id):
    """获取某留言的所有评论"""
    nickname = request.wx_user['name']
    is_admin, _ = check_admin_status(nickname)

    raw_comments = database.get_comments_by_message(message_id)
    comments = []
    for c in raw_comments:
        c['can_delete'] = (c.get('nickname') == nickname or is_admin)
        comments.append(c)

    return jsonify({'success': True, 'comments': comments})


@wx_bp.route('/comments', methods=['POST'])
@token_required
def add_comment():
    """添加评论"""
    data = request.get_json()
    message_id = data.get('message_id')
    content = data.get('content')

    if not all([message_id, content]):
        return jsonify({'success': False, 'error': 'Missing parameters'})

    nickname = request.wx_user['name']
    comment_id = database.add_comment(message_id, nickname, content)

    return jsonify({
        'success': True,
        'comment': {
            'id': comment_id,
            'message_id': message_id,
            'nickname': nickname,
            'content': content
        }
    })


@wx_bp.route('/comments/<int:comment_id>', methods=['DELETE'])
@token_required
def delete_comment(comment_id):
    """删除评论"""
    nickname = request.wx_user['name']
    is_admin = request.wx_user.get('is_admin', False)

    # 获取评论信息
    comments = database.read_comments(None)
    comment = None
    for c in comments:
        if c['id'] == comment_id:
            comment = c
            break

    if not comment:
        return jsonify({'success': False, 'error': 'Comment not found'})

    # 权限检查：评论人或管理员可删除
    if comment['nickname'] != nickname and not is_admin:
        return jsonify({'success': False, 'error': 'Permission denied'})

    database.delete_comment(comment_id)
    return jsonify({'success': True})


# ==================== 留言点赞API ====================

@wx_bp.route('/messages/<int:message_id>/like', methods=['GET'])
@token_required
def get_message_like_status(message_id):
    """获取留言点赞状态"""
    nickname = request.wx_user['name']
    count = database.get_message_likes(message_id)
    liked = database.has_liked_message(message_id, nickname)

    return jsonify({
        'success': True,
        'count': count,
        'liked': liked
    })


@wx_bp.route('/messages/<int:message_id>/like', methods=['POST'])
@token_required
def like_message():
    """点赞留言"""
    data = request.get_json()
    message_id = data.get('message_id')

    if not message_id:
        return jsonify({'success': False, 'error': 'Missing message_id'})

    nickname = request.wx_user['name']
    success = database.like_message(message_id, nickname)

    if success:
        count = database.get_message_likes(message_id)
        return jsonify({'success': True, 'count': count})
    else:
        return jsonify({'success': False, 'error': 'Already liked'})


@wx_bp.route('/messages/<int:message_id>/like', methods=['DELETE'])
@token_required
def unlike_message():
    """取消点赞留言"""
    data = request.get_json()
    message_id = data.get('message_id')

    if not message_id:
        return jsonify({'success': False, 'error': 'Missing message_id'})

    nickname = request.wx_user['name']
    database.unlike_message(message_id, nickname)
    count = database.get_message_likes(message_id)

    return jsonify({'success': True, 'count': count})


# ==================== 媒体点赞API ====================

@wx_bp.route('/media/<media_type>/<int:media_id>/like', methods=['GET'])
@token_required
def get_media_like_status(media_type, media_id):
    """获取媒体点赞状态"""
    if media_type not in ['photo', 'video']:
        return jsonify({'success': False, 'error': 'Invalid media type'})

    nickname = request.wx_user['name']
    count = database.get_media_likes(media_type, media_id)
    liked = database.has_liked_media(media_type, media_id, nickname)

    return jsonify({
        'success': True,
        'count': count,
        'liked': liked
    })


@wx_bp.route('/media/<media_type>/<int:media_id>/like', methods=['POST'])
@token_required
def like_media(media_type, media_id):
    """点赞媒体"""
    if media_type not in ['photo', 'video']:
        return jsonify({'success': False, 'error': 'Invalid media type'})

    nickname = request.wx_user['name']
    success = database.like_media(media_type, media_id, nickname)

    if success:
        count = database.get_media_likes(media_type, media_id)
        return jsonify({'success': True, 'count': count})
    else:
        return jsonify({'success': False, 'error': 'Already liked'})


@wx_bp.route('/media/<media_type>/<int:media_id>/like', methods=['DELETE'])
@token_required
def unlike_media(media_type, media_id):
    """取消点赞媒体"""
    if media_type not in ['photo', 'video']:
        return jsonify({'success': False, 'error': 'Invalid media type'})

    nickname = request.wx_user['name']
    database.unlike_media(media_type, media_id, nickname)
    count = database.get_media_likes(media_type, media_id)

    return jsonify({'success': True, 'count': count})


# ==================== 已删除内容API ====================

@wx_bp.route('/deleted', methods=['GET'])
@token_required
def get_deleted():
    """获取已删除内容列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 10

    items = database.read_deleted()
    total = len(items)
    total_pages = (total + per_page - 1) // per_page

    start = (page - 1) * per_page
    end = start + per_page
    page_items = items[start:end]

    return jsonify({
        'success': True,
        'items': page_items,
        'page': page,
        'total_pages': total_pages,
        'total': total
    })


@wx_bp.route('/deleted/<int:item_id>/restore', methods=['POST'])
@token_required
def restore_deleted(item_id):
    """恢复已删除内容"""
    nickname = request.wx_user['name']

    # 获取要恢复的内容
    items = database.read_deleted()
    item = None
    for i in items:
        if i['id'] == item_id:
            item = i
            break

    if not item:
        return jsonify({'success': False, 'error': 'Item not found'})

    # 恢复逻辑
    if item['type'] == 'message':
        # 恢复留言
        messages = database.read_lyb()
        messages.append({
            'id': database.get_next_lyb_id(),
            'nickname': item['owner'],
            'content': item['content'],
            'time': item['time'],
            'image': item.get('extra', ''),
            'voice': ''
        })
        database.write_lyb(messages)
    elif item['type'] == 'photo':
        # 恢复照片记录
        photos = database.read_photos()
        photos.append({
            'id': database.get_next_photo_id(),
            'filename': item['content'],
            'owner': item['owner'],
            'time': item['time']
        })
        database.write_photos(photos)
    elif item['type'] == 'video':
        # 恢复视频记录
        videos = database.read_videos()
        videos.append({
            'id': database.get_next_video_id(),
            'title': item['content'],
            'url': item.get('extra', ''),
            'cover': '',
            'owner': item['owner']
        })
        database.write_videos(videos)

    # 从已删除列表中移除
    database.delete_from_deleted(item_id)

    return jsonify({'success': True})


@wx_bp.route('/deleted/<int:item_id>/permanent', methods=['POST'])
@token_required
def permanent_delete(item_id):
    """永久删除内容"""
    nickname = request.wx_user['name']
    is_admin = request.wx_user.get('is_admin', False)

    if not is_admin:
        return jsonify({'success': False, 'error': 'Permission denied'})

    database.delete_from_deleted(item_id)
    return jsonify({'success': True})


# ==================== 消息通知API ====================

@wx_bp.route('/notifications', methods=['GET'])
@token_required
def get_notifications():
    """获取消息通知列表"""
    nickname = request.wx_user['name']
    notifications = database.get_notifications(nickname)

    return jsonify({
        'success': True,
        'notifications': notifications
    })


@wx_bp.route('/notifications/count', methods=['GET'])
@token_required
def get_notification_count():
    """获取未读通知数量"""
    nickname = request.wx_user['name']
    count = database.get_unread_notification_count(nickname)

    return jsonify({
        'success': True,
        'count': count
    })


@wx_bp.route('/notifications/mark_read', methods=['POST'])
@token_required
def mark_notifications_read():
    """标记通知已读"""
    nickname = request.wx_user['name']
    database.mark_all_notifications_read(nickname)

    return jsonify({'success': True})


# ==================== 最新动态API ====================

def get_wx_activities():
    """获取最新动态（小程序用）"""
    from datetime import datetime
    import re
    activities = []

    # 检查生日动态
    today = datetime.now()
    students = database.read_txl()
    for student in students:
        birthday_str = student.get('birthday', '')
        if birthday_str and len(birthday_str) >= 10:
            try:
                birthday_month = int(birthday_str[5:7])
                birthday_day = int(birthday_str[8:10])
                this_year_birthday = datetime(today.year, birthday_month, birthday_day)
                if this_year_birthday < today and (today - this_year_birthday).days > 5:
                    this_year_birthday = datetime(today.year + 1, birthday_month, birthday_day)
                days_until = (this_year_birthday - today).days
                if 0 <= days_until <= 5:
                    pronoun = '他' if student.get('gender', '') == '男' else '她'
                    if days_until == 0:
                        content = f'今天{student["name"]}生日！祝{pronoun}生日快乐！'
                    else:
                        content = f'{student["name"]} {birthday_month}月{birthday_day}日生日，还有{days_until}天'
                    activities.append({
                        'type': 'birthday',
                        'actor': student['name'],
                        'content': content,
                        'time': this_year_birthday.strftime('%Y-%m-%d 00:00:00')
                    })
            except:
                pass

    # 留言动态
    messages = database.read_lyb()
    for msg in sorted(messages, key=lambda x: x['time'], reverse=True)[:10]:
        has_voice = bool(msg.get('voice'))
        has_image = bool(msg.get('image'))
        if has_voice and has_image:
            content = '发表了语音留言并附带图片'
        elif has_voice:
            content = '发表了语音留言'
        elif has_image:
            content = '发表了新留言，并附带图片'
        else:
            content = '发表了新留言'
        activities.append({
            'type': 'message',
            'actor': msg['nickname'],
            'content': content,
            'time': msg['time'],
            'msg_id': msg['id'],
            'msg_content': msg['content'][:50] if msg['content'] else '',
            'has_image': has_image,
            'has_voice': has_voice
        })

    # 活动日志
    activity_logs = database.read_activities()
    for log in activity_logs[:20]:
        activity = {
            'type': log['type'],
            'actor': log['actor'],
            'content': log['content'],
            'time': log['time']
        }
        if log['type'] == 'photo':
            match = re.search(r'《(.+?)》', log['content'])
            if match:
                activity['img_name'] = match.group(1)
                activity['img_url'] = f'/static/imgs/messages/{match.group(1)}'
        if log['type'] == 'video':
            match = re.search(r'《(.+?)》', log['content'])
            if match:
                activity['video_title'] = match.group(1)
        activities.append(activity)

    # 按时间排序
    activities.sort(key=lambda x: x['time'], reverse=True)

    # 合并同一人同类动态
    deduplicated = []
    for activity in activities:
        if not deduplicated:
            activity['count'] = 1
            deduplicated.append(activity)
        else:
            last = deduplicated[-1]
            if activity['actor'] == last['actor'] and activity['type'] == last['type']:
                last['count'] = last.get('count', 1) + 1
            else:
                activity['count'] = 1
                deduplicated.append(activity)

    for act in deduplicated:
        count = act.get('count', 1)
        if count > 1:
            if act['type'] == 'photo':
                act['content'] = f'上传了{count}张照片'
            elif act['type'] == 'message':
                act['content'] = f'发表了{count}条留言'
            elif act['type'] == 'video':
                act['content'] = f'分享了{count}个视频'
            elif act['type'] == 'voice_shout':
                act['content'] = f'喊了{count}次话'

    return deduplicated[:10]


@wx_bp.route('/activities', methods=['GET'])
@token_required
def get_activities():
    """获取最新动态"""
    activities = get_wx_activities()
    return jsonify({
        'success': True,
        'activities': activities
    })


@wx_bp.route('/nearest', methods=['GET'])
@token_required
def get_nearest_classmates():
    """获取离我最近的同学"""
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)

    if lat is None or lon is None:
        return jsonify({'success': False, 'error': 'Missing location'})

    import math
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371  # 地球半径，单位公里
        dLat = math.radians(lat2 - lat1)
        dLon = math.radians(lon2 - lon1)
        a = math.sin(dLat/2) * math.sin(dLat/2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2) * math.sin(dLon/2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    students = database.read_txl()
    nearest = []
    for s in students:
        gps = s.get('gps_coords', '')
        if gps:
            try:
                parts = gps.split(',')
                if len(parts) >= 2:
                    s_lat = float(parts[0].strip())
                    s_lon = float(parts[1].strip())
                    dist = haversine(lat, lon, s_lat, s_lon)
                    nearest.append({
                        'id': s['id'],
                        'name': s['name'],
                        'avatar': s.get('avatar', ''),
                        'distance': round(dist, 1),
                        'city': s.get('city', ''),
                        'hometown': s.get('hometown_name', '')
                    })
            except:
                pass

    nearest.sort(key=lambda x: x['distance'])
    return jsonify({'success': True, 'nearest': nearest[:5]})


# ==================== 喊话API ====================

@wx_bp.route('/voice_shout/<to_name>', methods=['GET'])
@token_required
def get_voice_shouts(to_name):
    """获取对某人的喊话列表"""
    shouts = database.get_voice_shouts_by_target(to_name)
    return jsonify({'success': True, 'shouts': shouts})


@wx_bp.route('/voice_shout', methods=['POST'])
@token_required
def upload_voice_shout():
    """上传喊话语音"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file'})

    file = request.files['file']
    to_name = request.form.get('to_name', '')

    if not file.filename or not to_name:
        return jsonify({'success': False, 'error': 'Missing params'})

    from werkzeug.utils import secure_filename
    import uuid
    ext = secure_filename(file.filename).rsplit('.', 1)[-1] if '.' in file.filename else 'wav'
    if ext not in ['wav', 'mp3', 'webm', 'm4a', 'ogg']:
        ext = 'wav'

    filename = f"shout_{uuid.uuid4().hex}.{ext}"
    shout_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static/imgs/voice_shouts')
    os.makedirs(shout_dir, exist_ok=True)
    filepath = os.path.join(shout_dir, filename)
    file.save(filepath)

    audio_url = f'/static/imgs/voice_shouts/{filename}'
    from_name = request.wx_user.get('name', '')

    shout_id = database.add_voice_shout(from_name, to_name, audio_url)
    if shout_id:
        database.write_activity(from_name, 'voice_shout', f'对{to_name}喊了一段话')
        return jsonify({'success': True, 'shout_id': shout_id, 'audio_url': audio_url})

    return jsonify({'success': False, 'error': 'Failed to save'})


@wx_bp.route('/voice_shout/<int:shout_id>', methods=['DELETE'])
@token_required
def delete_voice_shout(shout_id):
    """删除喊话"""
    name = request.wx_user.get('name', '')
    success, msg = database.delete_voice_shout(shout_id, name)
    return jsonify({'success': success, 'message': msg})


# ==================== 班级时光API ====================

# 班级时间线数据（静态）
CLASS_TIMELINE = [
    {
        'year': '2015年 秋',
        'event': '金秋九月，带着梦想与期待，我们相聚在吉大南岭校区，军训场上挥洒汗水',
        'photos': []
    },
    {
        'year': '2016年',
        'event': '运动会上奋勇拼搏，元旦晚会上载歌载舞，班级凝聚力日益增强',
        'photos': []
    },
    {
        'year': '2017年',
        'event': '课程难度增加，我们互帮互助，实验室里共同探索通信的奥秘',
        'photos': []
    },
    {
        'year': '2018年 冬',
        'event': '考研复习的深夜，通宵自习室里的陪伴，梦想在心中发芽',
        'photos': []
    },
    {
        'year': '2019年 夏',
        'event': '毕业季，不说再见，穿着学士服定格青春，愿此去前程似锦',
        'photos': []
    },
    {
        'year': '2020年',
        'event': '疫情来袭，我们各自坚守，云端联络心系彼此',
        'photos': []
    },
    {
        'year': '2022年',
        'event': '疫情缓解，线下重聚，畅谈人生规划，共谋发展',
        'photos': []
    },
    {
        'year': '2024年',
        'event': '同学录网站上线，重建联系，记录青春，延续友情',
        'photos': []
    }
]


@wx_bp.route('/timeline', methods=['GET'])
@token_required
def get_timeline():
    """获取班级时光时间线"""
    return jsonify({
        'success': True,
        'timeline': CLASS_TIMELINE
    })


def check_admin_status(name):
    """检查用户的管理员权限"""
    db = database.get_db()
    cursor = db.execute("SELECT is_admin, super_admin FROM students WHERE name = ?", (name,))
    row = cursor.fetchone()
    if row:
        return row['is_admin'] == 1 or row['super_admin'] == 1 or name == '穆玉升', row['super_admin'] == 1 or name == '穆玉升'
    return False, False


# ==================== 动态管理API ====================

@wx_bp.route('/activities/<time>/<actor>', methods=['DELETE'])
@token_required
def delete_activity(time, actor):
    """删除动态"""
    nickname = request.wx_user['name']
    is_admin, _ = check_admin_status(nickname)

    if not is_admin:
        return jsonify({'success': False, 'error': 'Permission denied'})

    database.delete_activity(time, actor, None)
    return jsonify({'success': True})


# ==================== 登录日志API ====================

@wx_bp.route('/admin/login-logs', methods=['GET'])
@token_required
def get_login_logs():
    """获取登录日志（仅管理员）"""
    nickname = request.wx_user['name']
    is_admin, _ = check_admin_status(nickname)

    if not is_admin:
        return jsonify({'success': False, 'error': 'Permission denied'})

    raw_logs = database.read_login_logs()
    logs = []
    for log in raw_logs:
        logs.append({
            'name': log.get('username', ''),
            'ip': log.get('ip_address', ''),
            'location': '',  # 暂时为空，后续可扩展IP归属地查询
            'login_time': log.get('login_time', '')
        })
    return jsonify({
        'success': True,
        'logs': logs
    })


# ==================== 管理员设置API ====================

@wx_bp.route('/admin/students', methods=['GET'])
@token_required
def get_all_students():
    """获取所有学生列表及管理员状态（仅超管）"""
    nickname = request.wx_user['name']
    _, is_super_admin = check_admin_status(nickname)

    if not is_super_admin:
        return jsonify({'success': False, 'error': 'Permission denied'})

    students = database.read_txl()
    result = []
    for s in students:
        result.append({
            'id': s['id'],
            'name': s['name'],
            'is_admin': s.get('is_admin', 0) == 1 or s.get('name') == '穆玉升',
            'is_super_admin': s.get('super_admin', 0) == 1 or s.get('name') == '穆玉升'
        })
    return jsonify({'success': True, 'students': result})


@wx_bp.route('/admin/students/<int:student_id>', methods=['PUT'])
@token_required
def update_student_admin(student_id):
    """更新学生管理员权限（仅超管）"""
    nickname = request.wx_user['name']
    _, is_super_admin = check_admin_status(nickname)

    if not is_super_admin:
        return jsonify({'success': False, 'error': 'Permission denied'})

    data = request.get_json()
    is_admin = data.get('is_admin', False)
    is_super_admin_val = data.get('is_super_admin', False)

    database.update_student_admin(student_id, is_admin, is_super_admin_val)
    return jsonify({'success': True})


# ==================== 媒体管理API ====================

@wx_bp.route('/media/photo/<int:photo_id>', methods=['DELETE'])
@token_required
def delete_photo(photo_id):
    """删除照片（仅所有者或管理员）"""
    nickname = request.wx_user['name']
    is_admin, _ = check_admin_status(nickname)

    photos = database.read_photos()
    photo = None
    for p in photos:
        if p.get('id') == photo_id:
            photo = p
            break

    if not photo:
        return jsonify({'success': False, 'error': 'Photo not found'})

    # 检查权限：所有者或管理员可删除
    if photo.get('owner') != nickname and not is_admin:
        return jsonify({'success': False, 'error': 'Permission denied'})

    database.delete_photo(photo_id)

    # 记录到已删除列表
    deleted_item = {
        'id': database.get_next_deleted_id(),
        'type': 'photo',
        'content': photo.get('filename', ''),
        'owner': photo.get('owner', ''),
        'time': photo.get('time', ''),
        'deleted_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'extra': photo.get('filename', ''),
        'deleted_by': nickname
    }
    deleted_items = database.read_deleted()
    deleted_items.append(deleted_item)
    database.write_deleted(deleted_items)

    return jsonify({'success': True})


@wx_bp.route('/media/video/<int:video_id>', methods=['DELETE'])
@token_required
def delete_video(video_id):
    """删除视频（仅所有者或管理员）"""
    nickname = request.wx_user['name']
    is_admin, _ = check_admin_status(nickname)

    videos = database.read_videos()
    video = None
    for v in videos:
        if v.get('id') == video_id:
            video = v
            break

    if not video:
        return jsonify({'success': False, 'error': 'Video not found'})

    # 检查权限：所有者或管理员可删除
    if video.get('owner') != nickname and not is_admin:
        return jsonify({'success': False, 'error': 'Permission denied'})

    database.delete_video(video_id)

    # 记录到已删除列表
    deleted_item = {
        'id': database.get_next_deleted_id(),
        'type': 'video',
        'content': video.get('title', ''),
        'owner': video.get('owner', ''),
        'time': '',
        'deleted_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'extra': video.get('url', ''),
        'deleted_by': nickname
    }
    deleted_items = database.read_deleted()
    deleted_items.append(deleted_item)
    database.write_deleted(deleted_items)

    return jsonify({'success': True})


# ==================== 留言管理API ====================

@wx_bp.route('/messages/<int:message_id>', methods=['DELETE'])
@token_required
def delete_message(message_id):
    """删除留言（仅所有者或管理员）"""
    nickname = request.wx_user['name']
    is_admin, _ = check_admin_status(nickname)

    messages = database.read_lyb()
    message = None
    for m in messages:
        if m.get('id') == message_id:
            message = m
            break

    if not message:
        return jsonify({'success': False, 'error': 'Message not found'})

    # 检查权限：所有者或管理员可删除
    if message.get('nickname') != nickname and not is_admin:
        return jsonify({'success': False, 'error': 'Permission denied'})

    database.delete_message(message_id)
    return jsonify({'success': True})


@wx_bp.route('/messages/image', methods=['POST'])
@token_required
def upload_message_image():
    """上传留言图片"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file'})

    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'error': 'No file selected'})

    # 保存文件
    import uuid
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
    filename = f"{uuid.uuid4().hex}.{ext}"
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static/imgs/messages')
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    return jsonify({
        'success': True,
        'url': f'/static/imgs/messages/{filename}'
    })


@wx_bp.route('/messages/voice', methods=['POST'])
@token_required
def upload_voice_message():
    """上传语音留言"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file'})

    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'error': 'No file selected'})

    # 保存文件
    import uuid
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'wav'
    filename = f"{uuid.uuid4().hex}.{ext}"
    voice_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static/voice/lyb')
    os.makedirs(voice_dir, exist_ok=True)
    filepath = os.path.join(voice_dir, filename)
    file.save(filepath)

    nickname = request.wx_user['name']

    # 添加语音留言
    message = {
        'id': database.get_next_lyb_id(),
        'nickname': nickname,
        'content': '',
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'image': '',
        'voice': f'/static/voice/lyb/{filename}'
    }

    messages = database.read_lyb()
    messages.append(message)
    database.write_lyb(messages)

    return jsonify({'success': True})


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
