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
    """爬取吉林大学相关新闻（主入口）

    按关键词匹配度排序，高匹配度的新闻排在前面。
    """
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

    # 2. Tavily搜索（吉林大学和校友会相关新闻）
    print("\n[2] 搜索 Tavily 新闻...")
    results.extend(_fetch_tavily_news())

    # 3. 抓取南岭校区东区事务办公室新闻（dqswb.jlu.edu.cn）
    print("\n[3] 抓取南岭校区新闻...")
    results.extend(_fetch_nanling_news())

    # 4. 抓取南岭校区所有学院新闻
    print("\n[4] 抓取南岭校区各学院新闻...")
    results.extend(_fetch_all_college_news())

    # 去重（同时考虑标题和URL）
    seen = set()
    unique = []
    for r in results:
        title_key = r['title'][:30]
        url_key = r.get('source_url', '')[:50] if r.get('source_url') else ''
        # 使用标题+URL组合去重
        dedup_key = f"{title_key}|{url_key}"
        if dedup_key not in seen:
            seen.add(dedup_key)
            unique.append(r)
    results = unique

    # 先补充图片（确保排序时能判断是否有图片）
    for r in results:
        if not r.get('image_url'):
            r['image_url'] = get_jlu_image()

    # 按日期+图片排序（最新优先，有图片的放前面）
    def news_sort_key(news):
        pub_time = news.get('published_time', '')
        if pub_time:
            try:
                date = datetime.strptime(pub_time[:10], '%Y-%m-%d')
            except:
                date = datetime.min
        else:
            date = datetime.min
        has_image = 1 if news.get('image_url') else 0
        return (date, has_image)

    results.sort(key=news_sort_key, reverse=True)

    # 兜底
    if len(results) == 0:
        print("\n[4] 使用示例新闻...")
        results = _generate_samples(keywords)
    else:
        print(f"\n共获取 {len(results)} 条新闻（已按日期排序，最新优先，有图片的在前）")

    return results[:20]


