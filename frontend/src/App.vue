<template>
  <v-app class="bg-background">
    <v-navigation-drawer
        v-model="drawer"
        :location="$vuetify.display.mobile ? 'bottom' : undefined"
        :permanent="!$vuetify.display.mobile"
        :rail="!$vuetify.display.mobile && rail"
        :temporary="$vuetify.display.mobile"
        color="primary"
        expand-on-hover
    >
      <v-list density="compact" nav>
        <v-list-item
            class="mb-4"
            prepend-icon="mdi-download-box"
            subtitle="v2.0"
            title="Mikan-Downloader"
        ></v-list-item>
        <v-divider class="mb-2 opacity-20"></v-divider>

        <v-list-item
            v-for="item in menuItems"
            :key="item.value"
            :active="currentView === item.value"
            :prepend-icon="item.icon"
            :title="item.title"
            :value="item.value"
            rounded="xl"
            @click="currentView = item.value"
        ></v-list-item>
      </v-list>
    </v-navigation-drawer>

    <v-app-bar class="px-2 border-b" color="background" flat>
      <v-app-bar-nav-icon v-if="$vuetify.display.mobile" @click="drawer = !drawer"></v-app-bar-nav-icon>

      <v-app-bar-title class="text-h6 font-weight-bold text-primary pl-2">
        {{ pageTitle }}
      </v-app-bar-title>

      <v-spacer></v-spacer>

      <v-btn
          :loading="running"
          class="text-none"
          color="primary"
          prepend-icon="mdi-play"
          rounded="pill"
          variant="flat"
          @click="manualRun"
      >
        <span class="hidden-xs">立即运行</span>
      </v-btn>

      <!-- 消息中心挂载 -->
      <v-menu width="350" :close-on-content-click="true">
        <template v-slot:activator="{ props }">
          <v-btn v-bind="props" icon class="ml-2">
            <v-badge v-if="unreadCount > 0" color="error" :content="unreadCount" overlap>
              <v-icon>mdi-bell-outline</v-icon>
            </v-badge>
            <v-icon v-else>mdi-bell-outline</v-icon>
          </v-btn>
        </template>
        <v-list class="pa-0 rounded-lg">
          <div class="pa-3 bg-primary text-white d-flex align-center">
            <span class="text-subtitle-2 font-weight-bold">系统通知</span>
            <v-spacer></v-spacer>
            <v-btn size="x-small" variant="text" color="white" @click.stop="markAllReadQuick">一键已读</v-btn>
          </div>
          <v-divider></v-divider>
          <template v-if="recentNotifications.length > 0">
            <v-list-item 
              v-for="n in recentNotifications" 
              :key="n.id"
              class="border-b"
              @click="currentView = 'notifications'"
            >
              <template v-slot:prepend>
                <v-icon :color="getLevelColor(n.level)" :icon="getLevelIcon(n.level)" size="small"></v-icon>
              </template>
              <v-list-item-title class="text-caption font-weight-bold">{{ n.title }}</v-list-item-title>
              <v-list-item-subtitle class="text-xs">{{ n.timestamp }}</v-list-item-subtitle>
            </v-list-item>
          </template>
          <div v-else class="pa-10 text-center text-grey text-caption">
            暂无未读消息
          </div>
          <v-divider></v-divider>
          <v-btn block variant="text" class="text-caption py-3" height="auto" @click="currentView = 'notifications'">
            查看历史完整纪录
          </v-btn>
        </v-list>
      </v-menu>
    </v-app-bar>

    <v-main>
      <v-container class="pa-4 pa-md-6" fluid style="max-width: 1600px;">
        <v-fade-transition mode="out-in">
          <component :is="currentPageComponent" key="view"/>
        </v-fade-transition>
      </v-container>
    </v-main>

    <v-snackbar
        v-model="snackbar.show"
        :color="snackbar.color"
        elevation="4"
        location="top center"
        rounded="pill"
        timeout="3000"
    >
      <div class="d-flex align-center justify-center">
        <v-icon :icon="snackbar.color === 'success' ? 'mdi-check-circle' : 'mdi-alert-circle'" class="mr-2"></v-icon>
        <span class="font-weight-medium">{{ snackbar.text }}</span>
      </div>
    </v-snackbar>
  </v-app>
