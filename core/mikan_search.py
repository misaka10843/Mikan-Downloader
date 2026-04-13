import logging
import requests
import re
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from urllib.parse import quote
from core.config import read_config

log = logging.getLogger("MikanSearch")

def get_proxies(config: dict):
    if config.get('proxy'):
        return {"http": config['proxy'], "https": config['proxy']}
    return None

def get_mikan_hosts(config: dict):
    mikan_hosts = config.get('api_url', ['https://mikanani.me', 'https://mikanime.tv'])
    if not mikan_hosts:
        mikan_hosts = ['https://mikanani.me']
    return mikan_hosts

def search_bangumi(keyword: str) -> List[Dict[str, Any]]:
    """
    通过网页抓取 Mikan 搜索页，然后进入番组详情页提取订阅信息。
    """
    config = read_config()
    proxies = get_proxies(config)
    mikan_hosts = get_mikan_hosts(config)
    base_mikan = mikan_hosts[0].rstrip("/")
    
    url = f"{base_mikan}/Home/Search?searchstr={quote(keyword)}"
    log.info(f"正在搜索 Mikan: {url}")
    
    try:
        response = requests.get(url, proxies=proxies, timeout=10)
        response.raise_for_status()
    except Exception as e:
        log.error(f"Mikan 搜索请求失败: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    results = []
    
    # 步骤1：从搜索页提取直接相关的番剧列表
    bangumis = []
    # 匹配 ul.list-inline.an-ul 项目
    items = soup.select('ul.list-inline.an-ul li')
    for item in items:
        a_tag = item.find('a', href=True)
        if not a_tag:
            continue
        href = a_tag['href']
        if not href.startswith('/Home/Bangumi/'):
            continue
        bangumi_id = href.split('/')[-1]
        
        # 提取标题
        title_tag = item.select_one('.an-text')
        title = title_tag['title'] if title_tag and title_tag.has_attr('title') else title_tag.text.strip() if title_tag else "未知番剧"
        
        # 提取封面
        cover_tag = item.select_one('span.b-lazy')
        cover_url = ""
        if cover_tag and cover_tag.has_attr('data-src'):
            raw_src = cover_tag['data-src']
            cover_url = base_mikan + raw_src if raw_src.startswith('/') else raw_src
            
        bangumis.append({
            "id": bangumi_id,
            "title": title,
            "cover": cover_url,
            "url": f"{base_mikan}{href}"
        })
        
    log.info(f"找到 {len(bangumis)} 个相关的番剧概览，准备抓取字幕组...")

    # 步骤2：对前 3 个最相关的番剧请求详情页，获取字幕组信息
    for bgm in bangumis[:3]:
        try:
            bgm_res = requests.get(bgm["url"], proxies=proxies, timeout=10)
            bgm_res.raise_for_status()
            bgm_soup = BeautifulSoup(bgm_res.text, 'html.parser')
            
            subgroups = bgm_soup.select('div.subgroup-text')
            for sub in subgroups:
                sub_id = sub.get('id', '')
                
                # 寻找字幕组名字（通常是第一个链接）
                sub_name_a = sub.find('a', href=re.compile(r'/Home/PublishGroup/'))
                subgroup_name = sub_name_a.text.strip() if sub_name_a else "未知字幕组"
                
                # 寻找RSS链接
                rss_a = sub.find('a', class_='mikan-rss', href=True)
                if not rss_a:
                    continue
                rss_href = rss_a['href']
                
                results.append({
                    "bangumiId": bgm["id"],
                    "subgroupId": sub_id,
                    "url": rss_href,
                    "name": f"{bgm['title']} - {subgroup_name}",
                    "title": bgm['title'],
                    "cover": bgm['cover'],
                    "raw_url": f"{base_mikan}{rss_href}"
                })
        except Exception as e:
            log.warning(f"获取番剧 {bgm['title']} 详情页失败: {e}")
            continue

    log.info(f"搜集完成，共获取 {len(results)} 条可用订阅项。")
    return results
