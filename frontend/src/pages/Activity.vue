<template>
  <div>
    <div class="d-flex align-center mb-6">
      <h2 class="text-h5 font-weight-bold">运行日志</h2>
      <v-spacer></v-spacer>
      <v-btn color="error" variant="outlined" prepend-icon="mdi-delete-sweep" rounded="pill" @click="clearLogs" :loading="clearing">
        清空日志
      </v-btn>
    </div>

    <v-card class="rounded-xl overflow-hidden" elevation="2">
      <v-card-title class="pa-4 d-flex align-center flex-wrap">
        <v-chip-group v-model="filter" @update:modelValue="reload">
          <v-chip value="" variant="tonal">全部</v-chip>
          <v-chip value="fetch" color="blue" variant="tonal" prepend-icon="mdi-rss">获取</v-chip>
          <v-chip value="push" color="green" variant="tonal" prepend-icon="mdi-cloud-upload">推送</v-chip>
          <v-chip value="rename" color="purple" variant="tonal" prepend-icon="mdi-file-move">重命名</v-chip>
          <v-chip value="error" color="error" variant="tonal" prepend-icon="mdi-alert-circle">错误</v-chip>
        </v-chip-group>
        <v-spacer></v-spacer>
        <span class="text-caption text-grey mr-2">共 {{ total }} 条</span>
        <v-btn icon="mdi-refresh" variant="text" size="small" @click="reload"></v-btn>
      </v-card-title>

      <v-table density="comfortable">
        <thead>
          <tr>
            <th style="width: 110px">操作类型</th>
            <th style="width: 20%">番剧</th>
            <th style="width: 30%">集数 / 文件</th>
            <th>详情</th>
            <th style="width: 160px">时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="5" class="text-center py-8">
              <v-progress-circular indeterminate color="primary" size="24"></v-progress-circular>
            </td>
          </tr>
          <tr v-else-if="logs.length === 0">
            <td colspan="5" class="text-center py-8 text-grey">暂无日志记录</td>
          </tr>
          <template v-else>
            <tr v-for="item in logs" :key="item.id">
              <td>
                <v-chip :color="getActionColor(item.action)" size="x-small" variant="tonal" :prepend-icon="getActionIcon(item.action)">
                  {{ getActionLabel(item.action) }}
                </v-chip>
              </td>
              <td class="text-body-2 font-weight-medium">{{ item.anime_title || '—' }}</td>
              <td class="text-caption" style="word-break: break-all;">{{ item.episode || '—' }}</td>
              <td class="text-caption text-grey" style="max-width: 200px;" :title="item.detail || ''">
                <span class="text-truncate d-block" style="max-width: 200px;">{{ item.detail || '—' }}</span>
              </td>
              <td class="text-caption text-grey">{{ item.timestamp }}</td>
            </tr>
          </template>
        </tbody>
      </v-table>

      <v-divider></v-divider>
      <div class="pa-4 d-flex align-center">
        <v-spacer></v-spacer>
        <v-pagination
          v-model="page"
          :length="pageCount"
          total-visible="7"
          rounded="circle"
          size="small"
          @update:model-value="loadPage"
        ></v-pagination>
      </div>
    </v-card>
  </div>
</template>

<script setup>
import { ref, computed, inject, onMounted } from 'vue'
import axios from 'axios'

const showMsg = inject('showMsg')
const logs = ref([])
const filter = ref('')
const loading = ref(false)
const clearing = ref(false)
const total = ref(0)
const page = ref(1)
const PAGE_SIZE = 50

const pageCount = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

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

const fetchLogs = async () => {
  loading.value = true
  try {
    const params = { limit: PAGE_SIZE, offset: (page.value - 1) * PAGE_SIZE }
    if (filter.value) params.action = filter.value
    const res = await axios.get('/api/activity/logs', { params })
    total.value = res.data.total
    logs.value = res.data.items
  } catch (e) {
    showMsg('加载日志失败', 'error')
  } finally {
    loading.value = false
  }
}

const reload = () => {
  page.value = 1
  fetchLogs()
}

const loadPage = () => {
  fetchLogs()
}

const clearLogs = async () => {
  clearing.value = true
  try {
    await axios.delete('/api/activity/logs')
    logs.value = []
    total.value = 0
    page.value = 1
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
