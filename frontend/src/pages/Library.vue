<template>
  <div>
    <div class="d-flex align-center mb-6">
      <div class="flex-grow-1 mr-4">
        <h2 class="text-h5 font-weight-bold mb-2">本地媒体库 (Jellyfin 助手)</h2>
        <v-text-field
           v-model="customPath"
           label="媒体库所处服务器绝对路径 (留空则默认读取配置项中的下载目录 save_dir)"
           variant="outlined"
           density="compact"
           hide-details
           prepend-inner-icon="mdi-folder-search"
           @keyup.enter="loadLibrary"
        ></v-text-field>
      </div>
      <v-btn color="primary" prepend-icon="mdi-magnify-scan" rounded="pill" @click="loadLibrary" :loading="loading" height="42" class="mt-8">
        扫描此路径
      </v-btn>
    </div>

    <!-- 列表展示区 -->
    <v-row v-if="folders.length > 0">
      <v-col cols="12" md="6" lg="4" v-for="(folder, idx) in folders" :key="idx">
        <v-card class="rounded-xl h-100 d-flex flex-column" elevation="2">
          <v-card-item>
            <template v-slot:prepend>
              <v-icon color="warning" size="36" icon="mdi-folder" class="mr-3"></v-icon>
            </template>
            <v-card-title class="text-body-1 font-weight-bold" :title="folder.name">
              {{ folder.name }}
            </v-card-title>
          </v-card-item>
          
          <v-card-text class="pt-0 pb-2 px-4 d-flex align-center flex-wrap gap-2">
            <v-chip v-if="folder.is_compliant && !folder.needs_rename" color="success" size="small" variant="flat" class="mt-2">
              <v-icon start icon="mdi-check-circle"></v-icon> 已合规
            </v-chip>
            <v-chip v-if="folder.needs_rename" color="error" size="small" variant="flat" class="mt-2 text-white">
              <v-icon start icon="mdi-alert-circle"></v-icon> 需修整散落剧集
            </v-chip>
            <v-chip v-if="!folder.is_compliant && !folder.needs_rename" color="grey" size="small" variant="tonal" class="mt-2">
              暂无已识别结构
            </v-chip>
          </v-card-text>
          
          <v-spacer></v-spacer>
          
          <v-card-actions class="px-4 pb-4 pt-0">
            <v-spacer></v-spacer>
            <v-btn color="primary" variant="tonal" rounded="pill" size="small" @click="openPreview(folder)">
              <v-icon icon="mdi-magic-staff" class="mr-1"></v-icon> 重组为 Jellyfin 规范
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
    <v-alert v-else-if="!loading" type="info" variant="tonal" class="mt-4">
      媒体库目录中没有找到对应的番剧文件夹。
    </v-alert>
    
    <div v-if="loading" class="d-flex justify-center my-8">
      <v-progress-circular indeterminate color="primary"></v-progress-circular>
    </div>

    <!-- 预览与改名弹出窗 -->
    <v-dialog v-model="previewDialog.show" max-width="900" persistent>
      <v-card class="rounded-xl">
        <v-card-title class="bg-primary text-white d-flex align-center pa-4">
          重命名集数抓取预览
          <v-spacer></v-spacer>
          <v-btn icon="mdi-close" variant="text" @click="previewDialog.show = false" :disabled="previewDialog.processing"></v-btn>
        </v-card-title>
        
        <v-card-text class="pa-4 pt-6">
          <v-alert v-if="previewDialog.alreadyCompliant" type="warning" variant="tonal" class="mb-4 text-caption">
            <span class="font-weight-bold">检测到该目录疑似已完成 Jellyfin 规范化：</span><br/>
            系统检测到该目录下已存在 <code>Season</code> 或 <code>Specials</code> 等标准层级目录。继续执行将把子目录内搜寻到的视频重新归类和移动。如果您已经整理完毕，不建议重复执行。
          </v-alert>
          <div class="mb-4">
             <v-text-field
                v-model="previewDialog.regex"
                label="修正正规表达式 (留空 auto 为系统默认)"
                variant="outlined"
                density="compact"
                hide-details
                placeholder="例如: .*?(\d{2})\[GB\]"
              >
                <template v-slot:append>
                   <v-btn color="secondary" @click="runPreview" :loading="previewDialog.loading">重新扫描解析</v-btn>
                </template>
             </v-text-field>
             
             <v-expansion-panels class="mt-3" variant="accordion">
               <v-expansion-panel elevation="0" class="border">
                 <v-expansion-panel-title class="text-caption text-primary py-0 min-h-0" style="min-height: 36px">不会写正则？点击查看使用指南与常见例子大全</v-expansion-panel-title>
                 <v-expansion-panel-text class="text-caption pa-2">
                    <b>工作原理：</b><br/>系统会在这个表达式中寻找<b>第一个括号 <code>()</code>（即捕获组）</b>圈起来的数字，并把它作为第几集。<br/><br/>
                    <b>万能套用的常见场景速查表：</b><br/>
                    • 纯数字开头带下划线（例如 <code>10_burn-in.mp4</code>）：填写正则 <code>^(\d{1,3})_</code> <br/>
                    • 在特定的组名和前后缀中（例如 <code>KxIX 01 [GB]</code>）：填写正则 <code>KxIX\s+(\d{1,3})\s+\[GB\]</code> <br/>
                    • 前面有下划线，或者是集数直接跟在某单词后（例如 <code>ep10_v2.mp4</code>）：填写正则 <code>ep(\d{1,3})_</code> <br/>
                    • 针对 <b>OVA</b> 或特别篇等没有数字的视频：因为我们抓取后强制组装为 <code>S01E...</code> 的规范，目前不支持非数字映射。建议对于 OVA 您暂时只处理数字正编集数，OVA单独在对应 NAS 操作哦！
                 </v-expansion-panel-text>
               </v-expansion-panel>
             </v-expansion-panels>
          </div>
          
          <v-table density="compact" class="border rounded">
            <thead>
              <tr>
                <th class="text-left py-2">原始视频文件名</th>
                <th class="text-left py-2">预计重命名</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, idx) in previewDialog.results" :key="idx">
                <td class="text-caption text-grey py-2" style="max-width:300px; word-break:break-all">{{ item.original_name }}</td>
                <td class="py-2">
                  <div class="d-flex align-center">
                    <span v-if="item.status === 'success'" class="text-success mr-3 text-caption font-weight-bold" style="white-space: nowrap">
                      {{ item.new_name }} <span class="text-grey ml-1 font-weight-regular">(移至 {{ item.season === 0 ? 'Specials' : `Season ${item.season}` }})</span>
                    </span>
                    <span v-else class="text-error mr-3 text-caption font-weight-bold" style="white-space: nowrap">失败</span>
                    <v-text-field v-model="item.manualSeason" label="季/目录" density="compact" hide-details variant="outlined" class="mr-2" style="width: 85px; min-width: 85px" placeholder="0 或 SP"></v-text-field>
                    <v-text-field v-model="item.manualEpisode" label="集号(可选)" density="compact" hide-details variant="outlined" class="mr-2" style="width: 100px; min-width: 100px" placeholder="留空保持原名"></v-text-field>
                    <v-btn size="small" variant="tonal" :color="item.status === 'success' ? 'primary' : 'success'" @click="applyManual(item)">
                       {{ item.status === 'success' ? '修正' : '赋予' }}
                    </v-btn>
                  </div>
                </td>
              </tr>
              <tr v-if="previewDialog.results.length === 0 && !previewDialog.loading">
                <td colspan="2" class="text-center py-4 text-grey">该目录下未扫描到有效视频文件</td>
              </tr>
            </tbody>
          </v-table>
          
        </v-card-text>
        
        <v-divider></v-divider>
        <v-card-actions class="pa-4">
           <v-spacer></v-spacer>
           <v-btn variant="plain" @click="previewDialog.show = false" :disabled="previewDialog.processing">取消操作</v-btn>
           <v-btn color="error" variant="flat" 
                  rounded="pill" class="px-6"
                  :loading="previewDialog.processing" 
                  :disabled="previewDialog.loading || previewDialog.results.length === 0 || previewDialog.results.some(i => i.status !== 'success')"
                  @click="applyRename">
              正式执行整理与剪切应用
           </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, inject } from 'vue'
