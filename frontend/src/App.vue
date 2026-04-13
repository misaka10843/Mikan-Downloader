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

const { mobile } = useDisplay()
const drawer = ref(!mobile.value)
const rail = ref(true)
const currentView = ref('dashboard')
const running = ref(false)
const snackbar = ref({ show: false, text: '', color: 'success' })

const menuItems = [
  { title: '我的订阅', value: 'dashboard', icon: 'mdi-view-dashboard', component: Dashboard },
  { title: '本地片库整理 (Jellyfin)', value: 'library', icon: 'mdi-folder-play', component: Library },
  { title: '自动化与定时策略', value: 'schedule', icon: 'mdi-clock-outline', component: Schedule },
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
