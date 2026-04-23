"""
吉达通信八班 同学录网站
Flask Web Application
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import csv
import json
import os
import uuid
import re
from datetime import datetime, timedelta
from functools import wraps
import database
import news_crawler
from wx_api import wx_bp

# ===== 从新模块导入 =====
from config import (
    SECRET_KEY, MAX_CONTENT_LENGTH, UPLOAD_FOLDER, ALLOWED_EXTENSIONS,
    SESSION_COOKIE_SAMESITE, SESSION_COOKIE_SECURE, SESSION_COOKIE_HTTPONLY,
    SESSION_COOKIE_NAME, SESSION_COOKIE_PATH,
    DATA_DIR, TXL_FILE, LYB_FILE, VIDEOS_FILE, PHOTOS_FILE, DELETED_FILE,
    CACHE_TTL, ADMIN_USERS,
    AVATAR_MAX_SIZE, IMAGE_MAX_SIZE, IMAGE_QUALITY, THUMBNAIL_SIZE,
    PUBLIC_ROUTES,
)
from utils import (
    compress_avatar, compress_image, create_thumbnail,
    get_ip_location, get_real_ip, allowed_file, sanitize_input,
    haversine_distance, is_public_path,
    _news_cache, _alumni_cache,
    _get_cached_news, _set_cached_news,
    _get_cached_alumni, _set_cached_alumni,
)
from decorators import is_admin, is_super_admin, is_password_verified, require_login
from errors import register_error_handlers
from extensions import init_news_scheduler, update_news_scheduler
from location_data import (
    LOCATION_DATA, PROVINCE_NAME_TO_CODE, PROVINCE_CODE_TO_NAME,
    CITY_NAME_TO_CODE, CITY_CODE_TO_NAME, NAME_TO_PROVINCE_PINYIN,
    _strip_province_suffix,
)
from blueprints.news import news_bp
from blueprints.location import location_bp

app = Flask(__name__)
app.register_blueprint(wx_bp)
app.register_blueprint(news_bp)
app.register_blueprint(location_bp)
app.secret_key = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS
app.config['SESSION_COOKIE_SAMESITE'] = SESSION_COOKIE_SAMESITE
app.config['SESSION_COOKIE_SECURE'] = SESSION_COOKIE_SECURE
app.config['SESSION_COOKIE_HTTPONLY'] = SESSION_COOKIE_HTTPONLY
app.config['SESSION_COOKIE_NAME'] = SESSION_COOKIE_NAME
app.config['SESSION_COOKIE_PATH'] = SESSION_COOKIE_PATH

# 禁用页面缓存
@app.after_request
def add_no_cache_headers(response):
    # 静态文件缓存1小时，动态页面不缓存
    if request.path.startswith('/static/'): 
        response.headers['Cache-Control'] = 'public, max-age=3600'
    else:
        # 更强的缓存控制 - 特别针对微信浏览器
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0, private'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        # 微信浏览器需要这个 header
        response.headers['Surrogate-Control'] = 'no-store'
    return response

AVATAR_MAX_SIZE = 500 * 1024  # 500KB for avatars

# 错误处理统一注册（见 errors.py）

# get_ip_location, get_real_ip 已迁移到 utils.py
# get_real_ip 需要传入 request 参数（保持兼容）
# get_real_ip 已迁移到 utils.py, 调用 get_real_ip(request)
# ADMIN_USERS 已从 config.py 导入
# is_admin, is_super_admin, is_password_verified 已迁移到 decorators.py


# compress_avatar, compress_image, create_thumbnail 已迁移到 utils.py
# DATA_DIR 等路径配置已迁移到 config.py


# 初始化数据库
database.init_db()
database.migrate_from_csv()
database.create_wx_bindings_table()
database.add_wx_openid_column()


# 文件上传错误处理
@app.errorhandler(413)
def request_entity_too_large(e):
    return jsonify({'success': False, 'message': '文件过大,请选择小于20MB的图片'}), 413
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

# 中文名到拼音的反向映射
NAME_TO_PROVINCE_PINYIN = {v: k for k, v in PROVINCE_MAP.items()}

# 省份坐标(用于地图展示,简化版中国地图)
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


# allowed_file 已迁移到 utils.py
# get_province_name 已迁移到 utils.py
# get_student_coords 已迁移到 utils.py (get_province_name + PROVINCE_COORDS)
# sanitize_input 已迁移到 utils.py
# ==================== 登录保护 ====================

# 公开路由（无需登录）
PUBLIC_ROUTES = {'/login', '/api/captcha', '/api/check_user_login_password', '/api/verify', '/static'}

# is_public_path 已迁移到 utils.py
@app.before_request
def require_login():
    """未登录用户只能访问登录页"""
    if 'verified_student' not in session and not is_public_path(request.path):
        redirect_url = request.path
        if request.query_string:
            redirect_url += '?' + request.query_string.decode('utf-8')
        return redirect(f'/login?redirect={redirect_url}')

@app.route('/login')
def login_page():
    """登录页"""
    if 'verified_student' in session:
        # 已登录，跳转到原页面或留言页
        redirect_url = request.args.get('redirect', '/lyb')
        return redirect(redirect_url)
    return render_template('login.html')


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

    # 按时间倒序获取最新留言(最多12条)
    sorted_messages = sorted(messages, key=lambda x: x['time'], reverse=True)
    recent_messages = sorted_messages[:1]  # 只显示一条最新留言

    activities = get_activities()

    # 获取照片,按年份分组,每年最多3张
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
                           province_stats=province_stats,
                           logged_in='verified_student' in session)


def get_activities():
    """获取最新动态(去重:同一人连续同类型动态只保留最新一条)"""
    activities = []

    # 检查生日动态(提前5天开始显示)
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
                # 如果今年的生日已过但还没到,看明年的
                if this_year_birthday < today and (today - this_year_birthday).days > 5:
                    this_year_birthday = datetime(today.year + 1, birthday_month, birthday_day)
                # 检查是否在5天内
                days_until = (this_year_birthday - today).days
                if 0 <= days_until <= 5:
                    pronoun = '他' if student.get('gender', '') == '男' else '她'
                    if days_until == 0:
                        content = f'🎂 今天{student["name"]}生日!祝{pronoun}生日快乐!'
                    else:
                        content = f'🎂 {student["name"]} {birthday_month}月{birthday_day}日生日,还有{days_until}天,提前祝{pronoun}生日快乐!'
                    activities.append({
                        'type': 'birthday',
                        'actor': student['name'],
                        'content': content,
                        'time': this_year_birthday.strftime('%Y-%m-%d 00:00:00')
                    })
            except:
                pass

    messages = database.read_lyb()

    # 留言动态(取最新10条留言)
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
            content = '发表了新留言,并附带图片'
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

    # 从活动日志读取(profile_update、photo、video等)
    activity_logs = database.read_activities()
    for log in activity_logs[:20]:
        activity = {
            'type': log['type'],
            'actor': log['actor'],
            'content': log['content'],
            'time': log['time']
        }
        # 照片活动:从内容中提取文件名
        if log['type'] == 'photo':
            import re
            match = re.search(r'《(.+?)》', log['content'])
            if match:
                activity['img_name'] = match.group(1)
                activity['img_url'] = f'/static/imgs/messages/{match.group(1)}'
        # 视频活动:从内容中提取标题
        if log['type'] == 'video':
            import re
            match = re.search(r'《(.+?)》', log['content'])
            if match:
                activity['video_title'] = match.group(1)
        # 喊话活动:从内容中提取目标人名
        if log['type'] == 'voice_shout':
            import re
            match = re.search(r'对(.+?)喊', log['content'])
            if match:
                activity['target_name'] = match.group(1)
        activities.append(activity)

    # 按时间排序
    activities.sort(key=lambda x: x['time'], reverse=True)

    # 合并统计:同一人同类动态合并显示数量
    deduplicated = []
    for activity in activities:
        if not deduplicated:
            activity['count'] = 1
            activity['original_content'] = activity.get('content', '')  # 保存原始内容用于删除
            deduplicated.append(activity)
        else:
            last = deduplicated[-1]
            # 如果当前条目和上一个条目的actor和type都相同,累加计数
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
    """获取相册图片(按最新上传时间排序),排除已删除的照片"""
    photos = database.read_photos()
    deleted_items = database.read_deleted()
    # 获取已删除的文件名集合
    # filename可能在content(文件删除)或extra(ID删除)字段中
    deleted_filenames = set()
    for item in deleted_items:
        if item.get('type') == 'photo':
            # 对于照片,filename可能在content或extra字段中
            fn = item.get('content', '')
            if fn and fn not in deleted_filenames:
                deleted_filenames.add(fn)
            fn2 = item.get('extra', '')
            if fn2 and fn2 not in deleted_filenames:
                deleted_filenames.add(fn2)

    img_files = []
    avatars_dir = os.path.join(DATA_DIR, 'static/imgs/avatars')
    upload_dir = os.path.join(DATA_DIR, 'static/imgs')

    # 已知照片(从photos.csv)
    known_filenames = set()
    messages_dir = os.path.join(DATA_DIR, 'static/imgs/messages')
    for p in photos:
        # 跳过已删除的照片
        if p['filename'] in deleted_filenames:
            continue
        # 跳过留言板图片(没有年份或年份为0或年份为2020的视为留言板图片)
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

    # 扫描文件系统(static/imgs/下的图片,排除avatars子文件夹)
    if os.path.exists(upload_dir):
        for f in os.listdir(upload_dir):
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                # 跳过已删除的照片
                if f in deleted_filenames:
                    continue
                filepath = os.path.join(upload_dir, f)
                # 跳过子文件夹(如avatars)
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

    # 按上传时间倒序(最新在前)
    img_files.sort(key=lambda x: x['time'], reverse=True)
    return img_files


@app.route('/txl')
def txl():
    """通讯录页面"""
    is_logged = 'verified_student' in session

    # 未登录用户:不能查看同学通讯录
    if not is_logged:
        students = []
    else:
        students = database.read_txl()

    # 为每个学生添加拼音用于排序
    try:
        from pypinyin import lazy_pinyin
        for s in students:
            s['pinyin'] = ''.join(lazy_pinyin(s.get('name', '')))
    except:
        for s in students:
            s['pinyin'] = s.get('name', '')

    # 为没有坐标的学生填充坐标(根据城市名和区)
    for s in students:
        if not s.get('coords'):
            city = s.get('city', '') or s.get('hometown_name', '')
            district = s.get('district', '')
            if city:
                coords = database.get_coords_by_city(city, district)
                if coords:
                    s['coords'] = coords

    voice_shouts = database.read_voice_shouts()

    # 计算离我最近的同学(仅登录用户)
    nearest_classmates = []
    if is_logged:
        current_user = session['verified_student']
        # 优先使用GPS坐标,其次使用session中的城市坐标,最后根据当前用户的城市查找
        current_coords = current_user.get('coords', '')
        current_name = current_user.get('name', '')
        current_id = current_user.get('id', '')

        # 查找当前用户的GPS坐标(优先使用)
        for s in students:
            if s.get('name') == current_name and s.get('id') == current_id:
                gps = s.get('gps_coords', '')
                if gps:
                    current_coords = gps
                break

        # 如果没有GPS坐标也没有session坐标,根据城市获取
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
                    # 优先使用同学的GPS坐标,其次使用城市坐标
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

    return render_template('txl.html', students=students, voice_shouts=voice_shouts, nearest_classmates=nearest_classmates, logged_in=is_logged)


# haversine_distance 已迁移到 utils.py
# 地区数据加载已迁移到 location_data.py
LOCATION_DATA = {
    'provinces': [],
    'cities': {},
    'districts': {}
}

# 名称到代码的映射（用于回填用户数据）
PROVINCE_NAME_TO_CODE = {}
PROVINCE_CODE_TO_NAME = {}
CITY_NAME_TO_CODE = {}
CITY_CODE_TO_NAME = {}
CITY_CODE_PREFIX_TO_CODE = {}  # (province_prefix, city_suffix) -> full_city_code

def _strip_province_suffix(name):
    """去掉省份名称的后缀（省、市、自治区、特别行政区）"""
    if not name:
        return name
    for suffix in ['特别行政区', '自治区', '省', '市']:
        if name.endswith(suffix):
            return name[:-len(suffix)]
    return name

def _load_location_data():
    """加载地区数据到内存"""
    import json as _json
    base_path = os.path.join(os.path.dirname(__file__), 'static/js/location')

    # 加载省份
    with open(os.path.join(base_path, 'province.json'), encoding='utf-8') as f:
        provinces = _json.load(f)
    LOCATION_DATA['provinces'] = [{'code': p['code'], 'name': p['name']} for p in provinces]
    for p in provinces:
        PROVINCE_NAME_TO_CODE[p['name']] = p['code']
        PROVINCE_CODE_TO_NAME[p['code']] = p['name']
        # 同时添加去掉后缀的简称
        short_name = _strip_province_suffix(p['name'])
        if short_name != p['name']:
            PROVINCE_NAME_TO_CODE[short_name] = p['code']

    # 加载城市，按省份分组，同时构建反向映射
    with open(os.path.join(base_path, 'city.json'), encoding='utf-8') as f:
        cities = _json.load(f)
    for city in cities:
        prov = city['province']
        full_code = city['code']
        if prov not in LOCATION_DATA['cities']:
            LOCATION_DATA['cities'][prov] = []
        LOCATION_DATA['cities'][prov].append({'code': full_code, 'name': city['name']})
        CITY_NAME_TO_CODE[city['name']] = full_code
        CITY_CODE_TO_NAME[full_code] = city['name']
        # 构建 (province_prefix, city_suffix) -> full_code 的映射
        prov_prefix = prov  # 2位省份码
        city_suffix = city['city']  # 2位城市码
        CITY_CODE_PREFIX_TO_CODE[(prov_prefix, city_suffix)] = full_code

    # 加载区县，需要将short city code转换为full city code
    with open(os.path.join(base_path, 'area.json'), encoding='utf-8') as f:
        areas = _json.load(f)
    for area in areas:
        prov = area['province']
        city_short = area['city']  # 短码如 "01"
        # 尝试构建完整的城市代码
        full_city_code = CITY_CODE_PREFIX_TO_CODE.get((prov, city_short))
        if full_city_code:
            # 普通城市：使用完整城市代码作为键
            if full_city_code not in LOCATION_DATA['districts']:
                LOCATION_DATA['districts'][full_city_code] = []
            LOCATION_DATA['districts'][full_city_code].append({'code': area['code'], 'name': area['name']})
        else:
            # 直辖市等没有城市条目：使用 "province_code" 作为键来存储区县
            prov_full_code = prov + '0000'  # 补齐为省份代码
            if prov_full_code not in LOCATION_DATA['districts']:
                LOCATION_DATA['districts'][prov_full_code] = []
            LOCATION_DATA['districts'][prov_full_code].append({'code': area['code'], 'name': area['name']})

# 启动时加载
_load_location_data()

def get_location_names(province_code, city_code, district_code):
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

@app.route('/api/location/codes_to_names')
def codes_to_names():
    """将地区代码转换为存储格式，用于保存用户数据"""
    province_code = request.args.get('province', '')
    city_code = request.args.get('city', '')
    district_code = request.args.get('district', '')

    result = get_location_names(province_code, city_code, district_code)
    return jsonify({'success': True, 'data': result})

# @app.route('/api/location/provinces') -> migrated to blueprints/location
# @app.route('/api/location/cities/<province_code>') -> migrated to blueprints/location
# @app.route('/api/location/districts/<city_code>') -> migrated to blueprints/location

@app.route('/api/location/lookup')
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


@app.route('/api/update_coords', methods=['POST'])
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
    logged_in = 'verified_student' in session
    messages = database.read_lyb()
    messages.reverse()
    # 为每条留言添加头像信息
    students = database.read_txl()
    for msg in messages:
        msg['avatar'] = ''
        for s in students:
            if s.get('name') == msg.get('nickname'):
                msg['avatar'] = s.get('avatar', '')
                break
    return render_template('lyb.html', messages=messages, logged_in=logged_in)


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
                    content=f'{nickname}评论了你的留言:{content_preview}'
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

    # 检查权限:评论人或楼主可以删除,管理员可以删除任何评论
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

    # 发送通知(仅当点赞成功且不是给自己点赞)
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
    from datetime import datetime

    # 检查登录状态
    logged_in = 'verified_student' in session

    img_files = get_gallery_images()
    videos = get_videos()
    news = database.get_news(100)

    # 过滤掉旧新闻,只展示今年的新闻
    current_year = datetime.now().year
    news = [n for n in news if int(n['published_time'][:4]) >= current_year]

    # 只排除校友会相关内容(留给校友会tab展示)
    alumni_keywords = ['校友会', '校友总会', '北京校友会', '上海校友会', '深圳校友会', '广州校友会',
                       '成都校友会', '武汉校友会', '北美校友会', '校友大会', '校友联谊', '校友活动',
                       '校友交流', '校友企业', '校友返校']
    news = [n for n in news if not any(kw in (n.get('title', '') + ' ' + n.get('content', '')).lower() for kw in alumni_keywords)]

    # 按日期+图片排序(最新优先,有图片的放前面)
    def news_sort_key(n):
        pub_time = n.get('published_time', '')
        if pub_time:
            try:
                date = datetime.strptime(pub_time[:10], '%Y-%m-%d')
            except:
                date = datetime.min
        else:
            date = datetime.min
        has_image = 1 if n.get('image_url') else 0
        # 日期降序(最新优先),图片优先(有图片=1 > 无图片=0)
        return (date, has_image)
    news.sort(key=news_sort_key, reverse=True)
    news = news[:20]  # 最多渲染20条新闻

    # 检查当前用户是否是管理员
    is_admin_user = False
    if 'verified_student' in session:
        current_name = session['verified_student']['name']
        is_admin_user = is_admin(current_name)

    return render_template('media.html', images=img_files, videos=videos, news=news, is_admin_user=is_admin_user, logged_in=logged_in)


def get_videos():
    """获取视频列表,排除已删除的视频"""
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
        # 跳过已删除的视频(通过URL或标题匹配)
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


@app.route('/ai-chat')
def ai_chat():
    """AI 聊天助手页面（仅管理员）"""
    return render_template('ai-chat.html')


# ==================== API接口 ====================

# @app.route('/api/captcha') -> migrated to blueprints/news

@app.route('/api/verify', methods=['POST'])
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


@app.route('/api/txl/list')
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


@app.route('/api/txl/map')
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


# 腾讯地图 Key 配置
TENCENT_MAP_KEY = ''  # 请替换为您的腾讯地图 Key


@app.route('/api/stats')
def public_stats():
    """获取公开统计数据"""
    students = database.read_txl()
    messages = database.read_lyb()
    photos = database.read_photos()
    return jsonify({
        'students': len(students),
        'messages': len(messages),
        'photos': len(photos)
    })


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
            # 检查用户密码状态和头像
            students = database.read_txl()
            for s in students:
                if s['name'] == current_name:
                    student['login_password_set'] = bool(s.get('login_password', ''))
                    student['avatar'] = s.get('avatar', '')  # 添加头像
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
    """获取所有动态(用于管理,分页)"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    page = int(request.args.get('page', 1))
    per_page = 3
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
        return jsonify({'success': False, 'message': '验证已过期,请重新验证'})

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

    # 优先使用真实姓名(已登录),否则使用昵称
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

            # 压缩头像,如果失败则删除文件并返回错误
            result = compress_avatar(file, filepath)
            if result is False:
                return jsonify({'success': False, 'message': '图片处理失败,请尝试其他图片'})

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

            # 单独处理hometown,city,district(需要特殊转换)
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