import axios from 'axios'

const folders = ref([])
const customPath = ref('')
const loading = ref(false)
const showMsg = inject('showMsg')

const previewDialog = ref({
  show: false,
  loading: false,
  processing: false,
  regex: 'auto',
  targetFolder: null,
  alreadyCompliant: false,
  results: []
})

const loadLibrary = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/library/list', { params: { path: customPath.value } })
    if(res.data.status === 'success') {
       folders.value = res.data.folders || []
    } else {
       showMsg(res.data.message || '加载图库列表失败', 'error')
    }
    
    if(!customPath.value) {
       const sys = await axios.get('/api/settings/system')
       customPath.value = sys.data.save_dir
    }
  } catch(e) {
    showMsg('通信失败', 'error')
  } finally {
    loading.value = false
  }
}

const openPreview = (folder) => {
  previewDialog.value.targetFolder = folder
  previewDialog.value.regex = 'auto'
  previewDialog.value.show = true
  runPreview()
}

const runPreview = async () => {
  if (!previewDialog.value.targetFolder) return;
  previewDialog.value.loading = true
  try {
    const res = await axios.post('/api/library/preview_rename', {
      path: previewDialog.value.targetFolder.path,
      regex: previewDialog.value.regex || 'auto'
    })
    previewDialog.value.alreadyCompliant = res.data.already_compliant || false
    previewDialog.value.results = (res.data.results || []).map(r => ({
      ...r,
      manualSeason: r.season !== null ? r.season : (r.original_name.toUpperCase().includes('OVA') ? 0 : 1),
      manualEpisode: r.episode !== null ? r.episode : ''
    }))
  } catch(e) {
    showMsg('执行干预演练报错', 'error')
  } finally {
    previewDialog.value.loading = false
  }
}

