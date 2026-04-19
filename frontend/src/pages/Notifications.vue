<template>
  <div>
    <div class="d-flex justify-space-between align-center mb-6">
      <h2 class="text-h5 font-weight-bold">通知中心</h2>
      <div>
        <v-btn color="primary" variant="tonal" rounded="pill" class="mr-2" @click="markAllRead">
          全部标记已读
        </v-btn>
        <v-btn color="error" variant="text" size="small" @click="clearAll">
          清空历史项
        </v-btn>
      </div>
    </div>

    <v-card class="rounded-xl overflow-hidden" elevation="2">
      <v-data-table
        :headers="headers"
        :items="items"
        :loading="loading"
        hover
        class="bg-surface"
      >
        <template v-slot:item.level="{ item }">
          <v-chip
            :color="getLevelColor(item.level)"
            size="x-small"
            variant="flat"
            class="text-uppercase"
          >
            {{ item.level }}
          </v-chip>
        </template>
        
        <template v-slot:item.title="{ item }">
          <div :class="item.is_read ? 'text-grey' : 'font-weight-bold'">
            {{ item.title }}
          </div>
        </template>

        <template v-slot:item.message="{ item }">
          <div class="text-caption text-truncate" style="max-width: 400px" :title="item.message">
            {{ item.message }}
          </div>
        </template>

        <template v-slot:item.timestamp="{ item }">
          <span class="text-caption text-grey">{{ item.timestamp }}</span>
        </template>

        <template v-slot:no-data>
          <div class="pa-10 text-center">
            <v-icon color="grey-lighten-2" size="64" class="mb-4">mdi-bell-off-outline</v-icon>
            <div class="text-grey">暂无任何通知记录</div>
          </div>
        </template>
      </v-data-table>
    </v-card>
  </div>
</template>

<script setup>
import { ref, onMounted, inject } from 'vue'
import axios from 'axios'

const items = ref([])
const loading = ref(false)
const showMsg = inject('showMsg')

const headers = [
  { title: '状态', key: 'level', width: '100px' },
  { title: '标题', key: 'title', width: '200px' },
  { title: '内容详情', key: 'message' },
  { title: '发生时间', key: 'timestamp', width: '180px' },
]

const getLevelColor = (level) => {
  switch (level) {
    case 'success': return 'success'
    case 'error': return 'error'
    case 'warning': return 'warning'
    default: return 'primary'
  }
}

const loadNotifications = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/notifications', { params: { limit: 100 } })
    items.value = res.data
  } catch (e) {
    showMsg('加载通知失败', 'error')
  } finally {
    loading.value = false
  }
}

const markAllRead = async () => {
  try {
    await axios.post('/api/notifications/read', {})
    loadNotifications()
    showMsg('已全部标记为已读')
  } catch (e) {
    showMsg('操作失败', 'error')
  }
}

const clearAll = async () => {
  if (!confirm('确认清空所有通知历史吗？')) return
  try {
    await axios.delete('/api/notifications')
    loadNotifications()
    showMsg('通知已全量清空')
  } catch (e) {
    showMsg('清理失败', 'error')
  }
}

onMounted(() => {
  loadNotifications()
})
</script>
