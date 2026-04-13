import logging
import os
import yaml

CONFIG_PATH = 'config.yml'

def read_config():
    if not os.path.exists(CONFIG_PATH):
        import shutil
        if os.path.exists('config.example.yml'):
            shutil.copy('config.example.yml', CONFIG_PATH)
        else:
            return {}
            
    try:
        with open(CONFIG_PATH, 'r', encoding="UTF-8") as f:
            config = yaml.safe_load(f)
        return config or {}
    except Exception as e:
        logging.error(f"读取配合文件出错: {e}")
        return {}

def save_config(config_data):
    try:
        with open(CONFIG_PATH, 'w', encoding="UTF-8") as f:
            yaml.safe_dump(config_data, f, allow_unicode=True)
        return True
    except Exception as e:
        logging.error(f"写入配置文件出错: {e}")
        return False
