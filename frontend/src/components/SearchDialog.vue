<template>
  <v-dialog v-model="dialog" max-width="800">
    <v-card class="rounded-xl">
      <v-card-title class="d-flex align-center bg-primary text-white pa-4">
        搜索并在 Mikan 添加订阅
        <v-spacer></v-spacer>
        <v-btn icon="mdi-close" variant="text" @click="dialog = false"></v-btn>
      </v-card-title>
      <v-card-text class="pa-4 pt-6">
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

        <v-list v-if="results.length > 0" lines="two">
          <v-list-item
            v-for="(item, index) in results"
            :key="index"
            class="mb-2 border rounded-lg"
          >
            <template v-slot:title>
              <div class="font-weight-bold">{{ item.name }}</div>
            </template>
            <template v-slot:subtitle>
              <div>Bangumi ID: {{ item.bangumiId }} | Subgroup: {{ item.subgroupId }}</div>
              <div class="text-xs text-grey">{{ item.url }}</div>
            </template>
            <template v-slot:append>
              <v-btn color="success" size="small" variant="flat" @click="subscribe(item)">
                + 添加此订阅
              </v-btn>
            </template>
          </v-list-item>
        </v-list>
        
        <v-alert v-if="hasSearched && results.length === 0 && !loading" type="info" variant="tonal" class="mt-4">
          没有找到对应的番剧或字幕组 RSS 匹配结果。
        </v-alert>

        <v-divider class="my-4"></v-divider>
        <h3 class="text-subtitle-1 mb-2">或者手动添加规则流：</h3>
        <v-row>
          <v-col cols="6">
            <v-text-field v-model="manual.url" label="/RSS/Bangumi?xxx" density="compact" variant="outlined"></v-text-field>
          </v-col>
          <v-col cols="3">
            <v-text-field v-model="manual.rule" label="正则或规则" density="compact" variant="outlined"></v-text-field>
          </v-col>
          <v-col cols="3">
            <v-btn color="primary" block @click="subscribe(manual)" height="40">添加</v-btn>
          </v-col>
        </v-row>
        <h3 class="text-subtitle-1 mb-2 mt-2 font-weight-bold">配置文件提取正则 (重命名为 S01Exx)</h3>
        <v-alert type="info" variant="tonal" density="compact" class="mb-4">
          如果您发现字幕组起名不修边幅（如 <code>10_burn-in.mp4</code> 或 <code>[TSDM] KxIX 01</code>），您需要自己在这编写一条提取出代表集数的纯数字（且含有 1个 () 捕获组）的正则。<br/>
          例如提取开头数字请写 <code>^(\d{1,3})_</code>。提取字夹层数字请写 <code>KxIX\s+(\d{1,3})</code>。留空 `auto` 则是用最新版的 AI 组件系统智能抓取。
        </v-alert>
        
        <div class="d-flex mb-4">
          <v-text-field
            v-model="renameRule"
            label="集数重命名正则 (填写含有1个捕获组()的正则)"
            variant="outlined"
            density="compact"
            hide-details
            placeholder="留空即为 auto"
          ></v-text-field>
        </div>

        <div class="bg-grey-lighten-4 pa-3 rounded">
          <div class="d-flex align-center">
            <v-text-field
              v-model="testFilename"
              label="测试文件名 (例如 [Airota][01].mp4)"
              variant="underlined"
              density="compact"
              hide-details
              class="mr-2"
            ></v-text-field>
            <v-btn color="secondary" size="small" @click="testRename" :loading="testingRename">测试匹配</v-btn>
          </div>
          <div v-if="testResult" class="mt-2 text-primary font-weight-bold">
            模拟重命名集数解析结果: {{ testResult }}
          </div>
        </div>

      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, inject } from 'vue'
import axios from 'axios'

const dialog = ref(false)
const query = ref('')
const results = ref([])
const loading = ref(false)
const hasSearched = ref(false)

const showMsg = inject('showMsg')
const emit = defineEmits(['added'])

const manual = ref({ url: '', rule: '.*' })
const renameRule = ref('auto')
const testFilename = ref('')
const testResult = ref('')
const testingRename = ref(false)

const open = () => {
  dialog.value = true
  query.value = ''
  results.value = []
  hasSearched.value = false
  renameRule.value = 'auto'
  testResult.value = ''
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

const testRename = async () => {
  if (!testFilename.value) return;
  testingRename.value = true
  try {
    const res = await axios.post('/api/library/test_rename', {
      filename: testFilename.value,
      regex: renameRule.value || 'auto'
    })
    const s_str = (res.data.season ?? 1).toString().padStart(2, '0');
    testResult.value = res.data.episode ? `S${s_str}E${res.data.episode}` : '匹配失败 (未能提取出有效集数)'
  } catch(e) {
    showMsg('测算失败', 'error')
  } finally {
    testingRename.value = false
  }
}

const subscribe = (item) => {
  const payload = {
    url: item.url,
    rule: item.rule || '.*',
    rename_rule: renameRule.value || 'auto',
    date: new Date().getFullYear().toString(),
    title: item.title || '',
    cover: item.cover || ''
  }
  emit('added', payload)
  showMsg('组装了一项订阅参数！')
  dialog.value = false
}

defineExpose({ open })
</script>
