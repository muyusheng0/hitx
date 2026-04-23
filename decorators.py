"""
通用装饰器
"""

from flask import session, redirect, request
import database

from config import ADMIN_USERS
from utils import is_public_path


def is_admin(name):
    """检查用户是否为管理员"""
    if name in ADMIN_USERS:
        return True
    students = database.read_txl()
    for s in students:
        if s.get('name') == name and s.get('is_admin'):
            return True
    return False


def is_super_admin(name):
    """检查用户是否为超级管理员"""
    if name not in ADMIN_USERS:
        return False
    students = database.read_txl()
    for s in students:
        if s.get('name') == name:
            return bool(s.get('super_admin'))
    return False


def is_password_verified():
    """检查当前用户是否已验证密码"""
    if 'verified_student' not in session:
        return False
    return session.get('password_verified', False)


def require_login(app):
    """注册登录检查 before_request 钩子"""
    @app.before_request
    def _require_login():
        if 'verified_student' not in session and not is_public_path(request.path):
            redirect_url = request.path
            if request.query_string:
                redirect_url += '?' + request.query_string.decode('utf-8')
            return redirect(f'/login?redirect={redirect_url}')
