import os
import re
import shutil
import logging
import anitopy
from .config import read_config

log = logging.getLogger("Renamer")

def get_subtitle_suffix(filename):
    """
    识别字幕后缀并进行标准化映射
    如: .sc.ass -> .zh-Hans.ass
    """
    # 扩展名映射表 (标准化为 Jellyfin 推荐格式)
    suffix_map = {
        'sc': 'zh-Hans',
        'chs': 'zh-Hans',
        'tc': 'zh-Hant',
        'cht': 'zh-Hant',
        'jp': 'ja',
        'jpn': 'ja',
        'ts': 'zh-Hans', # 常见字幕组简写
    }

    # 尝试匹配多种字幕后缀格式: .sc.ass, .chs.srt, etc.
    # 匹配 . (word) . (ext)
    match = re.search(r'\.([a-zA-Z\-]+)\.(ass|srt|ssa|vtt)$', filename.lower())
    if match:
        tag = match.group(1)
        ext = match.group(2)
        if tag in suffix_map:
            return f".{suffix_map[tag]}.{ext}"
        return f".{tag}.{ext}"
    
    # 如果没查到特殊的二级后缀，返回原始后缀
    return os.path.splitext(filename)[1]

def parse_episode_number(filename, custom_regex=None, force_season=None):
    """
    解析文件名中的集数。
    返回 (season, episode_str)
    force_season: 如果提供，则强制使用该季号 (适用于用户手动指定)
    """
    season = 1 if force_season is None else force_season
    
    # 预处理：移除哈希值
    safe_filename = re.sub(r'\[[A-Fa-f0-9]{8}\]', '', filename)
    safe_filename = re.sub(r'\([A-Fa-f0-9]{8}\)', '', safe_filename)

    # 1. 如果用户提供了自定义正则
    if custom_regex and custom_regex != 'auto':
        try:
            match = re.search(custom_regex, safe_filename)
            if match:
                # 如果匹配成功且没有强制季号，尝试从正则中提取季号（如果正则包含两个捕获组）
                # 否则保持默认或强制季号
                ep_str = match.group(1).zfill(2)
                return (season, ep_str)
        except Exception as e:
            log.error(f"自定义正则执行错误: {e}")

    # 2. 尝试使用 anitopy 解析 (AI/Smart 模式)
    try:
        parsed = anitopy.parse(filename)
        
        # Handle Season parsing (only if not forced)
        if force_season is None:
            s_val = parsed.get("anime_season")
            if isinstance(s_val, str) and s_val.isdigit():
                season = int(s_val)
            elif isinstance(s_val, list):
                if s_val[0].isdigit():
                    season = int(s_val[0])
            
            # 改进 SP 识别逻辑，避免误伤 (如 SPYxFAMILY)
            a_type = parsed.get("anime_type", "")
            # 只有当明确包含 OVA/Special 等字样时才设为 0
            is_special = False
            if isinstance(a_type, str):
                if any(x in a_type.upper() for x in ["OVA", "SPECIAL", "OAD"]):
                    is_special = True
            elif isinstance(a_type, list):
                if any(x.upper() in ["OVA", "SPECIAL", "OAD"] for x in a_type):
                    is_special = True
            
            if is_special:
                season = 0
            
            # 特殊情况：如果是 Season X，且 anitopy 没取到，再次正则兜底
            if season == 1:
                match_s = re.search(r'(?i)Season\s*(\d+)', safe_filename)
                if match_s:
                    season = int(match_s.group(1))

        ep = parsed.get("episode_number")
        if ep:
            if isinstance(ep, str) and ep.isdigit():
                return (season, ep.zfill(2))
            elif isinstance(ep, list) and ep[0].isdigit():
                return (season, ep[0].zfill(2))
    except Exception as e:
        log.warning(f"Anitopy 解析失败: {e}")

    # 匹配 [01v2] 格式
    match = re.search(r'\[(\d{1,3})v(\d)\]', safe_filename)
    if match: return (season, f"{match.group(1)}v{match.group(2)}")

    # 匹配 [01] 格式 (放在最前面，最准确)
    match = re.search(r'\[(\d{1,3})(?:v\d)?\]', safe_filename)
    if match: return (season, match.group(1).zfill(2))

    # 匹配 v2/v3/Final 结尾
    ver_match = re.search(r'(?i)[\[\s_](v\d|Final|PROPER)[\]\s_\.]', safe_filename)
    version_suffix = f" ({ver_match.group(1)})" if ver_match else ""

    # 匹配 Ep01 格式
    match = re.search(r'(?i)Ep?(\d{1,3})', safe_filename)
    if match: return (season, (match.group(1).zfill(2) + version_suffix).strip())

    # 针对纯数字文件名的后备匹配 (如 01.mp4)
    pure_name = os.path.splitext(filename)[0]
    if pure_name.isdigit():
        return (season, (pure_name.zfill(2) + version_suffix).strip())

    return (season, None)

