import datetime
import os
import re
import time
import requests
import feedparser
import aria2p
import logging
from .config import read_config
from ..db.models import DownloadHistory, Subscription
from .notifications import add_notification

log = logging.getLogger("Downloader")

HEADER = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
}

async def add_to_history(guid: str, source: str):
    """
    添加下载历史 (异步 ORM 版)
    """
    await DownloadHistory.update_or_create(
        guid=guid,
        defaults={"source": source}
    )

async def check_history(guid: str) -> bool:
    """
    检查是否已在历史中
    """
    return await DownloadHistory.exists(guid=guid)

def request_url(url, get_url, need=False, proxies=None):
    if need:
        furl = url + get_url
    else:
        furl = get_url
    log.info(f"正在请求：{furl}")
    try:
        response = requests.get(furl, headers=HEADER, proxies=proxies, timeout=10)
        log.info(f"请求完成")
        return response
    except Exception as e:
        log.error(f"访问异常: {e}, URL:{furl}")
        return None

def mikan_request(get_url, api_urls, need=False, proxies=None):
    for url in api_urls:
        resp = request_url(url, get_url, need, proxies)
        if resp and resp.status_code == 200:
            return resp
        log.warning(f"当前URL无法访问，将切换下一个URl，当前URL:{url}")
    return None

def aria2_client(config):
    aria2_cfg = config.get('aria2', {})
    client = aria2p.API(aria2p.Client(
        host=aria2_cfg.get('host', 'http://127.0.0.1'),
        port=aria2_cfg.get('port', 6800),
        secret=aria2_cfg.get('secret', '')
    ))
    return client

async def aria2_add(client, title, rss_date, url, base_dir, torrents_dir, proxies=None):
    if not rss_date:
        rss_date = datetime.datetime.now().year
    
    # 使用临时路径，供后续 Renamer 检测 and 移动
    staging_dir = os.path.join(base_dir, ".mikan_staging", f"{title} ({rss_date})")
    
    if url.startswith("magnet:?xt="):
        client.add_torrent(url, options={'dir': staging_dir})
    else:
        _, filename = os.path.split(url)
        filename = os.path.join(torrents_dir, filename)
        if not os.path.exists(filename):
            resp = request_url("", url, proxies=proxies)
            if resp:
                with open(filename, 'wb') as f:
                    f.write(resp.content)
        client.add_torrent(filename, options={'dir': staging_dir})
    
    await add_notification("success", "已添加下载任务", f"番剧 {title} 的新资源已推送到 Aria2")

async def parse_rss_entries(rss_link, rss_date, rss_rule, config):
    api_urls = config.get('api_url', ['https://mikanani.me'])
    proxies = None
    if config.get('proxy'):
        proxies = {"http": config['proxy'], "https": config['proxy']}

    response = mikan_request(rss_link, api_urls, True, proxies)
    if not response:
        log.error(f"获取RSS失败: {rss_link}")
        await add_notification("error", "RSS 抓取失败", f"无法获取订阅 {rss_link} 的更新内容，请检查网络或代理设置。")
        return

    feed = feedparser.parse(response.text)
    channel_title = feed.get('channel', {}).get('title', '')
    title = channel_title.replace("Mikan Project - ", "")
    log.info(f"正在查询 {title}")

    base_dir = config.get('save_dir', '')
    torrents_dir = config.get('torrent_dir') or "./torrents"
    os.makedirs(torrents_dir, exist_ok=True)
    
    client = aria2_client(config)

    for entry in feed.entries:
        guid = entry.id
        if not await DownloadHistory.exists(guid=guid):
            if re.search(r'.*' + rss_rule + '.*', guid):
                for enclosure in entry.get('enclosures', []):
                    if enclosure.get('type') == 'application/x-bittorrent':
                        log.info(f"将 {entry.id} 添加到下载中")
                        await aria2_add(client, title, rss_date, enclosure.get('href'), base_dir, torrents_dir, proxies)
                await DownloadHistory.create(guid=guid, source=rss_link)

async def remove_unknown_rss_links(config):
    """
    清理配置中不再存在的历史记录
    """
    # 获取数据库中所有的 source
    db_sources = await DownloadHistory.all().distinct().values_list("source", flat=True)
    
    # 获取数据库中的所有订阅 URL
    subscriptions = await Subscription.filter(is_deleted=False).all()
    config_links = [s.url for s in subscriptions if s.url]
    
    remove_links = set(db_sources) - set(config_links)

    for remove_link in remove_links:
        log.info(f"找到配置中并未存在的RSS链接：{remove_link}，即将删除相关历史记录")
        await DownloadHistory.filter(source=remove_link).delete()

async def run_download_task():
    log.info("开始执行扫描下载任务...")
    config = await read_config()
    try:
        # Check aria2
        aria2_client(config).get_global_options()
    except Exception as e:
        log.error(f"无法连接至Aria2: {e}")
        await add_notification("error", "Aria2 连接失败", f"无法连接至 Aria2 服务，请检查设置。错误: {e}")
        return

    # 从数据库获取订阅
    subs = await Subscription.filter(is_deleted=False).all()
    rss_links = [(s.url, s.date, s.rule) for s in subs]

    for rss_link, rss_date, rss_rule in rss_links:
        if rss_link:
            try:
                await parse_rss_entries(rss_link, rss_date, rss_rule, config)
            except Exception as e:
                log.error(f"解析 {rss_link} 出错: {e}")
            time.sleep(2) # 休眠防ban

    log.info("正在搜索下载历史中是否有无效RSS")
    await remove_unknown_rss_links(config)
    log.info("查询完毕，已经将所有新的番剧添加到aria2中")
