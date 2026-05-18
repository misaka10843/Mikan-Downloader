<template>
  <div>
    <div class="d-flex justify-space-between align-center mb-4">
      <h2 class="text-h5 font-weight-bold">我的订阅列表</h2>
      <div>
        <v-btn-toggle v-model="viewMode" color="primary" mandatory variant="outlined" class="mr-4">
          <v-btn value="active">使用中</v-btn>
          <v-btn value="deleted">回收站</v-btn>
        </v-btn-toggle>
        <v-btn color="primary" prepend-icon="mdi-plus" rounded="pill" @click="openSearchDialog">
          添加新订阅
        </v-btn>
      </div>
    </div>

    <!-- 列表展示区 -->
    <v-row v-if="displayedSubs.length > 0">
      <v-col cols="12" md="6" lg="4" v-for="item in displayedSubs" :key="item.originalIndex">
        <v-card class="rounded-xl h-100 d-flex flex-column" elevation="3">
          <div class="d-flex flex-no-wrap justify-space-between pl-4 pt-4 pr-2">
            <div class="w-100 mr-2" style="min-width: 0;">
              <v-card-title class="text-body-1 font-weight-bold text-truncate px-0" :title="item.sub.title || item.sub.url">
                {{ item.sub.title || '自定义链接订阅' }}
              </v-card-title>
              <v-card-subtitle class="mt-1 px-0 text-wrap">
                年份标定: {{ item.sub.date || '自动获取' }}
              </v-card-subtitle>
            </div>
            <v-avatar
              size="70"
              rounded="lg"
              v-if="item.sub.cover"
            >
              <v-img :src="item.sub.cover" cover></v-img>
            </v-avatar>
          </div>
          
          <div class="px-4 mt-2">
             <div class="d-flex align-center">
               <v-text-field
                  v-model="subs[item.originalIndex].rule"
                  label="过滤规则 (正则或关键字)"
                  density="compact"
                  variant="outlined"
                  hide-details
                  @change="saveSubs"
                ></v-text-field>
                <v-btn icon="mdi-eye-outline" variant="text" size="small" 
                       color="primary" class="ml-2" 
                       @click="previewRegex(item.originalIndex)" 
                       title="预览匹配结果"></v-btn>
              </div>
              <div class="mt-2 text-xs text-grey" style="word-break: break-all;">{{ item.sub.url }}</div>
          </div>
          
          <v-spacer></v-spacer>
          
          <v-card-actions class="px-4 pb-4 pt-2">
            <v-btn color="primary" variant="text" size="small" prepend-icon="mdi-pencil" @click="openEdit(item.originalIndex)">编辑</v-btn>
            <v-btn v-if="viewMode === 'active'" color="warning" variant="text" size="small" @click="softDelete(item.originalIndex)">
              移至回收站
            </v-btn>
            <v-btn v-if="viewMode === 'deleted'" color="success" variant="text" size="small" @click="restoreSub(item.originalIndex)">
              恢复
            </v-btn>
            <v-btn v-if="viewMode === 'deleted'" color="error" variant="text" size="small" @click="hardDelete(item.originalIndex)">
              彻底删除
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
    <v-alert v-else type="info" variant="tonal" class="mt-4">
      此处空空如也。
    </v-alert>

    <SearchDialog ref="searchDialog" @added="onAdded" />

    <v-dialog v-model="previewDialog.show" max-width="600">
      <v-card class="rounded-xl">
        <v-card-title class="bg-primary text-white d-flex align-center pa-4">
          远端匹配列表速览
          <v-spacer></v-spacer>
          <v-btn icon="mdi-close" variant="text" @click="previewDialog.show = false"></v-btn>
        </v-card-title>
        <v-card-text class="pa-4 pt-6">
          <v-alert type="info" variant="tonal" class="mb-4" density="compact">匹配规则: <b>{{ previewDialog.rule }}</b></v-alert>
          <v-text-field
            v-model="previewDialog.rename_rule"
            label="集数解析规则 (auto 或自定义正则)"
            density="compact"
            variant="outlined"
            hide-details
            class="mb-2"
            @change="rePreview"
          ></v-text-field>
          <v-expansion-panels class="mb-4" variant="accordion">
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
          <div v-if="previewDialog.loading" class="d-flex justify-center my-6">
            <v-progress-circular indeterminate color="primary"></v-progress-circular>
          </div>
          <div v-else-if="previewDialog.results.length > 0">
            <div class="d-flex align-center mb-2 px-2">
              <v-btn size="x-small" variant="text" @click="selectAllPreview">全选匹配项</v-btn>
              <v-btn size="x-small" variant="text" @click="previewDialog.selected = []">取消全选</v-btn>
              <v-spacer></v-spacer>
              <v-btn :disabled="previewDialog.selected.length === 0" color="primary" size="small" rounded="pill" @click="addToHistoryBatch" :loading="previewDialog.addingHistory">
                将选中项加入历史 (跳过)
              </v-btn>
            </div>
            <v-list class="preview-list">
               <v-list-item v-for="(res, idx) in previewDialog.results" :key="idx" class="mb-2 rounded border" :active="res.match">
                  <template v-slot:prepend>
                    <v-checkbox-btn v-model="previewDialog.selected" :value="res.title" :disabled="res.in_history" color="primary"></v-checkbox-btn>
                    <v-icon :color="res.match ? 'success' : 'grey'" :icon="res.match ? 'mdi-check-circle' : 'mdi-close-circle'" class="ml-2"></v-icon>
                  </template>
                  <v-list-item-title class="text-wrap" :class="res.match ? 'font-weight-bold text-success' : 'text-grey'">
                    {{ res.title }}
                  </v-list-item-title>
                  <template v-slot:append>
                    <v-chip v-if="res.in_history" size="x-small" color="grey" variant="flat">已在历史中</v-chip>
                    <v-chip v-else-if="res.episode" size="x-small" color="primary" variant="tonal" class="ml-1">
                      S{{ String(res.season).padStart(2, '0') }}E{{ res.episode }}
                    </v-chip>
                  </template>
               </v-list-item>
            </v-list>
          </div>
          <v-alert v-else type="error" variant="tonal">无法获取预览，该源近无更新或无法访问。</v-alert>
        </v-card-text>
      </v-card>
    </v-dialog>

    <v-dialog v-model="editDialog.show" max-width="550">
      <v-card class="rounded-xl">
        <v-card-title class="bg-primary text-white d-flex align-center pa-4">
          编辑订阅
          <v-spacer></v-spacer>
          <v-btn icon="mdi-close" variant="text" @click="editDialog.show = false"></v-btn>
        </v-card-title>
        <v-card-text class="pa-4 pt-6">
          <v-text-field v-model="editDialog.form.title" label="番剧标题" density="compact" variant="outlined" class="mb-3"></v-text-field>
          <v-text-field v-model="editDialog.form.url" label="RSS 链接" density="compact" variant="outlined" class="mb-3"></v-text-field>
          <v-text-field v-model="editDialog.form.date" label="年份标定" density="compact" variant="outlined" class="mb-3" placeholder="如: 2024"></v-text-field>
          <v-text-field v-model="editDialog.form.rule" label="过滤规则 (正则或关键字)" density="compact" variant="outlined" class="mb-3"></v-text-field>
          <v-text-field v-model="editDialog.form.rename_rule" label="集数解析规则 (auto 或自定义正则)" density="compact" variant="outlined" class="mb-2"></v-text-field>
          <v-expansion-panels variant="accordion">
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
        </v-card-text>
        <v-card-actions class="pa-4 pt-0">
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="editDialog.show = false">取消</v-btn>
          <v-btn color="primary" variant="flat" rounded="pill" @click="saveEdit">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, inject } from 'vue'
