from flask import jsonify, session
from blueprints.txl import txl_bp
import database
from decorators import is_admin, is_super_admin


@txl_bp.route('/api/txl/list')
def txl_list():
    """获取通讯录列表(仅已验证用户)"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    students = database.read_txl()
    result = []
    for s in students:
        result.append({
            'name': s.get('name', ''),
            'is_admin': bool(s.get('is_admin', 0)) or s.get('name', '') in ADMIN_USERS,
            'super_admin': bool(s.get('super_admin', 0))
        })
    return jsonify({'success': True, 'students': result})


@txl_bp.route('/api/txl/map')
def txl_map():
    """获取通讯录地图数据(仅已验证用户)"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    students = database.read_txl()
    points = []
    for s in students:
        coords = s.get('gps_coords', '') or s.get('coords', '')
        if not coords:
            city = s.get('city', '') or s.get('hometown_name', '')
            district = s.get('district', '')
            if city:
                coords = database.get_coords_by_city(city, district)
        if coords:
            try:
                lat, lon = map(float, coords.split(','))
                points.append({
                    'name': s.get('name', ''),
                    'lat': lat,
                    'lon': lon,
                    'city': s.get('city', '') or s.get('hometown_name', ''),
                    'position': s.get('position', ''),
                    'company': s.get('company', ''),
                    'phone': s.get('phone', ''),
                })
            except (ValueError, AttributeError):
                pass

    # 获取当前用户坐标
    user_coords = None
    current_name = session['verified_student']['name']
    for s in students:
        if s.get('name') == current_name:
            user_coords = s.get('gps_coords', '') or s.get('coords', '')
            break

    return jsonify({'success': True, 'data': points, 'user_coords': user_coords})


@txl_bp.route('/api/get_student', methods=['POST'])
def get_student():
    """获取已验证同学的信息"""
    if 'verified_student' not in session:
        return jsonify({'success': False})

    students = database.read_txl()
    current_name = session['verified_student']['name']
    current_id = session['verified_student']['id']

    for s in students:
        if s['name'] == current_name and str(s['id']) == str(current_id):
            s['is_admin'] = is_admin(current_name)
            s['is_super_admin'] = is_super_admin(current_name)
            return jsonify({'success': True, 'student': s})

    return jsonify({'success': False})
