<template>
  <v-dialog v-model="dialog" max-width="900" persistent>
    <v-card class="rounded-xl">
      <v-card-title class="d-flex align-center bg-primary text-white pa-4">
        {{ currentStep === 0 ? '搜索并在 Mikan 添加订阅' : '配置订阅项预览' }}
        <v-spacer></v-spacer>
        <v-btn icon="mdi-close" variant="text" @click="dialog = false"></v-btn>
      </v-card-title>
      
      <!-- Step 0: Search and Basic Input -->
      <v-card-text v-if="currentStep === 0" class="pa-4 pt-6">
        <div class="d-flex mb-4">
          <v-text-field
            v-model="query"
            label="输入番剧搜索关键字..."
            variant="outlined"
            density="compact"
            hide-details
            @keyup.enter="search"
          ></v-text-field>
          <v-btn color="primary" class="ml-2" height="40" @click="search" :loading="loading">
            搜索
          </v-btn>
        </div>

        <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4"></v-progress-linear>

        <v-list v-if="results.length > 0" lines="two" max-height="300" class="overflow-y-auto mb-4 border rounded">
          <v-list-item
            v-for="(item, index) in results"
            :key="index"
            class="mb-1"
          >
            <template v-slot:title>
              <div class="font-weight-bold">{{ item.name }}</div>
            </template>
            <template v-slot:subtitle>
              <div class="text-caption">Subgroup: {{ item.subgroupId }}</div>
              <div class="text-xs text-grey text-truncate">{{ item.url }}</div>
            </template>
            <template v-slot:append>
              <v-btn color="primary" size="small" variant="tonal" @click="goToPreview(item)" :loading="previewData.loading && previewData.targetItem === item">
                配置并预览
              </v-btn>
            </template>
          </v-list-item>
        </v-list>
        
        <v-alert v-if="hasSearched && results.length === 0 && !loading" type="info" variant="tonal" class="mt-4">
          没有找到对应的番剧或字幕组 RSS 匹配结果。
        </v-alert>

        <v-divider class="my-4"></v-divider>
        <h3 class="text-subtitle-1 mb-2">或者手动添加规则流：</h3>
        <v-row class="mb-2">
          <v-col cols="6">
            <v-text-field v-model="manual.url" label="/RSS/Bangumi?xxx" density="compact" variant="outlined" hide-details></v-text-field>
          </v-col>
          <v-col cols="3">
            <v-text-field v-model="manual.rule" label="过滤正则" density="compact" variant="outlined" hide-details></v-text-field>
          </v-col>
          <v-col cols="3">
            <v-btn color="primary" block @click="goToPreview(manual)" height="40" :disabled="!manual.url" :loading="previewData.loading">预览并添加</v-btn>
          </v-col>
        </v-row>
      </v-card-text>

      <!-- Step 1: Preview and History Skip -->
      <v-card-text v-else class="pa-4 pt-6">
        <v-row>
          <v-col cols="8">
             <div class="text-h6 mb-1">{{ previewData.targetItem.name || previewData.targetItem.title || '自定义链接' }}</div>
             <div class="text-caption text-grey mb-4 text-truncate">{{ previewData.targetItem.url }}</div>
          </v-col>
          <v-col cols="4" class="text-right">
             <v-btn variant="text" prepend-icon="mdi-arrow-left" @click="currentStep = 0">返回修改</v-btn>
          </v-col>
        </v-row>

        <div class="mb-4">
          <v-row dense>
            <v-col cols="6">
              <v-text-field
                v-model="renameRule"
                label="集数提取正则 (含有1个捕获组)"
                variant="outlined"
                density="compact"
                hide-details
                placeholder="auto"
                @change="fetchPreview"
              ></v-text-field>
            </v-col>
            <v-col cols="6">
              <v-text-field
                v-model="filterRule"
                label="过滤正则 (用于匹配标题)"
                variant="outlined"
                density="compact"
                hide-details
                @change="fetchPreview"
              ></v-text-field>
            </v-col>
          </v-row>
        </div>

        <div class="d-flex align-center bg-grey-lighten-4 pa-2 rounded mb-2">
          <v-icon icon="mdi-history" size="small" class="mr-2"></v-icon>
          <span class="text-caption">在下方勾选您<b>不想</b>下载的项目（已看过的勾选即可跳过）</span>
          <v-spacer></v-spacer>
          <v-btn size="x-small" variant="text" @click="selectAllMatch">全选匹配项</v-btn>
          <v-btn size="x-small" variant="text" @click="previewData.selectedGuids = []">全不选</v-btn>
        </div>

        <v-table density="compact" class="border rounded fixed-header-table" height="350">
          <thead>
            <tr>
              <th style="width: 50px">跳过</th>
              <th>原始标题</th>
              <th style="width: 100px">解析集数</th>
              <th style="width: 80px">匹配</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(res, idx) in previewData.results" :key="idx">
              <td>
                <v-checkbox-btn v-model="previewData.selectedGuids" :value="res.title" density="compact" hide-details></v-checkbox-btn>
              </td>
              <td class="text-caption py-1">
                <div :class="res.match ? '' : 'text-grey'">{{ res.title }}</div>
              </td>
              <td class="text-center font-weight-bold">
                <v-chip v-if="res.episode" size="x-small" color="primary" variant="flat">S{{ String(res.season || 1).padStart(2, '0') }}E{{ res.episode }}</v-chip>
                <div v-else class="text-error text-xs">失败</div>
              </td>
              <td>
                <v-icon :icon="res.match ? 'mdi-check' : 'mdi-close'" :color="res.match ? 'success' : 'grey'"></v-icon>
              </td>
            </tr>
          </tbody>
        </v-table>
      </v-card-text>

      <v-divider></v-divider>
      <v-card-actions class="pa-4">
        <v-spacer></v-spacer>
        <v-btn variant="plain" @click="dialog = false">取消</v-btn>
        <v-btn v-if="currentStep === 1" color="success" variant="flat" rounded="pill" class="px-8" @click="confirmSubscribe">
          确认添加并跳过选中项
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, inject } from 'vue'
import axios from 'axios'

