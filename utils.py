"""
通用工具函数
"""

import os
import re
from datetime import datetime

from config import (
    AVATAR_MAX_SIZE, IMAGE_MAX_SIZE, IMAGE_QUALITY, THUMBNAIL_SIZE,
    ALLOWED_EXTENSIONS, CACHE_TTL, PUBLIC_ROUTES
)

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# ==================== 缓存 ====================

_news_cache = {'data': None, 'timestamp': None}
_alumni_cache = {'data': None, 'timestamp': None}
_ip_location_cache = {}


def _get_cached_news():
    """获取缓存的新闻数据"""
    now = datetime.now().timestamp()
    if _news_cache['data'] and _news_cache['timestamp']:
        if now - _news_cache['timestamp'] < CACHE_TTL:
            return _news_cache['data']
    return None


def _set_cached_news(data):
    """设置缓存的新闻数据"""
    _news_cache['data'] = data
    _news_cache['timestamp'] = datetime.now().timestamp()


def _get_cached_alumni():
    """获取缓存的校友会数据"""
    now = datetime.now().timestamp()
    if _alumni_cache['data'] and _alumni_cache['timestamp']:
        if now - _alumni_cache['timestamp'] < CACHE_TTL:
            return _alumni_cache['data']
    return None


def _set_cached_alumni(data):
    """设置缓存的校友会数据"""
    _alumni_cache['data'] = data
    _alumni_cache['timestamp'] = datetime.now().timestamp()


# ==================== 图片处理 ====================

def compress_avatar(file, filepath, max_size=AVATAR_MAX_SIZE):
    """压缩头像图片,确保不超过max_size"""
    if not HAS_PIL:
        file.save(filepath)
        return True
    try:
        file.save(filepath)
        file_size = os.path.getsize(filepath)
        if file_size <= max_size:
            return True

        img = Image.open(filepath)
        quality = 95
        while file_size > max_size and quality > 20:
            img.save(filepath, quality=quality, optimize=True)
            file_size = os.path.getsize(filepath)
            quality -= 10

        if file_size > max_size:
            width, height = img.size
            while file_size > max_size and width > 100:
                width = int(width * 0.8)
                height = int(height * 0.8)
                img = img.resize((width, height), Image.LANCZOS)
                img.save(filepath, quality=85, optimize=True)
                file_size = os.path.getsize(filepath)
    except Exception as e:
        print(f"Avatar compression error: {e}")
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except:
            pass
        return False
    return True


