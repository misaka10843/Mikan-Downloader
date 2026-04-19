from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List
import os
import logging

from ..core.renamer import dry_run_jellyfin_rename, apply_jellyfin_rename, parse_episode_number
from ..core.config import read_config, save_config

router = APIRouter(prefix="/api/library", tags=["library"])

@router.get("/list")
async def get_library_list(path: str = None):
    cfg = await read_config()
    save_dir = path if path else cfg.get("save_dir")
    if not save_dir or not os.path.exists(save_dir):
        return {"status": "error", "message": "库目录不存在或未填写"}
        
    folders = []
    logger = logging.getLogger("Library")
    
    try:
        if path and path != cfg.get("save_dir"):
            cfg["save_dir"] = path
            await save_config(cfg)
            
        items = os.listdir(save_dir)
        for item in items:
            item_path = os.path.join(save_dir, item)
            if os.path.isdir(item_path) and not item.startswith("."):
                is_compliant = False
                needs_rename = False
                try:
                    sub_items = os.listdir(item_path)
                    for subitem in sub_items:
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
async def preview_rename(data: Dict[str, Any]):
    folder_path = data.get("path")
    custom_regex = data.get("regex", "auto")
    
    if not folder_path or not os.path.exists(folder_path):
        return {"status": "error", "message": "文件夹路径无效"}
        
    items = await dry_run_jellyfin_rename(folder_path, custom_regex)
    return {
        "status": "success", 
        "results": items
    }

@router.post("/apply_rename")
async def execute_rename(mapping_list: List[Dict[str, Any]]):
    count = apply_jellyfin_rename(mapping_list)
    return {"status": "success", "count": count}

@router.post("/test_rename")
async def test_rename(data: Dict[str, str]):
    filename = data.get("filename", "")
    regex = data.get("regex", "auto")
    season, ep = parse_episode_number(filename, custom_regex=regex)
    return {"status": "success", "episode": ep, "season": season}

@router.delete("/file")
async def delete_file(path: str = Query(...)):
    if os.path.exists(path):
        try:
            os.remove(path)
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete: {e}")
    raise HTTPException(status_code=404, detail="File not found")
