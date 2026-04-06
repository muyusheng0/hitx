"""
吉大通信八班 同学录网站
Flask Web Application
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import csv
import os
import uuid
import re
from datetime import datetime, timedelta
from functools import wraps
import database
from PIL import Image
from apscheduler.schedulers.background import BackgroundScheduler
import news_crawler
from wx_api import wx_bp

app = Flask(__name__)
app.register_blueprint(wx_bp)
app.secret_key = 'jlu_tongxin_8_class_2024_secret_key'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max for video uploads
app.config['UPLOAD_FOLDER'] = 'static/imgs/avatars'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
# Session 配置
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
app.config['SESSION_COOKIE_HTTPONLY'] = True

AVATAR_MAX_SIZE = 500 * 1024  # 500KB for avatars

@app.errorhandler(413)
def request_entity_too_large(e):
    return jsonify({'success': False, 'message': '文件大小超过100MB限制'}), 413

# IP归属地缓存
_ip_location_cache = {}

def get_ip_location(ip_address):
    """获取IP归属地"""
    if not ip_address:
        return ''

    # 忽略本地IP
    if ip_address in ('127.0.0.1', 'localhost', '0.0.0.0') or ip_address.startswith('192.168.') or ip_address.startswith('10.'):
        return '本地网络'

    # 检查缓存（缓存1小时）
    if ip_address in _ip_location_cache:
        cached_time, cached_location = _ip_location_cache[ip_address]
        if (datetime.now() - cached_time).seconds < 3600:
            return cached_location

    try:
        import requests
        resp = requests.get(f'http://ip-api.com/json/{ip_address}?fields=status,country,regionName,city', timeout=3)
        data = resp.json()
        if data.get('status') == 'success':
            location = f"{data.get('country', '')} {data.get('regionName', '')} {data.get('city', '')}"
            _ip_location_cache[ip_address] = (datetime.now(), location)
            return location
    except:
        pass

    return ip_address


def get_real_ip():
    """获取真实客户端IP（支持代理）"""
    # 优先从代理头获取
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        ip = request.headers.get('X-Real-IP')
    else:
        ip = request.remote_addr or ''
    return ip

# 管理员名单
ADMIN_USERS = ['穆玉升']


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
    current_name = session['verified_student']['name']
    return session.get('password_verified', False)


def compress_avatar(file, filepath, max_size=AVATAR_MAX_SIZE):
    """压缩头像图片，确保不超过max_size"""
    try:
        # 先尝试保存原始图片
        file.save(filepath)

        # 获取文件大小
        file_size = os.path.getsize(filepath)

        # 如果小于限制，直接返回True
        if file_size <= max_size:
            return True

        # 需要压缩
        img = Image.open(filepath)

        # 逐步降低质量直到文件大小符合要求
        quality = 95
        while file_size > max_size and quality > 20:
            img.save(filepath, quality=quality, optimize=True)
            file_size = os.path.getsize(filepath)
            quality -= 10

        # 如果还是太大，缩小图片尺寸
        if file_size > max_size:
            width, height = img.size
            while file_size > max_size and width > 100:
                width = int(width * 0.8)
                height = int(height * 0.8)
                img = img.resize((width, height), Image.LANCZOS)
                img.save(filepath, quality=85, optimize=True)
                file_size = os.path.getsize(filepath)
    except Exception as e:
        app.logger.error(f"Avatar compression error: {e}")
        # 如果压缩失败，尝试删除可能创建的文件
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except:
            pass
        # 返回 False 表示压缩失败
        return False

    return True


# 图片压缩和缩略图配置
IMAGE_MAX_SIZE = 1024 * 1024  # 1MB 最大图片大小
IMAGE_QUALITY = 85  # 压缩质量
THUMBNAIL_SIZE = (800, 800)  # 缩略图最大尺寸


def compress_image(input_path, max_size=IMAGE_MAX_SIZE):
    """压缩图片，确保文件大小不超过max_size"""
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

        # 转换为 RGB（如果是 RGBA 或其他模式）
        if img.mode in ('RGBA', 'P', 'LA'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = rgb_img

        # 获取文件大小
        file_size = os.path.getsize(input_path)

        # 如果小于限制，直接返回
        if file_size <= max_size:
            # 但确保质量为85
            img.save(input_path, quality=IMAGE_QUALITY, optimize=True)
            return True

        # 需要压缩 - 逐步降低质量
        quality = 90
        while file_size > max_size and quality >= 50:
            img.save(input_path, quality=quality, optimize=True)
            file_size = os.path.getsize(input_path)
            quality -= 10

        # 如果还是太大，缩小图片尺寸
        if file_size > max_size:
            width, height = img.size
            scale = 1
            while file_size > max_size and width > 800:
                scale *= 0.8
                width = int(width * 0.8)
                height = int(height * 0.8)
                img_resized = img.resize((width, height), Image.LANCZOS)
                img_resized.save(input_path, quality=IMAGE_QUALITY, optimize=True)
                file_size = os.path.getsize(input_path)

        return True
    except Exception as e:
        app.logger.error(f"Image compression error: {e}")
        return False


def create_thumbnail(input_path, output_path, size=THUMBNAIL_SIZE):
    """生成缩略图"""
    try:
        img = Image.open(input_path)

        # 处理 EXIF 方向信息
        exif = img._getexif()
        if exif:
            orientation = exif.get(274, 1)  # 274 is the EXIF tag for Orientation
            if orientation == 3:
                img = img.rotate(180, expand=True)
            elif orientation == 6:
                img = img.rotate(270, expand=True)
            elif orientation == 8:
                img = img.rotate(90, expand=True)

        # 转换为 RGB
        if img.mode in ('RGBA', 'P', 'LA'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = rgb_img

        # 生成缩略图（保持宽高比）
        img.thumbnail(size, Image.LANCZOS)

        # 保存缩略图
        img.save(output_path, quality=IMAGE_QUALITY, optimize=True)
        return True
    except Exception as e:
        app.logger.error(f"Thumbnail creation error: {e}")
        return False


DATA_DIR = '/home/ubuntu/jlu8'
TXL_FILE = os.path.join(DATA_DIR, 'txl.csv')
LYB_FILE = os.path.join(DATA_DIR, 'lyb.csv')
VIDEOS_FILE = os.path.join(DATA_DIR, 'videos.csv')
PHOTOS_FILE = os.path.join(DATA_DIR, 'photos.csv')
DELETED_FILE = os.path.join(DATA_DIR, 'deleted.csv')

# 初始化数据库
database.init_db()
database.migrate_from_csv()
database.create_wx_bindings_table()
database.add_wx_openid_column()


# 文件上传错误处理
@app.errorhandler(413)
def request_entity_too_large(e):
    return jsonify({'success': False, 'message': '文件过大，请选择小于20MB的图片'}), 413
database.migrate_add_gps_coords()

# 省份拼音到汉字映射
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

# 省份坐标（用于地图展示，简化版中国地图）
PROVINCE_COORDS = {
    '北京': (60, 35),
    '上海': (85, 50),
    '天津': (65, 38),
    '重庆': (50, 65),
    '广东': (70, 80),
    '江苏': (75, 45),
    '浙江': (82, 55),
    '四川': (35, 55),
    '湖北': (60, 55),
    '湖南': (58, 68),
    '河南': (62, 42),
    '山东': (72, 38),
    '河北': (65, 35),
    '陕西': (48, 42),
    '辽宁': (78, 30),
    '吉林': (82, 25),
    '黑龙江': (85, 18),
    '内蒙古': (45, 28),
    '新疆': (12, 25),
    '甘肃': (28, 35),
    '青海': (22, 42),
    '宁夏': (48, 38),
    '山西': (55, 38),
    '安徽': (72, 50),
    '福建': (78, 68),
    '江西': (68, 62),
    '广西': (50, 78),
    '海南': (62, 88),
    '云南': (38, 72),
    '贵州': (48, 70),
    '西藏': (15, 45),
}

# 城市拼音到中文的映射
CITY_PINYIN_TO_NAME = {
    'beijing': '北京', 'shanghai': '上海', 'tianjin': '天津', 'chongqing': '重庆',
    'guangzhou': '广州', 'shenzhen': '深圳', 'zhuhai': '珠海', 'dongguan': '东莞', 'foshan': '佛山',
    'nanjing': '南京', 'suzhou': '苏州', 'wuxi': '无锡',
    'hangzhou': '杭州', 'ningbo': '宁波', 'wenzhou': '温州',
    'chengdu': '成都', 'mianyang': '绵阳',
    'wuhan': '武汉', 'yichang': '宜昌',
    'changsha': '长沙', 'zhuzhou': '株洲',
    'zhengzhou': '郑州', 'luoyang': '洛阳',
    'jinan': '济南', 'qingdao': '青岛', 'yantai': '烟台', 'weifang': '潍坊',
    'shijiazhuang': '石家庄', 'baoding': '保定', 'tangshan': '唐山',
    'xian': '西安', 'xianyang': '咸阳',
    'shenyang': '沈阳', 'dalian': '大连', 'anshan': '鞍山', 'fushun': '抚顺',
    'changchun': '长春', 'jilin': '吉林', 'siping': '四平',
    'harbin': '哈尔滨', 'qiqihar': '齐齐哈尔', 'mudanjiang': '牡丹江',
    'hohhot': '呼和浩特', 'baotou': '包头',
    'urumqi': '乌鲁木齐',
    'lanzhou': '兰州',
    'xining': '西宁',
    'yinchuan': '银川',
    'taiyuan': '太原', 'datong': '大同',
    'hefei': '合肥', 'wuhu': '芜湖', 'bangbu': '蚌埠',
    'fuzhou': '福州', 'xiamen': '厦门', 'quanzhou': '泉州', 'zhangzhou': '漳州',
    'nanchang': '南昌', 'ganzhou': '赣州', 'jiujiang': '九江',
    'nanning': '南宁', 'liuzhou': '柳州', 'guilin': '桂林',
    'haikou': '海口', 'sanya': '三亚',
    'kunming': '昆明', 'dali': '大理',
    'guiyang': '贵阳', 'zunyi': '遵义',
    'lhasa': '拉萨',
    'taipei': '台北', 'kaohsiung': '高雄',
    'hongkong': '香港', 'macau': '澳门'
}

def get_city_name(pinyin):
    """将城市拼音转换为中文名称"""
    return CITY_PINYIN_TO_NAME.get(pinyin.lower(), pinyin)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def get_province_name(pinyin):
    """将拼音转换为省份名称"""
    return PROVINCE_MAP.get(pinyin.lower(), pinyin)


def get_student_coords(province_name):
    """获取省份坐标"""
    return PROVINCE_COORDS.get(province_name, (50, 50))


def sanitize_input(text):
    """简单的XSS过滤"""
    if not text:
        return ''
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


# ==================== 路由 ====================

@app.route('/')
def index():
    """首页"""
    students = database.read_txl()
    messages = database.read_lyb()

    # 过去一周内的留言数量
    one_week_ago = datetime.now() - timedelta(days=7)
    week_messages = [m for m in messages
                      if datetime.strptime(m['time'], '%Y-%m-%d %H:%M:%S') > one_week_ago]
    week_message_count = len(week_messages)

    # 按时间倒序获取最新留言（最多12条）
    sorted_messages = sorted(messages, key=lambda x: x['time'], reverse=True)
    recent_messages = sorted_messages[:3]

    activities = get_activities()

    # 获取照片，按年份分组，每年最多3张
    img_files = get_gallery_images()
    photos_by_year = {}
    for img in img_files:
        year = img.get('year', 2020)
        if year not in photos_by_year:
            photos_by_year[year] = []
        if len(photos_by_year[year]) < 4:
            photos_by_year[year].append(img)

    # 获取省份统计
    province_stats = {}
    for s in students:
        p = s['hometown_name']
        if p:
            if p not in province_stats:
                province_stats[p] = {'count': 0, 'students': [], 'coords': s['coords']}
            province_stats[p]['count'] += 1
            province_stats[p]['students'].append({'name': s['name'], 'id': s['id']})

    return render_template('index.html',
                           student_count=len(students),
                           recent_messages=recent_messages,
                           week_message_count=week_message_count,
                           activities=activities[:9],  # 传递最新9条动态
                           photos_by_year=photos_by_year,
                           province_stats=province_stats)


def get_activities():
    """获取最新动态（去重：同一人连续同类型动态只保留最新一条）"""
    activities = []

    # 检查生日动态（提前5天开始显示）
    today = datetime.now()
    students = database.read_txl()
    for student in students:
        birthday_str = student.get('birthday', '')
        if birthday_str and len(birthday_str) >= 10:  # YYYY-MM-DD format
            try:
                birthday_month = int(birthday_str[5:7])
                birthday_day = int(birthday_str[8:10])
                # 构建今年的生日日期
                this_year_birthday = datetime(today.year, birthday_month, birthday_day)
                # 如果今年的生日已过但还没到，看明年的
                if this_year_birthday < today and (today - this_year_birthday).days > 5:
                    this_year_birthday = datetime(today.year + 1, birthday_month, birthday_day)
                # 检查是否在5天内
                days_until = (this_year_birthday - today).days
                if 0 <= days_until <= 5:
                    pronoun = '他' if student.get('gender', '') == '男' else '她'
                    if days_until == 0:
                        content = f'🎂 今天{student["name"]}生日！祝{pronoun}生日快乐！'
                    else:
                        content = f'🎂 {student["name"]} {birthday_month}月{birthday_day}日生日，还有{days_until}天，提前祝{pronoun}生日快乐！'
                    activities.append({
                        'type': 'birthday',
                        'actor': student['name'],
                        'content': content,
                        'time': this_year_birthday.strftime('%Y-%m-%d 00:00:00')
                    })
            except:
                pass

    messages = database.read_lyb()

    # 留言动态（取最新10条留言）
    for msg in sorted(messages, key=lambda x: x['time'], reverse=True)[:10]:
        has_voice = bool(msg.get('voice'))
        has_image = bool(msg.get('image'))
        # 根据类型设置内容
        if has_voice and has_image:
            content = '发表了语音留言并附带图片'
            msg_type = 'voice_image'
        elif has_voice:
            content = '发表了语音留言'
            msg_type = 'voice'
        elif has_image:
            content = '发表了新留言，并附带图片'
            msg_type = 'image'
        else:
            content = '发表了新留言'
            msg_type = 'text'
        activities.append({
            'type': 'message',
            'actor': msg['nickname'],
            'content': content,
            'time': msg['time'],
            'msg_id': msg['id'],
            'msg_content': msg['content'][:30],
            'msg_type': msg_type,
            'has_image': has_image,
            'has_voice': has_voice
        })

    # 从活动日志读取（profile_update、photo、video等）
    activity_logs = database.read_activities()
    for log in activity_logs[:20]:
        activity = {
            'type': log['type'],
            'actor': log['actor'],
            'content': log['content'],
            'time': log['time']
        }
        # 照片活动：从内容中提取文件名
        if log['type'] == 'photo':
            import re
            match = re.search(r'《(.+?)》', log['content'])
            if match:
                activity['img_name'] = match.group(1)
                activity['img_url'] = f'/static/imgs/messages/{match.group(1)}'
        # 视频活动：从内容中提取标题
        if log['type'] == 'video':
            import re
            match = re.search(r'《(.+?)》', log['content'])
            if match:
                activity['video_title'] = match.group(1)
        # 喊话活动：从内容中提取目标人名
        if log['type'] == 'voice_shout':
            import re
            match = re.search(r'对(.+?)喊', log['content'])
            if match:
                activity['target_name'] = match.group(1)
        activities.append(activity)

    # 按时间排序
    activities.sort(key=lambda x: x['time'], reverse=True)

    # 合并统计：同一人同类动态合并显示数量
    deduplicated = []
    for activity in activities:
        if not deduplicated:
            activity['count'] = 1
            activity['original_content'] = activity.get('content', '')  # 保存原始内容用于删除
            deduplicated.append(activity)
        else:
            last = deduplicated[-1]
            # 如果当前条目和上一个条目的actor和type都相同，累加计数
            if activity['actor'] == last['actor'] and activity['type'] == last['type']:
                last['count'] = last.get('count', 1) + 1
                # 更新原始内容为最新一条的内容
                last['original_content'] = activity.get('content', '')
            else:
                activity['count'] = 1
                activity['original_content'] = activity.get('content', '')
                deduplicated.append(activity)

    # 修改合并后的显示内容
    for act in deduplicated:
        count = act.get('count', 1)
        if count > 1:
            if act['type'] == 'photo':
                act['content'] = f'上传了{count}张照片'
            elif act['type'] == 'message':
                act['content'] = f'发表了{count}条留言'
            elif act['type'] == 'video':
                act['content'] = f'分享了{count}个视频'
            elif act['type'] == 'voice_shout':
                act['content'] = f'喊了{count}次话'

    return deduplicated[:10]


def get_gallery_images():
    """获取相册图片（按最新上传时间排序），排除已删除的照片"""
    photos = database.read_photos()
    deleted_items = database.read_deleted()
    # 获取已删除的文件名集合
    # filename可能在content(文件删除)或extra(ID删除)字段中
    deleted_filenames = set()
    for item in deleted_items:
        if item.get('type') == 'photo':
            # 对于照片，filename可能在content或extra字段中
            fn = item.get('content', '')
            if fn and fn not in deleted_filenames:
                deleted_filenames.add(fn)
            fn2 = item.get('extra', '')
            if fn2 and fn2 not in deleted_filenames:
                deleted_filenames.add(fn2)

    img_files = []
    avatars_dir = os.path.join(DATA_DIR, 'static/imgs/avatars')
    upload_dir = os.path.join(DATA_DIR, 'static/imgs')

    # 已知照片（从photos.csv）
    known_filenames = set()
    messages_dir = os.path.join(DATA_DIR, 'static/imgs/messages')
    for p in photos:
        # 跳过已删除的照片
        if p['filename'] in deleted_filenames:
            continue
        # 跳过留言板图片（没有年份或年份为0或年份为2020的视为留言板图片）
        year = p.get('year')
        if not year or year == '' or year == 0 or year == 2020:
            continue
        # 判断图片路径
        filepath = os.path.join(DATA_DIR, 'static/imgs/messages', p['filename'])
        if os.path.exists(filepath):
            # 在messages目录中
            img_files.append({
                'name': p['filename'],
                'url': f'/static/imgs/messages/{p["filename"]}',
                'owner': p['owner'],
                'time': p['time'],
                'year': year
            })
            known_filenames.add(p['filename'])
        else:
            # 在imgs目录中
            filepath = os.path.join(DATA_DIR, 'static/imgs', p['filename'])
            if os.path.exists(filepath):
                img_files.append({
                    'name': p['filename'],
                    'url': f'/static/imgs/{p["filename"]}',
                    'owner': p['owner'],
                    'time': p['time'],
                    'year': year
                })
                known_filenames.add(p['filename'])

    # 扫描文件系统（static/imgs/下的图片，排除avatars子文件夹）
    if os.path.exists(upload_dir):
        for f in os.listdir(upload_dir):
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                # 跳过已删除的照片
                if f in deleted_filenames:
                    continue
                filepath = os.path.join(upload_dir, f)
                # 跳过子文件夹（如avatars）
                if os.path.isdir(filepath):
                    continue
                if f not in known_filenames:
                    mtime = os.path.getmtime(filepath)
                    img_files.append({
                        'name': f,
                        'url': f'/static/imgs/{f}',
                        'owner': '穆玉升',
                        'time': datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                    })

    # 按上传时间倒序（最新在前）
    img_files.sort(key=lambda x: x['time'], reverse=True)
    return img_files


@app.route('/txl')
def txl():
    """通讯录页面"""
    students = database.read_txl()

    # 为没有坐标的学生填充坐标（根据城市名和区）
    for s in students:
        if not s.get('coords'):
            city = s.get('city', '') or s.get('hometown_name', '')
            district = s.get('district', '')
            if city:
                coords = database.get_coords_by_city(city, district)
                if coords:
                    s['coords'] = coords

    voice_shouts = database.read_voice_shouts()

    # 计算离我最近的同学
    nearest_classmates = []
    if 'verified_student' in session:
        current_user = session['verified_student']
        # 优先使用GPS坐标，其次使用session中的城市坐标，最后根据当前用户的城市查找
        current_coords = current_user.get('coords', '')
        current_name = current_user.get('name', '')
        current_id = current_user.get('id', '')

        # 查找当前用户的GPS坐标（优先使用）
        for s in students:
            if s.get('name') == current_name and s.get('id') == current_id:
                gps = s.get('gps_coords', '')
                if gps:
                    current_coords = gps
                break

        # 如果没有GPS坐标也没有session坐标，根据城市获取
        if not current_coords:
            for s in students:
                if s.get('name') == current_name and s.get('id') == current_id:
                    current_coords = s.get('coords', '')
                    break

        if current_coords:
            try:
                lat1, lon1 = map(float, current_coords.split(','))
                distances = []
                for s in students:
                    if s.get('name') == current_name:
                        continue
                    # 优先使用同学的GPS坐标，其次使用城市坐标
                    s_coords = s.get('gps_coords', '') or s.get('coords', '')
                    if s_coords:
                        try:
                            lat2, lon2 = map(float, s_coords.split(','))
                            dist = haversine_distance(lat1, lon1, lat2, lon2)
                            distances.append((s['name'], dist, s))
                        except:
                            continue
                distances.sort(key=lambda x: x[1])
                nearest_classmates = [(d[2], int(d[1])) for d in distances[:2]]
            except:
                pass

    return render_template('txl.html', students=students, voice_shouts=voice_shouts, nearest_classmates=nearest_classmates)


def haversine_distance(lat1, lon1, lat2, lon2):
    """计算两点之间的直线距离（公里）"""
    import math
    R = 6371  # 地球半径（公里）
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c


@app.route('/api/update_coords', methods=['POST'])
def update_coords():
    """批量更新所有学生的坐标（根据城市名）"""
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


@app.route('/api/update_gps_coords', methods=['POST'])
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


@app.route('/lyb')
def lyb():
    """留言板页面"""
    messages = database.read_lyb()
    messages.reverse()
    return render_template('lyb.html', messages=messages)


@app.route('/api/add_comment', methods=['POST'])
def add_comment():
    """添加评论"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    data = request.get_json()
    message_id = data.get('message_id')
    content = sanitize_input(data.get('content', ''))
    if not message_id or not content:
        return jsonify({'success': False, 'message': '参数错误'})
    nickname = session['verified_student']['name']
    comment_id = database.add_comment(message_id, nickname, content)

    # 获取留言主人并发送通知
    messages = database.read_lyb()
    for msg in messages:
        if str(msg['id']) == str(message_id):
            msg_owner = msg.get('nickname', '')
            if msg_owner and msg_owner != nickname:
                content_preview = content[:50] + '...' if len(content) > 50 else content
                database.create_notification(
                    recipient=msg_owner,
                    sender=nickname,
                    notif_type='comment',
                    ref_id=message_id,
                    content=f'{nickname}评论了你的留言：{content_preview}'
                )
            break

    return jsonify({'success': True, 'id': comment_id, 'nickname': nickname, 'content': content, 'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})


@app.route('/api/get_comments/<int:message_id>')
def get_comments(message_id):
    """获取留言的评论"""
    comments = database.get_comments_by_message(message_id)
    return jsonify({'success': True, 'comments': comments})


@app.route('/api/delete_comment', methods=['POST'])
def delete_comment():
    """删除评论"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    data = request.get_json()
    comment_id = data.get('id')
    message_id = data.get('message_id')

    if not comment_id:
        return jsonify({'success': False, 'message': '无效的评论ID'})

    current_name = session['verified_student']['name']

    # 获取评论信息
    comments = database.get_comments_by_message(message_id)
    comment = None
    for c in comments:
        if str(c['id']) == str(comment_id):
            comment = c
            break

    if not comment:
        return jsonify({'success': False, 'message': '评论不存在'})

    # 检查权限：评论人或楼主可以删除，管理员可以删除任何评论
    if not is_admin(current_name) and comment['nickname'] != current_name:
        # 获取留言信息检查是否是楼主
        messages = database.read_lyb()
        is_owner = False
        for msg in messages:
            if str(msg['id']) == str(message_id) and msg['nickname'] == current_name:
                is_owner = True
                break
        if not is_owner:
            return jsonify({'success': False, 'message': '无权限删除该评论'})

    # 记录到已删除列表
    deleted_item = {
        'id': database.get_next_deleted_id(),
        'type': 'comment',
        'content': comment.get('content', '')[:100],
        'owner': comment['nickname'],
        'time': comment.get('time', ''),
        'deleted_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'extra': ''
    }
    deleted_items = database.read_deleted()
    deleted_items.append(deleted_item)
    database.write_deleted(deleted_items)

    # 删除评论
    database.delete_comment(comment_id)
    return jsonify({'success': True, 'message': '删除成功'})


@app.route('/api/like_message', methods=['POST'])
def like_message():
    """点赞留言"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    data = request.get_json()
    message_id = data.get('message_id')
    if not message_id:
        return jsonify({'success': False, 'message': '参数错误'})
    nickname = session['verified_student']['name']
    success = database.like_message(message_id, nickname)
    count = database.get_message_likes(message_id)

    # 发送通知（仅当点赞成功且不是给自己点赞）
    if success:
        messages = database.read_lyb()
        for msg in messages:
            if str(msg['id']) == str(message_id):
                msg_owner = msg.get('nickname', '')
                if msg_owner and msg_owner != nickname:
                    database.create_notification(
                        recipient=msg_owner,
                        sender=nickname,
                        notif_type='like',
                        ref_id=message_id,
                        content=f'{nickname}点赞了你的留言'
                    )
                break

    return jsonify({'success': success, 'liked': success, 'count': count})


@app.route('/api/unlike_message', methods=['POST'])
def unlike_message():
    """取消点赞"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    data = request.get_json()
    message_id = data.get('message_id')
    if not message_id:
        return jsonify({'success': False, 'message': '参数错误'})
    nickname = session['verified_student']['name']
    success = database.unlike_message(message_id, nickname)
    count = database.get_message_likes(message_id)
    return jsonify({'success': success, 'liked': not success, 'count': count})


@app.route('/api/get_message_likes/<int:message_id>')
def get_message_likes(message_id):
    """获取留言点赞信息"""
    count = database.get_message_likes(message_id)
    has_liked = False
    if 'verified_student' in session:
        nickname = session['verified_student']['name']
        has_liked = database.has_liked_message(message_id, nickname)
    return jsonify({'success': True, 'count': count, 'has_liked': has_liked})


@app.route('/gallery')
def gallery():
    """相册页面 - 重定向到媒体中心"""
    return redirect('/media')


@app.route('/video')
def video_page():
    """视频页面 - 重定向到媒体中心"""
    return redirect('/media')


@app.route('/media')
def media():
    """媒体中心 - 相册和视频合并页面"""
    img_files = get_gallery_images()
    videos = get_videos()
    news = database.get_news(5)
    # 过滤掉旧新闻，只展示2026年的新闻
    from datetime import datetime
    current_year = datetime.now().year
    news = [n for n in news if int(n['published_time'][:4]) >= current_year]

    # 检查当前用户是否是管理员
    is_admin_user = False
    if 'verified_student' in session:
        current_name = session['verified_student']['name']
        is_admin_user = is_admin(current_name)

    return render_template('media.html', images=img_files, videos=videos, news=news, is_admin_user=is_admin_user)


def get_videos():
    """获取视频列表，排除已删除的视频"""
    videos = database.read_videos()
    deleted_items = database.read_deleted()

    # 获取已删除的视频URL或标题集合
    deleted_video_urls = set()
    deleted_video_titles = set()
    for item in deleted_items:
        if item.get('type') == 'video':
            if item.get('extra'):
                deleted_video_urls.add(item['extra'])
            if item.get('content'):
                deleted_video_titles.add(item['content'])

    # 过滤已删除的视频
    filtered = []
    for v in videos:
        url = v.get('url', '')
        title = v.get('title', '')
        # 跳过已删除的视频（通过URL或标题匹配）
        if url in deleted_video_urls or title in deleted_video_titles:
            continue
        filtered.append(v)

    return filtered


@app.route('/api/like_media', methods=['POST'])
def like_media():
    """点赞媒体"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    data = request.get_json()
    media_type = data.get('media_type')  # 'photo' or 'video'
    media_id = data.get('media_id')
    if not media_type or not media_id:
        return jsonify({'success': False, 'message': '参数错误'})
    nickname = session['verified_student']['name']
    success = database.like_media(media_type, media_id, nickname)
    count = database.get_media_likes(media_type, media_id)

    # 发送通知
    if success:
        owner = None
        if media_type == 'photo':
            photos = database.read_photos()
            for p in photos:
                if p['filename'] == media_id:
                    owner = p.get('owner', '')
                    break
        elif media_type == 'video':
            videos = database.read_videos()
            for v in videos:
                if str(v['id']) == str(media_id):
                    owner = v.get('owner', '')
                    break

        if owner and owner != nickname:
            media_label = '照片' if media_type == 'photo' else '视频'
            database.create_notification(
                recipient=owner,
                sender=nickname,
                notif_type='like',
                ref_id=media_id,
                content=f'{nickname}点赞了你的{media_label}',
                media_type=media_type
            )

    return jsonify({'success': True, 'liked': success, 'count': count})


@app.route('/api/unlike_media', methods=['POST'])
def unlike_media():
    """取消点赞"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    data = request.get_json()
    media_type = data.get('media_type')
    media_id = data.get('media_id')
    if not media_type or not media_id:
        return jsonify({'success': False, 'message': '参数错误'})
    nickname = session['verified_student']['name']
    success = database.unlike_media(media_type, media_id, nickname)
    count = database.get_media_likes(media_type, media_id)
    return jsonify({'success': True, 'liked': not success, 'count': count})


@app.route('/api/get_media_likes/<media_type>/<path:media_id>')
def get_media_likes(media_type, media_id):
    """获取媒体点赞信息"""
    count = database.get_media_likes(media_type, media_id)
    has_liked = False
    if 'verified_student' in session:
        nickname = session['verified_student']['name']
        has_liked = database.has_liked_media(media_type, media_id, nickname)
    return jsonify({'success': True, 'count': count, 'has_liked': has_liked})


@app.route('/about')
def about():
    """个人中心页面"""
    return render_template('about.html')


# ==================== API接口 ====================

@app.route('/api/captcha')
def generate_captcha():
    """生成数学验证码"""
    import random
    a = random.randint(1, 9)
    b = random.randint(1, 9)
    captcha_text = f"{a}+{b}="
    result = str(a + b)
    session['captcha'] = result
    session['captcha_time'] = datetime.now().isoformat()
    return jsonify({'captcha': captcha_text})

@app.route('/api/verify', methods=['POST'])
def verify_student():
    """验证同学身份（姓名+学号+验证码+登录密码）"""
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
        return jsonify({'success': False, 'message': '验证码已过期，请刷新'})
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
            ip = get_real_ip()
            ua = request.headers.get('User-Agent', '')[:200]
            database.write_login_log(name, ip, ua)
            return jsonify({'success': True, 'message': '验证成功'})

    return jsonify({'success': False, 'message': '姓名或学号不正确'})


@app.route('/api/txl/list')
def txl_list():
    """获取通讯录列表（仅已验证用户）"""
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


@app.route('/api/check_verify')
def check_verify():
    """检查是否已验证"""
    if 'verified_student' in session:
        verify_time = datetime.fromisoformat(session['verify_time'])
        if datetime.now() - verify_time < timedelta(minutes=30):
            current_name = session['verified_student']['name']
            student = session['verified_student'].copy()
            student['is_admin'] = is_admin(current_name)
            student['is_super_admin'] = is_super_admin(current_name)
            # 检查用户密码状态
            students = database.read_txl()
            for s in students:
                if s['name'] == current_name:
                    student['login_password_set'] = bool(s.get('login_password', ''))
                    break
            return jsonify({'verified': True, 'student': student})
    return jsonify({'verified': False})


@app.route('/api/user/set_password', methods=['POST'])
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


@app.route('/api/check_user_login_password', methods=['POST'])
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


@app.route('/api/user/verify_password', methods=['POST'])
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


@app.route('/api/user/check_password_verified')
def admin_check_password_verified():
    """检查管理员密码是否已验证"""
    if 'verified_student' not in session:
        return jsonify({'verified': False})
    current_name = session['verified_student']['name']
    if not is_admin(current_name):
        return jsonify({'verified': False})
    return jsonify({'verified': session.get('password_verified', False)})


@app.route('/api/user/get_password_prompt', methods=['GET'])
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


@app.route('/api/user/set_password_prompt', methods=['POST'])
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


@app.route('/api/super_admin/set_admin', methods=['POST'])
def set_admin():
    """设置用户为管理员（仅超级管理员可操作）"""
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


@app.route('/api/get_unread_activity_count')
def get_unread_activity_count():
    """获取未读活动数量"""
    activities = get_activities()
    nickname = session.get('verified_student', {}).get('name', '') if 'verified_student' in session else ''
    if not nickname:
        return jsonify({'success': True, 'count': 0})
    count = database.get_unread_activity_count(nickname, activities)
    return jsonify({'success': True, 'count': count})


@app.route('/api/get_activities')
def api_get_activities():
    """获取所有动态（用于管理，分页）"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    page = int(request.args.get('page', 1))
    per_page = 5
    max_items = 30  # 最多显示30条
    activities = get_activities()[:max_items]

    total = len(activities)
    total_pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page

    return jsonify({
        'success': True,
        'activities': activities[start:end],
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages
    })


@app.route('/api/mark_activities_viewed', methods=['POST'])
def mark_activities_viewed():
    """标记活动为已浏览"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    nickname = session['verified_student']['name']
    activities = get_activities()
    database.mark_activities_viewed(nickname, activities)
    return jsonify({'success': True})


@app.route('/api/logout')
def logout():
    """退出验证"""
    session.pop('verified_student', None)
    session.pop('verify_time', None)
    return jsonify({'success': True})


@app.route('/api/notifications')
def get_notifications():
    """获取当前用户通知列表"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    nickname = session['verified_student']['name']
    notifications = database.get_notifications(nickname)
    return jsonify({'success': True, 'notifications': notifications})


@app.route('/api/notifications/count')
def get_notification_count():
    """获取未读通知数量"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    nickname = session['verified_student']['name']
    count = database.get_unread_notification_count(nickname)
    return jsonify({'success': True, 'count': count})


@app.route('/api/notifications/mark_read', methods=['POST'])
def mark_notifications_read():
    """标记通知为已读"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    data = request.get_json()
    nickname = session['verified_student']['name']
    notification_id = data.get('id')
    if notification_id:
        database.mark_notification_read(notification_id, nickname)
    else:
        database.mark_all_notifications_read(nickname)
    return jsonify({'success': True})


@app.route('/api/update_profile', methods=['POST'])
def update_profile():
    """更新个人信息"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先验证身份'})

    verify_time = datetime.fromisoformat(session['verify_time'])
    if datetime.now() - verify_time >= timedelta(minutes=30):
        session.pop('verified_student', None)
        return jsonify({'success': False, 'message': '验证已过期，请重新验证'})

    data = request.get_json()
    current_name = session['verified_student']['name']
    current_id = session['verified_student']['id']

    students = database.read_txl()
    for s in students:
        if s['name'] == current_name and s['id'] == current_id:
            # 记录所有旧值用于比较
            old_values = {k: s.get(k, '') for k in ['phone', 'note', 'custom_intro', 'hobby', 'dream', 'industry', 'company', 'weibo', 'xiaohongshu', 'douyin', 'wechat', 'qq', 'email', 'work', 'position', 'birthday', 'github', 'avatar', 'hometown', 'city', 'district']}

            if 'phone' in data:
                s['phone'] = sanitize_input(data['phone'])
            if 'hometown' in data:
                s['hometown'] = sanitize_input(data['hometown'])
                s['hometown_name'] = get_province_name(s['hometown'])
            if 'city' in data:
                city_val = sanitize_input(data['city'])
                s['city'] = get_city_name(city_val) if city_val else city_val
            if 'district' in data:
                s['district'] = sanitize_input(data['district'])
            if 'note' in data:
                s['note'] = sanitize_input(data['note'])
            if 'avatar' in data:
                s['avatar'] = data['avatar']
            if 'custom_intro' in data:
                s['custom_intro'] = sanitize_input(data['custom_intro'])
            if 'hobby' in data:
                s['hobby'] = sanitize_input(data['hobby'])
            if 'dream' in data:
                s['dream'] = sanitize_input(data['dream'])
            if 'industry' in data:
                s['industry'] = sanitize_input(data['industry'])
            if 'company' in data:
                s['company'] = sanitize_input(data['company'])
            if 'weibo' in data:
                s['weibo'] = sanitize_input(data['weibo'])
            if 'xiaohongshu' in data:
                s['xiaohongshu'] = sanitize_input(data['xiaohongshu'])
            if 'douyin' in data:
                s['douyin'] = sanitize_input(data['douyin'])

            database.write_txl(students)

            # 检查是否有任何字段发生变化
            changed = False
            for key in old_values:
                if s.get(key, '') != old_values[key]:
                    changed = True
                    break

            if changed:
                database.write_activity(current_name, 'profile_update', '更新了个人信息')

            return jsonify({'success': True, 'message': '更新成功'})

    return jsonify({'success': False, 'message': '未找到该同学信息'})


@app.route('/api/add_message', methods=['POST'])
def add_message():
    """添加留言"""
    data = request.get_json()
    content = sanitize_input(data.get('content', ''))
    image = data.get('image', '')

    # 优先使用真实姓名（已登录），否则使用昵称
    if 'verified_student' in session:
        nickname = session['verified_student']['name']
    else:
        nickname = sanitize_input(data.get('nickname', '穆玉升'))

    if not content:
        return jsonify({'success': False, 'message': '留言内容不能为空'})

    if len(content) > 500:
        return jsonify({'success': False, 'message': '留言内容过长'})

    message = {
        'id': database.get_next_lyb_id(),
        'nickname': nickname[:50],
        'content': content[:500],
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'image': image,
        'voice': ''
    }

    messages = database.read_lyb()
    messages.append(message)
    database.write_lyb(messages)

    # 记录活动日志
    database.write_activity(nickname, 'message', content[:50])

    return jsonify({'success': True, 'message': message})


@app.route('/api/add_voice_message', methods=['POST'])
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


@app.route('/api/upload_avatar', methods=['POST'])
def upload_avatar():
    """上传头像"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先验证身份'})

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '没有文件'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '没有选择文件'})

    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        student_id = session['verified_student']['id']
        filename = f"avatar_{student_id}.{ext}"
        avatars_dir = os.path.join(DATA_DIR, 'static/imgs/avatars')
        os.makedirs(avatars_dir, exist_ok=True)
        filepath = os.path.join(avatars_dir, filename)
        compress_avatar(file, filepath)

        avatar_url = f'/static/imgs/avatars/{filename}'

        # 更新数据库中的头像路径
        current_name = session['verified_student']['name']
        students = database.read_txl()
        for s in students:
            if s['name'] == current_name and s['id'] == student_id:
                s['avatar'] = avatar_url
                database.write_txl(students)
                break

        return jsonify({
            'success': True,
            'message': '上传成功',
            'url': avatar_url
        })

    return jsonify({'success': False, 'message': '不支持的文件类型'})


