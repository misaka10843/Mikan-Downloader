<template>
  <div>
    <v-card class="mb-4 rounded-xl" elevation="2">
      <v-card-title class="pa-4 d-flex align-center">
        <span>系统设置</span>
        <v-spacer></v-spacer>
        <v-btn color="primary" @click="saveSystem" :loading="saving" rounded="pill">保存配置</v-btn>
      </v-card-title>
      <v-divider></v-divider>
      <v-card-text v-if="settings" class="pa-4">
        <v-form>
          <v-row>
            <v-col cols="12" md="4">
              <v-text-field
                v-model="mirrorObj"
                label="Mikan 主站/镜像站地址"
                variant="outlined"
                hint="例如： https://mikanani.me"
              ></v-text-field>
            </v-col>
            <v-col cols="12" md="4">
              <v-text-field
                v-model="settings.save_dir"
                label="下载保存目录"
                variant="outlined"
                hint="例如： /mnt/media/anime"
              ></v-text-field>
            </v-col>
            <v-col cols="12" md="4">
              <v-text-field
                v-model="settings.proxy"
                label="网络代理 (可选)"
                variant="outlined"
                hint="例如： http://127.0.0.1:7890"
              ></v-text-field>
            </v-col>
          </v-row>

          <v-divider class="my-4"></v-divider>
          <h3 class="mb-3 text-h6">Aria2 连接设置</h3>
          
          <v-row>
            <v-col cols="12" md="4">
              <v-text-field
                v-model="settings.aria2.host"
                label="主机 / Host"
                variant="outlined"
              ></v-text-field>
            </v-col>
            <v-col cols="12" md="4">
              <v-text-field
                v-model="settings.aria2.port"
                label="RPC 端口"
                type="number"
                variant="outlined"
              ></v-text-field>
            </v-col>
            <v-col cols="12" md="4">
              <v-text-field
                v-model="settings.aria2.secret"
                label="RPC Token (Secret)"
                type="password"
                variant="outlined"
              ></v-text-field>
            </v-col>
          </v-row>
        </v-form>
      </v-card-text>
    </v-card>

    <v-card class="mb-4 rounded-xl" elevation="2">
      <v-card-title class="pa-4 d-flex align-center">
        <span>自动拉取与整理频率</span>
        <v-spacer></v-spacer>
        <v-btn color="primary" @click="saveSystem" :loading="saving" rounded="pill">保存并立即生效</v-btn>
      </v-card-title>
      <v-divider></v-divider>
      <v-card-text v-if="settings" class="pa-4">
        <v-form>
          <v-row class="align-center">
            <v-col cols="12" md="4">
              <v-select
                v-model="settings.schedule.mode"
                :items="[{title: '每天定时 (推荐)', value: 'cron'}, {title: '间隔轮询', value: 'interval'}]"
                label="拉取规则"
                variant="outlined"
              ></v-select>
            </v-col>
            <v-col cols="12" md="4" v-if="settings.schedule.mode === 'cron'">
              <v-text-field
                v-model="settings.schedule.cron_time"
                label="每天指定时间 (HH:MM)"
                type="time"
                variant="outlined"
              ></v-text-field>
            </v-col>
            <v-col cols="12" md="4" v-if="settings.schedule.mode === 'interval'">
              <v-text-field
                v-model="settings.schedule.interval"
                label="间隔分钟数"
                type="number"
                variant="outlined"
              ></v-text-field>
            </v-col>
          </v-row>
        </v-form>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, onMounted, inject } from 'vue'
import axios from 'axios'

const settings = ref(null)
const mirrorObj = ref('')
const saving = ref(false)
const showMsg = inject('showMsg')

const loadSystem = async () => {
  try {
    const res = await axios.get('/api/settings/system')
    settings.value = res.data
    mirrorObj.value = (settings.value.api_url && settings.value.api_url.length > 0) ? settings.value.api_url[0] : 'https://mikanani.me'
  } catch (e) {
    showMsg('加载设置失败', 'error')
  }
}

const saveSystem = async () => {
  saving.value = true
  settings.value.api_url = [mirrorObj.value] // 覆盖写入列表作为主镜像
  try {
    await axios.post('/api/settings/system', settings.value)
    
    // 立即通知 scheduler 重载
    await axios.post('/api/schedule/update', {})
    
    showMsg('设置已保存并立即生效！')
  } catch (e) {
    showMsg('保存失败', 'error')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadSystem()
})
</script>
