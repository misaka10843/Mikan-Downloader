import datetime
import time

import feedparser
import sqlite3
import requests as requests
import yaml
import re
import os
import aria2p

HEADER = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/58.0.3029.110 Safari/537.36'
}
PROXIES = {}
ARIA2 = {}
BASE_DRI = ""
API_COUNTER = 0
TORRENTS_DIR = "./torrents"


def get_db_connection():
    if os.path.isfile('history.db'):
        conn = sqlite3.connect('history.db')
    else:
        conn = sqlite3.connect('history.db')
        db = conn.cursor()
        db.execute('''CREATE TABLE guids
                     (guid TEXT PRIMARY KEY, source TEXT)''')
        conn.commit()
        db.close()
    return conn


def read_config():
    with open('config.yml', 'r',encoding="UTF-8") as f:
        config = yaml.safe_load(f)
    return config


def api_restriction():
    global API_COUNTER
    API_COUNTER += 1
    # 防止退出后立马再次运行
    if API_COUNTER >= 5:
        API_COUNTER = 0
        print("休息一下，给服务器一点喘息的时间吧qwq")
        time.sleep(15)


def aria2(title, rss_date, url):
    client = aria2p.API(aria2p.Client(
        host=ARIA2['host'],
        port=ARIA2['port'],
        secret=ARIA2['secret']
    ))
    try:
        options = client.get_global_options()
    except Exception as e:
        print(f"无法连接至Aria2: {e}")
        exit()
    base_dir = BASE_DRI or client.get_global_options().get('dir')
    if not rss_date:
        rss_date = datetime.datetime.now().year
    if url.startswith("magnet:?xt="):
        client.add_torrent(url, options={'dir': f'{base_dir}/{title} ({rss_date})'})
    else:
        _, filename = os.path.split(url)
        filename = os.path.join(TORRENTS_DIR, filename)
        if not os.path.exists(filename):
            resp = requests.get(url, headers=HEADER, proxies=PROXIES)
            api_restriction()
            with open(filename, 'wb') as f:
                f.write(resp.content)
        client.add_torrent(filename, options={'dir': f'{base_dir}/{title} ({rss_date})'})


def get_rss_links(config):
    rss_links = [(source['url'], source['date'], source['rule']) for source in config['mikan']]
    return rss_links


def parse_rss_entries(rss_link, rss_date, rss_rule, conn):
    response = requests.get(rss_link, headers=HEADER, proxies=PROXIES)
    api_restriction()
    feed = feedparser.parse(response.text)
    title = feed['channel']['title'].replace("Mikan Project - ", "")
    print(f"正在查询{title}")

    for entry in feed.entries:
        guid = entry.id
        c = conn.cursor()
        c.execute("SELECT * FROM guids WHERE guid=?", (guid,))
        if not c.fetchone():
            if re.search(rss_rule, guid):
                for enclosure in entry.get('enclosures', []):
                    if enclosure.get('type') == 'application/x-bittorrent':
                        print(f"将{entry.id}添加到下载中")
                        aria2(title, rss_date, enclosure.get('href'))

            c.execute("INSERT INTO guids VALUES (?, ?)", (guid, rss_link))
            conn.commit()
        c.close()


def remove_unknown_rss_links(config, conn):
    c = conn.cursor()
    c.execute("SELECT DISTINCT source FROM guids")
    db_links = [row[0] for row in c.fetchall()]

    remove_links = set(db_links) - set([source['url'] for source in config['mikan']])

    for remove_link in remove_links:
        print(f"找到配置中并未存在的RSS链接：{remove_link}，即将删除相关历史记录")
        c.execute("DELETE FROM guids WHERE source=?", (remove_link,))
        conn.commit()
    c.close()


def main():
    global PROXIES, ARIA2, BASE_DRI, TORRENTS_DIR
    conn = get_db_connection()
    config = read_config()
    # 将配置写入全局变量
    if config['proxy']:
        PROXIES = {
            "http": config['proxy'],
            "https": config['proxy']
        }
    BASE_DRI = config['save_dir']
    ARIA2 = config['aria2']
    if config['torrent_dir']:
        TORRENTS_DIR = config['torrent_dir']
    os.makedirs(TORRENTS_DIR, exist_ok=True)
    # 获取所有的rss链接
    rss_links = get_rss_links(config)

    for rss_link, rss_date, rss_rule in rss_links:
        parse_rss_entries(rss_link, rss_date, rss_rule, conn)
    print("正在搜索下载历史中是否有无效RSS")
    remove_unknown_rss_links(config, conn)
    conn.close()
    print("查询完毕，已经将所有新的番剧添加到aria2中")


if __name__ == '__main__':
    main()
