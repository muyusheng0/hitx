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
    result = []
    for m in messages:
        result.append({
            'id': m['id'],
            'nickname': m['nickname'],
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
    data = request.get_json()
    content = data.get('content', '').strip()

    if not content:
        return jsonify({'success': False, 'error': 'Empty content'})

    if len(content) > 500:
        return jsonify({'success': False, 'error': 'Content too long'})

    nickname = request.wx_user['name']

    message = {
        'id': database.get_next_lyb_id(),
        'nickname': nickname,
        'content': content,
        'time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'image': '',
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
            return jsonify({'success': True, 'profile': dict(s)})
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
            allowed_fields = ['phone', 'wechat', 'qq', 'email', 'work', 'position',
                             'hobby', 'dream', 'company', 'industry']
            for field in allowed_fields:
                if field in data:
                    s[field] = data[field]

            database.write_txl(students)
            return jsonify({'success': True})

    return jsonify({'success': False, 'error': 'Profile not found'})


# ==================== 评论API ====================

@wx_bp.route('/comments/<int:message_id>', methods=['GET'])
@token_required
def get_comments(message_id):
    """获取某留言的所有评论"""
    comments = database.get_comments_by_message(message_id)
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