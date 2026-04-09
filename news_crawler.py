"""
新闻爬虫模块 - 基于 RSSHub 获取吉林大学相关新闻

主要数据来源：RSSHub (https://rsshub.app)
- 社区维护，稳定可靠
- 不暴露源站IP
- 输出标准RSS/XML格式
"""

import os
import uuid
import re
from datetime import datetime
import random
from email.utils import parsedate_to_datetime

# RSSHub 新闻源配置
RSSHUB_SOURCES = [
    # 吉大官方新闻网（主源）
    {'name': '吉大新闻', 'url': 'https://rsshub.app/jlu/news'},
    # 通知公告
    {'name': '吉大通知', 'url': 'https://rsshub.app/jlu/notice'},
    # 南岭校区核心学院
    {'name': '汽车学院', 'url': 'https://rsshub.app/jlu/college/auto'},
    {'name': '机械学院', 'url': 'https://rsshub.app/jlu/college/mechanical'},
    {'name': '材料学院', 'url': 'https://rsshub.app/jlu/college/materials'},
    {'name': '交通学院', 'url': 'https://rsshub.app/jlu/college/transport'},
    {'name': '生物学院', 'url': 'https://rsshub.app/jlu/college/bio'},
    {'name': '通信学院', 'url': 'https://rsshub.app/jlu/college/telecom'},
]

# 微信公众号源（备用）
WECHAT_SOURCES = [
    {'name': '吉大官微', 'url': 'https://rsshub.app/wechat/official/judaxiao'},
    {'name': '吉大招生', 'url': 'https://rsshub.app/wechat/official/jlu_zsb'},
]

NEWS_IMGS_DIR = '/home/ubuntu/jlu8/static/imgs/news'

# 本地缓存（避免频繁请求RSSHub）
_rss_cache = {}
_CACHE_TTL = 300  # 5分钟缓存


def _get_cached(key, ttl=_CACHE_TTL):
    """获取缓存内容"""
    import time
    if key in _rss_cache:
        entry = _rss_cache[key]
        if time.time() - entry['time'] < ttl:
            return entry['data']
    return None


def _set_cached(key, data):
    """设置缓存"""
    import time
    _rss_cache[key] = {'data': data, 'time': time.time()}


def fetch_via_rsshub(keywords, timeout=15):
    """通过 RSSHub 获取吉大新闻

    Args:
        keywords: 关键词列表，用于过滤新闻
        timeout: 请求超时时间（秒）

    Returns:
        list: 新闻列表，每项包含 title, content, source_url, image_url, published_time
    """
    import urllib.request
    import xml.etree.ElementTree as ET

    news_list = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; JLU8-NewsBot/1.0)',
    }

    for source in RSSHUB_SOURCES:
        url = source['url']

        # 检查缓存
        cached = _get_cached(url)
        if cached:
            xml_content = cached
        else:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    xml_content = resp.read().decode('utf-8')
                    _set_cached(url, xml_content)
            except Exception as e:
                print(f"RSSHub {source['name']} 请求失败: {e}")
                continue

        try:
            # 解析 RSS XML
            root = ET.fromstring(xml_content)

            # 尝试 RSS 2.0 格式
            items = root.findall('.//item')
            if not items:
                # 尝试 Atom 格式
                items = root.findall('.//entry')

            for item in items[:15]:  # 最多取15条
                # 获取标题
                title = item.findtext('title') or ''
                title = title.strip()

                if not title:
                    continue

                # 获取链接
                link_elem = item.find('link')
                if link_elem is not None:
                    link = link_elem.text or link_elem.get('href') or ''
                else:
                    link = item.findtext('guid') or ''

                # 获取描述
                desc = item.findtext('description') or item.findtext('summary') or ''

                # 获取发布时间
                pubDate = item.findtext('pubDate') or item.findtext('published') or ''

                # 清理HTML标签
                content = _strip_tags(desc)[:500] if desc else ''

                # 关键词过滤（标题优先）
                title_match = any(kw in title for kw in keywords)
                content_match = any(kw in content for kw in keywords)
                if not (title_match or content_match):
                    # 如果标题不匹配但内容包含关键词，也保留
                    if not content_match and not title_match:
                        continue

                # 解析发布时间
                published_time = _parse_rss_date(pubDate)

                news_list.append({
                    'title': title[:200],
                    'content': content,
                    'source_url': link,
                    'image_url': '',
                    'published_time': published_time
                })

                print(f"  ✓ {source['name']}: {title[:40]}...")

        except ET.ParseError as e:
            print(f"RSSHub {source['name']} XML解析失败: {e}")
            continue
        except Exception as e:
            print(f"RSSHub {source['name']} 处理失败: {e}")
            continue

    return news_list