const dialog = ref(false)
const currentStep = ref(0)
const query = ref('')
const results = ref([])
const loading = ref(false)
const hasSearched = ref(false)

const showMsg = inject('showMsg')
const emit = defineEmits(['added'])

const manual = ref({ url: '', rule: '.*' })
const renameRule = ref('auto')
const filterRule = ref('.*')

const previewData = ref({
  loading: false,
  results: [],
  selectedGuids: [],
  targetItem: null
})

const open = () => {
  dialog.value = true
  currentStep.value = 0
  query.value = ''
  results.value = []
  hasSearched.value = false
  renameRule.value = 'auto'
  filterRule.value = '.*'
  manual.value = { url: '', rule: '.*' }
}

const search = async () => {
  if (!query.value.trim()) return
  loading.value = true
  hasSearched.value = true
  
  try {
    const res = await axios.get('/api/mikan/search', { params: { q: query.value }})
    results.value = res.data
  } catch (e) {
    showMsg('搜索异常', 'error')
  } finally {
    loading.value = false
  }
}

const goToPreview = async (item) => {
  previewData.value.targetItem = item
  filterRule.value = item.rule || '.*'
  currentStep.value = 1
  previewData.value.loading = true
  
  // 如果是手动添加的链接，尝试回溯获取番剧标题和封面图
  if (!item.name && item.url) {
    try {
      const res = await axios.get('/api/mikan/fetch_rss', { params: { url: item.url } })
      if (res.data.title) {
        previewData.value.targetItem.name = res.data.title
        previewData.value.targetItem.cover = res.data.cover
      }
    } catch (e) {
      console.error('Failed to fetch RSS metadata', e)
    }
  }
  
  await fetchPreview()
}

const fetchPreview = async () => {
  previewData.value.loading = true
  previewData.value.results = []
  try {
    const res = await axios.post('/api/mikan/preview', {
      url: previewData.value.targetItem.url,
      rule: filterRule.value,
      rename_rule: renameRule.value
    })
    if (res.data.status === 'success') {
      previewData.value.results = res.data.results
      // 默认根据 history 自动补全勾选，或者保持空让用户自己勾？
      // 用户说“选择哪些下载”，这里预设勾选已经命中的且已经在历史的
      previewData.value.selectedGuids = res.data.results.filter(r => r.in_history).map(r => r.title)
    }
  } catch (e) {
    showMsg('拉取预览失败', 'error')
  } finally {
    previewData.value.loading = false
  }
}

const selectAllMatch = () => {
  previewData.value.selectedGuids = previewData.value.results
    .filter(r => r.match)
    .map(r => r.title)
}

const confirmSubscribe = async () => {
  const item = previewData.value.targetItem
  
  // 1. 处理历史跳过
  if (previewData.value.selectedGuids.length > 0) {
    try {
      await axios.post('/api/mikan/history/add', {
        source: item.url,
        guids: previewData.value.selectedGuids
      })
    } catch (e) {
      console.error('Failed to pre-add history', e)
    }
  }

  // 2. 添加正式订阅
  const payload = {
    url: item.url,
    rule: filterRule.value || '.*',
    rename_rule: renameRule.value || 'auto',
    date: new Date().getFullYear().toString(),
    title: item.name || item.title || '',
    cover: item.cover || ''
  }
  
  emit('added', payload)
  showMsg('订阅已添加！命中历史的项目将不会触发初始下载。')
  dialog.value = false
}

defineExpose({ open })
</script>

<style scoped>
.fixed-header-table {
  overflow-y: auto;
}
</style>