# ==================== 全站搜索 ====================

@app.route('/api/search')
def api_search():
    """全站搜索"""
    keyword = request.args.get('q', '').strip()
    if not keyword:
        return jsonify({'success': False, 'message': '请输入搜索关键词'})

    results = {
        'students': database.search_students(keyword),
        'messages': database.search_messages(keyword),
        'photos': database.search_photos(keyword),
    }
    return jsonify({'success': True, 'keyword': keyword, 'results': results})


# ==================== 个人主页增强 ====================

@app.route('/api/profile/data')
def api_profile_data():
    """获取个人主页增强数据"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    user = session['verified_student']
    name = user['name']

    data = {
        'messages': database.get_messages_by_user(name),
        'photos': database.get_photos_by_user(name),
        'activities': database.get_activities_by_user(name),
        'last_active': database.get_user_last_active(name),
        'visitors': database.get_visitors(name),
    }
    return jsonify({'success': True, 'data': data})


@app.route('/api/profile/<name>')
def api_public_profile(name):
    """获取他人公开主页信息"""
    student = database.get_student_by_name(name)
    if not student:
        return jsonify({'success': False, 'message': '未找到该同学'})

    data = {
        'name': student.get('name', ''),
        'hometown_name': student.get('hometown_name', ''),
        'city': student.get('city', ''),
        'industry': student.get('industry', ''),
        'company': student.get('company', ''),
        'position': student.get('position', ''),
        'avatar': student.get('avatar', ''),
        'custom_intro': student.get('custom_intro', ''),
        'last_active': database.get_user_last_active(name),
        'messages': database.get_messages_by_user(name, limit=10),
        'photos': database.get_photos_by_user(name, limit=10),
    }
    return jsonify({'success': True, 'data': data})


@app.route('/api/visit/<name>', methods=['POST'])
def api_record_visit(name):
    """记录访客"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    visitor = session['verified_student']['name']
    database.record_visit(visitor, name)
    return jsonify({'success': True})


