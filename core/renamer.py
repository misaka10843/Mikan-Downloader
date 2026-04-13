import os
import shutil
import re
import logging
from .config import read_config
from .downloader import aria2_client

log = logging.getLogger("Renamer")

def parse_episode_number(filename: str, custom_regex: str = None, fallback_auto: bool = True):
    season = 1
    
    if custom_regex and custom_regex != 'auto':
        try:
            match = re.search(custom_regex, filename)
            if match and match.lastindex and match.lastindex >= 1:
                return (season, match.group(1).zfill(2))
            elif match:
                if len(match.groups()) > 0:
                    return (season, match.group(1).zfill(2))
        except Exception as e:
            log.warning(f"自定义正则解析失败 {e} -> {custom_regex}")
    
    if not fallback_auto:
        return (None, None)

    # Try anitopy first
    try:
        import anitopy
        parsed = anitopy.parse(filename)
        
        # Handle Season parsing
        s_val = parsed.get("anime_season")
        if isinstance(s_val, str) and s_val.isdigit():
            season = int(s_val)
            
        a_type = parsed.get("anime_type", "")
        if "OVA" in a_type or "Special" in a_type or "SP" in a_type or "OAD" in a_type:
            season = 0

        ep = parsed.get("episode_number")
        if ep and isinstance(ep, str) and ep.isdigit():
            return (season, ep.zfill(2))
    except:
        pass

    # Drop 8-character hex CRCs (like [DD28AE19] or (DD28AE19)) to avoid false matching
    safe_filename = re.sub(r'\[[A-Fa-f0-9]{8}\]', '', filename)
    safe_filename = re.sub(r'\([A-Fa-f0-9]{8}\)', '', safe_filename)

    # Simple SP/OVA detection for fallback
    if "OVA" in safe_filename.upper() or " SP" in safe_filename.upper() or "[SP" in safe_filename.upper():
        season = 0

    match = re.search(r'\[(\d{1,3})(?:v\d)?\]', safe_filename)
    if match: return (season, match.group(1).zfill(2))
        
    match = re.search(r'【(\d{1,3})(?:v\d)?】', safe_filename)
    if match: return (season, match.group(1).zfill(2))
        
    # include 話 (traditional/JP) and 话 (simplified) and 集
    match = re.search(r'第(\d{1,3})[话話集]', safe_filename)
    if match: return (season, match.group(1).zfill(2))
        
    match = re.search(r'\s-\s(\d{1,3})\s', safe_filename)
    if match: return (season, match.group(1).zfill(2))
        
    match = re.search(r'(?i)\bE(\d{1,3})\b', safe_filename)
    if match: return (season, match.group(1).zfill(2))
        
    match = re.search(r'(?i)Ep?(\d{1,3})', safe_filename)
    if match: return (season, match.group(1).zfill(2))

    return (None, None)

def dry_run_jellyfin_rename(target_dir: str, title: str, custom_regex: str = None) -> dict:
    """
    返回干预演练映射表，不进行任何真实的文件移动，但包含 compliant_warning。
    """
    results = []
    already_compliant = False
    
    if not os.path.exists(target_dir):
        return {"already_compliant": False, "items": results}
        
    for root, dirs, files in os.walk(target_dir):
        # 探测是否已经是符合规范的层级结构（仅在顶层探测）
        if root == target_dir:
            for d in dirs:
                dl = d.lower()
                if dl.startswith("season ") or dl in ("specials", "sp", "scans", "extras"):
                    already_compliant = True
        
        # 原地修改 dirs 来剪除这些不需要重复处理的成品文件夹，防止二次污染或死循环
        dirs[:] = [d for d in dirs if not (d.lower().startswith("season ") or d.lower() in ("specials", "sp", "scans", "extras", "featurettes"))]

        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in ['.mp4', '.mkv', '.avi', '.prm', '.ass', '.srt', '.vtt', '.sup', '.ssa', '.nfo']:
                continue
                
            if ext == '.nfo' and (filename.lower() in ['tvshow.nfo', 'season.nfo'] or filename.lower().startswith('season')):
                continue
            
            # 强化字幕后缀探测
            suffix = ext
            if ext in ['.ass', '.srt', '.vtt', '.sup', '.ssa']:
                base = os.path.splitext(filename)[0]
                sub_ext2 = os.path.splitext(base)[1].lower()
                if sub_ext2 in ['.tc', '.sc', '.chs', '.cht', '.zh', '.zh-cn', '.zh-tw', '.eng', '.jpn', '.en', '.jp']:
                    suffix = sub_ext2 + ext
                else:
                    for lang in ['chs', 'cht', 'tc', 'sc', 'zh-cn', 'zh-tw', 'eng', 'jpn']:
                        if lang in filename.lower() and not f".{lang}" in sub_ext2:
                            suffix = f".{lang}{ext}"
                            break
            
            filepath = os.path.join(root, filename)
            season, ep = parse_episode_number(filename, custom_regex)
            
            season_folder = "Specials" if season == 0 else f"Season {season}"

            if ep:
                new_name = f"S{str(season).zfill(2)}E{ep}{suffix}"
                target_dest = os.path.join(target_dir, season_folder, new_name)
                # target_dest 这里作为在原目录下的重构，或者是基于基准库
            else:
                new_name = None
                target_dest = None
                
            results.append({
                "original_path": filepath,
                "original_name": filename,
                "season": season,
                "episode": ep,
                "title": title,
                "target_dir": target_dir,
                "ext": suffix,
                "new_name": new_name,
                "target_path": target_dest,
                "status": "success" if ep else "failed"
            })
            
    return {"already_compliant": already_compliant, "items": results}