def _fetch_jlu_homepage():
    """抓取吉大新闻网新闻列表页及其详情页内容"""
    import urllib.request

    results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }

    try:
        # 改用新闻列表页，而不是首页（首页都是置顶旧闻）
        list_url = 'https://news.jlu.edu.cn/jdxw/jdxw.htm'
        req = urllib.request.Request(list_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')

        # 从列表页提取新闻条目
        # 页面格式: <a href="../info/1306/60905.htm" target="_blank">新闻标题</a>
        # 同时有日期信息: <span>2026-04-14</span>
        base_news_url = 'https://news.jlu.edu.cn/'

        # 提取所有新闻条目（链接+标题+日期）
        # 先找到所有包含日期和链接的条目
        article_pattern = r'<a[^>]+href="(\.\./info/\d+/\d+\.htm)"[^>]*>([^<]{5,100})</a>'
        date_pattern = r'<span>(\d{4}-\d{2}-\d{2})</span>'

        # 解析日期（在链接附近的<span>标签中）
        # 简化处理：先提取所有链接，再在整段HTML中找对应日期
        link_matches = list(re.finditer(article_pattern, html))

        news_items = []
        for match in link_matches[:20]:
            link = match.group(1)
            title = _clean_text(match.group(2).strip())

            if len(title) < 5:
                continue

            # 转换相对路径为完整URL: ../info/1306/60905.htm -> https://news.jlu.edu.cn/info/1306/60905.htm
            full_url = base_news_url + link.replace('../', '')

            # 尝试从链接附近提取日期
            # 查找该链接位置前后500字符内的日期
            start_pos = max(0, match.start() - 200)
            end_pos = min(len(html), match.end() + 200)
            nearby_html = html[start_pos:end_pos]
            date_match = re.search(date_pattern, nearby_html)
            pub_date = date_match.group(1) if date_match else datetime.now().strftime('%Y-%m-%d')

            # 关键词匹配（宽松）
            title_lower = title.lower()
            if any(kw.lower() in title_lower or kw.lower() in link.lower()
                   for kw in ['吉大', '南岭', '自动化', '学院', '大学', '校园', '学生', '教学', '科研', '杏花', '校', '体育', '比赛', '活动']):
                news_items.append({
                    'title': title[:200],
                    'source_url': full_url,
                    'published_time': pub_date,
                })

        # 抓取详情页获取内容和图片（限制最多8个）
        for i, item in enumerate(news_items[:8]):
            try:
                detail = _fetch_news_detail(item['source_url'])
                item['content'] = detail.get('content', '来源：吉大新闻网')
                item['image_url'] = detail.get('image_url', '')
                # 如果详情页也没有日期，用列表页的日期
                if not detail.get('published_time'):
                    detail['published_time'] = item['published_time']
                print(f"  ✓ {item['title'][:40]}... [{item['published_time']}]")
            except Exception as e:
                item['content'] = '来源：吉大新闻网'
                item['image_url'] = ''
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


def _fetch_all_college_news():
    """抓取南岭校区所有学院的新闻"""
    # 南岭校区学院列表
    colleges = [
        ('https://auto.jlu.edu.cn', '汽车工程学院'),
        ('https://jtxy.jlu.edu.cn', '交通学院'),
        ('https://jxhk.jlu.edu.cn', '机械与航空航天工程学院'),
        ('https://swny.jlu.edu.cn', '生物与农业工程学院'),
        ('https://clxy.jlu.edu.cn', '材料科学与工程学院'),
        ('https://txgcxy.jlu.edu.cn', '通信工程学院'),
        ('https://dzgcxy.jlu.edu.cn', '电子科学与工程学院'),
        ('https://ccst.jlu.edu.cn', '计算机科学与技术学院'),
        ('https://math.jlu.edu.cn', '数学学院'),
        ('https://physics.jlu.edu.cn', '物理学院'),
        ('https://chem.jlu.edu.cn', '化学学院'),
        ('https://skxy.jlu.edu.cn', '生命科学学院'),
    ]

    all_results = []
    for url, name in colleges:
        try:
            results = _fetch_college_news(url, name)
            all_results.extend(results)
            print(f"  ✓ {name}: 抓取到 {len(results)} 条")
        except Exception as e:
            print(f"  ✗ {name}失败: {e}")
            continue

    return all_results


def _fetch_nanling_news():
    """抓取南岭校区东区事务办公室新闻 (dqswb.jlu.edu.cn)"""
    import urllib.request

    results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }

    base_url = 'https://dqswb.jlu.edu.cn'
    # 收集所有文章链接
    article_links = set()

    # 1. 首页
    try:
        req = urllib.request.Request(base_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        # 提取 info/XXXX/XXXX.htm 格式的文章链接
        for link in re.findall(r'href=["\'](info/\d+/\d+\.htm)', html):
            article_links.add(link)
        print(f"  ✓ 首页找到 {len(article_links)} 篇文章")
    except Exception as e:
        print(f"  ✗ 南岭首页失败: {e}")

    # 2. 学工动态页面 xwkx.htm
    try:
        req = urllib.request.Request(f'{base_url}/xwkx.htm', headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        for link in re.findall(r'href=["\'](info/\d+/\d+\.htm)', html):
            article_links.add(link)
        for link in re.findall(r'href=["\'](/info/\d+/\d+\.htm)', html):
            article_links.add(link.lstrip('/'))
        print(f"  ✓ 学工动态页面找到 {len(article_links)} 篇文章")
    except Exception as e:
        print(f"  ✗ 学工动态页面失败: {e}")

    # 3. 抓取每篇文章详情
    for link in list(article_links)[:15]:
        if not link.startswith('http'):
            url = f'{base_url}/{link}'
        else:
            url = link

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode('utf-8', errors='ignore')

            # 提取标题
            title_match = re.search(r'<title>([^<]+)</title>', html)
            title = _clean_text(title_match.group(1).replace('-吉林大学东区事务办公室', '').replace('-吉林大学东区事务办公室', '').strip()) if title_match else ''

            if not title or len(title) < 5:
                continue

            # 提取正文段落
            paras = re.findall(r'<p[^>]*>([^<]+)</p>', html)
            content = ' '.join([_clean_text(p) for p in paras[:15] if _clean_text(p)])
            content = content[:500] if content else '来源：南岭校区东区事务办公室'

            # 提取发布时间（多种格式支持）
            # 格式1: 2026年3月27日 / 2026-03-27 / 2026/03/27
            time_match = re.search(r'(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})', html)
            if time_match:
                pub_time = f"{time_match.group(1)}-{time_match.group(2).zfill(2)}-{time_match.group(3).zfill(2)}"
            else:
                # 格式2: 3月27日（从正文中找，使用当前年份）
                chinese_date = re.search(r'(\d{1,2})月(\d{1,2})日', html)
                if chinese_date:
                    current_year = datetime.now().year
                    pub_time = f"{current_year}-{chinese_date.group(1).zfill(2)}-{chinese_date.group(2).zfill(2)}"
                else:
                    pub_time = datetime.now().strftime('%Y-%m-%d')

            # 提取图片
            img_url = ''
            img_matches = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html)
            for img in img_matches:
                if img.startswith('//'):
                    img = 'https:' + img
                elif img.startswith('/'):
                    img = base_url + img
                if img.startswith('http') and _is_valid_img(img):
                    if any(bad in img.lower() for bad in ['logo', 'icon', 'banner', 'nav', 'menu', 'button']):
                        continue
                    downloaded = download_image(img)
                    if downloaded:
                        img_url = downloaded
                        break

            results.append({
                'title': title[:200],
                'content': content,
                'source_url': url,
                'image_url': img_url,
                'published_time': pub_time
            })
            print(f"  ✓ {title[:40]}...")

        except Exception as e:
            print(f"  ✗ 抓取失败 {url}: {e}")

    return results


def _fetch_tavily_news():
    """通过 Tavily API 搜索吉林大学和校友会相关新闻"""
    import urllib.request
    import json
    import database

    results = []
    api_key = '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'

    # 搜索关键词
    search_queries = [
        '吉林大学',
        '吉林大学 新闻',
        '吉林大学 南岭校区',
        '吉林大学南岭校区 新闻',
        '吉林大学 活动',
        '吉林大学校友会',
        '吉林大学北京校友会',
        '吉林大学上海校友会',
        '吉林大学深圳校友会',
        '吉林大学广州校友会',
        '吉林大学成都校友会',
        '吉林大学武汉校友会',
        '吉林大学北美校友会',
        '吉林大学杏花节',
    ]

    # 追加管理员设置的关键词
    db_keywords = database.get_news_keywords()
    for kw in db_keywords:
        if kw not in search_queries:
            search_queries.append(kw)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }

    for query in search_queries[:5]:  # 限制搜索次数
        try:
            # Tavily Search API
            search_url = 'https://api.tavily.com/search'
            payload = json.dumps({
                'api_key': api_key,
                'query': query,
                'search_depth': 'basic',
                'max_results': 3,
                'include_answer': False,
                'include_raw_content': False,
            })

            req = urllib.request.Request(
                search_url,
                data=payload.encode('utf-8'),
                headers={**headers, 'Content-Type': 'application/json'},
                method='POST'
            )

            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            results_list = data.get('results', [])
            for item in results_list[:3]:
                title = _clean_text(item.get('title', ''))
                if len(title) < 5:
                    continue

                content = _clean_text(item.get('content', ''))[:300] if item.get('content') else '来源：Tavily搜索'
                source_url = item.get('url', '')
                pub_date = item.get('published_date', '')
                if not pub_date:
                    pub_date = datetime.now().strftime('%Y-%m-%d')

                # 尝试从URL提取图片（如果有的话）
                img_url = ''

                results.append({
                    'title': title[:200],
                    'content': content,
                    'source_url': source_url,
                    'image_url': img_url,
                    'published_time': pub_date,
                })
                print(f"  ✓ Tavily: {title[:40]}...")

        except Exception as e:
            print(f"  ✗ Tavily 搜索失败 ({query}): {e}")
            continue

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
