"""
扩展初始化 — APScheduler 新闻爬取调度器
"""

from apscheduler.schedulers.background import BackgroundScheduler
import database


def do_crawl_news(app, news_cache, alumni_cache):
    """执行新闻爬取(供调度器调用)"""
    from datetime import datetime
    executed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with app.app_context():
        try:
            database.clear_news()
            import news_crawler
            news_list = news_crawler.fetch_jlu_news()
            for news_item in news_list:
                database.save_news(
                    title=news_item.get('title', ''),
                    content=news_item.get('content', '来源:吉大新闻网'),
                    source_url=news_item.get('source_url', ''),
                    image_url=news_item.get('image_url', ''),
                    published_time=news_item.get('published_time', '')
                )
            database.set_news_crawl_log(executed_at, 'success', len(news_list), '定时爬取成功')
            print(f"[News Crawler] 成功爬取{len(news_list)}条新闻")

            # 清除缓存
            news_cache['data'] = None
            news_cache['timestamp'] = None
            alumni_cache['data'] = None
            alumni_cache['timestamp'] = None
        except Exception as e:
            database.set_news_crawl_log(executed_at, 'failed', 0, f'定时爬取失败: {e}')
            print(f"[News Crawler] 爬取失败: {e}")


def update_news_scheduler(app, news_cache, alumni_cache):
    """更新新闻爬取调度器"""
    hour = int(database.get_config('news_crawl_hour', '1'))
    minute = int(database.get_config('news_crawl_minute', '0'))

    scheduler = app.news_scheduler

    # 移除旧任务
    try:
        scheduler.remove_job('crawl_news')
    except:
        pass

    # 添加新任务
    scheduler.add_job(
        func=do_crawl_news,
        trigger='cron',
        hour=hour,
        minute=minute,
        id='crawl_news',
        replace_existing=True,
        args=[app, news_cache, alumni_cache]
    )


def init_news_scheduler(app, news_cache, alumni_cache):
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
        replace_existing=True,
        args=[app, news_cache, alumni_cache]
    )
    scheduler.start()
    app.news_scheduler = scheduler
    print(f"[News Scheduler] 已启动,每天{hour:02d}:{minute:02d}自动爬取新闻")