def apply_jellyfin_rename(mapping_list: list):
    """
    应用由前端发来的实际重命名与物理移动字典列表
    mapping_list 形如: [{ original_path: "...", target_path: "...", ... }]
    """
    success_count = 0
    for item in mapping_list:
        if item.get("status") == "success" and item.get("new_name"):
            src = item["original_path"]
            dst = item["target_path"]
            if os.path.exists(src):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                try:
                    shutil.move(src, dst)
                    success_count += 1
                except Exception as e:
                    log.error(f"移动重命名失败：{e} | {src} -> {dst}")
    return success_count

def process_completed_downloads():
    log.info("开始检查已完成下载进行Jellyfin重命名...")
    config = read_config()
    try:
        client = aria2_client(config)
        downloads = client.get_downloads()
    except Exception as e:
        log.error(f"无法连接Aria2: {e}")
        return

    base_dir = config.get('save_dir')
    if not base_dir:
        return

    mikan_staging = os.path.join(base_dir, ".mikan_staging")
    if not os.path.exists(mikan_staging):
        return
        
    subs = config.get('mikan', [])

    for download in downloads:
        if download.status == 'complete' and download.dir and mikan_staging in download.dir:
            log.info(f"处理完成的下载: {download.name}")
            anime_folder_name = os.path.basename(download.dir)
            title_only = anime_folder_name
            year_match = re.search(r'(.*)\s\(\d{4}\)', anime_folder_name)
            if year_match:
                title_only = year_match.group(1).strip()
                
            # 从订阅里寻找对应的 custom_regex
            custom_regex = None
            for sub in subs:
                if sub.get('title') == title_only or (title_only in (sub.get('name') or '')):
                    custom_regex = sub.get('rename_rule', 'auto')
                    break
                
            target_season_dir = os.path.join(base_dir, anime_folder_name, "Season 1")
            
            for file in download.files:
                filepath = file.path
                if not filepath or not os.path.exists(filepath):
                    continue
                
                filename = os.path.basename(filepath)
                ext = os.path.splitext(filename)[1].lower()
                if ext not in ['.mp4', '.mkv', '.avi', '.prm', '.ass', '.srt', '.vtt', '.sup', '.ssa', '.nfo']:
                    continue
                    
                if ext == '.nfo' and (filename.lower() in ['tvshow.nfo', 'season.nfo'] or filename.lower().startswith('season')):
                    continue
                    
                # 强化字幕后缀探测
                suffix = ext
                if ext in ['.ass', '.srt', '.vtt', '.sup', '.ssa']:
                    base = os.path.splitext(filename)[0]
                    sub_ext2 = os.path.splitext(base)[1].lower()
                    if sub_ext2 in ['.tc', '.sc', '.chs', '.cht', '.zh', '.zh-cn', '.zh-tw', '.eng', '.jpn', '.en', '.jp']:
                        suffix = sub_ext2 + ext
                    else:
                        for lang in ['chs', 'cht', 'tc', 'sc', 'zh-cn', 'zh-tw', 'eng', 'jpn']:
                            if lang in filename.lower() and not f".{lang}" in sub_ext2:
                                suffix = f".{lang}{ext}"
                                break
                    
                season, episode = parse_episode_number(filename, custom_regex)
                if not episode:
                    log.warning(f"无法解析集数，跳过重命名/清理: {filename}")
                    continue
                    
                season_folder = "Specials" if season == 0 else f"Season {season}"
                new_filename = f"S{str(season).zfill(2)}E{episode}{suffix}"
                
                target_season_dir = os.path.join(base_dir, anime_folder_name, season_folder)
                target_filepath = os.path.join(target_season_dir, new_filename)
                
                os.makedirs(target_season_dir, exist_ok=True)
                
                try:
                    shutil.move(filepath, target_filepath)
                    log.info(f"重命名并移动成功: {new_filename}")
                except Exception as e:
                    log.error(f"移动失败: {e}")
            
            client.remove([download], force=True, files=True)
            try:
                if os.path.exists(download.dir) and not os.listdir(download.dir):
                    os.rmdir(download.dir)
            except:
                pass

