from fastapi import APIRouter
from typing import Dict, Any, List
import os
import logging

from core.renamer import dry_run_jellyfin_rename, apply_jellyfin_rename, parse_episode_number
from core.config import read_config, save_config

router = APIRouter(prefix="/api/library")

@router.get("/list")
def get_library_list(path: str = None):
    cfg = read_config()
    save_dir = path if path else cfg.get("save_dir")
    if not save_dir or not os.path.exists(save_dir):
        return {"status": "error", "message": "库目录不存在或未填写"}
        
    # 只列出根目录下的文件夹（番剧文件夹）
    folders = []
    logger = logging.getLogger("Library")
    
    try:
        # Save as long term preference if path is provided explicitly
        if path and path != cfg.get("save_dir"):
            cfg["save_dir"] = path
            save_config(cfg)
            
        for item in os.listdir(save_dir):
            item_path = os.path.join(save_dir, item)
            if os.path.isdir(item_path) and not item.startswith("."): # 忽略 .mikan_staging
                is_compliant = False
                needs_rename = False
                try:
                    for subitem in os.listdir(item_path):
                        dl = subitem.lower()
                        if dl.startswith("season ") or dl in ("specials", "sp", "scans", "extras", "featurettes"):
                            is_compliant = True
                        elif dl.endswith(('.mp4', '.mkv', '.avi', '.ass', '.srt', '.vtt', '.nfo')):
                            if dl not in ('tvshow.nfo', 'season.nfo') and not dl.startswith('season'):
                                needs_rename = True
                except:
                    pass
                
                folders.append({
                    "name": item,
                    "path": item_path,
                    "is_compliant": is_compliant,
                    "needs_rename": needs_rename
                })
    except Exception as e:
        logger.error(f"Error listing library: {e}")
        return {"status": "error", "message": str(e)}
        
    return {"status": "success", "folders": folders}

@router.post("/preview_rename")
def preview_rename(data: Dict[str, Any]):
    # data: {"path": "/mnt/share/anime/SomeAnime (2024)", "regex": "..."}
    folder_path = data.get("path")
    custom_regex = data.get("regex", "auto")
    
    if not folder_path or not os.path.exists(folder_path):
        return {"status": "error", "message": "文件夹路径无效"}
        
    title = os.path.basename(folder_path)
    import re
    year_match = re.search(r'(.*)\s\(\d{4}\)', title)
    if year_match:
        title = year_match.group(1).strip()
        
    results = dry_run_jellyfin_rename(folder_path, title, custom_regex)
    return {
        "status": "success", 
        "already_compliant": results.get("already_compliant", False),
        "results": results.get("items", [])
    }

@router.post("/apply_rename")
def execute_rename(mapping_list: List[Dict[str, Any]]):
    count = apply_jellyfin_rename(mapping_list)
    return {"status": "success", "count": count}

@router.post("/test_rename")
def test_rename(data: Dict[str, str]):
    # data: {"filename": "xxx", "regex": "xxx"}
    filename = data.get("filename", "")
    regex = data.get("regex", "auto")
    season, ep = parse_episode_number(filename, custom_regex=regex)
    return {"status": "success", "episode": ep, "season": season}
