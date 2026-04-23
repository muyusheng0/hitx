"""
配置集中管理
"""

import os

# ==================== 应用配置 ====================

SECRET_KEY = 'jlu_tongxin_8_class_2024_secret_key'
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB

# Session 配置
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_NAME = 'jlu_session'
SESSION_COOKIE_PATH = '/'

# ==================== 路径配置 ====================

# 数据目录（生产环境: /home/ubuntu/jlu8, 开发环境: /tmp/hitx）
_DATA_DIR_ENV = os.environ.get('HITX_DATA_DIR', '/home/ubuntu/jlu8')
DATA_DIR = _DATA_DIR_ENV

# 数据库路径
DB_FILE = os.path.join(DATA_DIR, 'alumni.db')

# 静态文件子目录
AVATARS_DIR = os.path.join(DATA_DIR, 'static/imgs/avatars')
MESSAGES_IMG_DIR = os.path.join(DATA_DIR, 'static/imgs/messages')
THUMBS_DIR = os.path.join(DATA_DIR, 'static/imgs/thumbs')
VOICE_DIR = os.path.join(DATA_DIR, 'static/voice')
VOICE_LYB_DIR = os.path.join(DATA_DIR, 'static/voice/lyb')
VIDEOS_DIR = os.path.join(DATA_DIR, 'static/videos')
MUSIC_DIR = os.path.join(DATA_DIR, 'static/music')

# 上传文件夹（Flask config）
UPLOAD_FOLDER = 'static/imgs/avatars'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_VIDEO_TYPES = {'mp4', 'webm', 'ogg', 'mov', 'avi', 'wmv', 'flv', 'mkv'}

# ==================== 管理员 ====================

ADMIN_USERS = ['穆玉升']

# ==================== 图片处理 ====================

AVATAR_MAX_SIZE = 500 * 1024  # 500KB
IMAGE_MAX_SIZE = 1024 * 1024  # 1MB
IMAGE_QUALITY = 85
THUMBNAIL_SIZE = (800, 800)

# ==================== 缓存 ====================

CACHE_TTL = 300  # 5分钟

# ==================== 公开路由 ====================

PUBLIC_ROUTES = {'/login', '/api/captcha', '/api/check_user_login_password', '/api/verify', '/static', '/api/stats'}

# ==================== OpenClaw ====================

OPENCLAW_CONNECTION_FILE = '/tmp/openclaw_connection.json'
OPENCLAW_COOLDOWN_FILE = '/tmp/openclaw_disconnect_cooldown.json'
OPENCLAW_CHAT_LOCK = '/tmp/openclaw_chat.lock'

# ==================== 数据文件 ====================

TXL_FILE = os.path.join(DATA_DIR, 'txl.csv')
LYB_FILE = os.path.join(DATA_DIR, 'lyb.csv')
VIDEOS_FILE = os.path.join(DATA_DIR, 'videos.csv')
PHOTOS_FILE = os.path.join(DATA_DIR, 'photos.csv')
DELETED_FILE = os.path.join(DATA_DIR, 'deleted.csv')


def get_db_file():
    """获取数据库文件路径（兼容不同环境）"""
    return os.environ.get('HITX_DB_FILE', DB_FILE)