# 个人中心专用接口
@app.route('/upload_avatar', methods=['POST'])
def upload_avatar_pc():
    """个人中心上传头像"""
    try:
        if 'verified_student' not in session:
            return jsonify({'success': False, 'message': '请先验证身份'})

        if 'avatar' not in request.files:
            return jsonify({'success': False, 'message': '没有文件'})

        file = request.files['avatar']
        if file.filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'})

        if file and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            student_id = session['verified_student']['id']
            filename = f"avatar_{student_id}.{ext}"
            avatars_dir = os.path.join(DATA_DIR, 'static/imgs/avatars')
            os.makedirs(avatars_dir, exist_ok=True)
            filepath = os.path.join(avatars_dir, filename)

            # 压缩头像，如果失败则删除文件并返回错误
            result = compress_avatar(file, filepath)
            if result is False:
                return jsonify({'success': False, 'message': '图片处理失败，请尝试其他图片'})

            avatar_url = f'/static/imgs/avatars/{filename}'

            # 更新数据库中的头像路径
            current_name = session['verified_student']['name']
            students = database.read_txl()
            for s in students:
                if s['name'] == current_name and s['id'] == student_id:
                    s['avatar'] = avatar_url
                    database.write_txl(students)
                    break

            return jsonify({
                'success': True,
                'message': '上传成功',
                'avatar_url': avatar_url
            })

        return jsonify({'success': False, 'message': '不支持的文件类型'})
    except Exception as e:
        app.logger.error(f"Upload avatar error: {e}")
        return jsonify({'success': False, 'message': f'服务器错误: {str(e)}'})