async def dry_run_jellyfin_rename(folder_path, custom_regex='auto'):
    """
    模拟重命名，用于前端列表展示
    folder_path: 目标文件夹路径 (番剧主目录)
    """
    results = []
    if not os.path.exists(folder_path):
        return []
    
    for root, dirs, files in os.walk(folder_path):
        # 排除 Season 子目录，除非我们要递归处理所有文件并整理
        # 这里逻辑是：如果是库管理，我们可能想要把杂乱的文件丢进各个 Season 文件夹
        for filename in files:
            if filename.lower().endswith(('.mp4', '.mkv', '.ts', '.ass', '.srt')):
                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(root, folder_path)
                if rel_path == ".":
                    rel_path = ""

                # 如果已经在 Season 文件夹里了，我们可能不建议移动，除非季号不对
                # 但库整理工具通常就是要把外面的文件挪进去
                season, episode = parse_episode_number(filename, custom_regex)
                
                suffix = get_subtitle_suffix(filename)
                new_filename = f"S{str(season).zfill(2)}E{episode}{suffix}" if episode else "解析失败"
                
                # 计算目标路径
                season_folder = "Specials" if season == 0 else f"Season {season}"
                target_path = os.path.join(season_folder, new_filename)

                results.append({
                    "original": filename,
                    "relative_path": rel_path,
                    "full_path": filepath,
                    "target": new_filename,
                    "target_path": target_path,
                    "season": season,
                    "episode": episode or "",
                    "conflict": False # 初始化冲突标识
                })
    
    # 检测重名冲突 (多个源文件指向同一个目标文件名)
    target_counts = {}
    for r in results:
        if r["episode"]:
            tp = r["target_path"]
            target_counts[tp] = target_counts.get(tp, 0) + 1
            
    for r in results:
        if r["episode"] and target_counts.get(r["target_path"], 0) > 1:
            r["conflict"] = True
            
    return results

def apply_jellyfin_rename(mapping_list):
    """
    执行库文件重命名和移动
    mapping_list: [{"source": "full_path", "target": "full_target_path"}, ...]
    """
    count = 0
    for item in mapping_list:
        src = item.get("source")
        dst = item.get("target")
        if src and dst and os.path.exists(src):
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.move(src, dst)
                count += 1
            except Exception as e:
                log.error(f"重命名失败 {src} -> {dst}: {e}")
    return count

async def process_completed_downloads():
    """
    全量扫描暂存区，执行重命名并移动到正式目录（异步版）
    """
    config = await read_config()
    base_dir = config.get('save_dir', '')
    if not base_dir:
        return
    
    staging_base = os.path.join(base_dir, ".mikan_staging")
    if not os.path.exists(staging_base):
        return

    from .notifications import add_notification
    from ..db.models import Subscription

    # 遍历番剧文件夹
    for staging_subdir in os.listdir(staging_base):
        dir_path = os.path.join(staging_base, staging_subdir)
        if not os.path.isdir(dir_path):
            continue
            
        title_match = re.match(r'^(.*) \((\d{4})\)$', staging_subdir)
        title_only = title_match.group(1) if title_match else staging_subdir
        
        # 目标番剧根目录
        target_anime_dir = os.path.join(base_dir, staging_subdir)
        
        # 从数据库获取规则
        sub = await Subscription.get_or_none(title=title_only, is_deleted=False)
        custom_regex = sub.rename_rule if sub else 'auto'

        for root, dirs, files in os.walk(dir_path):
            for filename in files:
                filepath = os.path.join(root, filename)
                season, episode = parse_episode_number(filename, custom_regex)
                
                if not episode:
                    log.warning(f"无法解析集数，跳过重命名/清理: {filename}")
                    await add_notification("warning", "集数解析失败", f"文件 {filename} 无法识别集数，请在本地库手动修正")
                    continue
                    
                season_folder = "Specials" if season == 0 else f"Season {season}"
                target_dir = os.path.join(target_anime_dir, season_folder)
                os.makedirs(target_dir, exist_ok=True)
                
                suffix = get_subtitle_suffix(filename)
                new_filename = f"S{str(season).zfill(2)}E{episode}{suffix}"
                target_filepath = os.path.join(target_dir, new_filename)
                
                try:
                    shutil.move(filepath, target_filepath)
                    log.info(f"重命名并移动成功: {new_filename}")
                    await add_notification("success", "文件自动整理完成", f"{title_only} - {new_filename} 已归档")
                except Exception as e:
                    log.error(f"移动失败: {e}")
                    await add_notification("error", "文件整理失败", f"无法移动文件 {filename}: {e}")
            
            # 清理空目录
            if not os.listdir(root) and root != staging_base:
                try:
                    os.rmdir(root)
                except:
                    pass
