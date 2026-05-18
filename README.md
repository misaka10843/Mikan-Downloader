# Mikan-Downloader
蜜柑计划番剧下载器

<img width="1907" height="960" alt="image" src="https://github.com/user-attachments/assets/f67065d0-c2e1-4561-bfcf-67f0884b680d" />

> **Warning**
> Mikan Project is a Chinese website, so I will not add any language other than Chinese, please understand

虽然知道有其他功能更多的下载程序，但是因为种种原因并不是特别好部署/无法使用aria2下载

所以我制作了这个下载器

## 如何使用

此程序需要依靠Aria2来下载，还请注意！

### 配置文件

当前本程序已经移至docker+webUI，可以直接部署后访问UI地址进行配置

## 特色功能

### 自动清洗标题

内置标题清洗以及允许用户手动编写标题识别规则，然后将下载/库中未为jellyfin等的命名规则的番剧重新整理为支持的命名规则

<img width="1909" height="965" alt="image" src="https://github.com/user-attachments/assets/d6d88446-d841-4021-a99d-adc2926c8c59" />
<img width="1372" height="859" alt="image" src="https://github.com/user-attachments/assets/e7c3105e-eee7-4ba4-a389-e74f8c271360" />

### 可视化定时

允许用户可视化操作定时任务

<img width="972" height="885" alt="image" src="https://github.com/user-attachments/assets/18e5d793-5e60-4215-90c6-ac8b7cf7fef6" />



并且检测如果配置文件中没有对应的RSS就直接删除所有相关内容

这样就可以解决历史记录过大，以及响应速度提升
