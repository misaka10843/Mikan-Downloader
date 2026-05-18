<template>
  <div>
    <div class="d-flex justify-space-between align-center mb-4">
      <h2 class="text-h5 font-weight-bold">运行日志</h2>
      <div class="d-flex gap-2">
        <v-btn icon="mdi-refresh" variant="text" size="small" @click="reload"></v-btn>
        <v-btn color="error" variant="outlined" size="small" prepend-icon="mdi-delete-sweep" @click="clearLogs" :loading="clearing">清空</v-btn>
      </div>
    </div>

    <v-chip-group v-model="filter" class="mb-4" @update:modelValue="reload">
      <v-chip value="" variant="tonal">全部</v-chip>
      <v-chip value="fetch" color="blue" variant="tonal">
        <v-icon start>mdi-rss</v-icon>获取
      </v-chip>
      <v-chip value="push" color="green" variant="tonal">
        <v-icon start>mdi-cloud-upload</v-icon>推送
      </v-chip>
      <v-chip value="rename" color="purple" variant="tonal">
        <v-icon start>mdi-file-move</v-icon>重命名
      </v-chip>
      <v-chip value="error" color="error" variant="tonal">
        <v-icon start>mdi-alert-circle</v-icon>错误
      </v-chip>
    </v-chip-group>

    <div v-if="loading && logs.length === 0" class="d-flex justify-center my-10">
      <v-progress-circular indeterminate color="primary"></v-progress-circular>
    </div>

    <v-alert v-else-if="!loading && logs.length === 0" type="info" variant="tonal">暂无日志记录。</v-alert>

    <v-timeline v-else density="compact" side="end" truncate-line="both">
      <v-timeline-item
        v-for="item in logs"
        :key="item.id"
        :dot-color="getActionColor(item.action)"
        size="small"
      >
        <template v-slot:icon>
          <v-icon size="x-small" color="white">{{ getActionIcon(item.action) }}</v-icon>
        </template>
        <v-card class="rounded-xl" elevation="1" border>
          <v-card-text class="pa-3">
            <div class="d-flex align-center justify-space-between mb-1">
              <v-chip size="x-small" :color="getActionColor(item.action)" variant="flat">
                {{ getActionLabel(item.action) }}
              </v-chip>
              <span class="text-caption text-medium-emphasis">{{ item.timestamp }}</span>
            </div>
            <div class="font-weight-bold text-body-2">{{ item.anime_title || '—' }}</div>
            <div class="text-body-2 text-medium-emphasis mt-1" style="word-break: break-all;">{{ item.episode || '—' }}</div>
            <div v-if="item.detail" class="text-caption text-grey mt-1" style="word-break: break-all;">{{ item.detail }}</div>
          </v-card-text>
        </v-card>
      </v-timeline-item>
    </v-timeline>

    <div v-if="hasMore" class="d-flex justify-center mt-4">
      <v-btn variant="tonal" :loading="loading" @click="loadMore">加载更多</v-btn>
    </div>
  </div>
</template>

<script setup>
import { ref, inject, onMounted } from 'vue'
import axios from 'axios'

const showMsg = inject('showMsg')
const logs = ref([])
const filter = ref('')
const loading = ref(false)
const clearing = ref(false)
const total = ref(0)
const offset = ref(0)
const PAGE_SIZE = 50

const hasMore = ref(false)

const getActionColor = (action) => {
  switch (action) {
    case 'fetch': return 'blue'
    case 'push': return 'green'
    case 'rename': return 'purple'
    case 'error': return 'error'
    default: return 'grey'
  }
}

const getActionIcon = (action) => {
  switch (action) {
    case 'fetch': return 'mdi-rss'
    case 'push': return 'mdi-cloud-upload'
    case 'rename': return 'mdi-file-move'
    case 'error': return 'mdi-alert-circle'
    default: return 'mdi-information'
  }
}

const getActionLabel = (action) => {
  switch (action) {
    case 'fetch': return '获取'
    case 'push': return '推送'
    case 'rename': return '重命名'
    case 'error': return '错误'
    default: return action
  }
}

const fetchLogs = async (append = false) => {
  loading.value = true
  try {
    const params = { limit: PAGE_SIZE, offset: offset.value }
    if (filter.value) params.action = filter.value
    const res = await axios.get('/api/activity/logs', { params })
    total.value = res.data.total
    if (append) {
      logs.value.push(...res.data.items)
    } else {
      logs.value = res.data.items
    }
    hasMore.value = logs.value.length < total.value
  } catch (e) {
    showMsg('加载日志失败', 'error')
  } finally {
    loading.value = false
  }
}

const reload = () => {
  offset.value = 0
  fetchLogs(false)
}

const loadMore = () => {
  offset.value += PAGE_SIZE
  fetchLogs(true)
}

const clearLogs = async () => {
  clearing.value = true
  try {
    await axios.delete('/api/activity/logs')
    logs.value = []
    total.value = 0
    hasMore.value = false
    showMsg('日志已清空')
  } catch (e) {
    showMsg('清空失败', 'error')
  } finally {
    clearing.value = false
  }
}

onMounted(() => {
  fetchLogs()
})
</script>
