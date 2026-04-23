from flask import request, jsonify, session
from blueprints.notification import notification_bp
import database


@notification_bp.route('/api/notifications')
def get_notifications():
    """获取当前用户通知列表"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    nickname = session['verified_student']['name']
    notifications = database.get_notifications(nickname)
    return jsonify({'success': True, 'notifications': notifications})


@notification_bp.route('/api/notifications/count')
def get_notification_count():
    """获取未读通知数量"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    nickname = session['verified_student']['name']
    count = database.get_unread_notification_count(nickname)
    return jsonify({'success': True, 'count': count})


@notification_bp.route('/api/notifications/mark_read', methods=['POST'])
def mark_notifications_read():
    """标记通知为已读"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    data = request.get_json()
    nickname = session['verified_student']['name']
    notification_id = data.get('id')
    if notification_id:
        database.mark_notification_read(notification_id, nickname)
    else:
        database.mark_all_notifications_read(nickname)
    return jsonify({'success': True})
