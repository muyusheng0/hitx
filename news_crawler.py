"""
新闻爬虫模块 - 吉林大学相关新闻获取

策略（按优先级）：
1. 吉大新闻网首页 - 直接爬取，稳定
2. 吉大各学院官网 - 静态HTML好抓
3. 示例新闻 - 兜底
"""

import os
import re
import uuid
from datetime import datetime
import random
import urllib.parse

NEWS_IMGS_DIR = '/home/ubuntu/jlu8/static/imgs/news'
DEFAULT_KEYWORDS = ['吉林大学', '南岭', '自动化', '杏花节']


def fetch_jlu_news(keywords=None):
    """爬取吉林大学相关新闻（主入口）"""
    results = []

    if keywords is None:
        try:
            import database
            keywords = database.get_news_keywords()
        except:
            keywords = DEFAULT_KEYWORDS

    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split(',') if k.strip()]

    print(f"\n=== 开始获取新闻 (关键词: {keywords}) ===")

    # 1. 吉大新闻网首页（最稳定）
    print("\n[1] 抓取吉大新闻网...")
    results.extend(_fetch_jlu_homepage())

    # 2. 抓取汽车工程学院
    print("\n[2] 抓取汽车学院...")
    results.extend(_fetch_college_news('https://auto.jlu.edu.cn', '汽车学院'))

    # 去重
    seen = set()
    unique = []
    for r in results:
        key = r['title'][:30]
        if key not in seen:
            seen.add(key)
            unique.append(r)
    results = unique

    # 补充图片
    for r in results:
        if not r.get('image_url'):
            r['image_url'] = get_jlu_image()

    # 兜底
    if len(results) == 0:
        print("\n[3] 使用示例新闻...")
        results = _generate_samples(keywords)
    else:
        print(f"\n共获取 {len(results)} 条新闻")

    return results[:10]


def _fetch_jlu_homepage():
    """抓取吉大新闻网首页及其详情页内容"""
    import urllib.request

    results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }

    try:
        url = 'https://news.jlu.edu.cn/'
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')

        # 提取新闻链接和标题
        pattern = r'<a[^>]+href="([^"]+\.htm[^"]*)"[^>]*>([^<]{5,100})</a>'
        matches = re.findall(pattern, html)

        base_url = 'https://news.jlu.edu.cn/'
        news_items = []

        for link, title in matches[:15]:
            title = _clean_text(title.strip())

            # 过滤无效链接
            if len(title) < 5:
                continue

            # 完整URL
            if link.startswith('/'):
                full_url = 'https://news.jlu.edu.cn' + link
            elif link.startswith('http'):
                full_url = link
            else:
                full_url = base_url + link

            # 关键词匹配（宽松）
            title_lower = title.lower()
            if any(kw.lower() in title_lower or kw.lower() in link.lower()
                   for kw in ['吉大', '南岭', '自动化', '学院', '大学', '校园', '学生', '教学', '科研', '杏花']):
                news_items.append({
                    'title': title[:200],
                    'source_url': full_url,
                })

        # 抓取详情页获取内容和图片（限制并发，最多5个）
        for i, item in enumerate(news_items[:5]):
            try:
                detail = _fetch_news_detail(item['source_url'])
                item['content'] = detail.get('content', '来源：吉大新闻网')
                item['image_url'] = detail.get('image_url', '')
                item['published_time'] = detail.get('published_time', datetime.now().strftime('%Y-%m-%d'))
                print(f"  ✓ {item['title'][:40]}...")
            except Exception as e:
                item['content'] = '来源：吉大新闻网'
                item['image_url'] = ''
                item['published_time'] = datetime.now().strftime('%Y-%m-%d')
                print(f"  ✓ {item['title'][:40]}... (详情获取失败)")

        results = news_items

    except Exception as e:
        print(f"  ✗ 吉大新闻网失败: {e}")

    return results


