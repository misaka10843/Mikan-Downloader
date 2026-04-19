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
            <v-col cols="12">
              <div class="d-flex align-center mb-2">
                <h3 class="text-subtitle-1 font-weight-bold">Mikan API 域名冗余设置</h3>
                <v-spacer></v-spacer>
                <v-btn size="small" color="primary" variant="text" prepend-icon="mdi-plus" @click="addApiUrl">添加域名</v-btn>
              </div>
              <p class="text-caption text-grey mb-3">系统将按顺序尝试访问以下域名，第一个可用的将作为主站。你可以通过拖拽或按钮调整优先级。</p>
              
              <v-list border rounded="lg" class="pa-0">
                <v-list-item v-for="(url, index) in settings.api_url" :key="index" class="py-2">
                  <template v-slot:prepend>
                    <div class="d-flex flex-column mr-2">
                      <v-btn icon="mdi-chevron-up" variant="text" size="x-small" :disabled="index === 0" @click="moveUrl(index, -1)"></v-btn>
                      <v-btn icon="mdi-chevron-down" variant="text" size="x-small" :disabled="index === settings.api_url.length - 1" @click="moveUrl(index, 1)"></v-btn>
                    </div>
                  </template>

                  <v-text-field
                    v-model="settings.api_url[index]"
                    placeholder="https://mikanani.me"
                    variant="underlined"
                    density="compact"
                    hide-details
                    class="mr-4"
                  ></v-text-field>

                  <template v-slot:append>
                    <div class="d-flex align-center">
                      <div v-if="latencies[url]" class="mr-4 text-caption" :class="getLatencyColor(latencies[url])">
                        {{ latencies[url] }} ms
                      </div>
                      <v-btn icon="mdi-speedometer" variant="text" size="small" color="secondary" @click="testUrl(index)" :loading="testingIdx === index"></v-btn>
                      <v-btn icon="mdi-delete-outline" variant="text" size="small" color="error" @click="removeUrl(index)"></v-btn>
                    </div>
                  </template>
                </v-list-item>
              </v-list>
            </v-col>
            <v-col cols="12" md="6">
              <v-text-field
                v-model="settings.save_dir"
                label="下载保存目录"
                variant="outlined"
                hint="例如： /mnt/media/anime"
              ></v-text-field>
            </v-col>
            <v-col cols="12" md="6">
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

  </div>
</template>

<script setup>
import { ref, onMounted, inject } from 'vue'
import axios from 'axios'

const settings = ref(null)
const mirrorObj = ref('')
const saving = ref(false)
const showMsg = inject('showMsg')

const latencies = ref({})
const testingIdx = ref(-1)

const loadSystem = async () => {
  try {
    const res = await axios.get('/api/settings/system')
    settings.value = res.data
    if (!settings.value.api_url) settings.value.api_url = []
    if (settings.value.api_url.length === 0) settings.value.api_url = ['https://mikanani.me']
  } catch (e) {
    showMsg('加载设置失败', 'error')
  }
}

const addApiUrl = () => {
  settings.value.api_url.push('')
}

const removeUrl = (index) => {
  if (settings.value.api_url.length <= 1) {
    showMsg('至少保留一个域名', 'warning')
    return
  }
  settings.value.api_url.splice(index, 1)
}

const moveUrl = (index, direction) => {
  const newIndex = index + direction
  if (newIndex < 0 || newIndex >= settings.value.api_url.length) return
  const item = settings.value.api_url.splice(index, 1)[0]
  settings.value.api_url.splice(newIndex, 0, item)
}

const testUrl = async (index) => {
  const url = settings.value.api_url[index]
  if (!url) return
  testingIdx.value = index
  try {
    const res = await axios.post('/api/settings/test_url', { url })
    if (res.data.status === 'success') {
      latencies.value[url] = res.data.latency
    } else {
      latencies.value[url] = 'Error'
    }
  } catch (e) {
    latencies.value[url] = 'Down'
  } finally {
    testingIdx.value = -1
  }
}

const getLatencyColor = (latency) => {
  if (typeof latency !== 'number') return 'text-error'
  if (latency < 300) return 'text-success'
  if (latency < 1000) return 'text-warning'
  return 'text-error'
}

const saveSystem = async () => {
  saving.value = true
  try {
    await axios.post('/api/settings/system', settings.value)
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
