"""
地理位置路由
迁移自 app.py
"""

import os

from flask import jsonify, request, session

import database
from config import ADMIN_USERS
from location_data import (
    LOCATION_DATA,
    PROVINCE_NAME_TO_CODE,
    PROVINCE_CODE_TO_NAME,
    CITY_NAME_TO_CODE,
    CITY_CODE_TO_NAME,
    NAME_TO_PROVINCE_PINYIN,
    _strip_province_suffix,
)

from blueprints.location import location_bp


def _get_location_names(province_code, city_code, district_code):
    """将地区代码转换为存储格式（hometown用拼音，city/district用中文名）"""
    result = {
        'hometown': '',
        'hometown_name': '',
        'city': '',
        'district': ''
    }

    if province_code:
        full_name = PROVINCE_CODE_TO_NAME.get(province_code, '')
        result['hometown_name'] = full_name
        # 去掉后缀后查找拼音
        short_name = _strip_province_suffix(full_name)
        result['hometown'] = NAME_TO_PROVINCE_PINYIN.get(short_name, '')
        # 如果还是找不到，尝试直接查找
        if not result['hometown']:
            result['hometown'] = NAME_TO_PROVINCE_PINYIN.get(full_name, '')

    if city_code:
        result['city'] = CITY_CODE_TO_NAME.get(city_code, '')

    if district_code:
        # 在区县字典中查找
        for city_key, districts in LOCATION_DATA['districts'].items():
            for d in districts:
                if d['code'] == district_code:
                    result['district'] = d['name']
                    break
            if result['district']:
                break

    return result


@location_bp.route('/api/location/codes_to_names')
def codes_to_names():
    """将地区代码转换为存储格式，用于保存用户数据"""
    province_code = request.args.get('province', '')
    city_code = request.args.get('city', '')
    district_code = request.args.get('district', '')

    result = _get_location_names(province_code, city_code, district_code)
    return jsonify({'success': True, 'data': result})


@location_bp.route('/api/location/provinces')
def get_provinces():
    """获取所有省份"""
    return jsonify({'success': True, 'data': LOCATION_DATA['provinces']})


@location_bp.route('/api/location/cities/<province_code>')
def get_cities(province_code):
    """获取指定省份的所有城市"""
    # 省份代码的前两位作为城市字典的键
    prov_prefix = province_code[:2] if len(province_code) >= 2 else province_code
    cities = LOCATION_DATA['cities'].get(prov_prefix, [])
    return jsonify({'success': True, 'data': cities})


@location_bp.route('/api/location/districts/<city_code>')
def get_districts(city_code):
    """获取指定城市的所有区县"""
    districts = LOCATION_DATA['districts'].get(city_code, [])
    return jsonify({'success': True, 'data': districts})


@location_bp.route('/api/location/lookup')
def lookup_location():
    """根据名称查找省/市/区的代码，用于回填用户数据"""
    province_name = request.args.get('province', '')
    city_name = request.args.get('city', '')
    district_name = request.args.get('district', '')

    result = {'province_code': '', 'city_code': '', 'district_code': ''}

    if province_name:
        # 尝试直接查找
        result['province_code'] = PROVINCE_NAME_TO_CODE.get(province_name, '')
        # 如果没找到，尝试去掉后缀
        if not result['province_code']:
            short_name = _strip_province_suffix(province_name)
            result['province_code'] = PROVINCE_NAME_TO_CODE.get(short_name, '')

    if city_name:
        prov_code = result['province_code']
        # 先在city.json中查找该省份下的城市
        if prov_code and prov_code in LOCATION_DATA['cities']:
            cities = LOCATION_DATA['cities'][prov_code]
            for c in cities:
                if c['name'] == city_name:
                    result['city_code'] = c['code']
                    break
            # 如果没找到，尝试去掉"市"后缀
            if not result['city_code'] and city_name.endswith('市'):
                short_city = city_name[:-1]
                for c in cities:
                    if c['name'] == short_city or c['name'].startswith(short_city):
                        result['city_code'] = c['code']
                        break

        # 如果没找到，尝试在整个city.json中查找（可能有重名城市）
        if not result['city_code']:
            for code, name in CITY_NAME_TO_CODE.items():
                if name == city_name:
                    result['city_code'] = code
                    break
            # 尝试去掉"市"后缀
            if not result['city_code'] and city_name.endswith('市'):
                short_city = city_name[:-1]
                for code, name in CITY_NAME_TO_CODE.items():
                    if name == short_city or name.startswith(short_city):
                        result['city_code'] = code
                        break

    # 处理区县查找（关键：区县按城市代码存储，需要找到正确的城市代码）
    if district_name:
        prov_code = result['province_code']

        # 如果已经有city_code，先尝试直接查找
        if result['city_code'] and result['city_code'] in LOCATION_DATA['districts']:
            districts = LOCATION_DATA['districts'][result['city_code']]
            for d in districts:
                if d['name'] == district_name:
                    result['district_code'] = d['code']
                    break

        # 如果没找到，在该省份所有区县中查找
        if not result['district_code'] and prov_code:
            # 遍历所有城市，查找该省份下的区县
            for city_code, district_list in LOCATION_DATA['districts'].items():
                if not city_code.startswith(prov_code[:2]):
                    continue
                for d in district_list:
                    if d['name'] == district_name:
                        result['district_code'] = d['code']
                        # 同时设置city_code
                        result['city_code'] = city_code
                        break
                if result['district_code']:
                    break

    return jsonify({'success': True, 'data': result})


@location_bp.route('/api/update_coords', methods=['POST'])
def update_coords():
    """批量更新所有学生的坐标(根据城市名)"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    current_name = session['verified_student']['name']
    if current_name not in ADMIN_USERS:
        return jsonify({'success': False, 'message': '只有穆玉升可以执行此操作'})

    students = database.read_txl()
    updated_count = 0

    for s in students:
        city = s.get('city', '') or s.get('hometown_name', '')
        district = s.get('district', '')
        if city and not s.get('coords'):
            coords = database.get_coords_by_city(city, district)
            if coords:
                s['coords'] = coords
                updated_count += 1

    database.write_txl(students)

    return jsonify({'success': True, 'message': f'已更新 {updated_count} 位同学的坐标'})


@location_bp.route('/api/update_gps_coords', methods=['POST'])
def update_gps_coords():
    """更新当前用户的GPS坐标"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    data = request.get_json()
    gps_coords = data.get('gps_coords', '')

    if not gps_coords:
        return jsonify({'success': False, 'message': '坐标不能为空'})

    # 验证坐标格式
    try:
        lat, lon = map(float, gps_coords.split(','))
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return jsonify({'success': False, 'message': '坐标格式不正确'})
    except:
        return jsonify({'success': False, 'message': '坐标格式不正确'})

    current_name = session['verified_student']['name']
    current_id = session['verified_student']['id']

    success = database.update_student_gps_coords(current_name, current_id, gps_coords)

    if success:
        # 更新session中的坐标信息
        session['verified_student']['coords'] = gps_coords
        session['verified_student']['gps_coords'] = gps_coords
        session.modified = True
        return jsonify({'success': True, 'message': 'GPS坐标已更新'})
    else:
        return jsonify({'success': False, 'message': '更新失败'})