@app.route('/update_profile', methods=['POST'])
def update_profile_pc():
    """个人中心更新资料"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先验证身份'})

    current_name = session['verified_student']['name']
    current_id = session['verified_student']['id']

    students = database.read_txl()
    for s in students:
        if s['name'] == current_name and s['id'] == current_id:
            # 记录所有旧值用于比较
            old_values = {k: s.get(k, '') for k in ['phone', 'note', 'custom_intro', 'hobby', 'dream', 'industry', 'company', 'weibo', 'xiaohongshu', 'douyin', 'wechat', 'qq', 'email', 'work', 'position', 'birthday', 'github', 'avatar', 'hometown', 'city', 'district']}

            # 处理各种字段
            for field in ['phone', 'wechat', 'qq', 'email', 'work', 'position',
                         'birthday', 'hobby', 'dream', 'github',
                         'douyin', 'xiaohongshu', 'avatar', 'industry', 'company',
                         'custom_intro', 'note']:
                if field in request.form:
                    value = sanitize_input(request.form[field]) if field != 'avatar' else request.form[field]
                    s[field] = value

            # 单独处理hometown,city,district（需要特殊转换）
            if 'hometown' in request.form:
                s['hometown'] = sanitize_input(request.form['hometown'])
                s['hometown_name'] = get_province_name(s['hometown'])
            if 'city' in request.form:
                city_val = sanitize_input(request.form['city'])
                s['city'] = get_city_name(city_val) if city_val else city_val
            if 'district' in request.form:
                s['district'] = sanitize_input(request.form['district'])

            database.write_txl(students)

            # 检查是否有任何字段发生变化
            changed = False
            for key in old_values:
                if s.get(key, '') != old_values[key]:
                    changed = True
                    break

            if changed:
                database.write_activity(current_name, 'profile_update', '更新了个人信息')

            return jsonify({'success': True, 'message': '更新成功'})

    return jsonify({'success': False, 'message': '未找到该同学信息'})


@app.route('/api/upload_image', methods=['POST'])
def upload_image():
    """上传留言图片"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先验证身份'})

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '没有文件'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '没有选择文件'})

    year = request.form.get('year', '2020')
    try:
        year = int(year)
        if year < 2015 or year > 2026:
            year = 2020
    except:
        year = 2020

    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        messages_dir = os.path.join(DATA_DIR, 'static/imgs/messages')
        thumbs_dir = os.path.join(DATA_DIR, 'static/imgs/thumbs')
        os.makedirs(messages_dir, exist_ok=True)
        os.makedirs(thumbs_dir, exist_ok=True)

        # 保存原图
        filepath = os.path.join(messages_dir, filename)
        file.save(filepath)

        # 压缩图片
        compress_image(filepath)

        # 生成缩略图
        thumb_filename = f"thumb_{filename}"
        thumb_filepath = os.path.join(thumbs_dir, thumb_filename)
        create_thumbnail(filepath, thumb_filepath)

        # 如果提供了有效年份（不是2020），则添加到相册数据库
        if year and year != 2020:
            nickname = session['verified_student']['name']
            photos = database.read_photos()
            new_photo = {
                'id': database.get_next_photo_id(),
                'filename': filename,
                'owner': nickname,
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'year': year
            }
            photos.append(new_photo)
            database.write_photos(photos)
            # 记录活动日志
            database.write_activity(nickname, 'photo', f'上传了新照片《{filename}》')

        return jsonify({
            'success': True,
            'message': '上传成功',
            'url': f'/static/imgs/messages/{filename}',
            'thumb_url': f'/static/imgs/thumbs/{thumb_filename}'
        })

    return jsonify({'success': False, 'message': '不支持的文件类型'})


