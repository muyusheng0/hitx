"""
活动动态路由
迁移自 app.py
"""

from datetime import datetime
import re
from flask import session, request, jsonify
import database
from decorators import is_admin
from blueprints.activity import activity_bp


def get_activities():
    """获取最新动态(去重:同一人连续同类型动态只保留最新一条)"""
    activities = []

    # 检查生日动态(提前5天开始显示)
    today = datetime.now()
    students = database.read_txl()
    for student in students:
        birthday_str = student.get('birthday', '')
        if birthday_str and len(birthday_str) >= 10:  # YYYY-MM-DD format
            try:
                birthday_month = int(birthday_str[5:7])
                birthday_day = int(birthday_str[8:10])
                # 构建今年的生日日期
                this_year_birthday = datetime(today.year, birthday_month, birthday_day)
                # 如果今年的生日已过但还没到,看明年的
                if this_year_birthday < today and (today - this_year_birthday).days > 5:
                    this_year_birthday = datetime(today.year + 1, birthday_month, birthday_day)
                # 检查是否在5天内
                days_until = (this_year_birthday - today).days
                if 0 <= days_until <= 5:
                    pronoun = '他' if student.get('gender', '') == '男' else '她'
                    if days_until == 0:
                        content = f'🎂 今天{student["name"]}生日!祝{pronoun}生日快乐!'
                    else:
                        content = f'🎂 {student["name"]} {birthday_month}月{birthday_day}日生日,还有{days_until}天,提前祝{pronoun}生日快乐!'
                    activities.append({
                        'type': 'birthday',
                        'actor': student['name'],
                        'content': content,
                        'time': this_year_birthday.strftime('%Y-%m-%d 00:00:00')
                    })
            except:
                pass

    messages = database.read_lyb()

    # 留言动态(取最新10条留言)
    for msg in sorted(messages, key=lambda x: x['time'], reverse=True)[:10]:
        has_voice = bool(msg.get('voice'))
        has_image = bool(msg.get('image'))
        # 根据类型设置内容
        if has_voice and has_image:
            content = '发表了语音留言并附带图片'
            msg_type = 'voice_image'
        elif has_voice:
            content = '发表了语音留言'
            msg_type = 'voice'
        elif has_image:
            content = '发表了新留言,并附带图片'
            msg_type = 'image'
        else:
            content = '发表了新留言'
            msg_type = 'text'
        activities.append({
            'type': 'message',
            'actor': msg['nickname'],
            'content': content,
            'time': msg['time'],
            'msg_id': msg['id'],
            'msg_content': msg['content'][:30],
            'msg_type': msg_type,
            'has_image': has_image,
            'has_voice': has_voice
        })

    # 从活动日志读取(profile_update、photo、video等)
    activity_logs = database.read_activities()
    for log in activity_logs[:20]:
        activity = {
            'type': log['type'],
            'actor': log['actor'],
            'content': log['content'],
            'time': log['time']
        }
        # 照片活动:从内容中提取文件名
        if log['type'] == 'photo':
            match = re.search(r'《(.+?)》', log['content'])
            if match:
                activity['img_name'] = match.group(1)
                activity['img_url'] = f'/static/imgs/messages/{match.group(1)}'
        # 视频活动:从内容中提取标题
        if log['type'] == 'video':
            match = re.search(r'《(.+?)》', log['content'])
            if match:
                activity['video_title'] = match.group(1)
        # 喊话活动:从内容中提取目标人名
        if log['type'] == 'voice_shout':
            match = re.search(r'对(.+?)喊', log['content'])
            if match:
                activity['target_name'] = match.group(1)
        activities.append(activity)

    # 按时间排序
    activities.sort(key=lambda x: x['time'], reverse=True)

    # 合并统计:同一人同类动态合并显示数量
    deduplicated = []
    for activity in activities:
        if not deduplicated:
            activity['count'] = 1
            activity['original_content'] = activity.get('content', '')  # 保存原始内容用于删除
            deduplicated.append(activity)
        else:
            last = deduplicated[-1]
            # 如果当前条目和上一个条目的actor和type都相同,累加计数
            if activity['actor'] == last['actor'] and activity['type'] == last['type']:
                last['count'] = last.get('count', 1) + 1
                # 更新原始内容为最新一条的内容
                last['original_content'] = activity.get('content', '')
            else:
                activity['count'] = 1
                activity['original_content'] = activity.get('content', '')
                deduplicated.append(activity)

    # 修改合并后的显示内容
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


@activity_bp.route('/api/get_unread_activity_count')
def get_unread_activity_count():
    """获取未读活动数量"""
    activities = get_activities()
    nickname = session.get('verified_student', {}).get('name', '') if 'verified_student' in session else ''
    if not nickname:
        return jsonify({'success': True, 'count': 0})
    count = database.get_unread_activity_count(nickname, activities)
    return jsonify({'success': True, 'count': count})


@activity_bp.route('/api/get_activities')
def api_get_activities():
    """获取所有动态(用于管理,分页)"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    page = int(request.args.get('page', 1))
    per_page = 3
    max_items = 30  # 最多显示30条
    activities = get_activities()[:max_items]

    total = len(activities)
    total_pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page

    return jsonify({
        'success': True,
        'activities': activities[start:end],
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages
    })


@activity_bp.route('/api/mark_activities_viewed', methods=['POST'])
def mark_activities_viewed():
    """标记活动为已浏览"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    nickname = session['verified_student']['name']
    activities = get_activities()
    database.mark_activities_viewed(nickname, activities)
    return jsonify({'success': True})


@activity_bp.route('/api/delete_activity', methods=['POST'])
def delete_activity():
    """删除动态(仅管理员)"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    current_name = session['verified_student']['name']

    # 只有管理员可以删除动态
    if not is_admin(current_name):
        return jsonify({'success': False, 'message': '只有管理员可以删除动态'})

    data = request.get_json()
    activity_time = data.get('time')
    activity_actor = data.get('actor')
    activity_type = data.get('type', 'message')
    activity_content = data.get('original_content') or data.get('content')

    if not activity_time or not activity_actor:
        return jsonify({'success': False, 'message': '参数不完整'})

    try:
        # 如果是留言动态,同时删除messages表中的记录
        if activity_type == 'message':
            database.delete_message_by_time_nickname(activity_time, activity_actor)
        database.delete_activity(activity_time, activity_actor, activity_content)
        return jsonify({'success': True, 'message': '删除成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})