import axios from 'axios'
import SearchDialog from '../components/SearchDialog.vue'

const subs = ref([])
const searchDialog = ref(null)
const showMsg = inject('showMsg')
const viewMode = ref('active')

const previewDialog = ref({
  show: false,
  loading: false,
  rule: '',
  rename_rule: 'auto',
  results: [],
  selected: [],
  url: '',
  addingHistory: false
})

const editDialog = ref({
  show: false,
  idx: -1,
  form: { url: '', title: '', date: '', rule: '', rename_rule: 'auto' }
})

const displayedSubs = computed(() => {
  return subs.value.map((s, idx) => ({ sub: s, originalIndex: idx }))
    .filter(item => {
      if (viewMode.value === 'active') return !item.sub.is_deleted;
      return !!item.sub.is_deleted;
    })
})

const loadSubs = async () => {
  try {
    const res = await axios.get('/api/mikan/subs')
    subs.value = res.data || []
  } catch (e) {
    showMsg('加载订阅列表失败', 'error')
  }
}

const saveSubs = async () => {
  try {
    await axios.post('/api/mikan/subs', subs.value)
    showMsg('更改已自动保存')
  } catch (e) {
    showMsg('保存失败', 'error')
  }
}

const softDelete = (idx) => {
  subs.value[idx].is_deleted = true;
  saveSubs();
}