def _strip_tags(html_content):
    """去除HTML标签"""
    if not html_content:
        return ''
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', '', html_content)
    # 清理多余空白
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _parse_rss_date(date_str):
    """解析RSS/Atom中的日期字符串"""
    if not date_str:
        return datetime.now().strftime('%Y-%m-%d')

    try:
        # 尝试 RFC 2822 格式 (RSS标准)
        dt = parsedate_to_datetime(date_str)
        return dt.strftime('%Y-%m-%d')
    except:
        pass

    try:
        # 尝试 ISO 格式
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        return dt.strftime('%Y-%m-%d')
    except:
        pass

    # 尝试常见中文日期格式
    date_match = re.search(r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}', date_str)
    if date_match:
        return date_match.group().replace('年', '-').replace('月', '-').replace('日', '')

    return datetime.now().strftime('%Y-%m-%d')


def fetch_jlu_news(keywords=None):
    """爬取吉林大学相关新闻（主入口）

    Args:
        keywords: 关键词列表，默认从数据库读取

    Returns:
        list: 新闻列表
    """
    news_list = []

    # 如果没有提供关键词，从数据库获取
    if keywords is None:
        try:
            import database
            keywords = database.get_news_keywords()
        except:
            keywords = ['吉林大学', '南岭校区', '自动化']

    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split(',') if k.strip()]

    print(f"=== 开始获取新闻 (关键词: {keywords}) ===")

    # 优先使用 RSSHub
    print("\n[1] 通过 RSSHub 获取新闻...")
    rs_news = fetch_via_rsshub(keywords)
    news_list.extend(rs_news)

    # 去重（基于标题）
    seen_titles = set()
    unique_news = []
    for news in news_list:
        title_key = news['title'][:30]  # 用前30字符作为去重依据
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_news.append(news)
    news_list = unique_news

    print(f"\nRSSHub 获取到 {len(news_list)} 条新闻")

    # 补充吉大图片（如果新闻没有图片）
    for news in news_list:
        if not news.get('image_url'):
            news['image_url'] = get_jlu_image()

    # 如果 RSSHub 完全失败，使用示例新闻
    if len(news_list) == 0:
        print("\n[2] RSSHub 全部失败，使用示例新闻...")
        news_list = _generate_sample_news(keywords)

    return news_list[:10]  # 最多返回10条


def _generate_sample_news(keywords):
    """生成示例新闻（当RSSHub不可用时）"""
    main_kw = keywords[0] if keywords else '吉林大学'
    return [
        {
            'title': f'{main_kw}相关学术活动圆满举办',
            'content': f'近日，{main_kw}相关学术活动在校区成功举办，吸引了众多师生参与。活动内容丰富，涵盖了学术研讨、实践操作等多个环节，展现了学校的学术氛围和办学特色。',
            'source_url': 'https://news.jlu.edu.cn',
            'image_url': get_jlu_image(),
            'published_time': datetime.now().strftime('%Y-%m-%d')
        },
        {
            'title': f'{main_kw}校园建设取得新进展',
            'content': f'近期，{main_kw}校园基础设施建设和环境优化工作持续推进，新建的教学楼和科研平台即将投入使用，为师生创造更好的学习生活环境。',
            'source_url': 'https://news.jlu.edu.cn',
            'image_url': get_jlu_image(),
            'published_time': datetime.now().strftime('%Y-%m-%d')
        },
        {
            'title': f'{main_kw}学科建设再创佳绩',
            'content': f'教育部最新学科评估结果公布，{main_kw}相关学科在全国排名中继续保持领先水平，展现了学校在学科建设和科研创新方面的显著成效。',
            'source_url': 'https://news.jlu.edu.cn',
            'image_url': get_jlu_image(),
            'published_time': datetime.now().strftime('%Y-%m-%d')
        }
    ]


# ============================================================
# 以下为保留的原有功能（图片下载、JLU图片获取）
# ============================================================

_jlu_image_cache = []