def _fetch_college_news(base_url, college_name):
    """抓取学院官网新闻"""
    import urllib.request

    results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }

    try:
        req = urllib.request.Request(base_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')

        # 提取链接
        pattern = r'<a[^>]+href="([^"]+\.htm[^"]*)"[^>]*>([^<]{5,80})</a>'
        matches = re.findall(pattern, html)

        for link, title in matches[:10]:
            title = _clean_text(title.strip())
            if len(title) < 5:
                continue

            # 完整URL
            if link.startswith('/'):
                full_url = urllib.parse.urljoin(base_url, link)
            elif link.startswith('http'):
                full_url = link
            else:
                full_url = base_url.rstrip('/') + '/' + link

            # 过滤新闻类链接
            if any(kw in link.lower() for kw in ['xw', 'news', 'dt', 'zx', 'xyjj', 'xygk']):
                results.append({
                    'title': title[:200],
                    'content': f'来源：{college_name}',
                    'source_url': full_url,
                    'image_url': '',
                    'published_time': datetime.now().strftime('%Y-%m-%d')
                })
                print(f"  ✓ {college_name}: {title[:40]}...")

    except Exception as e:
        print(f"  ✗ {college_name}失败: {e}")

    return results


def _fetch_news_detail(url):
    """抓取新闻详情页，获取内容和图片"""
    import urllib.request

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }

    result = {'content': '', 'image_url': '', 'published_time': ''}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')

        # 提取正文内容 (在 vsbcontent_start 和 vsbcontent_end 之间)
        # 匹配从 vsbcontent_start 到 vsbcontent_end 的所有内容
        content_match = re.search(r'<p class="vsbcontent_start">(.*?)</p>\s*<p class="vsbcontent_end">', html, re.DOTALL)
        if content_match:
            # 提取 vsbcontent_start 之后、vsbcontent_end 之前的所有段落
            full_content = content_match.group(1) + ' '
            # 再加上 vsbcontent_end 之前的内容
            end_match = re.search(r'</p>\s*<p class="vsbcontent_end">', html)
            if end_match:
                # 提取 vsbcontent_start 到 vsbcontent_end 之间的所有<p>标签
                all_paras = re.findall(r'<p[^>]*>([^<]+)</p>', html)
                content = ' '.join([_clean_text(p) for p in all_paras[:10] if _clean_text(p)])
            else:
                content = _clean_text(full_content)
            result['content'] = content[:500] if content else '来源：吉大新闻网'
        else:
            # 备选：直接提取所有段落
            all_paras = re.findall(r'<p[^>]*>([^<]+)</p>', html)
            content = ' '.join([_clean_text(p) for p in all_paras[:10] if _clean_text(p)])
            result['content'] = content[:500] if content else '来源：吉大新闻网'

        # 提取图片（新闻详情页通常在正文区域有图片）
        img_patterns = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html)
        for img_url in img_patterns:
            if img_url.startswith('//'):
                img_url = 'https:' + img_url
            elif img_url.startswith('/'):
                base = '/'.join(url.split('/')[:3])
                img_url = base + img_url

            if img_url.startswith('http') and _is_valid_img(img_url):
                # 跳过logo、icon等
                if any(bad in img_url.lower() for bad in ['logo', 'icon', 'banner', 'nav', 'menu']):
                    continue
                downloaded = download_image(img_url)
                if downloaded:
                    result['image_url'] = downloaded
                    break

        # 提取发布时间
        time_match = re.search(r'(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})', html)
        if time_match:
            result['published_time'] = f"{time_match.group(1)}-{time_match.group(2).zfill(2)}-{time_match.group(3).zfill(2)}"

    except Exception as e:
        print(f"    详情页获取失败: {e}")

    return result


def _clean_text(text):
    """清理HTML和特殊字符"""
    if not text:
        return ''
    # 去除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    # 清理空白
    text = re.sub(r'\s+', ' ', text)
    # 还原实体
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
    return text.strip()


