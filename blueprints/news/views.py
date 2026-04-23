"""
新闻/校友/验证码 路由
迁移自 app.py
"""

import random
from datetime import datetime

from flask import jsonify, session, request

import database
import news_crawler
from utils import (
    _get_cached_news, _set_cached_news,
    _get_cached_alumni, _set_cached_alumni,
)

from blueprints.news import news_bp


@news_bp.route('/api/news')
def get_news():
    """获取新闻列表(只排除校友会内容,按日期排序)"""
    # 检查缓存
    cached = _get_cached_news()
    if cached is not None:
        return jsonify({'success': True, 'news': cached})

    news = database.get_news(100)

    # 过滤掉旧新闻,只展示今年的新闻
    current_year = datetime.now().year
    news = [n for n in news if int(n['published_time'][:4]) >= current_year]

    # 只排除校友会相关内容(留给校友会tab展示)
    alumni_keywords = ['校友会', '校友总会', '北京校友会', '上海校友会', '深圳校友会', '广州校友会',
                      '成都校友会', '武汉校友会', '杭州校友会', '北美校友会', '欧洲校友会', '澳大利亚校友会',
                      '校友大会', '校友联谊', '校友活动', '校友交流', '校友企业', '校友返校']

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
        return (date, has_image)

    news.sort(key=news_sort_key, reverse=True)
    news = news[:50]  # 最多返回50条

    # 缓存结果
    _set_cached_news(news)

    return jsonify({'success': True, 'news': news})


@news_bp.route('/api/alumni')
def get_alumni():
    """获取校友会信息和相关新闻"""
    # 检查缓存
    cached = _get_cached_alumni()
    if cached is not None:
        return jsonify({'success': True, 'alumni': cached})

    # 预定义各地校友会基本信息
    alumni_associations = [
        {
            'name': '吉林大学校友总会',
            'location': '长春',
            'contact': '0431-85166001',
            'wechat': 'JLU_alumni',
            'email': 'xyh@jlu.edu.cn',
            'join_method': '联系校友总会咨询',
            'description': '吉林大学官方校友组织,统筹各地校友会工作',
            'type': 'association'
        },
        {
            'name': '吉林大学北京校友会',
            'location': '北京',
            'contact': '微信群:BJ_JLUers',
            'wechat': 'jlu_bj',
            'email': 'jlu_bj@126.com',
            'join_method': '扫码加入北京校友群',
            'description': '京城吉大人的温馨家园,定期举办联谊活动',
            'type': 'association'
        },
        {
            'name': '吉林大学上海校友会',
            'location': '上海',
            'contact': '联系人:王师兄',
            'wechat': 'sh_jlu',
            'email': 'shjlu@163.com',
            'join_method': '联系负责人邀请入群',
            'description': '海纳百川,沪上吉大人交流合作的平台',
            'type': 'association'
        },
        {
            'name': '吉林大学深圳校友会',
            'location': '深圳',
            'contact': '联系人:李师兄',
            'wechat': 'sz_jlu8',
            'email': 'jlu_sz@qq.com',
            'join_method': '扫码加入深圳校友群',
            'description': '创新之城,吉大人共谋发展的桥梁',
            'type': 'association'
        },
        {
            'name': '吉林大学广州校友会',
            'location': '广州',
            'contact': '联系人:张师姐',
            'wechat': 'gz_jlu',
            'email': 'gzjlu@163.com',
            'join_method': '联系负责人邀请入群',
            'description': '花城吉大人,资源共享事业互助',
            'type': 'association'
        },
        {
            'name': '吉林大学北美校友会',
            'location': '海外',
            'contact': '联系人:刘师兄',
            'wechat': 'namerica_jlu',
            'email': 'jlu.us@gmail.com',
            'join_method': '邮件联系或微信群',
            'description': '跨越重洋,海外学子的精神家园',
            'type': 'association'
        },
        {
            'name': '吉林大学成都校友会',
            'location': '成都',
            'contact': '联系人:赵师兄',
            'wechat': 'cd_jlu',
            'email': 'cdjlu@163.com',
            'join_method': '扫码加入成都校友群',
            'description': '天府之国,吉大人的巴蜀情缘',
            'type': 'association'
        },
        {
            'name': '吉林大学武汉校友会',
            'location': '武汉',
            'contact': '联系人:陈师兄',
            'wechat': 'wh_jlu',
            'email': 'jlu_wh@126.com',
            'join_method': '联系负责人邀请入群',
            'description': '江城吉大人,九省通衢共发展',
            'type': 'association'
        },
    ]

    # 获取校友会相关新闻
    news = database.get_news(100)
    alumni_keywords = ['校友', '校友会', '校友活动', '校友交流', '校友企业', '校友返校']
    alumni_news = []
    for n in news:
        title = n.get('title', '').lower()
        content = n.get('content', '').lower()
        text = title + ' ' + content
        if any(kw in text for kw in alumni_keywords):
            n['type'] = 'news'
            alumni_news.append(n)

    # 按内容类型排序
    def alumni_priority(n):
        text = (n.get('title', '') + ' ' + n.get('content', '')).lower()
        score = 0
        for kw in ['北京校友会', '上海校友会', '深圳校友会', '广州校友会', '北美校友会', '成都校友会', '武汉校友会', '欧洲校友会', '澳大利亚校友会']:
            if kw in text:
                score += 10
        for kw in ['校友大会', '校友联谊', '校友讲座', '校友走访', '校友活动', '校友交流', '校友企业']:
            if kw in text:
                score += 5
        return score
    alumni_news.sort(key=alumni_priority, reverse=True)

    # 提取地点信息
    def extract_location(n):
        title = n.get('title', '')
        content = n.get('content', '')[:200]
        locations = ['北京', '上海', '深圳', '广州', '成都', '武汉', '杭州', '南京', '西安', '天津', '大连', '青岛', '厦门', '长沙', '郑州', '济南', '合肥', '昆明', '重庆', '哈尔滨', '长春', '沈阳', '北美', '欧洲', '澳大利亚', '海外']
        for loc in locations:
            if loc in title or loc in content:
                return loc
        return ''

    for n in alumni_news:
        n['location'] = extract_location(n)

    # 合并:校友会信息 + 新闻
    result = alumni_associations + alumni_news[:15]

    # 缓存结果
    _set_cached_alumni(result)

    return jsonify({'success': True, 'alumni': result})


@news_bp.route('/api/captcha')
def generate_captcha():
    """生成数学验证码"""
    a = random.randint(1, 9)
    b = random.randint(1, 9)
    captcha_text = f"{a}+{b}="
    result = str(a + b)
    session['captcha'] = result
    session['captcha_time'] = datetime.now().isoformat()
    return jsonify({'captcha': captcha_text})