@app.route('/api/upload_voice_shout', methods=['POST'])
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
        content=f'{from_name}对你喊了一段话，快去听听吧！',
        target_name=to_name
    )

    return jsonify({
        'success': True,
        'message': '喊话成功',
        'id': shout_id,
        'url': audio_url
    })


@app.route('/api/get_voice_shouts/<target_name>')
def get_voice_shouts(target_name):
    """获取某人的喊话"""
    shouts = database.get_voice_shouts_by_target(target_name)
    return jsonify({'success': True, 'shouts': shouts})


@app.route('/api/voice_shout/delete', methods=['POST'])
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


@app.route('/api/voice_shout/restore', methods=['POST'])
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


@app.route('/api/add_video', methods=['POST'])
def add_video():
    """添加视频链接"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先验证身份'})

    data = request.get_json()
    title = sanitize_input(data.get('title', ''))
    url = sanitize_input(data.get('url', ''))

    if not title or not url:
        return jsonify({'success': False, 'message': '标题和链接不能为空'})

    nickname = session['verified_student']['name']
    video = {
        'id': database.get_next_video_id(),
        'title': title[:100],
        'url': url,
        'cover': '',
        'owner': nickname
    }

    videos = database.read_videos()
    videos.append(video)
    database.write_videos(videos)

    # 记录活动日志
    database.write_activity(nickname, 'video', f'分享了视频《{title}》')

    return jsonify({'success': True, 'message': '添加成功'})


@app.route('/add_video', methods=['POST'])
def add_video_pc():
    """媒体中心添加视频"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先验证身份'})

    data = request.get_json()
    title = sanitize_input(data.get('title', ''))
    url = sanitize_input(data.get('url', ''))

    if not title or not url:
        return jsonify({'success': False, 'message': '标题和链接不能为空'})

    nickname = session['verified_student']['name']
    video = {
        'id': database.get_next_video_id(),
        'title': title[:100],
        'url': url,
        'cover': '',
        'owner': nickname
    }

    videos = database.read_videos()
    videos.append(video)
    database.write_videos(videos)

    # 记录活动日志
    database.write_activity(nickname, 'video', f'分享了视频《{title}》')

    return jsonify({'success': True, 'message': '添加成功'})


