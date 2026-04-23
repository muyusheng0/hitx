"""
统一错误处理
"""

from flask import jsonify


def register_error_handlers(app):
    """注册全局错误处理器"""

    @app.errorhandler(413)
    def request_entity_too_large(e):
        return jsonify({'success': False, 'message': '文件大小超过100MB限制'}), 413

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'success': False, 'message': '页面不存在'}), 404

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({'success': False, 'message': '服务器内部错误'}), 500

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({'success': False, 'message': '未授权'}), 401
