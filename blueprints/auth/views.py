"""
认证/用户管理 路由
迁移自 app.py
"""

from datetime import datetime, timedelta

from flask import jsonify, session, request

import database
from utils import get_real_ip, sanitize_input
from decorators import is_admin, is_super_admin

from blueprints.auth import auth_bp


@auth_bp.route('/api/verify', methods=['POST'])
def verify_student():
    """验证同学身份(姓名+学号+验证码+登录密码)"""
    data = request.get_json()
    name = sanitize_input(data.get('name', ''))
    student_id = sanitize_input(data.get('student_id', ''))
    captcha = data.get('captcha', '')
    login_password = data.get('login_password', '')

    # 验证验证码
    if 'captcha' not in session or 'captcha_time' not in session:
        return jsonify({'success': False, 'message': '请先获取验证码'})
    captcha_time = datetime.fromisoformat(session['captcha_time'])
    if datetime.now() - captcha_time > timedelta(minutes=5):
        return jsonify({'success': False, 'message': '验证码已过期,请刷新'})
    if captcha != session['captcha']:
        return jsonify({'success': False, 'message': '验证码不正确'})

    students = database.read_txl()
    for s in students:
        if s['name'] == name and s['id'] == student_id:
            # 检查是否设置了登录密码
            if s.get('login_password'):
                # 需要验证登录密码
                if not login_password:
                    return jsonify({'success': False, 'message': 'password_required', 'prompt': '请输入登录密码'})
                # 验证登录密码
                if s['login_password'] != login_password:
                    return jsonify({'success': False, 'message': '登录密码错误'})
            session['verified_student'] = {
                'name': name,
                'id': student_id,
                'coords': s.get('coords', ''),
                'hometown_name': s.get('hometown_name', ''),
                'city': s.get('city', '')
            }
            session['verify_time'] = datetime.now().isoformat()
            # 清除验证码
            session.pop('captcha', None)
            session.pop('captcha_time', None)
            # 记录登录日志
            ip = get_real_ip(request)
            ua = request.headers.get('User-Agent', '')[:200]
            database.write_login_log(name, ip, ua)
            return jsonify({'success': True, 'message': '验证成功'})

    return jsonify({'success': False, 'message': '姓名或学号不正确'})


@auth_bp.route('/api/logout')
def logout():
    """退出验证"""
    session.pop('verified_student', None)
    session.pop('verify_time', None)
    return jsonify({'success': True})


@auth_bp.route('/api/check_verify')
def check_verify():
    """检查是否已验证"""
    if 'verified_student' in session:
        verify_time = datetime.fromisoformat(session['verify_time'])
        if datetime.now() - verify_time < timedelta(minutes=30):
            current_name = session['verified_student']['name']
            student = session['verified_student'].copy()
            student['is_admin'] = is_admin(current_name)
            student['is_super_admin'] = is_super_admin(current_name)
            # 检查用户密码状态和头像
            students = database.read_txl()
            for s in students:
                if s['name'] == current_name:
                    student['login_password_set'] = bool(s.get('login_password', ''))
                    student['avatar'] = s.get('avatar', '')
                    break
            return jsonify({'verified': True, 'student': student})
    return jsonify({'verified': False})


@auth_bp.route('/api/user/set_password', methods=['POST'])
def admin_set_password():
    """设置管理员密码"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    current_name = session['verified_student']['name']
    if not is_admin(current_name):
        return jsonify({'success': False, 'message': '无权限'})
    data = request.get_json()
    password = data.get('password', '')
    if not password:
        return jsonify({'success': False, 'message': '密码不能为空'})
    students = database.read_txl()
    for s in students:
        if s['name'] == current_name:
            s['login_password'] = password
            break
    database.write_txl(students)
    return jsonify({'success': True, 'message': '密码设置成功'})


@auth_bp.route('/api/check_user_login_password', methods=['POST'])
def check_user_login_password():
    """检查用户是否设置了登录密码"""
    data = request.get_json()
    name = data.get('name', '')
    student_id = data.get('student_id', '')
    if not name or not student_id:
        return jsonify({'has_password': False})

    students = database.read_txl()
    for s in students:
        if s.get('name') == name and str(s.get('id')) == str(student_id):
            return jsonify({'has_password': bool(s.get('login_password'))})
    return jsonify({'has_password': False})


@auth_bp.route('/api/user/verify_password', methods=['POST'])
def admin_verify_password():
    """验证管理员密码"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    current_name = session['verified_student']['name']
    if not is_admin(current_name):
        return jsonify({'success': False, 'message': '无权限'})
    data = request.get_json()
    password = data.get('password', '')
    students = database.read_txl()
    for s in students:
        if s['name'] == current_name:
            if s.get('login_password', '') == password:
                session['password_verified'] = True
                return jsonify({'success': True, 'message': '验证成功'})
            else:
                return jsonify({'success': False, 'message': '密码错误'})
            break
    return jsonify({'success': False, 'message': '用户不存在'})


@auth_bp.route('/api/user/check_password_verified')
def admin_check_password_verified():
    """检查管理员密码是否已验证"""
    if 'verified_student' not in session:
        return jsonify({'verified': False})
    current_name = session['verified_student']['name']
    if not is_admin(current_name):
        return jsonify({'verified': False})
    return jsonify({'verified': session.get('password_verified', False)})


@auth_bp.route('/api/user/get_password_prompt', methods=['GET'])
def get_password_prompt():
    """获取是否不再提示设置密码"""
    if 'verified_student' not in session:
        return jsonify({'success': False})
    current_name = session['verified_student']['name']
    students = database.read_txl()
    for s in students:
        if s['name'] == current_name:
            return jsonify({'success': True, 'no_prompt': bool(s.get('no_password_prompt', 0))})
    return jsonify({'success': False})


@auth_bp.route('/api/user/set_password_prompt', methods=['POST'])
def set_password_prompt():
    """设置不再提示设置密码"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    current_name = session['verified_student']['name']
    data = request.get_json()
    no_prompt = data.get('no_prompt', True)
    students = database.read_txl()
    for s in students:
        if s['name'] == current_name:
            s['no_password_prompt'] = 1 if no_prompt else 0
            break
    database.write_txl(students)
    return jsonify({'success': True})


@auth_bp.route('/api/super_admin/set_admin', methods=['POST'])
def set_admin():
    """设置用户为管理员(仅超级管理员可操作)"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    current_name = session['verified_student']['name']
    if not is_super_admin(current_name):
        return jsonify({'success': False, 'message': '无权限'})
    data = request.get_json()
    target_name = data.get('name', '')
    is_admin_flag = data.get('is_admin', False)
    if not target_name:
        return jsonify({'success': False, 'message': '无效的用户名'})
    students = database.read_txl()
    for s in students:
        if s['name'] == target_name:
            s['is_admin'] = 1 if is_admin_flag else 0
            break
    database.write_txl(students)
    return jsonify({'success': True, 'message': '设置成功'})