@app.route('/api/upload_video', methods=['POST'])
def upload_video():
    """上传视频文件"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先验证身份'})

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '没有文件'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '没有选择文件'})

    title = request.form.get('title', '')
    if not title:
        return jsonify({'success': False, 'message': '请输入视频标题'})

    # 检查文件类型
    allowed_video_types = {'mp4', 'webm', 'ogg', 'mov', 'avi', 'wmv', 'flv', 'mkv'}
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    if ext not in allowed_video_types:
        return jsonify({'success': False, 'message': '不支持的视频格式'})

    nickname = session['verified_student']['name']
    filename = f"{uuid.uuid4().hex}.{ext}"
    videos_dir = os.path.join(DATA_DIR, 'static/videos')
    os.makedirs(videos_dir, exist_ok=True)

    filepath = os.path.join(videos_dir, filename)
    file.save(filepath)

    video = {
        'id': database.get_next_video_id(),
        'title': title[:100],
        'url': f'/static/videos/{filename}',
        'cover': '',
        'owner': nickname
    }

    videos = database.read_videos()
    videos.append(video)
    database.write_videos(videos)

    # 记录活动日志
    database.write_activity(nickname, 'video', f'分享了视频《{title}》')

    return jsonify({'success': True, 'message': '上传成功', 'url': video['url']})


@app.route('/api/get_student')
def get_student():
    """获取已验证同学的信息"""
    if 'verified_student' not in session:
        return jsonify({'success': False})

    students = database.read_txl()
    current_name = session['verified_student']['name']
    current_id = session['verified_student']['id']

    for s in students:
        if s['name'] == current_name and s['id'] == current_id:
            s['is_admin'] = is_admin(current_name)
            s['is_super_admin'] = is_super_admin(current_name)
            return jsonify({'success': True, 'student': s})

    return jsonify({'success': False})


@app.route('/api/delete_message', methods=['POST'])
def delete_message():
    """删除留言"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    data = request.get_json()
    msg_id = data.get('id')

    if not msg_id:
        return jsonify({'success': False, 'message': '无效的留言ID'})

    current_name = session['verified_student']['name']
    messages = database.read_lyb()

    # 找到留言并检查是否是本人（管理员可以删除任何留言）
    for i, msg in enumerate(messages):
        if str(msg['id']) == str(msg_id):
            if not is_admin(current_name) and msg['nickname'] != current_name:
                return jsonify({'success': False, 'message': '只能删除自己的留言'})

            # 记录到已删除列表
            deleted_item = {
                'id': database.get_next_deleted_id(),
                'type': 'message',
                'content': msg['content'][:100],
                'owner': msg['nickname'],
                'time': msg['time'],
                'deleted_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'extra': msg.get('image', ''),
                'deleted_by': current_name
            }
            deleted_items = database.read_deleted()
            deleted_items.append(deleted_item)
            database.write_deleted(deleted_items)

            # 从留言列表中删除
            messages.pop(i)
            database.write_lyb(messages)

            return jsonify({'success': True, 'message': '删除成功'})

    return jsonify({'success': False, 'message': '留言不存在'})


