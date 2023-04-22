import feedparser
import sqlite3
import yaml
import re
import os
from datetime import datetime, timedelta

HEADER = {

}
# 读取配置文件
with open('config.yml', 'r') as f:
    config = yaml.safe_load(f)

# 连接到SQLite数据库
if os.path.isfile('history.db'):
    conn = sqlite3.connect('history.db')
else:
    conn = sqlite3.connect('history.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE guids
                 (guid TEXT PRIMARY KEY, source TEXT)''')
    conn.commit()
    c.close()

# 获取所有RSS源的链接、日期和正则表达式规则
rss_links = [(source['url'], source['date'], source['rule']) for source in config['mikan']]

# 获取当前日期
current_date = datetime.now()

# 遍历所有的RSS源
for rss_link, rss_date, rss_rule in rss_links:
    # 解析RSS源
    feed = feedparser.parse(rss_link)

    # 获取最新条目的日期
    last_entry_date = datetime.strptime(feed.entries[0].published, '%a, %d %b %Y %H:%M:%S %z')

    # 输出RSS源的日期
    print(f"{rss_link}: {rss_date}")

    # 遍历所有的RSS条目
    for entry in feed.entries:
        # 获取当前条目的guid字符串
        guid = entry.guid

        # 判断是否为第一次输出
        c = sqlite3.connect('history.db').cursor()
        c.execute("SELECT * FROM guids WHERE guid=?", (guid,))
        if not c.fetchone() and entry.enclosures:
            # 判断guid是否符合规则
            if re.match(rss_rule, guid):
                # 输出type="application/x-bittorrent"的url
                enclosure = entry.enclosures[0]
                if enclosure.type == 'application/x-bittorrent':
                    print(enclosure.url)

            # 将guid字符串和RSS源的URL插入到数据库中
            c.execute("INSERT INTO guids VALUES (?, ?)", (guid, rss_link))
            conn.commit()
        c.close()

    # 计算最新条目的日期和当前日期之间的差距
    delta = current_date - last_entry_date

    # 如果差距超过3个月，就从数据库中删除所有关于这个RSS源的内容
    if delta >= timedelta(days=90):
        c = conn.cursor()
        c.execute("DELETE FROM guids WHERE source=?", (rss_link,))
        conn.commit()
        c.close()

# 获取所有在`history.db`中的RSS源的链接
conn = sqlite3.connect('history.db')
c = conn.cursor()
c.execute("SELECT DISTINCT source FROM guids")
db_links = [row[0] for row in c.fetchall()]

# 找出不在配置文件中的RSS源
remove_links = set(db_links) - set([source['link'] for source in config['sources']])

# 删除所有不在配置文件中的RSS源的内容
for remove_link in remove_links:
    c.execute("DELETE FROM guids WHERE source=?", (remove_link,))
    conn.commit()
c.close()

# 关闭数据库连接
conn.close()