from flask import jsonify, session, request
from blueprints.recycle import recycle_bp
import database
from config import ADMIN_USERS
from datetime import datetime


@recycle_bp.route('/api/get_deleted')
def get_deleted():
    """获取当前用户的已删除项目,管理员可以看到所有删除记录"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    current_name = session['verified_student']['name']
    from decorators import is_admin
    is_admin_user = is_admin(current_name)

    deleted_items = database.read_deleted()
    # 管理员可以看到所有删除记录,其他人只能看到自己的
    if is_admin_user:
        user_items = deleted_items
    else:
        user_items = [item for item in deleted_items if item['owner'] == current_name]

    # 按删除时间倒序
    user_items.sort(key=lambda x: x['deleted_time'], reverse=True)

    # 分页:每页3条
    page = request.args.get('page', 1, type=int)
    per_page = 3
    total = len(user_items)
    start = (page - 1) * per_page
    end = start + per_page
    page_items = user_items[start:end]

    return jsonify({
        'success': True,
        'items': page_items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    })


@recycle_bp.route('/api/restore_deleted', methods=['POST'])
def restore_deleted():
    """恢复已删除的项目"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    data = request.get_json()
    deleted_id = data.get('id')

    if not deleted_id:
        return jsonify({'success': False, 'message': '无效的项目ID'})

    current_name = session['verified_student']['name']
    is_muyusheng = current_name in ADMIN_USERS
    deleted_items = database.read_deleted()

    for i, item in enumerate(deleted_items):
        if str(item['id']) == str(deleted_id):
            # 检查权限
            if not is_muyusheng and item['owner'] != current_name:
                return jsonify({'success': False, 'message': '只能恢复自己的删除记录'})

            item_type = item['type']
            restored = False

            # 根据类型恢复
            if item_type == 'message':
                # 恢复留言
                messages = database.read_lyb()
                messages.append({
                    'id': database.get_next_lyb_id(),
                    'nickname': item['owner'],
                    'content': item['content'],
                    'time': item['time'],
                    'image': item.get('extra', '')
                })
                database.write_lyb(messages)
                restored = True
            elif item_type == 'video':
                # 恢复视频
                videos = database.read_videos()
                videos.append({
                    'id': database.get_next_video_id(),
                    'title': item['content'],
                    'url': item.get('extra', ''),
                    'cover': '',
                    'owner': item['owner']
                })
                database.write_videos(videos)
                restored = True
            elif item_type == 'photo':
                # 恢复照片记录
                photos = database.read_photos()
                photos.append({
                    'id': database.get_next_photo_id(),
                    'filename': item.get('extra', ''),
                    'owner': item['owner'],
                    'time': item.get('time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                })
                database.write_photos(photos)
                restored = True

            if restored:
                # 从删除记录中移除
                deleted_items.pop(i)
                database.write_deleted(deleted_items)
                return jsonify({'success': True, 'message': '恢复成功'})

    return jsonify({'success': False, 'message': '项目不存在'})


@recycle_bp.route('/api/permanent_delete', methods=['POST'])
def permanent_delete():
    """彻底删除项目"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    data = request.get_json()
    deleted_id = data.get('id')

    if not deleted_id:
        return jsonify({'success': False, 'message': '无效的项目ID'})

    current_name = session['verified_student']['name']
    is_muyusheng = current_name in ADMIN_USERS
    deleted_items = database.read_deleted()

    for i, item in enumerate(deleted_items):
        if str(item['id']) == str(deleted_id):
            # 检查权限
            if not is_muyusheng and item['owner'] != current_name:
                return jsonify({'success': False, 'message': '只能删除自己的删除记录'})

            # 从删除记录中彻底删除
            deleted_items.pop(i)
            database.write_deleted(deleted_items)
            return jsonify({'success': True, 'message': '彻底删除成功'})

    return jsonify({'success': False, 'message': '项目不存在'})