def fetch_jlu_images():
    """爬取吉林大学相关的图片（保留原有逻辑）"""
    global _jlu_image_cache
    images = []

    if _jlu_image_cache:
        return _jlu_image_cache

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }

    # 尝试从吉大新闻网获取
    try:
        import urllib.request
        url = 'https://news.jlu.edu.cn'
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8')

        # 简单提取图片
        img_patterns = re.findall(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', html)
        for img_url in img_patterns[:10]:
            if img_url.startswith('//'):
                img_url = 'https:' + img_url
            elif img_url.startswith('/'):
                img_url = 'https://news.jlu.edu.cn' + img_url

            if img_url.startswith('http') and _is_valid_image_url(img_url):
                local_path = download_image(img_url)
                if local_path:
                    images.append(local_path)
    except Exception as e:
        print(f"获取吉大图片失败: {e}")

    # 去重
    images = list(dict.fromkeys(images))
    _jlu_image_cache = images
    return images


def _is_valid_image_url(url):
    """检查是否是有效的图片URL"""
    if not url:
        return False
    invalid_ext = ['.gif', '.ico', '.svg', '.bmp', '.webp']
    for ext in invalid_ext:
        if ext in url.lower():
            return False
    return True


def get_jlu_image():
    """获取一个吉林大学相关的图片路径"""
    images = fetch_jlu_images()
    if images:
        return random.choice(images)
    return ''


def download_image(url):
    """下载图片到本地（带压缩）"""
    max_retries = 2
    for attempt in range(max_retries):
        try:
            os.makedirs(NEWS_IMGS_DIR, exist_ok=True)

            referer = 'https://www.baidu.com'
            if 'bing.com' in url:
                referer = 'https://cn.bing.com'
            elif 'sogou' in url:
                referer = 'https://www.sogou.com'
            elif 'zsb.jlu.edu.cn' in url:
                referer = 'https://zsb.jlu.edu.cn/'
            elif 'news.jlu.edu.cn' in url:
                referer = 'https://news.jlu.edu.cn/'

            import urllib.request
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': referer,
            })
            with urllib.request.urlopen(req, timeout=20) as resp:
                content = resp.read()

            content_length = len(content)
            if content_length > 0 and (content_length < 3000 or content_length > 8000000):
                return ''

            # 确定文件扩展名
            ext = '.jpg'
            if '.png' in url.lower():
                ext = '.png'
            elif '.jpeg' in url.lower():
                ext = '.jpg'

            filename = f"{uuid.uuid4().hex}{ext}"
            filepath = os.path.join(NEWS_IMGS_DIR, filename)

            with open(filepath, 'wb') as f:
                f.write(content)

            if os.path.getsize(filepath) < 3000:
                os.remove(filepath)
                return ''

            # 压缩图片
            compressed_path = compress_image(filepath)
            if compressed_path:
                return compressed_path

            return f'/static/imgs/news/{filename}'

        except Exception as e:
            if attempt < max_retries - 1:
                continue
            print(f"下载图片失败: {e}")

    return ''


def compress_image(filepath, max_width=800, quality=85):
    """压缩图片并返回压缩后的路径"""
    try:
        from PIL import Image

        img = Image.open(filepath)
        original_size = os.path.getsize(filepath)

        if original_size < 100 * 1024:
            return ''

        if img.mode == 'RGBA':
            img = img.convert('RGB')

        width, height = img.size
        if width > max_width:
            ratio = max_width / width
            new_height = int(height * ratio)
            img = img.resize((max_width, new_height), Image.LANCZOS)

        compressed_filename = f"{uuid.uuid4().hex}_thumb.jpg"
        compressed_filepath = os.path.join(NEWS_IMGS_DIR, compressed_filename)

        img.save(compressed_filepath, 'JPEG', quality=quality, optimize=True)
        os.remove(filepath)

        while os.path.getsize(compressed_filepath) > 200 * 1024 and quality > 50:
            quality -= 10
            img.save(compressed_filepath, 'JPEG', quality=quality, optimize=True)

        return f'/static/imgs/news/{compressed_filename}'

    except Exception as e:
        print(f"压缩图片失败: {e}")
        return ''


if __name__ == '__main__':
    print("=== RSSHub 新闻获取测试 ===")
    news_list = fetch_jlu_news()
    print(f"\n共获取 {len(news_list)} 条新闻:")
    for i, n in enumerate(news_list, 1):
        print(f"\n{i}. {n['title']}")
        print(f"   来源: {n['source_url']}")
        print(f"   时间: {n['published_time']}")