const restoreSub = (idx) => {
  subs.value[idx].is_deleted = false;
  saveSubs();
}

const hardDelete = (idx) => {
  subs.value.splice(idx, 1)
  saveSubs()
}

const openSearchDialog = () => {
  searchDialog.value.open()
}

const onAdded = (newSub) => {
  subs.value.push(newSub)
  saveSubs()
}

const previewRegex = async (idx) => {
  const target = subs.value[idx]
  if (!target || !target.url) return;
  
  previewDialog.value.results = []
  previewDialog.value.selected = []
  previewDialog.value.loading = true
  previewDialog.value.url = target.url
  previewDialog.value.rule = target.rule || '.*'
  previewDialog.value.rename_rule = target.rename_rule || 'auto'
  previewDialog.value.show = true
  
  try {
    const res = await axios.post('/api/mikan/preview', { url: target.url, rule: previewDialog.value.rule, rename_rule: previewDialog.value.rename_rule })
    if (res.data.status === 'success') {
       previewDialog.value.results = res.data.results
    } else {
       showMsg(res.data.message || '预览出错', 'error')
    }
  } catch(e) {
    showMsg('拉取番剧预览列表异常', 'error')
  } finally {
    previewDialog.value.loading = false
  }
}

const rePreview = async () => {
  if (!previewDialog.value.url) return
  previewDialog.value.loading = true
  previewDialog.value.results = []
  try {
    const res = await axios.post('/api/mikan/preview', {
      url: previewDialog.value.url,
      rule: previewDialog.value.rule,
      rename_rule: previewDialog.value.rename_rule
    })
    if (res.data.status === 'success') {
      previewDialog.value.results = res.data.results
    }
  } catch(e) {
    showMsg('重新预览失败', 'error')
  } finally {
    previewDialog.value.loading = false
  }
}

const openEdit = (idx) => {
  const sub = subs.value[idx]
  editDialog.value = {
    show: true,
    idx,
    form: {
      url: sub.url || '',
      title: sub.title || '',
      date: sub.date || '',
      rule: sub.rule || '',
      rename_rule: sub.rename_rule || 'auto'
    }
  }
}

const saveEdit = () => {
  const idx = editDialog.value.idx
  Object.assign(subs.value[idx], editDialog.value.form)
  editDialog.value.show = false
  saveSubs()
}

const selectAllPreview = () => {
  previewDialog.value.selected = previewDialog.value.results
    .filter(r => r.match && !r.in_history)
    .map(r => r.title)
}

const addToHistoryBatch = async () => {
  if (previewDialog.value.selected.length === 0) return
  
  previewDialog.value.addingHistory = true
  try {
    const res = await axios.post('/api/mikan/history/add', {
      source: previewDialog.value.url,
      guids: previewDialog.value.selected
    })
    if (res.data.status === 'success') {
      showMsg(`成功将 ${previewDialog.value.selected.length} 项标记为跳过`)
      // 局部更新状态，避免重新拉入
      previewDialog.value.results.forEach(r => {
        if (previewDialog.value.selected.includes(r.title)) {
          r.in_history = true
        }
      })
      previewDialog.value.selected = []
    }
  } catch(e) {
    showMsg('标记失败', 'error')
  } finally {
    previewDialog.value.addingHistory = false
  }
}

onMounted(() => {
  loadSubs()
})
</script>
