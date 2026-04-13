import datetime
import os
import re
import sqlite3
import time
import requests
import feedparser
import aria2p
import logging
from .config import read_config

log = logging.getLogger("Downloader")

HEADER = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
}

def get_db_connection():
    conn = sqlite3.connect('history.db')
    db = conn.cursor()
    db.execute('''CREATE TABLE IF NOT EXISTS guids (guid TEXT PRIMARY KEY, source TEXT)''')
    conn.commit()
    return conn

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

def aria2_add(client, title, rss_date, url, base_dir, torrents_dir):
    if not rss_date:
        rss_date = datetime.datetime.now().year
    
    # 使用临时路径，供后续 Renamer 检测和移动
    staging_dir = os.path.join(base_dir, ".mikan_staging", f"{title} ({rss_date})")
    
    if url.startswith("magnet:?xt="):
        client.add_torrent(url, options={'dir': staging_dir})
    else:
        _, filename = os.path.split(url)
        filename = os.path.join(torrents_dir, filename)
        if not os.path.exists(filename):
            resp = request_url("", url)
            if resp:
                with open(filename, 'wb') as f:
                    f.write(resp.content)
        client.add_torrent(filename, options={'dir': staging_dir})

def parse_rss_entries(rss_link, rss_date, rss_rule, conn, config):
    api_urls = config.get('api_url', ['https://mikanani.me'])
    proxies = None
    if config.get('proxy'):
        proxies = {"http": config['proxy'], "https": config['proxy']}

    response = mikan_request(rss_link, api_urls, True, proxies)
    if not response:
        log.error(f"获取RSS失败: {rss_link}")
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
        c = conn.cursor()
        c.execute("SELECT * FROM guids WHERE guid=?", (guid,))
        if not c.fetchone():
            if re.search(r'.*' + rss_rule + '.*', guid):
                for enclosure in entry.get('enclosures', []):
                    if enclosure.get('type') == 'application/x-bittorrent':
                        log.info(f"将 {entry.id} 添加到下载中")
                        aria2_add(client, title, rss_date, enclosure.get('href'), base_dir, torrents_dir)
                c.execute("INSERT INTO guids VALUES (?, ?)", (guid, rss_link))
            conn.commit()
        c.close()

def remove_unknown_rss_links(config, conn):
    c = conn.cursor()
    c.execute("SELECT DISTINCT source FROM guids")
    db_links = [row[0] for row in c.fetchall()]

    config_links = [source.get('url') for source in config.get('mikan', []) if source.get('url')]
    remove_links = set(db_links) - set(config_links)

    for remove_link in remove_links:
        log.info(f"找到配置中并未存在的RSS链接：{remove_link}，即将删除相关历史记录")
        c.execute("DELETE FROM guids WHERE source=?", (remove_link,))
        conn.commit()
    c.close()

def run_download_task():
    log.info("开始执行扫描下载任务...")
    config = read_config()
    conn = get_db_connection()
    try:
        # Check aria2
        aria2_client(config).get_global_options()
    except Exception as e:
        log.error(f"无法连接至Aria2: {e}")
        conn.close()
        return

    rss_links = [(source.get('url'), source.get('date'), source.get('rule')) for source in config.get('mikan', []) if not source.get('is_deleted')]

    for rss_link, rss_date, rss_rule in rss_links:
        if rss_link:
            try:
                parse_rss_entries(rss_link, rss_date, rss_rule, conn, config)
            except Exception as e:
                log.error(f"解析 {rss_link} 出错: {e}")
            time.sleep(2) # 休眠防ban

    log.info("正在搜索下载历史中是否有无效RSS")
    remove_unknown_rss_links(config, conn)
    conn.close()
    log.info("查询完毕，已经将所有新的番剧添加到aria2中")
