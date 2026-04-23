"""
测试 /api/stats 端点
"""

import json


class TestStatsEndpoint:
    """GET /api/stats 公开统计数据接口测试"""

    def test_stats_returns_200(self, client):
        """状态码 200"""
        rv = client.get('/api/stats')
        assert rv.status_code == 200

    def test_stats_returns_json(self, client):
        """Content-Type 是 application/json"""
        rv = client.get('/api/stats')
        assert 'application/json' in rv.content_type

    def test_stats_has_required_keys(self, client):
        """返回包含 students, messages, photos 三个 key"""
        rv = client.get('/api/stats')
        data = rv.get_json()
        assert 'students' in data
        assert 'messages' in data
        assert 'photos' in data

    def test_stats_values_are_integers(self, client):
        """所有值都是整数"""
        rv = client.get('/api/stats')
        data = rv.get_json()
        assert isinstance(data['students'], int)
        assert isinstance(data['messages'], int)
        assert isinstance(data['photos'], int)

    def test_stats_values_non_negative(self, client):
        """计数值非负"""
        rv = client.get('/api/stats')
        data = rv.get_json()
        assert data['students'] >= 0
        assert data['messages'] >= 0
        assert data['photos'] >= 0

    def test_stats_no_auth_required(self, client):
        """不需要登录/认证"""
        rv = client.get('/api/stats')
        assert rv.status_code == 200
        # 不需要任何 cookie 或 token
        rv2 = client.get('/api/stats', headers={'Cookie': ''})
        assert rv2.status_code == 200
