"""
地区数据加载模块 + 省份拼音映射
从 static/js/location/*.json 加载省市区数据
"""

import os
import json

# ==================== 省份拼音映射 ====================

PROVINCE_MAP = {
    'beijing': '北京',
    'shanghai': '上海',
    'tianjin': '天津',
    'chongqing': '重庆',
    'guangdong': '广东',
    'jiangsu': '江苏',
    'zhejiang': '浙江',
    'sichuan': '四川',
    'hubei': '湖北',
    'hunan': '湖南',
    'henan': '河南',
    'shandong': '山东',
    'hebei': '河北',
    'shaanxi': '陕西',
    'liaoning': '辽宁',
    'jilin': '吉林',
    'heilongjiang': '黑龙江',
    'neimenggu': '内蒙古',
    'xinjiang': '新疆',
    'gansu': '甘肃',
    'qinghai': '青海',
    'ningxia': '宁夏',
    'shanxi': '山西',
    'anhui': '安徽',
    'fujian': '福建',
    'jiangxi': '江西',
    'guangxi': '广西',
    'hainan': '海南',
    'yunnan': '云南',
    'guizhou': '贵州',
    'xizang': '西藏',
    'taiwan': '台湾',
    'xianggang': '香港',
    'aomen': '澳门'
}

NAME_TO_PROVINCE_PINYIN = {v: k for k, v in PROVINCE_MAP.items()}

# ==================== 地区数据 ====================

LOCATION_DATA = {
    'provinces': [],
    'cities': {},
    'districts': {}
}

PROVINCE_NAME_TO_CODE = {}
PROVINCE_CODE_TO_NAME = {}
CITY_NAME_TO_CODE = {}
CITY_CODE_TO_NAME = {}
CITY_CODE_PREFIX_TO_CODE = {}  # (province_prefix, city_suffix) -> full_city_code

_location_loaded = False


def _strip_province_suffix(name):
    """去掉省份名称的后缀（省、市、自治区、特别行政区）"""
    if not name:
        return name
    for suffix in ['特别行政区', '自治区', '省', '市']:
        if name.endswith(suffix):
            return name[:-len(suffix)]
    return name


def _load_location_data():
    """加载地区数据到内存（幂等，只加载一次）"""
    global _location_loaded
    if _location_loaded:
        return

    base_path = os.path.join(os.path.dirname(__file__), 'static/js/location')

    # 加载省份
    with open(os.path.join(base_path, 'province.json'), encoding='utf-8') as f:
        provinces = json.load(f)
    LOCATION_DATA['provinces'] = [{'code': p['code'], 'name': p['name']} for p in provinces]
    for p in provinces:
        PROVINCE_NAME_TO_CODE[p['name']] = p['code']
        PROVINCE_CODE_TO_NAME[p['code']] = p['name']
        short_name = _strip_province_suffix(p['name'])
        if short_name != p['name']:
            PROVINCE_NAME_TO_CODE[short_name] = p['code']

    # 加载城市
    with open(os.path.join(base_path, 'city.json'), encoding='utf-8') as f:
        cities = json.load(f)
    for city in cities:
        prov = city['province']
        full_code = city['code']
        if prov not in LOCATION_DATA['cities']:
            LOCATION_DATA['cities'][prov] = []
        LOCATION_DATA['cities'][prov].append({'code': full_code, 'name': city['name']})
        CITY_NAME_TO_CODE[city['name']] = full_code
        CITY_CODE_TO_NAME[full_code] = city['name']
        prov_prefix = prov
        city_suffix = city['city']
        CITY_CODE_PREFIX_TO_CODE[(prov_prefix, city_suffix)] = full_code

    # 加载区县
    with open(os.path.join(base_path, 'area.json'), encoding='utf-8') as f:
        areas = json.load(f)
    for area in areas:
        prov = area['province']
        city_short = area['city']
        full_city_code = CITY_CODE_PREFIX_TO_CODE.get((prov, city_short))
        if full_city_code:
            if full_city_code not in LOCATION_DATA['districts']:
                LOCATION_DATA['districts'][full_city_code] = []
            LOCATION_DATA['districts'][full_city_code].append({'code': area['code'], 'name': area['name']})
        else:
            prov_full_code = prov + '0000'
            if prov_full_code not in LOCATION_DATA['districts']:
                LOCATION_DATA['districts'][prov_full_code] = []
            LOCATION_DATA['districts'][prov_full_code].append({'code': area['code'], 'name': area['name']})

    _location_loaded = True


def get_location_names(province_code, city_code, district_code):
    """将地区代码转换为存储格式"""
    result = {
        'hometown': '',
        'hometown_name': '',
        'city': '',
        'district': ''
    }

    if province_code:
        full_name = PROVINCE_CODE_TO_NAME.get(province_code, '')
        result['hometown_name'] = full_name
        short_name = _strip_province_suffix(full_name)
        # 从 app.py 的 PROVINCE_MAP 查找拼音（这里只提供中文名，拼音映射保留在 app.py）
        result['hometown'] = ''

    if city_code:
        result['city'] = CITY_CODE_TO_NAME.get(city_code, '')

    if district_code:
        for city_key, districts in LOCATION_DATA['districts'].items():
            for d in districts:
                if d['code'] == district_code:
                    result['district'] = d['name']
                    break
            if result['district']:
                break

    return result


# 启动时加载
_load_location_data()