def compress_image(input_path, max_size=IMAGE_MAX_SIZE):
    """压缩图片,确保文件大小不超过max_size"""
    if not HAS_PIL:
        return True
    try:
        img = Image.open(input_path)

        # 处理 EXIF 方向信息
        exif = img._getexif()
        if exif:
            orientation = exif.get(274, 1)
            if orientation == 3:
                img = img.rotate(180, expand=True)
            elif orientation == 6:
                img = img.rotate(270, expand=True)
            elif orientation == 8:
                img = img.rotate(90, expand=True)

        if img.mode in ('RGBA', 'P', 'LA'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = rgb_img

        file_size = os.path.getsize(input_path)
        if file_size <= max_size:
            img.save(input_path, quality=IMAGE_QUALITY, optimize=True)
            return True

        quality = 90
        while file_size > max_size and quality >= 50:
            img.save(input_path, quality=quality, optimize=True)
            file_size = os.path.getsize(input_path)
            quality -= 10

        if file_size > max_size:
            width, height = img.size
            while file_size > max_size and width > 800:
                width = int(width * 0.8)
                height = int(height * 0.8)
                img_resized = img.resize((width, height), Image.LANCZOS)
                img_resized.save(input_path, quality=IMAGE_QUALITY, optimize=True)
                file_size = os.path.getsize(input_path)

        return True
    except Exception as e:
        print(f"Image compression error: {e}")
        return False


def create_thumbnail(input_path, output_path, size=THUMBNAIL_SIZE):
    """生成缩略图"""
    if not HAS_PIL:
        return False
    try:
        img = Image.open(input_path)

        exif = img._getexif()
        if exif:
            orientation = exif.get(274, 1)
            if orientation == 3:
                img = img.rotate(180, expand=True)
            elif orientation == 6:
                img = img.rotate(270, expand=True)
            elif orientation == 8:
                img = img.rotate(90, expand=True)

        if img.mode in ('RGBA', 'P', 'LA'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = rgb_img

        img.thumbnail(size, Image.LANCZOS)
        img.save(output_path, quality=IMAGE_QUALITY, optimize=True)
        return True
    except Exception as e:
        print(f"Thumbnail creation error: {e}")
        return False


# ==================== IP 相关 ====================

# 中英文映射表
_COUNTRY_MAP = {
    'China': '中国', 'United States': '美国', 'Japan': '日本',
    'South Korea': '韩国', 'Germany': '德国', 'France': '法国',
    'United Kingdom': '英国', 'Russia': '俄罗斯', 'Canada': '加拿大',
    'Australia': '澳大利亚', 'Singapore': '新加坡', 'India': '印度',
    'Brazil': '巴西', 'Netherlands': '荷兰', 'Italy': '意大利',
    'Spain': '西班牙', 'Mexico': '墨西哥', 'Indonesia': '印尼',
    'Thailand': '泰国', 'Vietnam': '越南', 'Malaysia': '马来西亚',
    'Philippines': '菲律宾', 'Pakistan': '巴基斯坦', 'Bangladesh': '孟加拉国',
    'Turkey': '土耳其', 'Saudi Arabia': '沙特阿拉伯', 'United Arab Emirates': '阿联酋',
    'Nigeria': '尼日利亚', 'Egypt': '埃及', 'South Africa': '南非',
    'Kenya': '肯尼亚', 'Morocco': '摩洛哥', 'Ghana': '加纳',
    'Tanzania': '坦桑尼亚', 'Ethiopia': '埃塞俄比亚', 'Uganda': '乌干达',
    'Argentina': '阿根廷', 'Colombia': '哥伦比亚', 'Peru': '秘鲁',
    'Chile': '智利', 'Venezuela': '委内瑞拉', 'Ecuador': '厄瓜多尔',
    'Cuba': '古巴', 'Dominican Republic': '多米尼加', 'Guatemala': '危地马拉',
    'Portugal': '葡萄牙', 'Poland': '波兰', 'Belgium': '比利时',
    'Sweden': '瑞典', 'Norway': '挪威', 'Denmark': '丹麦', 'Finland': '芬兰',
    'Austria': '奥地利', 'Switzerland': '瑞士', 'Czech Republic': '捷克',
    'Greece': '希腊', 'Hungary': '匈牙利', 'Romania': '罗马尼亚',
    'Bulgaria': '保加利亚', 'Ukraine': '乌克兰', 'Israel': '以色列',
    'Jordan': '约旦', 'Lebanon': '黎巴嫩', 'Iraq': '伊拉克', 'Iran': '伊朗',
    'Afghanistan': '阿富汗', 'Kazakhstan': '哈萨克斯坦', 'Uzbekistan': '乌兹别克斯坦',
    'Mongolia': '蒙古', 'North Korea': '朝鲜', 'Taiwan': '台湾',
    'Hong Kong': '香港', 'Macau': '澳门',
}

_REGION_MAP = {
    'Beijing': '北京', 'Shanghai': '上海', 'Guangdong': '广东', 'Zhejiang': '浙江',
    'Jiangsu': '江苏', 'Shandong': '山东', 'Sichuan': '四川', 'Henan': '河南',
    'Hubei': '湖北', 'Shaanxi': '陕西', 'Fujian': '福建', 'Liaoning': '辽宁',
    'Tianjin': '天津', 'Chongqing': '重庆', 'Jilin': '吉林', 'Heilongjiang': '黑龙江',
    'Inner Mongolia': '内蒙古', 'Guangxi': '广西', 'Yunnan': '云南', 'Guizhou': '贵州',
    'Xinjiang': '新疆', 'Tibet': '西藏', 'Ningxia': '宁夏', 'Qinghai': '青海',
    'Gansu': '甘肃', 'Hainan': '海南', 'Hunan': '湖南', 'Anhui': '安徽',
    'Jiangxi': '江西', 'Shanxi': '山西', 'Hebei': '河北', 'Taiwan': '台湾',
    'Hong Kong': '香港', 'Macau': '澳门',
    'California': '加利福尼亚', 'New York': '纽约', 'Texas': '得克萨斯',
    'Florida': '佛罗里达', 'Illinois': '伊利诺伊', 'Pennsylvania': '宾夕法尼亚',
    'Ohio': '俄亥俄', 'Georgia': '乔治亚', 'Michigan': '密歇根', 'Arizona': '亚利桑那',
}


def get_ip_location(ip_address):
    """获取IP归属地（中文）"""
    if not ip_address:
        return ''
    if ip_address in ('127.0.0.1', 'localhost', '0.0.0.0') or ip_address.startswith('192.168.') or ip_address.startswith('10.'):
        return '本地网络'

    if ip_address in _ip_location_cache:
        cached_time, cached_location = _ip_location_cache[ip_address]
        if (datetime.now() - cached_time).seconds < 3600:
            return cached_location

    try:
        import requests
        resp = requests.get(f'http://ip-api.com/json/{ip_address}?fields=status,country,regionName,city', timeout=3)
        data = resp.json()
        if data.get('status') == 'success':
            country = _COUNTRY_MAP.get(data.get('country', ''), data.get('country', ''))
            region = _REGION_MAP.get(data.get('regionName', ''), data.get('regionName', ''))
            city = data.get('city', '')
            location = f"{country} {region} {city}".strip()
            _ip_location_cache[ip_address] = (datetime.now(), location)
            return location
    except:
        pass

    return ip_address


def get_real_ip(request):
    """获取真实客户端IP(支持代理)"""
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        ip = request.headers.get('X-Real-IP')
    else:
        ip = request.remote_addr or ''
    return ip


# ==================== 输入处理 ====================

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def sanitize_input(text):
    """简单的XSS过滤"""
    if not text:
        return ''
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


def is_public_path(path):
    """检查是否是公开路径"""
    if path in PUBLIC_ROUTES:
        return True
    if path.startswith('/static/'):
        return True
    if path.startswith('/api/location/'):
        return True
    return False


# ==================== 地理计算 ====================

def haversine_distance(lat1, lon1, lat2, lon2):
    """计算两点之间的直线距离(公里)"""
    import math
    R = 6371  # 地球半径(公里)
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c