# ==================== 评论回复 ====================

@app.route('/api/add_reply', methods=['POST'])
def api_add_reply():
    """添加回复（回复到评论）"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    data = request.get_json()
    message_id = data.get('message_id')
    parent_comment_id = data.get('parent_comment_id', 0)
    reply_to = data.get('reply_to', '')
    content = sanitize_input(data.get('content', ''))

    if not message_id or not content:
        return jsonify({'success': False, 'message': '参数错误'})

    nickname = session['verified_student']['name']
    reply_id = database.add_reply(message_id, nickname, reply_to, content, parent_comment_id)

    # 发送通知给评论作者或留言作者
    if reply_to:
        # 通知被回复的人
        database.create_notification(
            recipient=reply_to,
            sender=nickname,
            notif_type='reply',
            ref_id=message_id,
            content=f'{nickname}回复了你: {content[:50]}'
        )
    else:
        # 通知留言作者
        messages = database.read_lyb()
        for msg in messages:
            if str(msg['id']) == str(message_id):
                msg_owner = msg.get('nickname', '')
                if msg_owner and msg_owner != nickname:
                    database.create_notification(
                        recipient=msg_owner,
                        sender=nickname,
                        notif_type='reply',
                        ref_id=message_id,
                        content=f'{nickname}回复了你的留言: {content[:50]}'
                    )
                break

    return jsonify({
        'success': True,
        'id': reply_id,
        'nickname': nickname,
        'reply_to': reply_to,
        'content': content,
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


@app.route('/api/get_replies/<int:message_id>')
def api_get_replies(message_id):
    """获取某留言的所有回复"""
    replies = database.get_replies_by_message(message_id)
    return jsonify({'success': True, 'replies': replies})


@app.route('/api/delete_reply', methods=['POST'])
def api_delete_reply():
    """删除回复"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    data = request.get_json()
    reply_id = data.get('id')
    if not reply_id:
        return jsonify({'success': False, 'message': '无效的回复ID'})

    database.delete_reply(reply_id)
    return jsonify({'success': True})


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

        # 如果提供了有效年份(不是2020),则添加到相册数据库
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
        content=f'{from_name}对你喊了一段话,快去听听吧!',
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
        if s['name'] == current_name and str(s['id']) == str(current_id):
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

    # 找到留言并检查是否是本人(管理员可以删除任何留言)
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

    # 找到视频并检查是否是本人(管理员可以删除任何视频,但需要验证密码)
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
    """删除照片(只从列表移除,不删除源文件)"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    data = request.get_json()
    photo_id = data.get('id')
    filename = data.get('filename', '')

    current_name = session['verified_student']['name']
    photos = database.read_photos()

    # 如果有ID,从photos.csv中查找并删除记录
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

    # 如果没有ID(旧照片),只有管理员可以删除,并记录到已删除列表
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
    """获取当前用户的已删除项目,管理员可以看到所有删除记录"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    current_name = session['verified_student']['name']
    is_admin_user = is_admin(current_name)

    deleted_items = database.read_deleted()
    # 管理员可以看到所有删除记录,其他人只能看到自己的
    if is_admin_user:
        user_items = deleted_items
    else:
        user_items = [item for item in deleted_items if item['owner'] == current_name]

    # 按删除时间倒序
    user_items.sort(key=lambda x: x['deleted_time'], reverse=True)

    # 分页:每页3条
    page = request.args.get('page', 1, type=int)
    per_page = 3
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
    """删除动态(仅管理员)"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    current_name = session['verified_student']['name']

    # 只有管理员可以删除动态
    if not is_admin(current_name):
        return jsonify({'success': False, 'message': '只有管理员可以删除动态'})

    data = request.get_json()
    activity_time = data.get('time')
    activity_actor = data.get('actor')
    activity_type = data.get('type', 'message')
    activity_content = data.get('original_content') or data.get('content')

    if not activity_time or not activity_actor:
        return jsonify({'success': False, 'message': '参数不完整'})

    try:
        # 如果是留言动态,同时删除messages表中的记录
        if activity_type == 'message':
            database.delete_message_by_time_nickname(activity_time, activity_actor)
        database.delete_activity(activity_time, activity_actor, activity_content)
        return jsonify({'success': True, 'message': '删除成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})


@app.route('/api/get_login_logs')
def get_login_logs():
    """获取登录日志(仅超级管理员,分页)"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    current_name = session['verified_student']['name']

    # 只有超级管理员可以查看登录日志
    if not is_super_admin(current_name):
        return jsonify({'success': False, 'message': '无权限查看'})

    page = int(request.args.get('page', 1))
    per_page = 3
    max_logs = 30  # 最多显示30条

    all_logs = database.read_login_logs(limit=1000)

    # 计算最近一周的统计(全量)
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
    """删除指定用户的登录日志(仅超级管理员)"""
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