@app.route('/api/delete_video', methods=['POST'])
def delete_video():
    """删除视频"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    data = request.get_json()
    video_id = data.get('id')

    if not video_id:
        return jsonify({'success': False, 'message': '无效的视频ID'})

    current_name = session['verified_student']['name']
    videos = database.read_videos()

    # 找到视频并检查是否是本人（管理员可以删除任何视频，但需要验证密码）
    for i, video in enumerate(videos):
        if str(video['id']) == str(video_id):
            video_owner = video.get('owner', '')
            # 管理员可以删除任何视频
            if not is_admin(current_name) and video_owner != current_name:
                return jsonify({'success': False, 'message': '只能删除自己上传的视频'})

            # 记录到已删除列表
            deleted_item = {
                'id': database.get_next_deleted_id(),
                'type': 'video',
                'content': video['title'],
                'owner': video_owner,
                'time': '',
                'deleted_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'extra': video['url'],
                'deleted_by': current_name
            }
            deleted_items = database.read_deleted()
            deleted_items.append(deleted_item)
            database.write_deleted(deleted_items)

            return jsonify({'success': True, 'message': '删除成功'})

    return jsonify({'success': False, 'message': '视频不存在'})


@app.route('/api/delete_photo', methods=['POST'])
def delete_photo():
    """删除照片（只从列表移除，不删除源文件）"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    data = request.get_json()
    photo_id = data.get('id')
    filename = data.get('filename', '')

    current_name = session['verified_student']['name']
    photos = database.read_photos()

    # 如果有ID，从photos.csv中查找并删除记录
    if photo_id:
        for i, photo in enumerate(photos):
            if str(photo['id']) == str(photo_id):
                if not is_admin(current_name) and photo.get('owner') != current_name:
                    return jsonify({'success': False, 'message': '只能删除自己上传的照片'})

                # 记录到已删除列表
                deleted_item = {
                    'id': database.get_next_deleted_id(),
                    'type': 'photo',
                    'content': photo['filename'],
                    'owner': photo.get('owner', ''),
                    'time': photo.get('time', ''),
                    'deleted_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'extra': photo['filename'],
                    'deleted_by': current_name
                }
                deleted_items = database.read_deleted()
                deleted_items.append(deleted_item)
                database.write_deleted(deleted_items)

                return jsonify({'success': True, 'message': '删除成功'})

        return jsonify({'success': False, 'message': '照片不存在'})

    # 如果没有ID（旧照片），只有管理员可以删除，并记录到已删除列表
    elif filename:
        if not is_admin(current_name):
            return jsonify({'success': False, 'message': '只能删除自己上传的照片'})

        # 记录到已删除列表
        deleted_item = {
            'id': database.get_next_deleted_id(),
            'type': 'photo',
            'content': filename,
            'owner': current_name,
            'time': '',
            'deleted_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'extra': filename,
            'deleted_by': current_name
        }
        deleted_items = database.read_deleted()
        deleted_items.append(deleted_item)
        database.write_deleted(deleted_items)

        return jsonify({'success': True, 'message': '删除成功'})

    return jsonify({'success': False, 'message': '无效的照片ID或文件名'})


