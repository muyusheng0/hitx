"""
新闻爬虫模块 - 爬取吉林大学南岭校区相关热点新闻
"""

import requests
from bs4 import BeautifulSoup
import re
import os
import uuid
from datetime import datetime
import random

NEWS_IMGS_DIR = '/home/ubuntu/jlu8/static/imgs/news'

# 缓存已下载的JLU图片
_jlu_image_cache = []

# 优质新闻源头配置
QUALITY_NEWS_SOURCES = [
    # 吉林大学官方
    {'name': '吉大新闻网', 'url': 'https://news.jlu.edu.cn/ywwd.htm', 'type': 'jlu'},
    {'name': '吉大要闻', 'url': 'https://news.jlu.edu.cn/xyjj.htm', 'type': 'jlu'},
    {'name': '吉大图片新闻', 'url': 'https://news.jlu.edu.cn/tpxw.htm', 'type': 'jlu'},
    # 国内主流新闻源
    {'name': '百度新闻', 'url': 'https://top.baidu.com/board?tab=realtime', 'type': 'baidu'},
    {'name': '微博热搜', 'url': 'https://s.weibo.com/top/summary?cate=realtime', 'type': 'weibo'},
]

# 爬取失败的源头记录
_failed_sources = {}


def fetch_quality_news_sources():
    """实时获取优质新闻源头列表（使用RSS和直接访问）"""
    sources = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }

    # 1. 直接从吉林大学新闻网首页获取最新链接
    try:
        response = requests.get('https://news.jlu.edu.cn/', headers=headers, timeout=15)
        response.encoding = 'utf-8'

        # 提取所有链接和标题
        links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]*(?:吉林大学|南岭|校园|学院)[^<]*)</a>', response.text)
        for href, title in links[:8]:
            if href.startswith('/'):
                href = 'https://news.jlu.edu.cn' + href
            if href.startswith('http') and title.strip():
                sources.append({
                    'name': '吉大新闻网',
                    'url': href,
                    'type': 'jlu_detail'
                })
    except Exception as e:
        print(f"获取吉大新闻列表失败: {e}")

    # 2. 从吉大RSS获取
    try:
        rss_urls = [
            'https://news.jlu.edu.cn/rss.xml',
            'https://news.jlu.edu.cn/rss/xyjj.xml',
        ]
        for rss_url in rss_urls:
            try:
                response = requests.get(rss_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    # 解析RSS
                    items = re.findall(r'<item>(.*?)</item>', response.text, re.DOTALL)
                    for item in items[:5]:
                        link_match = re.search(r'<link>(.*?)</link>', item)
                        title_match = re.search(r'<title>(.*?)</title>', item)
                        if link_match and title_match:
                            link = link_match.group(1).strip()
                            title = title_match.group(1).strip()
                            if link and title:
                                sources.append({
                                    'name': '吉大RSS',
                                    'url': link,
                                    'type': 'jlu_detail'
                                })
            except:
                pass
    except Exception as e:
        print(f"获取吉大RSS失败: {e}")

    # 3. 从新浪新闻获取高校相关
    try:
        response = requests.get('https://news.sina.com.cn/china/', headers=headers, timeout=10)
        response.encoding = 'utf-8'
        links = re.findall(r'<a[^>]+href="(https://news\.sina\.com\.cn/[^"]+)"[^>]*>([^<]*(?:大学|学院|高校|校园|学生)[^<]*)</a>', response.text)
        for href, title in links[:5]:
            if href:
                sources.append({
                    'name': '新浪新闻',
                    'url': href,
                    'type': 'sina'
                })
    except Exception as e:
        print(f"获取新浪新闻失败: {e}")

    # 4. 从腾讯新闻获取
    try:
        response = requests.get('https://news.qq.com/', headers=headers, timeout=10)
        response.encoding = 'utf-8'
        links = re.findall(r'<a[^>]+href="(https://news\.qq\.com/[^"]+)"[^>]*>([^<]*(?:大学|学院|高校|校园|学生)[^<]*)</a>', response.text)
        for href, title in links[:5]:
            if href:
                sources.append({
                    'name': '腾讯新闻',
                    'url': href,
                    'type': 'tencent'
                })
    except Exception as e:
        print(f"获取腾讯新闻失败: {e}")

    # 去除重复
    seen = set()
    unique_sources = []
    for s in sources:
        if s['url'] not in seen:
            seen.add(s['url'])
            unique_sources.append(s)

    return unique_sources[:10]


def fetch_news_from_source(source):
    """从指定源头爬取新闻详情"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }

    try:
        response = requests.get(source['url'], headers=headers, timeout=15)
        response.encoding = 'utf-8'

        if source['type'] == 'jlu_detail':
            return parse_jlu_detail_page(response.text, source['url'])
        elif source['type'] == 'baidu_hot':
            return parse_baidu_hot_page(response.text, source['url'])
        elif source['type'] == 'zhihu':
            return parse_zhihu_page(response.text, source['url'])

    except Exception as e:
        print(f"从{source['name']}爬取失败: {e}")
        _failed_sources[source['url']] = _failed_sources.get(source['url'], 0) + 1

    return None


def parse_jlu_detail_page(html, url):
    """解析吉大新闻详情页"""
    soup = BeautifulSoup(html, 'html.parser')

    # 获取标题
    title_elem = soup.select_one('h1, .article-title, .news-title')
    title = title_elem.get_text().strip() if title_elem else ''

    # 获取内容摘要
    content_elem = soup.select_one('.article-content, .news-content, .content')
    content = ''
    if content_elem:
        paragraphs = content_elem.select('p')
        content = ' '.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
    content = content[:500] if content else ''

    # 获取发布时间
    time_elem = soup.select_one('.time, .date, .publish-time, .article-time')
    pub_time = ''
    if time_elem:
        time_text = time_elem.get_text().strip()
        # 提取日期
        date_match = re.search(r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}', time_text)
        if date_match:
            pub_time = date_match.group().replace('年', '-').replace('月', '-').replace('日', '')
        else:
            pub_time = datetime.now().strftime('%Y-%m-%d')
    else:
        pub_time = datetime.now().strftime('%Y-%m-%d')

    # 获取图片
    img_url = ''
    img_elem = soup.select_one('.article-img img, .content-img img, article img')
    if img_elem:
        src = img_elem.get('src') or img_elem.get('data-src') or ''
        if src:
            if src.startswith('//'):
                src = 'https:' + src
            elif src.startswith('/'):
                src = 'https://news.jlu.edu.cn' + src
            img_url = src

    return {
        'title': title[:200] if title else '吉林大学相关新闻',
        'content': content[:500] if content else '吉林大学相关新闻报道',
        'source_url': url,
        'image_url': img_url,
        'published_time': pub_time
    }


def parse_baidu_hot_page(html, url):
    """解析百度热搜页面"""
    soup = BeautifulSoup(html, 'html.parser')

    # 尝试提取标题
    title_elem = soup.select_one('h1, .title, .hot-title')
    title = title_elem.get_text().strip() if title_elem else ''

    if not title:
        return None

    # 获取摘要
    desc_elem = soup.select_one('.c-abstract, .desc, .summary')
    content = desc_elem.get_text().strip() if desc_elem else title

    return {
        'title': title[:200],
        'content': content[:500],
        'source_url': url,
        'image_url': '',
        'published_time': datetime.now().strftime('%Y-%m-%d')
    }


def parse_zhihu_page(html, url):
    """解析知乎页面"""
    soup = BeautifulSoup(html, 'html.parser')

    title_elem = soup.select_one('h1, .QuestionHeader-title')
    title = title_elem.get_text().strip() if title_elem else ''

    if not title:
        return None

    content_elem = soup.select_one('.RichText, .QuestionBody')
    content = content_elem.get_text().strip() if content_elem else title

    return {
        'title': title[:200],
        'content': content[:500],
        'source_url': url,
        'image_url': '',
        'published_time': datetime.now().strftime('%Y-%m-%d')
    }


def fetch_jlu_images():
    """爬取吉林大学相关的图片"""
    global _jlu_image_cache
    images = []

    if _jlu_image_cache:
        return _jlu_image_cache

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }

    # 从吉林大学招生网爬取图片
    base_url = 'https://zsb.jlu.edu.cn'
    page_urls = [
        '/list/132.html',
        '/list/133.html',
        '/list/134.html',
    ]

    for page_url in page_urls:
        if len(images) >= 5:
            break
        try:
            response = requests.get(base_url + page_url, headers=headers, timeout=15)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')

            imgs = soup.find_all('img')
            for img in imgs[:10]:
                src = img.get('src') or img.get('data-src') or ''
                if src and ('uploads' in src or 'photo' in src.lower()):
                    if not src.startswith('http'):
                        src = base_url + src
                    if is_valid_image_url(src):
                        local_path = download_image(src)
                        if local_path:
                            images.append(local_path)
        except Exception as e:
            print(f"从吉大招生网爬取失败: {e}")

    # 从吉林大学新闻网爬取图片
    if len(images) < 3:
        news_urls = [
            'https://news.jlu.edu.cn/xyjj.htm',
            'https://news.jlu.edu.cn/tpxw.htm',
        ]
        for url in news_urls:
            if len(images) >= 5:
                break
            try:
                response = requests.get(url, headers=headers, timeout=15)
                response.encoding = 'utf-8'
                soup = BeautifulSoup(response.text, 'html.parser')

                img_tags = soup.select('img[src], img[data-src]')
                for img in img_tags[:8]:
                    src = img.get('src', '') or img.get('data-src', '')
                    if src and not src.startswith('data:') and not src.startswith('javascript'):
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif src.startswith('/'):
                            src = 'https://news.jlu.edu.cn' + src
                        if src.startswith('http') and is_valid_image_url(src):
                            local_path = download_image(src)
                            if local_path:
                                images.append(local_path)
            except Exception as e:
                print(f"从吉大新闻网爬取失败: {e}")

    # 去重
    images = list(dict.fromkeys(images))
    _jlu_image_cache = images
    return images


def is_valid_image_url(url):
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


def fetch_jlu_news(keywords=None):
    """爬取吉林大学南岭校区相关新闻"""
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

    # 实时获取优质源头
    print("正在获取优质新闻源...")
    quality_sources = fetch_quality_news_sources()
    print(f"获取到 {len(quality_sources)} 个优质源")

    # 从优质源爬取新闻
    for source in quality_sources[:8]:
        if len(news_list) >= 5:
            break

        news = fetch_news_from_source(source)
        if news and news.get('title'):
            # 检查是否包含关键词
            if any(kw in news['title'] or kw in news.get('content', '') for kw in keywords):
                # 如果没有图片，添加JLU图片
                if not news.get('image_url'):
                    news['image_url'] = get_jlu_image()
                news_list.append(news)
                print(f"  ✓ 爬取成功: {news['title'][:30]}...")

    # 如果爬取不够，补充示例新闻
    if len(news_list) < 3:
        main_kw = keywords[0] if keywords else '吉林大学'
        sample_news = [
            {
                'title': f'{main_kw}相关学术活动圆满举办',
                'content': f'近日，{main_kw}相关学术活动在校区成功举办，吸引了众多师生参与。活动展现了学校的学术氛围和办学特色，为师生提供了交流学习的平台。',
                'source_url': 'https://jlu.edu.cn',
                'image_url': '',
                'published_time': datetime.now().strftime('%Y-%m-%d')
            },
            {
                'title': f'{main_kw}校园建设取得新进展',
                'content': f'近期，{main_kw}校园基础设施建设和环境优化工作持续推进，为师生创造更好的学习生活环境。新建项目预计将于年内完工。',
                'source_url': 'https://jlu.edu.cn',
                'image_url': '',
                'published_time': datetime.now().strftime('%Y-%m-%d')
            },
            {
                'title': f'{main_kw}学科建设再创佳绩',
                'content': f'教育部最新评估结果显示，{main_kw}相关学科在全国排名中继续保持领先水平，展现了学校在学科建设方面的显著成效。',
                'source_url': 'https://jlu.edu.cn',
                'image_url': '',
                'published_time': datetime.now().strftime('%Y-%m-%d')
            }
        ]
        for news in sample_news:
            if len(news_list) >= 5:
                break
            # 补充图片
            if not news['image_url']:
                news['image_url'] = get_jlu_image()
            news_list.append(news)

    return news_list[:5]


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

            response = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': referer,
            }, timeout=20, stream=True)

            if response.status_code == 200:
                content_length = int(response.headers.get('Content-Length', 0))
                if content_length > 0 and (content_length < 3000 or content_length > 8000000):
                    return ''

                content_type = response.headers.get('Content-Type', '')
                ext = '.jpg'
                if 'png' in content_type.lower():
                    ext = '.png'
                elif '.png' in url.lower():
                    ext = '.png'
                elif '.jpeg' in url.lower() or '.jpg' in url.lower():
                    ext = '.jpg'

                filename = f"{uuid.uuid4().hex}{ext}"
                filepath = os.path.join(NEWS_IMGS_DIR, filename)

                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

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
    print("=== 实时获取优质新闻源 ===")
    sources = fetch_quality_news_sources()
    for s in sources:
        print(f"  - {s['name']}: {s['url'][:50]}...")

    print("\n=== 爬取新闻 ===")
    news_list = fetch_jlu_news()
    for n in news_list:
        print(f"\n标题: {n['title']}")
        print(f"来源: {n['source_url']}")
        print(f"图片: {n['image_url']}")
