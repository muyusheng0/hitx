"""
留言、评论、点赞 路由
迁移自 app.py
"""

from datetime import datetime

from flask import jsonify, request, session

import database
from utils import sanitize_input
from decorators import is_admin

from blueprints.message import message_bp


@message_bp.route('/api/add_message', methods=['POST'])
def add_message():
    """添加留言"""
    data = request.get_json()
    content = sanitize_input(data.get('content', ''))
    image = data.get('image', '')

    # 优先使用真实姓名(已登录),否则使用昵称
    if 'verified_student' in session:
        nickname = session['verified_student']['name']
    else:
        nickname = sanitize_input(data.get('nickname', '穆玉升'))

    if not content:
        return jsonify({'success': False, 'message': '留言内容不能为空'})

    if len(content) > 500:
        return jsonify({'success': False, 'message': '留言内容过长'})

    message = {
        'id': database.get_next_lyb_id(),
        'nickname': nickname[:50],
        'content': content[:500],
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'image': image,
        'voice': ''
    }

    messages = database.read_lyb()
    messages.append(message)
    database.write_lyb(messages)

    # 记录活动日志
    database.write_activity(nickname, 'message', content[:50])

    return jsonify({'success': True, 'message': message})


@message_bp.route('/api/add_comment', methods=['POST'])
def add_comment():
    """添加评论"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    data = request.get_json()
    message_id = data.get('message_id')
    content = sanitize_input(data.get('content', ''))
    if not message_id or not content:
        return jsonify({'success': False, 'message': '参数错误'})
    nickname = session['verified_student']['name']
    comment_id = database.add_comment(message_id, nickname, content)

    # 获取留言主人并发送通知
    messages = database.read_lyb()
    for msg in messages:
        if str(msg['id']) == str(message_id):
            msg_owner = msg.get('nickname', '')
            if msg_owner and msg_owner != nickname:
                content_preview = content[:50] + '...' if len(content) > 50 else content
                database.create_notification(
                    recipient=msg_owner,
                    sender=nickname,
                    notif_type='comment',
                    ref_id=message_id,
                    content=f'{nickname}评论了你的留言:{content_preview}'
                )
            break

    return jsonify({'success': True, 'id': comment_id, 'nickname': nickname, 'content': content, 'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})


@message_bp.route('/api/get_comments/<int:message_id>')
def get_comments(message_id):
    """获取留言的评论"""
    comments = database.get_comments_by_message(message_id)
    return jsonify({'success': True, 'comments': comments})


@message_bp.route('/api/delete_comment', methods=['POST'])
def delete_comment():
    """删除评论"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    data = request.get_json()
    comment_id = data.get('id')
    message_id = data.get('message_id')

    if not comment_id:
        return jsonify({'success': False, 'message': '无效的评论ID'})

    current_name = session['verified_student']['name']

    # 获取评论信息
    comments = database.get_comments_by_message(message_id)
    comment = None
    for c in comments:
        if str(c['id']) == str(comment_id):
            comment = c
            break

    if not comment:
        return jsonify({'success': False, 'message': '评论不存在'})

    # 检查权限:评论人或楼主可以删除,管理员可以删除任何评论
    if not is_admin(current_name) and comment['nickname'] != current_name:
        # 获取留言信息检查是否是楼主
        messages = database.read_lyb()
        is_owner = False
        for msg in messages:
            if str(msg['id']) == str(message_id) and msg['nickname'] == current_name:
                is_owner = True
                break
        if not is_owner:
            return jsonify({'success': False, 'message': '无权限删除该评论'})

    # 记录到已删除列表
    deleted_item = {
        'id': database.get_next_deleted_id(),
        'type': 'comment',
        'content': comment.get('content', '')[:100],
        'owner': comment['nickname'],
        'time': comment.get('time', ''),
        'deleted_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'extra': ''
    }
    deleted_items = database.read_deleted()
    deleted_items.append(deleted_item)
    database.write_deleted(deleted_items)

    # 删除评论
    database.delete_comment(comment_id)
    return jsonify({'success': True, 'message': '删除成功'})


@message_bp.route('/api/like_message', methods=['POST'])
def like_message():
    """点赞留言"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    data = request.get_json()
    message_id = data.get('message_id')
    if not message_id:
        return jsonify({'success': False, 'message': '参数错误'})
    nickname = session['verified_student']['name']
    success = database.like_message(message_id, nickname)
    count = database.get_message_likes(message_id)

    # 发送通知(仅当点赞成功且不是给自己点赞)
    if success:
        messages = database.read_lyb()
        for msg in messages:
            if str(msg['id']) == str(message_id):
                msg_owner = msg.get('nickname', '')
                if msg_owner and msg_owner != nickname:
                    database.create_notification(
                        recipient=msg_owner,
                        sender=nickname,
                        notif_type='like',
                        ref_id=message_id,
                        content=f'{nickname}点赞了你的留言'
                    )
                break

    return jsonify({'success': success, 'liked': success, 'count': count})


@message_bp.route('/api/unlike_message', methods=['POST'])
def unlike_message():
    """取消点赞"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    data = request.get_json()
    message_id = data.get('message_id')
    if not message_id:
        return jsonify({'success': False, 'message': '参数错误'})
    nickname = session['verified_student']['name']
    success = database.unlike_message(message_id, nickname)
    count = database.get_message_likes(message_id)
    return jsonify({'success': success, 'liked': not success, 'count': count})


@message_bp.route('/api/get_message_likes/<int:message_id>')
def get_message_likes(message_id):
    """获取留言点赞信息"""
    count = database.get_message_likes(message_id)
    has_liked = False
    if 'verified_student' in session:
        nickname = session['verified_student']['name']
        has_liked = database.has_liked_message(message_id, nickname)
    return jsonify({'success': True, 'count': count, 'has_liked': has_liked})