# ==================== 新闻模块 (已迁移到 blueprints/news) ====================
# @app.route('/api/news') -> migrated to blueprints/news
# @app.route('/api/alumni') -> migrated to blueprints/news


@app.route('/api/admin/news/crawl', methods=['POST'])
def crawl_news():
    """手动爬取新闻(仅管理员)"""
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
        database.set_news_crawl_log(executed_at, 'success', len(news_list), f'手动爬取成功,下载 {image_count} 张图片')

        # 清除缓存
        _news_cache['data'] = None
        _news_cache['timestamp'] = None
        _alumni_cache['data'] = None
        _alumni_cache['timestamp'] = None

        return jsonify({'success': True, 'message': f'成功爬取{len(news_list)}条新闻'})
    except Exception as e:
        database.set_news_crawl_log(executed_at, 'failed', 0, f'爬取失败: {str(e)}')
        return jsonify({'success': False, 'message': f'爬取失败: {str(e)}'})


@app.route('/api/admin/news/schedule', methods=['POST'])
def set_news_schedule():
    """设置新闻爬取时间(仅超级管理员)"""
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
    """获取新闻爬取时间(管理员可查看)"""
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


# ==================== OpenClaw 聊天模块 ====================

import subprocess

@app.route('/api/openclaw/chat', methods=['POST'])
def openclaw_chat():
    """与 OpenClaw AI 对话（仅管理员可用）"""
    if 'verified_student' not in session:
        return jsonify({'code': 401, 'message': '需要先登录', 'data': None})

    current_name = session['verified_student']['name']
    if not is_admin(current_name):
        return jsonify({'code': 403, 'message': '仅管理员可以使用此功能', 'data': None})

    data = request.json
    message = data.get('message', '').strip()
    if not message:
        return jsonify({'code': 1, 'message': '消息不能为空', 'data': None})

    if len(message) > 2000:
        return jsonify({'code': 1, 'message': '消息过长', 'data': None})

    # 文件锁防止并发冲突
    import fcntl
    lock_file = '/tmp/openclaw_chat.lock'
    lock_fd = open(lock_file, 'w')

    try:
        # 非阻塞获取锁，如果被占用则直接返回繁忙提示
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            lock_fd.close()
            return jsonify({'code': 1, 'message': 'AI正在处理其他请求，请稍后再试', 'data': None})

        result = subprocess.run(
            ['openclaw', 'agent', '--agent', 'web-agent', '--message', message, '--json'],
            capture_output=True, text=True, timeout=120
        )

        # 释放锁
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()

        output = json.loads(result.stdout)
        reply = output.get('result', {}).get('payloads', [{}])[0].get('text', '')
        if not reply:
            reply = '抱歉，AI 没有返回有效回复'

        # 保存聊天记录（异常也尝试保存）
        try:
            database.save_ai_chat(current_name, message, reply)
        except Exception as save_err:
            import logging
            logging.error(f'保存AI聊天记录失败: {save_err}')

        return jsonify({'code': 0, 'message': 'success', 'data': {'reply': reply}})
    except subprocess.TimeoutExpired:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        except:
            pass
        lock_fd.close()
        return jsonify({'code': 1, 'message': '请求超时，请稍后重试', 'data': None})
    except Exception as e:
        # 记录错误但不丢失用户消息
        import logging
        logging.error(f'AI聊天异常: {e}, 用户消息: {message[:50]}')
        # 即使异常也尝试保存用户消息
        try:
            database.save_ai_chat(current_name, message, f'错误: {str(e)[:100]}')
        except:
            pass
        return jsonify({'code': 1, 'message': f'错误: {str(e)}', 'data': None})
    except json.JSONDecodeError:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        except:
            pass
        lock_fd.close()
        return jsonify({'code': 1, 'message': 'AI 响应解析失败', 'data': None})
    except Exception as e:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        except:
            pass
        lock_fd.close()
        return jsonify({'code': 1, 'message': f'错误: {str(e)}', 'data': None})


