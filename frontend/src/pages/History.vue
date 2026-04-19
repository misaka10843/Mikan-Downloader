<template>
  <div>
    <div class="d-flex align-center mb-6">
      <h2 class="text-h5 font-weight-bold">下载历史管理</h2>
      <v-spacer></v-spacer>
      <v-btn color="error" variant="outlined" prepend-icon="mdi-trash-can-outline" rounded="pill" @click="cleanOrphans" :loading="cleaning">
        清理冗余历史记录
      </v-btn>
    </div>

    <v-card class="rounded-xl overflow-hidden" elevation="2">
      <v-card-title class="pa-4 d-flex align-center">
        <v-text-field
          v-model="searchQuery"
          prepend-inner-icon="mdi-magnify"
          label="搜索 GUID / 标题关键字"
          variant="outlined"
          density="compact"
          hide-details
          class="max-width-400"
          @keyup.enter="loadHistory"
        ></v-text-field>
        <v-spacer></v-spacer>
        <div class="text-caption text-grey">共 {{ total }} 条记录</div>
      </v-card-title>

      <v-table density="comfortable">
        <thead>
          <tr>
            <th>GUID / 资源标识</th>
            <th>来源 RSS URL</th>
            <th>添加日期</th>
            <th class="text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in historyItems" :key="item.guid">
            <td class="text-caption font-weight-medium">{{ item.guid }}</td>
            <td class="text-xs text-grey" style="max-width: 300px; word-break: break-all;">{{ item.source }}</td>
            <td class="text-caption">{{ formatDate(item.created_at) }}</td>
            <td class="text-right">
              <v-btn icon="mdi-delete-outline" variant="text" size="small" color="error" @click="deleteItem(item)"></v-btn>
            </td>
          </tr>
          <tr v-if="historyItems.length === 0 && !loading">
            <td colspan="4" class="text-center py-8 text-grey">暂无历史记录</td>
          </tr>
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
          @update:model-value="loadHistory"
        ></v-pagination>
      </div>
    </v-card>

    <div v-if="loading" class="mt-8 d-flex justify-center">
      <v-progress-circular indeterminate color="primary"></v-progress-circular>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, inject } from 'vue'
import axios from 'axios'

const historyItems = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const searchQuery = ref('')
const loading = ref(false)
const cleaning = ref(false)
const showMsg = inject('showMsg')

const pageCount = computed(() => Math.ceil(total.value / pageSize.value))

const loadHistory = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/history/list', {
      params: {
        q: searchQuery.value,
        limit: pageSize.value,
        offset: (page.value - 1) * pageSize.value
      }
    })
    historyItems.value = res.data.items
    total.value = res.data.total
  } catch (e) {
    showMsg('加载历史失败', 'error')
  } finally {
    loading.value = false
  }
}

const deleteItem = async (item) => {
  if (!confirm('确认从历史记录中删除该项吗？(删除后如果有该资源的更新可能会被重新拉取)')) return
  try {
    await axios.delete(`/api/history/${item.guid}`)
    showMsg('记录已删除')
    loadHistory()
  } catch (e) {
    showMsg('操作失败', 'error')
  }
}

const cleanOrphans = async () => {
  if (!confirm('确认清理冗余历史吗？这将删除所有“已删除订阅”对应的历史记录。')) return
  cleaning.value = true
  try {
    const res = await axios.post('/api/history/clean_orphans')
    showMsg(res.data.message || '清理完成')
    loadHistory()
  } catch (e) {
    showMsg('清理失败', 'error')
  } finally {
    cleaning.value = false
  }
}

const formatDate = (dateStr) => {
  const d = new Date(dateStr)
  return d.toLocaleString()
}

onMounted(() => {
  loadHistory()
})
</script>

<style scoped>
.max-width-400 {
  max-width: 400px;
}
</style>
