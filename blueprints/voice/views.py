from flask import request, jsonify, session
import os
import uuid
from datetime import datetime

from database import database
from config import DATA_DIR
from blueprints.voice import voice_bp


@voice_bp.route('/api/add_voice_message', methods=['POST'])
def add_voice_message():
    """添加语音留言"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '没有音频文件'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '没有选择文件'})

    nickname = session['verified_student']['name']

    # 保存音频文件
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'wav'
    filename = f"{uuid.uuid4().hex}.{ext}"
    voice_dir = os.path.join(DATA_DIR, 'static/voice/lyb')
    os.makedirs(voice_dir, exist_ok=True)
    filepath = os.path.join(voice_dir, filename)
    file.save(filepath)

    voice_url = f'/static/voice/lyb/{filename}'

    message = {
        'id': database.get_next_lyb_id(),
        'nickname': nickname,
        'content': '[语音留言]',
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'image': '',
        'voice': voice_url
    }

    messages = database.read_lyb()
    messages.append(message)
    database.write_lyb(messages)

    # 记录活动日志
    database.write_activity(nickname, 'message', '发表了语音留言')

    return jsonify({'success': True, 'message': message})


@voice_bp.route('/api/upload_voice_shout', methods=['POST'])
def upload_voice_shout():
    """上传喊话音频"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先验证身份'})

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '没有音频文件'})

    if 'to_name' not in request.form:
        return jsonify({'success': False, 'message': '缺少目标用户'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '没有选择文件'})

    from_name = session['verified_student']['name']
    to_name = request.form['to_name']

    # 不能对自己喊话
    if from_name == to_name:
        return jsonify({'success': False, 'message': '不能对自己喊话'})

    # 保存音频文件
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'wav'
    filename = f"{uuid.uuid4().hex}.{ext}"
    voice_dir = os.path.join(DATA_DIR, 'static/voice')
    os.makedirs(voice_dir, exist_ok=True)
    filepath = os.path.join(voice_dir, filename)
    file.save(filepath)

    # 记录到数据库
    audio_url = f'/static/voice/{filename}'
    shout_id = database.add_voice_shout(from_name, to_name, audio_url)
    database.write_activity(from_name, 'voice_shout', f'对{to_name}喊了一段话')

    # 发送通知
    database.create_notification(
        recipient=to_name,
        sender=from_name,
        notif_type='voice_shout',
        ref_id=shout_id,
        content=f'{from_name}对你喊了一段话,快去听听吧!',
        target_name=to_name
    )

    return jsonify({
        'success': True,
        'message': '喊话成功',
        'id': shout_id,
        'url': audio_url
    })


@voice_bp.route('/api/get_voice_shouts/<target_name>')
def get_voice_shouts(target_name):
    """获取某人的喊话"""
    shouts = database.get_voice_shouts_by_target(target_name)
    return jsonify({'success': True, 'shouts': shouts})


@voice_bp.route('/api/voice_shout/delete', methods=['POST'])
def delete_voice_shout():
    """删除喊话"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先验证身份'})
    data = request.get_json()
    shout_id = data.get('id')
    if not shout_id:
        return jsonify({'success': False, 'message': '缺少喊话ID'})
    user_name = session['verified_student']['name']
    success, msg = database.delete_voice_shout(shout_id, user_name)
    return jsonify({'success': success, 'message': msg})


@voice_bp.route('/api/voice_shout/restore', methods=['POST'])
def restore_voice_shout():
    """恢复喊话"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先验证身份'})
    data = request.get_json()
    shout_id = data.get('id')
    if not shout_id:
        return jsonify({'success': False, 'message': '缺少喊话ID'})
    user_name = session['verified_student']['name']
    success, msg = database.restore_voice_shout(shout_id, user_name)
    return jsonify({'success': success, 'message': msg})