@app.route('/api/get_deleted')
def get_deleted():
    """获取当前用户的已删除项目，管理员可以看到所有删除记录"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    current_name = session['verified_student']['name']
    is_admin_user = is_admin(current_name)

    deleted_items = database.read_deleted()
    # 管理员可以看到所有删除记录，其他人只能看到自己的
    if is_admin_user:
        user_items = deleted_items
    else:
        user_items = [item for item in deleted_items if item['owner'] == current_name]

    # 按删除时间倒序
    user_items.sort(key=lambda x: x['deleted_time'], reverse=True)

    # 分页：每页5条
    page = request.args.get('page', 1, type=int)
    per_page = 5
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


@app.route('/api/restore_deleted', methods=['POST'])
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


@app.route('/api/permanent_delete', methods=['POST'])
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


@app.route('/api/delete_activity', methods=['POST'])
def delete_activity():
    """删除动态（仅管理员）"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    current_name = session['verified_student']['name']

    # 只有管理员可以删除动态
    if not is_admin(current_name):
        return jsonify({'success': False, 'message': '只有管理员可以删除动态'})

    data = request.get_json()
    activity_time = data.get('time')
    activity_actor = data.get('actor')
    activity_content = data.get('original_content') or data.get('content')

    if not activity_time or not activity_actor:
        return jsonify({'success': False, 'message': '参数不完整'})

    try:
        database.delete_activity(activity_time, activity_actor, activity_content)
        return jsonify({'success': True, 'message': '删除成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})


@app.route('/api/get_login_logs')
def get_login_logs():
    """获取登录日志（仅管理员，分页）"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    current_name = session['verified_student']['name']

    # 只有管理员可以查看登录日志
    if not is_admin(current_name):
        return jsonify({'success': False, 'message': '无权限查看'})

    page = int(request.args.get('page', 1))
    per_page = 5
    max_logs = 30  # 最多显示30条

    all_logs = database.read_login_logs(limit=1000)

    # 计算最近一周的统计（全量）
    one_week_ago = datetime.now() - timedelta(days=7)
    weekly_logs = []
    for log in all_logs:
        try:
            log_time = datetime.strptime(log['login_time'], '%Y-%m-%d %H:%M:%S')
            if log_time >= one_week_ago:
                weekly_logs.append(log)
        except:
            pass
    weekly_count = len(weekly_logs)
    weekly_users = len(set(log['username'] for log in weekly_logs))

    # 只取最新的30条
    all_logs = all_logs[:max_logs]
    total = len(all_logs)
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    start = (page - 1) * per_page
    end = start + per_page
    logs = all_logs[start:end]

    # 为每条日志添加IP归属地
    for log in logs:
        log['ip_location'] = get_ip_location(log.get('ip_address', ''))

    return jsonify({
        'success': True,
        'logs': logs,
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages,
        'weekly_count': weekly_count,
        'weekly_users': weekly_users
    })


@app.route('/api/admin/login_logs/delete', methods=['POST'])
def delete_login_logs():
    """删除指定用户的登录日志（仅超级管理员）"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    current_name = session['verified_student']['name']
    if not is_super_admin(current_name):
        return jsonify({'success': False, 'message': '只有超级管理员可以操作'})

    data = request.get_json()
    username = data.get('username', '')

    if not username:
        return jsonify({'success': False, 'message': '用户名不能为空'})

    deleted = database.delete_login_logs(username)
    return jsonify({'success': True, 'message': f'已删除 {deleted} 条记录'})


# ==================== 新闻模块 ====================

@app.route('/api/news')
def get_news():
    """获取新闻列表"""
    news = database.get_news(5)
    # 过滤掉旧新闻，只展示2026年的新闻
    from datetime import datetime
    current_year = datetime.now().year
    news = [n for n in news if int(n['published_time'][:4]) >= current_year]
    return jsonify({'success': True, 'news': news})


@app.route('/api/admin/news/crawl', methods=['POST'])
def crawl_news():
    """手动爬取新闻（仅管理员）"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    current_name = session['verified_student']['name']
    if not is_admin(current_name):
        return jsonify({'success': False, 'message': '无权限'})

    from datetime import datetime
    executed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        # 清空旧新闻
        database.clear_news()

        # 爬取新新闻
        news_list = news_crawler.fetch_jlu_news()

        # 保存到数据库
        image_count = 0
        for news in news_list:
            database.save_news(
                title=news['title'],
                content=news['content'],
                source_url=news['source_url'],
                image_url=news['image_url'],
                published_time=news['published_time']
            )
            # 统计下载的图片数量
            if news.get('image_url') and news['image_url'].startswith('/static/'):
                image_count += 1

        # 保存日志
        database.set_news_crawl_log(executed_at, 'success', len(news_list), f'手动爬取成功，下载 {image_count} 张图片')

        return jsonify({'success': True, 'message': f'成功爬取{len(news_list)}条新闻'})
    except Exception as e:
        database.set_news_crawl_log(executed_at, 'failed', 0, f'爬取失败: {str(e)}')
        return jsonify({'success': False, 'message': f'爬取失败: {str(e)}'})


@app.route('/api/admin/news/schedule', methods=['POST'])
def set_news_schedule():
    """设置新闻爬取时间（仅超级管理员）"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    current_name = session['verified_student']['name']
    if not is_super_admin(current_name):
        return jsonify({'success': False, 'message': '只有超级管理员可以设置'})

    data = request.get_json()
    hour = int(data.get('hour', 1))
    minute = int(data.get('minute', 0))

    database.set_config('news_crawl_hour', str(hour))
    database.set_config('news_crawl_minute', str(minute))

    # 更新调度器
    update_news_scheduler()

    return jsonify({'success': True, 'message': f'爬取时间已设置为{hour:02d}:{minute:02d}'})


@app.route('/api/admin/news/schedule', methods=['GET'])
def get_news_schedule():
    """获取新闻爬取时间（管理员可查看）"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    current_name = session['verified_student']['name']
    if not is_admin(current_name):
        return jsonify({'success': False, 'message': '无权限'})

    hour = int(database.get_config('news_crawl_hour', '1'))
    minute = int(database.get_config('news_crawl_minute', '0'))

    # 获取上次爬取日志
    log = database.get_news_crawl_log()

    return jsonify({
        'success': True,
        'hour': hour,
        'minute': minute,
        'last_crawl': log
    })


@app.route('/api/admin/news/keywords', methods=['GET'])
def get_news_keywords():
    """获取新闻爬取关键词（管理员可查看）"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    current_name = session['verified_student']['name']
    if not is_super_admin(current_name):
        return jsonify({'success': False, 'message': '无权限'})

    keywords = database.get_news_keywords()
    return jsonify({'success': True, 'keywords': keywords})


@app.route('/api/admin/news/keywords', methods=['POST'])
def set_news_keywords():
    """设置新闻爬取关键词（仅超级管理员），设置后触发爬虫"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    current_name = session['verified_student']['name']
    if not is_super_admin(current_name):
        return jsonify({'success': False, 'message': '只有超级管理员可以设置'})

    data = request.get_json()
    keywords = data.get('keywords', [])

    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split(',') if k.strip()]
    elif isinstance(keywords, list):
        keywords = [k.strip() for k in keywords if k.strip()]

    if not keywords:
        return jsonify({'success': False, 'message': '关键词不能为空'})

    # 保存关键词
    database.set_news_keywords(keywords)

    # 立即触发一次爬虫
    from datetime import datetime
    executed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        database.clear_news()
        news_list = news_crawler.fetch_jlu_news()
        for news in news_list:
            database.save_news(
                title=news['title'],
                content=news['content'],
                source_url=news['source_url'],
                image_url=news['image_url'],
                published_time=news['published_time']
            )
        database.set_news_crawl_log(executed_at, 'success', len(news_list), f'关键词更新后爬取成功')
        crawl_result = f'成功爬取{len(news_list)}条新闻'
    except Exception as e:
        database.set_news_crawl_log(executed_at, 'failed', 0, f'爬取失败: {str(e)}')
        crawl_result = f'爬取失败: {str(e)}'

    return jsonify({
        'success': True,
        'message': f'关键词已更新为: {",".join(keywords)}',
        'crawl_result': crawl_result
    })


def do_crawl_news():
    """执行新闻爬取（供调度器调用）"""
    from datetime import datetime
    executed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with app.app_context():
        try:
            database.clear_news()
            news_list = news_crawler.fetch_jlu_news()
            for news in news_list:
                database.save_news(
                    title=news['title'],
                    content=news['content'],
                    source_url=news['source_url'],
                    image_url=news['image_url'],
                    published_time=news['published_time']
                )
            database.set_news_crawl_log(executed_at, 'success', len(news_list), '定时爬取成功')
            print(f"[News Crawler] 成功爬取{len(news_list)}条新闻")
        except Exception as e:
            database.set_news_crawl_log(executed_at, 'failed', 0, f'定时爬取失败: {e}')
            print(f"[News Crawler] 爬取失败: {e}")


def update_news_scheduler():
    """更新新闻爬取调度器"""
    hour = int(database.get_config('news_crawl_hour', '1'))
    minute = int(database.get_config('news_crawl_minute', '0'))

    # 移除旧任务
    if hasattr(app, 'news_scheduler'):
        app.news_scheduler.remove_job('crawl_news')

    # 添加新任务
    app.news_scheduler.add_job(
        func=do_crawl_news,
        trigger='cron',
        hour=hour,
        minute=minute,
        id='crawl_news',
        replace_existing=True
    )


# 初始化调度器
def init_news_scheduler():
    """初始化新闻爬取调度器"""
    hour = int(database.get_config('news_crawl_hour', '1'))
    minute = int(database.get_config('news_crawl_minute', '0'))

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=do_crawl_news,
        trigger='cron',
        hour=hour,
        minute=minute,
        id='crawl_news',
        replace_existing=True
    )
    scheduler.start()
    app.news_scheduler = scheduler
    print(f"[News Scheduler] 已启动，每天{hour:02d}:{minute:02d}自动爬取新闻")


if __name__ == '__main__':
    init_news_scheduler()
    app.run(host='0.0.0.0', port=5000, debug=False)