def get_cpu_usage():
    """获取CPU使用率 (0-100)"""
    try:
        import psutil
        return psutil.cpu_percent(interval=1)
    except:
        # 如果没有psutil，使用/proc/stat
        try:
            with open('/proc/stat', 'r') as f:
                line = f.readline()
                fields = line.split()
                # cpu  user nice system idle iowait irq softirq
                idle = int(fields[4])
                total = sum(int(x) for x in fields[1:8])
                return 100 - (idle * 100.0 / total) if total > 0 else 0
        except:
            return 0


def check_openclaw_gateway():
    """检查 OpenClaw Gateway 状态，返回 (is_healthy, message)"""
    import subprocess
    import urllib.request
    import urllib.error

    # 方法1：直接检查Gateway HTTP端口是否可达（最快）
    gateway_url = 'http://127.0.0.1:18789'
    try:
        req = urllib.request.Request(gateway_url + '/', method='GET')
        req.add_header('User-Agent', 'OpenClaw-Check/1.0')
        with urllib.request.urlopen(req, timeout=3) as response:
            if response.status == 200:
                return True, 'ok'
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        return False, f'Gateway HTTP错误: {e.code}'
    except Exception as e:
        pass

    # 方法2：检查Gateway进程是否在运行
    try:
        result = subprocess.run(
            ['systemctl', '--user', 'is-active', 'openclaw-gateway'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and 'active' in result.stdout:
            return False, 'Gateway进程运行中但HTTP无响应'
        else:
            return False, 'Gateway服务未运行'
    except Exception as e:
        return False, f'检查异常: {str(e)}'

    return False, 'Gateway服务未启动或无响应'


@app.route('/api/openclaw/queue_status', methods=['GET'])
def get_openclaw_queue_status():
    """获取 AI 队列状态"""
    if 'verified_student' not in session:
        return jsonify({'code': 401, 'message': '需要先登录', 'data': None})

    current_name = session['verified_student']['name']
    if not is_admin(current_name):
        return jsonify({'code': 403, 'message': '仅管理员可以使用此功能', 'data': None})

    import time
    import json as json_module

    # 检查 CPU 使用率
    cpu_usage = get_cpu_usage()
    cpu_too_high = cpu_usage > 80  # CPU > 80% 认为过高

    # 检查 OpenClaw Gateway 状态
    gateway_healthy, gateway_message = check_openclaw_gateway()
    gateway_unhealthy = not gateway_healthy

    # 检查断开冷却期（30秒内刚断开，允许立即重新连接）
    cooldown_file = '/tmp/openclaw_disconnect_cooldown.json'
    in_cooldown = False
    try:
        if os.path.exists(cooldown_file):
            with open(cooldown_file, 'r') as f:
                cooldown_data = json_module.load(f)
            cooldown_elapsed = time.time() - cooldown_data.get('time', 0)
            if cooldown_elapsed < 30:
                in_cooldown = True
            else:
                os.remove(cooldown_file)
    except:
        pass

    # 检查是否有其他管理员连接
    conn_file = '/tmp/openclaw_connection.json'
    other_connected = None
    try:
        if os.path.exists(conn_file):
            with open(conn_file, 'r') as f:
                conn_data = json_module.load(f)
            # 如果是其他管理员连接且在5分钟内
            if conn_data.get('name') and conn_data.get('name') != current_name:
                elapsed = time.time() - conn_data.get('time', 0)
                if elapsed < 300:
                    other_connected = conn_data['name']
    except:
        pass

    # 读取 web-agent 会话文件获取最后更新时间
    sessions_file = '/root/.openclaw/agents/web-agent/sessions/sessions.json'
    try:
        with open(sessions_file, 'r') as f:
            sessions_data = json_module.load(f)

        # 获取 web-agent:main 会话的最后更新时间
        web_agent_session = sessions_data.get('agent:web-agent:main', {})
        last_updated = web_agent_session.get('updatedAt', 0)
        last_updated_seconds_ago = (int(time.time() * 1000) - last_updated) / 1000

        # 如果最后更新在5分钟内，认为可能正在处理中
        # 但如果在冷却期内（刚断开），允许绕过忙碌状态
        is_busy = last_updated_seconds_ago < 300 if not in_cooldown else False

        # 如果其他管理员连接中，也标记为忙
        if other_connected:
            is_busy = True

        # 如果CPU过高，也标记为忙
        if cpu_too_high:
            is_busy = True

        # 如果Gateway不健康，也标记为忙
        if gateway_unhealthy:
            is_busy = True

        return jsonify({
            'code': 0,
            'message': 'success',
            'data': {
                'is_busy': is_busy,
                'last_updated_seconds_ago': int(last_updated_seconds_ago),
                'other_connected': other_connected,
                'in_cooldown': in_cooldown,
                'cpu_usage': cpu_usage,
                'cpu_too_high': cpu_too_high,
                'gateway_healthy': gateway_healthy,
                'gateway_message': gateway_message
            }
        })
    except FileNotFoundError:
        return jsonify({'code': 0, 'message': 'success', 'data': {
            'is_busy': False,
            'last_updated_seconds_ago': 0,
            'other_connected': other_connected,
            'in_cooldown': in_cooldown,
            'cpu_usage': cpu_usage,
            'cpu_too_high': cpu_too_high,
            'gateway_healthy': gateway_healthy,
            'gateway_message': gateway_message
        }})
    except Exception as e:
        return jsonify({'code': 0, 'message': 'success', 'data': {
            'is_busy': False,
            'last_updated_seconds_ago': 0,
            'error': str(e)
        }})


@app.route('/api/openclaw/mark_connected', methods=['POST'])
def mark_connected():
    """标记当前管理员已连接AI"""
    if 'verified_student' not in session:
        return jsonify({'code': 401, 'message': '需要先登录', 'data': None})

    current_name = session['verified_student']['name']
    if not is_admin(current_name):
        return jsonify({'code': 403, 'message': '仅管理员可以使用此功能', 'data': None})

    import json
    import time

    conn_file = '/tmp/openclaw_connection.json'

    # 检查是否已有其他人连接
    try:
        if os.path.exists(conn_file):
            with open(conn_file, 'r') as f:
                conn_data = json.load(f)

            # 如果有其他管理员连接（超过5分钟未更新则忽略）
            if conn_data.get('name') and conn_data.get('name') != current_name:
                elapsed = time.time() - conn_data.get('time', 0)
                if elapsed < 300:  # 5分钟内
                    return jsonify({
                        'code': 1,
                        'message': f'{conn_data["name"]}正在使用AI聊天，请稍后再试',
                        'data': {'busy': True, 'by': conn_data.get('name')}
                    })
    except:
        pass

    # 写入连接状态
    with open(conn_file, 'w') as f:
        json.dump({
            'name': current_name,
            'time': time.time()
        }, f)

    # 清除冷却期文件
    cooldown_file = '/tmp/openclaw_disconnect_cooldown.json'
    try:
        if os.path.exists(cooldown_file):
            os.remove(cooldown_file)
    except:
        pass

    return jsonify({'code': 0, 'message': 'success', 'data': None})


@app.route('/api/openclaw/mark_disconnected', methods=['POST'])
def mark_disconnected():
    """标记当前管理员已断开AI连接"""
    if 'verified_student' not in session:
        return jsonify({'code': 401, 'message': '需要先登录', 'data': None})

    current_name = session['verified_student']['name']
    if not is_admin(current_name):
        return jsonify({'code': 403, 'message': '仅管理员可以使用此功能', 'data': None})

    import json
    conn_file = '/tmp/openclaw_connection.json'
    cooldown_file = '/tmp/openclaw_disconnect_cooldown.json'

    try:
        if os.path.exists(conn_file):
            with open(conn_file, 'r') as f:
                conn_data = json.load(f)

            # 只删除自己的连接
            if conn_data.get('name') == current_name:
                os.remove(conn_file)
                # 创建断开冷却文件，允许立即重新连接（30秒内）
                with open(cooldown_file, 'w') as f:
                    json.dump({'time': time.time()}, f)
    except:
        pass

    return jsonify({'code': 0, 'message': 'success', 'data': None})


@app.route('/api/openclaw/history', methods=['GET'])
def get_openclaw_history():
    """获取 AI 聊天记录

    - 超级管理员：可以查看所有人的记录，可按用户筛选
    - 普通管理员：只能查看自己的记录
    """
    if 'verified_student' not in session:
        return jsonify({'code': 401, 'message': '需要先登录', 'data': None})

    current_name = session['verified_student']['name']
    is_super = is_super_admin(current_name)

    # 获取请求参数
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    offset = (page - 1) * limit
    filter_user = request.args.get('user', None)  # 筛选特定用户

    # 普通管理员只能看自己的记录
    if is_super:
        history = database.get_ai_chat_history(user_name=filter_user, limit=limit, offset=offset)
        total = database.get_ai_chat_history_count(user_name=filter_user)
    else:
        history = database.get_ai_chat_history(user_name=current_name, limit=limit, offset=offset)
        total = database.get_ai_chat_history_count(user_name=current_name)

    return jsonify({
        'code': 0,
        'message': 'success',
        'data': {
            'history': history,
            'total': total,
            'page': page,
            'limit': limit,
            'pages': (total + limit - 1) // limit if limit > 0 else 0,
            'is_super_admin': is_super,
            'filter_user': filter_user
        }
    })


@app.route('/api/openclaw/history/users', methods=['GET'])
def get_ai_chat_history_users():
    """获取所有有聊天记录的用户列表（仅超级管理员）"""
    if 'verified_student' not in session:
        return jsonify({'code': 401, 'message': '需要先登录', 'data': None})

    if not is_super_admin(session['verified_student']['name']):
        return jsonify({'code': 403, 'message': '仅超级管理员可以使用此功能', 'data': None})

    users = database.get_ai_chat_history_users()
    return jsonify({'code': 0, 'message': 'success', 'data': users})


@app.route('/api/openclaw/history', methods=['DELETE'])
def delete_openclaw_history():
    """删除聊天记录（仅超级管理员）"""
    if 'verified_student' not in session:
        return jsonify({'code': 401, 'message': '需要先登录', 'data': None})

    current_name = session['verified_student']['name']
    if not is_super_admin(current_name):
        return jsonify({'code': 403, 'message': '仅超级管理员可以删除聊天记录', 'data': None})

    data = request.json
    user_name = data.get('user_name')
    if not user_name:
        return jsonify({'code': 1, 'message': '用户名不能为空', 'data': None})

    deleted = database.delete_ai_chat_history(user_name)
    return jsonify({'code': 0, 'message': 'success', 'data': {'deleted': deleted}})


@app.route('/api/admin/news/keywords', methods=['GET'])
def get_news_keywords():
    """获取新闻爬取关键词(管理员可查看)"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    current_name = session['verified_student']['name']
    if not is_super_admin(current_name):
        return jsonify({'success': False, 'message': '无权限'})

    keywords = database.get_news_keywords()
    return jsonify({'success': True, 'keywords': keywords})


@app.route('/api/admin/news/keywords', methods=['POST'])
def set_news_keywords():
    """设置新闻爬取关键词(仅超级管理员),设置后触发爬虫"""
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


@app.route('/api/admin/music/generate', methods=['POST'])
def generate_music():
    """AI生成背景音乐(管理员)"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    current_name = session['verified_student']['name']
    if not is_admin(current_name) and not is_super_admin(current_name):
        return jsonify({'success': False, 'message': '管理员才能生成音乐'})

    data = request.get_json()
    prompt = data.get('prompt', '')
    lyrics = data.get('lyrics', '')
    title = data.get('title', '背景音乐')

    if not prompt:
        return jsonify({'success': False, 'message': '请输入音乐描述'})

    import os
    api_key = database.get_config('minimax_api_key', '')
    if not api_key:
        return jsonify({'success': False, 'message': '请先在设置中配置MiniMax API Key'})

    import requests
    url = 'https://api.minimaxi.com/v1/music_generation'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    payload = {
        'model': 'music-2.6',
        'prompt': prompt,
        'lyrics': lyrics if lyrics else '[Inst]\n(纯音乐)',
        'audio_setting': {
            'sample_rate': 44100,
            'bitrate': 256000,
            'format': 'mp3'
        },
        'output_format': 'url'
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        result = response.json()

        if result.get('base_resp', {}).get('status_code') == 0:
            music_data = result.get('data', {})
            audio_url = music_data.get('audio') or music_data.get('audio_url', '')
            if audio_url:
                # 下载音频文件
                music_dir = '/home/ubuntu/jlu8/static/music'
                os.makedirs(music_dir, exist_ok=True)

                filename = f'bg-music-{datetime.now().strftime("%Y%m%d%H%M%S")}.mp3'
                filepath = os.path.join(music_dir, filename)

                audio_response = requests.get(audio_url, timeout=60)
                if audio_response.status_code == 200:
                    with open(filepath, 'wb') as f:
                        f.write(audio_response.content)

                    # 保存元数据
                    music_id = database.save_generated_music(
                        title=title,
                        prompt=prompt,
                        lyrics=lyrics,
                        filename=filename,
                        created_by=current_name
                    )

                    return jsonify({
                        'success': True,
                        'message': '音乐生成成功',
                        'music_id': music_id,
                        'filename': filename,
                        'url': f'/static/music/{filename}'
                    })

            return jsonify({'success': False, 'message': '生成失败，未获取到音频URL'})
        else:
            err_msg = result.get('base_resp', {}).get('status_msg', '未知错误')
            return jsonify({'success': False, 'message': f'生成失败: {err_msg}'})

    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'message': '请求超时，请稍后重试'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'生成异常: {str(e)}'})


@app.route('/api/admin/music/list', methods=['GET'])
def get_music_list():
    """获取生成的音乐列表(管理员)"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    current_name = session['verified_student']['name']
    if not is_admin(current_name) and not is_super_admin(current_name):
        return jsonify({'success': False, 'message': '无权限'})

    music_list = database.get_generated_music_list()
    return jsonify({'success': True, 'list': music_list})


@app.route('/api/admin/music/delete', methods=['POST'])
def delete_music():
    """删除生成的音乐(管理员)"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    current_name = session['verified_student']['name']
    if not is_admin(current_name) and not is_super_admin(current_name):
        return jsonify({'success': False, 'message': '无权限'})

    data = request.get_json()
    music_id = data.get('music_id')
    filename = data.get('filename')

    if music_id:
        database.delete_generated_music(music_id)

    if filename:
        filepath = f'/home/ubuntu/jlu8/static/music/{filename}'
        if os.path.exists(filepath):
            os.remove(filepath)

    return jsonify({'success': True, 'message': '删除成功'})


@app.route('/api/admin/music/apikey', methods=['GET'])
def get_music_apikey():
    """获取MiniMax API Key配置(仅超级管理员)"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    current_name = session['verified_student']['name']
    if not is_super_admin(current_name):
        return jsonify({'success': False, 'message': '无权限'})

    api_key = database.get_config('minimax_api_key', '')
    # 返回脱敏的key
    if api_key and len(api_key) > 8:
        masked = api_key[:6] + '****' + api_key[-4:]
    else:
        masked = ''
    return jsonify({'success': True, 'has_key': bool(api_key), 'masked_key': masked})


@app.route('/api/admin/music/apikey', methods=['POST'])
def set_music_apikey():
    """设置MiniMax API Key(仅超级管理员)"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    current_name = session['verified_student']['name']
    if not is_super_admin(current_name):
        return jsonify({'success': False, 'message': '无权限'})

    data = request.get_json()
    api_key = data.get('api_key', '').strip()

    if not api_key:
        return jsonify({'success': False, 'message': 'API Key不能为空'})

    database.set_config('minimax_api_key', api_key)
    return jsonify({'success': True, 'message': 'API Key设置成功'})


@app.route('/api/admin/music/setting', methods=['GET'])
def get_music_setting():
    """获取背景音乐设置(管理员)"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    current_name = session['verified_student']['name']
    if not is_admin(current_name) and not is_super_admin(current_name):
        return jsonify({'success': False, 'message': '无权限'})

    bg_music_timeline = database.get_config('bg_music_timeline', '')
    bg_music_gallery = database.get_config('bg_music_gallery', '')
    bg_music_vinyl = database.get_config('bg_music_vinyl', '')

    # 获取音乐详情
    def get_music_info(music_id):
        if not music_id:
            return None
        conn = database.get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM generated_music WHERE id = ?', (music_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    return jsonify({
        'success': True,
        'bg_music_timeline': get_music_info(bg_music_timeline),
        'bg_music_gallery': get_music_info(bg_music_gallery),
        'bg_music_vinyl': get_music_info(bg_music_vinyl)
    })


@app.route('/api/admin/music/setting', methods=['POST'])
def set_music_setting():
    """设置背景音乐(管理员)"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    current_name = session['verified_student']['name']
    if not is_admin(current_name) and not is_super_admin(current_name):
        return jsonify({'success': False, 'message': '无权限'})

    data = request.get_json()
    location = data.get('location')  # timeline, gallery, vinyl
    music_id = data.get('music_id')  # 音乐ID或空字符串(取消)

    if location not in ['timeline', 'gallery', 'vinyl']:
        return jsonify({'success': False, 'message': '无效的音乐位置'})

    config_key = f'bg_music_{location}'
    if music_id:
        database.set_config(config_key, str(music_id))
    else:
        # 取消设置 - 删除配置
        conn = database.get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM config WHERE key = ?', (config_key,))
        conn.commit()

    return jsonify({'success': True, 'message': '设置成功'})


@app.route('/api/music/bg', methods=['GET'])
def get_bg_music():
    """获取各位置背景音乐URL(公开)"""
    import os

    def get_music_url(music_id):
        if not music_id:
            return None
        conn = database.get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT filename FROM generated_music WHERE id = ?', (music_id,))
        row = cursor.fetchone()
        if row:
            filepath = f'/home/ubuntu/jlu8/static/music/{row[0]}'
            if os.path.exists(filepath):
                return f'/static/music/{row[0]}'
        return None

    bg_timeline = get_music_url(database.get_config('bg_music_timeline', ''))
    bg_gallery = get_music_url(database.get_config('bg_music_gallery', ''))
    bg_vinyl = get_music_url(database.get_config('bg_music_vinyl', ''))

    return jsonify({
        'success': True,
        'timeline': bg_timeline,
        'gallery': bg_gallery,
        'vinyl': bg_vinyl
    })


@app.route('/api/music/all', methods=['GET'])
def get_all_music():
    """获取所有AI生成的音乐(公开)"""
    import os
    music_list = database.get_generated_music_list()
    result = []
    for m in music_list:
        filepath = f'/home/ubuntu/jlu8/static/music/{m["filename"]}'
        if os.path.exists(filepath):
            result.append({
                'id': m['id'],
                'prompt': m.get('prompt', ''),
                'url': f'/static/music/{m["filename"]}'
            })
    return jsonify({'success': True, 'list': result})


@app.route('/api/ai_image/generate', methods=['POST'])
def generate_ai_image():
    """AI生成图片(需登录)"""
    if 'verified_student' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    data = request.get_json()
    prompt = data.get('prompt', '')
    ref_image = data.get('ref_image', '')  # base64编码的参考图，可选
    aspect_ratio = data.get('aspect_ratio', '1:1')

    if not prompt:
        return jsonify({'success': False, 'message': '请输入图片描述'})

    api_key = database.get_config('minimax_api_key', '')
    if not api_key:
        return jsonify({'success': False, 'message': '请先在管理页面配置MiniMax API Key'})

    import base64
    import requests
    import os

    try:
        url = 'https://api.minimaxi.com/v1/image_generation'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        payload = {
            'model': 'image-01',
            'prompt': prompt,
            'aspect_ratio': aspect_ratio,
            'response_format': 'base64'
        }
        if ref_image:
            payload['subject_reference'] = [{
                'type': 'character',
                'image_file': ref_image if ref_image.startswith('data:') else f'data:image/jpeg;base64,{ref_image}'
            }]

        response = requests.post(url, headers=headers, json=payload, timeout=120)
        result = response.json()
        print(f"[AI Image] API response keys: {result.keys()}")

        # MiniMax 图片生成 API 响应格式
        # 成功: {"id": "...", "data": {"image_base64": ["..."]}}
        # 失败: {"base_resp": {"status_code": 1004, "status_msg": "..."}}
        images = []
        status_code = result.get('base_resp', {}).get('status_code') if result.get('base_resp') else None

        if status_code is not None and status_code != 0:
            # 失败的响应
            err_msg = result.get('base_resp', {}).get('status_msg', '未知错误')
            return jsonify({'success': False, 'message': f'生成失败: {err_msg}'})

        # 获取图片数据
        data = result.get('data', {})
        if isinstance(data, dict):
            images = data.get('image_base64', [])
        elif isinstance(data, list) and len(data) > 0:
            images = [d.get('b64_json', '') for d in data if d.get('b64_json')]

        if not images or not images[0]:
            return jsonify({'success': False, 'message': '生成失败：未返回图片数据'})

        # 保存图片
        img_dir = os.path.join(DATA_DIR, 'static/imgs/messages')
        os.makedirs(img_dir, exist_ok=True)
        filename = f'ai-{datetime.now().strftime("%Y%m%d%H%M%S")}-{uuid.uuid4().hex[:8]}.png'
        filepath = os.path.join(img_dir, filename)

        with open(filepath, 'wb') as f:
            f.write(base64.b64decode(images[0]))

        # 生成缩略图
        try:
            from PIL import Image
            with Image.open(filepath) as img:
                img.thumbnail((800, 800), Image.Resampling.LANCZOS)
                thumb_filename = f'thumb_{filename}'
                img.save(os.path.join(DATA_DIR, 'static/imgs/thumbs', thumb_filename), quality=85)
        except Exception as e:
            print(f'生成缩略图失败: {e}')

        image_url = f'/static/imgs/messages/{filename}'
        return jsonify({
            'success': True,
            'message': '图片生成成功',
            'url': image_url
        })

    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'message': '请求超时，请稍后重试'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'生成异常: {str(e)}'})


def do_crawl_news():
    """执行新闻爬取(供调度器调用)"""
    from datetime import datetime
    executed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with app.app_context():
        try:
            database.clear_news()
            news_list = news_crawler.fetch_jlu_news()
            for news in news_list:
                database.save_news(
                    title=news.get('title', ''),
                    content=news.get('content', '来源:吉大新闻网'),
                    source_url=news.get('source_url', ''),
                    image_url=news.get('image_url', ''),
                    published_time=news.get('published_time', '')
                )
            database.set_news_crawl_log(executed_at, 'success', len(news_list), '定时爬取成功')
            print(f"[News Crawler] 成功爬取{len(news_list)}条新闻")

            # 清除缓存
            _news_cache['data'] = None
            _news_cache['timestamp'] = None
            _alumni_cache['data'] = None
            _alumni_cache['timestamp'] = None
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
    print(f"[News Scheduler] 已启动,每天{hour:02d}:{minute:02d}自动爬取新闻")


if __name__ == '__main__':
    init_news_scheduler()
    app.run(host='0.0.0.0', port=5000, debug=False)