def _generate_samples(keywords):
    """生成示例新闻"""
    kw = keywords[0] if keywords else '吉林大学'
    return [
        {
            'title': f'{kw}校园文化活动丰富多彩',
            'content': f'近日，{kw}校园内举办了多场文化活动，吸引了众多师生参与，展现了校园文化的独特魅力。',
            'source_url': 'https://news.jlu.edu.cn',
            'image_url': get_jlu_image(),
            'published_time': datetime.now().strftime('%Y-%m-%d')
        },
        {
            'title': f'{kw}南岭校区建设稳步推进',
            'content': f'{kw}南岭校区各项基础设施建设工作正在稳步推进，为师生创造更好的学习和生活环境。',
            'source_url': 'https://news.jlu.edu.cn',
            'image_url': get_jlu_image(),
            'published_time': datetime.now().strftime('%Y-%m-%d')
        },
        {
            'title': f'{kw}学科建设取得新成果',
            'content': f'{kw}相关学科在教学和科研方面取得了新的进展，学科竞争力不断提升。',
            'source_url': 'https://news.jlu.edu.cn',
            'image_url': get_jlu_image(),
            'published_time': datetime.now().strftime('%Y-%m-%d')
        }
    ]


# ============================================================
# 图片功能
# ============================================================

_jlu_img_cache = []


def fetch_jlu_images():
    """获取吉大相关图片"""
    global _jlu_img_cache
    if _jlu_img_cache:
        return _jlu_img_cache

    import urllib.request
    images = []

    try:
        url = 'https://news.jlu.edu.cn/tpxw.htm'
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')

        # 提取图片
        for m in re.findall(r'<img[^>]+src="([^"]+)"', html):
            img_url = m
            if img_url.startswith('//'):
                img_url = 'https:' + img_url
            elif img_url.startswith('/'):
                img_url = 'https://news.jlu.edu.cn' + img_url

            if img_url.startswith('http') and _is_valid_img(img_url):
                path = download_image(img_url)
                if path:
                    images.append(path)
    except Exception as e:
        print(f"获取图片失败: {e}")

    _jlu_img_cache = list(dict.fromkeys(images))
    return _jlu_img_cache


def _is_valid_img(url):
    """检查是否有效图片URL"""
    if not url:
        return False
    bad = ['.gif', '.ico', '.svg', '.bmp', '.webp', 'data:', 'logo', 'icon']
    return not any(ext in url.lower() for ext in bad)


def get_jlu_image():
    """获取一张吉大图片"""
    imgs = fetch_jlu_images()
    return random.choice(imgs) if imgs else ''


def download_image(url):
    """下载图片"""
    import urllib.request

    try:
        os.makedirs(NEWS_IMGS_DIR, exist_ok=True)

        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://news.jlu.edu.cn/',
        })

        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()

        if len(content) < 3000 or len(content) > 8000000:
            return ''

        ext = '.jpg'
        if '.png' in url.lower():
            ext = '.png'

        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(NEWS_IMGS_DIR, filename)

        with open(filepath, 'wb') as f:
            f.write(content)

        # 压缩
        compressed = _compress(filepath)
        if compressed:
            return compressed
        return filepath.replace(NEWS_IMGS_DIR, '/static/imgs/news')

    except Exception as e:
        print(f"下载失败: {e}")
        return ''


def _compress(filepath, max_w=800, qual=85):
    """压缩图片"""
    try:
        from PIL import Image

        img = Image.open(filepath)
        if os.path.getsize(filepath) < 100 * 1024:
            return ''

        if img.mode == 'RGBA':
            img = img.convert('RGB')

        w, h = img.size
        if w > max_w:
            img = img.resize((max_w, int(h * max_w / w)), Image.LANCZOS)

        out = os.path.join(NEWS_IMGS_DIR, f"{uuid.uuid4().hex}_thumb.jpg")
        img.save(out, 'JPEG', quality=qual, optimize=True)
        os.remove(filepath)

        while os.path.getsize(out) > 200 * 1024 and qual > 50:
            qual -= 10
            img.save(out, 'JPEG', quality=qual, optimize=True)

        return out.replace(NEWS_IMGS_DIR, '/static/imgs/news')

    except Exception as e:
        print(f"压缩失败: {e}")
        return ''


if __name__ == '__main__':
    print("=== 新闻获取测试 ===")
    news = fetch_jlu_news()
    print(f"\n结果: {len(news)} 条")
    for i, n in enumerate(news, 1):
        print(f"{i}. {n['title'][:50]}")
