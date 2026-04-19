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
          <v-alert type="info" variant="tonal" class="mb-4" density="compact">当前正则: <b>{{ previewDialog.rule }}</b></v-alert>
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
                  </template>
               </v-list-item>
            </v-list>
          </div>
          <v-alert v-else type="error" variant="tonal">无法获取预览，该源近无更新或无法访问。</v-alert>
        </v-card-text>
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
  results: [],
  selected: [],
  url: '',
  addingHistory: false
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
  
  previewDialog.value.show = true
  previewDialog.value.loading = true
  previewDialog.value.results = []
  previewDialog.value.selected = []
  previewDialog.value.url = target.url
  previewDialog.value.rule = target.rule || '.*'
  
  try {
    const res = await axios.post('/api/mikan/preview', { url: target.url, rule: previewDialog.value.rule })
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