</template>

<script setup>
import { computed, provide, ref } from 'vue'
import axios from 'axios'
import { useDisplay } from 'vuetify'

import Dashboard from './pages/Dashboard.vue'
import Settings from './pages/Settings.vue'
import Library from './pages/Library.vue'
import Schedule from './pages/Schedule.vue'
import Notifications from './pages/Notifications.vue'
import History from './pages/History.vue'

const { mobile } = useDisplay()
const drawer = ref(!mobile.value)
const rail = ref(true)
const currentView = ref('dashboard')
const running = ref(false)
const snackbar = ref({ show: false, text: '', color: 'success' })

const unreadCount = ref(0)
const recentNotifications = ref([])

const menuItems = [
  { title: '我的订阅', value: 'dashboard', icon: 'mdi-view-dashboard', component: Dashboard },
  { title: '本地片库整理 (Jellyfin)', value: 'library', icon: 'mdi-folder-play', component: Library },
  { title: '自动化与定时策略', value: 'schedule', icon: 'mdi-clock-outline', component: Schedule },
  { title: '通知中心', value: 'notifications', icon: 'mdi-bell-ring', component: Notifications },
  { title: '下载历史记录', value: 'history', icon: 'mdi-history', component: History },
  { title: '系统设置', value: 'settings', icon: 'mdi-cog', component: Settings },
]

const currentPageComponent = computed(() => {
  const item = menuItems.find(i => i.value === currentView.value)
  return item ? item.component : Dashboard
})

const pageTitle = computed(() => {
  const item = menuItems.find(i => i.value === currentView.value)
  return item ? item.title : 'Dashboard'
})

const showMsg = (text, color = 'success') => {
  snackbar.value = { show: true, text, color }
}
provide('showMsg', showMsg)

const manualRun = async () => {
  running.value = true
  try {
    const res = await axios.post('/api/run')
    showMsg('后台抓取任务已启动')
  } catch (e) {
    showMsg('启动失败', 'error')
  } finally {
    setTimeout(() => running.value = false, 2000)
  }
}

const fetchNotifications = async () => {
  try {
    const res = await axios.get('/api/notifications', { params: { limit: 5, unread: true } })
    recentNotifications.value = res.data
    unreadCount.value = res.data.length
  } catch (e) {
    console.error('Failed to fetch notifications', e)
  }
}

const markAllReadQuick = async () => {
  try {
    await axios.post('/api/notifications/read', {})
    unreadCount.value = 0
    recentNotifications.value = []
    showMsg('全部标记已读')
  } catch (e) {}
}

const getLevelColor = (level) => {
  switch (level) {
    case 'success': return 'success'
    case 'error': return 'error'
    case 'warning': return 'warning'
    default: return 'primary'
  }
}

const getLevelIcon = (level) => {
  switch (level) {
    case 'success': return 'mdi-check-circle'
    case 'error': return 'mdi-alert-circle'
    case 'warning': return 'mdi-alert'
    default: return 'mdi-information'
  }
}

// 每 30 秒轮询一次通知
import { onMounted, onUnmounted } from 'vue'
let pollTimer = null

onMounted(() => {
  fetchNotifications()
  pollTimer = setInterval(fetchNotifications, 30000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style>
html {
  overflow-y: auto;
}
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-corner {
    background-color: transparent;
}
::-webkit-scrollbar-thumb {
    background: rgb(var(--v-theme-background));
    border-radius: 8px;
    cursor: pointer;
}
::-webkit-scrollbar-thumb {
    background-color: #888;
    opacity: 1;
    transition: opacity .5s;
}
::-webkit-scrollbar-track {
    background-color: transparent;
}
::-webkit-scrollbar-track {
    background-color: transparent;
}
</style>
