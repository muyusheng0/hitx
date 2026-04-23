"""
Pytest 配置 & 公共 fixtures
"""

import os
import sys
import sqlite3
import tempfile
import shutil
import pytest


@pytest.fixture(scope='session')
def test_db_setup():
    """创建测试数据库（从运行库复制），返回临时目录和 DB 路径"""
    tmpdir = tempfile.mkdtemp(prefix='hitx_test_')
    # 复制运行库的 alumni.db 作为测试数据基础
    src_db = '/tmp/hitx/alumni.db'
    dst_db = os.path.join(tmpdir, 'alumni.db')
    if os.path.exists(src_db):
        shutil.copy2(src_db, dst_db)
    else:
        # 如果没有运行库，创建一个空的最小数据库
        conn = sqlite3.connect(dst_db)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS students (
            id TEXT PRIMARY KEY, name TEXT, hometown TEXT, hometown_name TEXT,
            city TEXT, district TEXT, phone TEXT, note TEXT,
            custom_intro TEXT, hobby TEXT, dream TEXT, avatar TEXT,
            industry TEXT, company TEXT, weibo TEXT, xiaohongshu TEXT,
            douyin TEXT, wechat TEXT, qq TEXT, email TEXT,
            work TEXT, position TEXT, birthday TEXT, github TEXT,
            coords TEXT, gps_coords TEXT, gender TEXT,
            login_password TEXT, no_password_prompt INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0, super_admin INTEGER DEFAULT 0
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, content TEXT,
            time TEXT, avatar TEXT, likes INTEGER DEFAULT 0
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT,
            owner TEXT, time TEXT, year INTEGER
        )''')
        # 插入测试数据
        c.executemany('INSERT INTO students (id, name) VALUES (?, ?)', [
            ('1', '张三'), ('2', '李四'), ('3', '王五'),
        ])
        c.executemany('INSERT INTO messages (name, content, time) VALUES (?, ?, ?)', [
            ('张三', '大家好！', '2024-01-01'),
            ('李四', '好久不见！', '2024-01-02'),
        ])
        c.executemany('INSERT INTO photos (filename, owner, time, year) VALUES (?, ?, ?, ?)', [
            ('photo1.jpg', '张三', '2024-01-01', 2024),
        ])
        conn.commit()
        conn.close()

    # 确保必要的目录存在
    os.makedirs(os.path.join(tmpdir, 'static/imgs/avatars'), exist_ok=True)
    os.makedirs(os.path.join(tmpdir, 'static/imgs/messages'), exist_ok=True)
    os.makedirs(os.path.join(tmpdir, 'static/imgs/thumbs'), exist_ok=True)
    os.makedirs(os.path.join(tmpdir, 'static/voice/lyb'), exist_ok=True)
    os.makedirs(os.path.join(tmpdir, 'static/videos'), exist_ok=True)
    os.makedirs(os.path.join(tmpdir, 'static/music'), exist_ok=True)

    yield tmpdir, dst_db

    # 清理
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture(scope='session')
def patched_database(test_db_setup):
    """在导入 app 之前 monkeypatch database 模块的 DB_FILE"""
    tmpdir, db_path = test_db_setup

    # 在 sys.modules 中预置 monkeypatched database 模块
    import importlib

    # 先设置环境变量让 config 模块使用
    os.environ['HITX_DATA_DIR'] = tmpdir
    os.environ['HITX_DB_FILE'] = db_path

    # 添加项目路径
    project_dir = os.path.dirname(os.path.abspath(__file__))
    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)

    # monkeypatch database module before app imports it
    import database
    database.DB_FILE = db_path
    database.DATA_DIR = tmpdir
    database.TXL_FILE = os.path.join(tmpdir, 'txl.csv')
    database.LYB_FILE = os.path.join(tmpdir, 'lyb.csv')
    database.VIDEOS_FILE = os.path.join(tmpdir, 'videos.csv')
    database.PHOTOS_FILE = os.path.join(tmpdir, 'photos.csv')
    database.DELETED_FILE = os.path.join(tmpdir, 'deleted.csv')
    # 重置连接，确保使用新路径
    if hasattr(database._thread_local, 'conn'):
        database._thread_local.conn.close()
        del database._thread_local.conn

    return db_path


@pytest.fixture
def app(patched_database):
    """创建 Flask 测试 app"""
    import app as app_module
    app_module.app.config['TESTING'] = True
    app_module.app.config['SECRET_KEY'] = 'test-secret-key'
    yield app_module.app


@pytest.fixture
def client(app):
    """Flask 测试客户端"""
    return app.test_client()