const applyManual = (item) => {
  const s_raw = String(item.manualSeason).trim()
  const s_upper = s_raw.toUpperCase()
  const e = item.manualEpisode.trim()
  
  if (!s_raw) {
     showMsg('请至少填写目标季数或目录（如 1, 0, SP, Scans）！', 'error'); return;
  }
  
  let s = parseInt(s_raw)
  let seasonStr = ''
  let seasonFolder = ''
  
  // 处理非数字的特殊文件夹，如果是数字正常走
  if (isNaN(s)) {
      if (s_upper === 'SP' || s_upper === 'OVA' || s_upper === 'SPECIALS') {
          s = 0; seasonStr = '00'; seasonFolder = 'Specials';
      } else {
          s = 0; seasonStr = '00'; seasonFolder = s_raw;
      }
  } else {
      seasonStr = s.toString().padStart(2, '0')
      seasonFolder = s === 0 ? 'Specials' : `Season ${s}`
  }

  item.season = s
  if (!e) {
      // 留空代表不重新命名，原样塞进特殊文件夹
      item.episode = ''
      item.new_name = item.original_name
  } else {
      // 针对例如 12.5 这种小数集数处理
      let epStr = e;
      if(!e.includes('.')) {
          epStr = e.padStart(2, '0');
      } else if (e.startsWith('.')) {
          epStr = "0" + e;
      } else if (e.length === 3 && e.indexOf('.') === 1) { // 1.5 -> 01.5
          epStr = "0" + e;
      }
      item.episode = epStr
      item.new_name = `S${seasonStr}E${epStr}${item.ext}`
  }
  
  // Need to mimic Python's os.path.join in JS carefully, avoiding double slashes.
  const baseTgt = item.target_dir.replace(/\\/g, '/').replace(/\/$/, '')
  item.target_path = `${baseTgt}/${seasonFolder}/${item.new_name}`
  
  item.status = 'success'
  showMsg('局部覆盖成功，请检查全表后点正式执行')
}

const applyRename = async () => {
  previewDialog.value.processing = true
  try {
    const res = await axios.post('/api/library/apply_rename', previewDialog.value.results)
    if (res.data.status === 'success') {
      showMsg(`整理大获成功！成功移入 ${res.data.count} 个文件至 Season 1。`)
      previewDialog.value.show = false
    } else {
      showMsg('部分或全部重构失败', 'error')
    }
  } catch(e) {
    showMsg('合并请求遇到错误', 'error')
  } finally {
    previewDialog.value.processing = false
  }
}

onMounted(() => {
  loadLibrary()
})
</script>
