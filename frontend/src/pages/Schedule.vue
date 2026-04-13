<template>
  <div class="d-flex justify-center">
    <div style="width: 100%; max-width: 900px;">
      <v-card border class="rounded-xl pa-2" elevation="0" flat>
        <div class="text-center my-8">
          <v-avatar class="mb-4" color="primary-lighten-5" size="80">
            <v-icon color="primary" size="40">mdi-clock-time-eight-outline</v-icon>
          </v-avatar>
          <h2 class="text-h5 font-weight-bold">定时下载策略</h2>
          <p class="text-body-2 text-medium-emphasis mt-2">配置自动检查订阅及元数据更新的时间频率</p>
        </div>

        <cron-generator v-model="cronExpression" class="mx-4 mb-6"></cron-generator>

        <div class="d-flex justify-center gap-4 mb-6">
          <v-btn size="large" variant="text" @click="init">重置</v-btn>
          <v-btn class="px-8" color="primary" prepend-icon="mdi-content-save" rounded="pill" size="large"
                 :loading="saving" @click="saveCron">保存策略
          </v-btn>
        </div>
      </v-card>

      <v-card border class="rounded-xl pa-4 mt-6" elevation="0" flat>
         <h3 class="text-h6 font-weight-bold mb-4 d-flex align-center">
            <v-icon color="secondary" class="mr-2">mdi-format-list-checks</v-icon> 当前运行的任务列表
            <v-spacer></v-spacer>
            <v-btn icon="mdi-refresh" variant="text" size="small" @click="loadJobs"></v-btn>
         </h3>
         <v-table density="comfortable">
            <thead>
               <tr>
                  <th class="text-left font-weight-bold">任务名称 (ID)</th>
                  <th class="text-left font-weight-bold">上次运行时间</th>
                  <th class="text-left font-weight-bold">下一次预计执行</th>
               </tr>
            </thead>
            <tbody>
               <tr v-for="job in jobs" :key="job.id">
                  <td>{{ job.id }}</td>
                  <td class="text-grey">{{ job.last_run_time || '未知 / 刚启动' }}</td>
                  <td class="font-weight-bold text-primary">{{ job.next_run_time }}</td>
               </tr>
            </tbody>
         </v-table>
      </v-card>
    </div>
  </div>
</template>

<script setup>
import {inject, onMounted, ref} from 'vue'
import axios from 'axios'
import CronGenerator from '../components/CronGenerator.vue'

const showMsg = inject('showMsg')
const cronExpression = ref('* * * * *')
const saving = ref(false)
const jobs = ref([])

const init = async () => {
  try {
    const res = await axios.get('/api/settings/system')
    if (res.data && res.data.schedule && res.data.schedule.cron) {
      cronExpression.value = res.data.schedule.cron
    } else {
      cronExpression.value = '30 2 * * *'
    }
  } catch (e) {
    showMsg('获取定时属性失败', 'error')
  }
}

const loadJobs = async () => {
    try {
        const res = await axios.get('/api/schedule/jobs')
        jobs.value = res.data.jobs || []
    } catch(e) {}
}

const saveCron = async () => {
  saving.value = true
  try {
    const res = await axios.get('/api/settings/system')
    const cfg = res.data
    cfg.schedule = { mode: 'cron_advanced', cron: cronExpression.value }
    await axios.post('/api/settings/system', cfg)
    await axios.post('/api/schedule/update', {})
    showMsg('定时策略已保存并应用')
    loadJobs()
  } catch (e) {
    showMsg('保存 Cron 失败', 'error')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
    init()
    loadJobs()
})
</script>
