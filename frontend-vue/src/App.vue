<template>
  <n-config-provider :theme="darkTheme">
    <n-message-provider>
      <div class="app">
        <header class="app-header">
          <button class="lang-toggle" @click="toggleLang">
            {{ appStore.lang === 'zh' ? 'EN' : '中文' }}
          </button>
          <h1 class="app-header__logo">AI Voice Cover</h1>
          <p class="app-header__tagline">{{ t('pageSubtitle') }}</p>
        </header>

        <!-- Health Status -->
        <div class="health-bar">
          <span :class="['health-dot', healthDotClass]"></span>
          <span class="health-text">
            <strong>{{ healthStatusText }}</strong>
            <template v-if="appStore.health.gpu.device">
              • {{ appStore.health.gpu.device }}
            </template>
          </span>
          <button
            v-if="showInstallMl"
            class="ml-install-btn"
            :disabled="mlInstalling"
            @click="installMlDeps"
          >
            {{ mlInstalling ? mlProgress : t('installMlDeps') }}
          </button>
        </div>

        <!-- Tab Navigation -->
        <nav class="tab-nav">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            :class="['tab-nav__btn', { active: activeTab === tab.id }]"
            @click="activeTab = tab.id"
          >
            <component :is="tab.icon" />
            <span>{{ t(tab.label) }}</span>
          </button>
        </nav>

        <!-- Tab Content -->
        <main class="main-content">
          <CoverView v-if="activeTab === 'cover'" />
          <TtsView v-else-if="activeTab === 'tts'" />
          <TrainView v-else-if="activeTab === 'train'" />
        </main>

        <ToastContainer />
      </div>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { darkTheme } from 'naive-ui'
import { useAppStore } from '@/stores/app'
import { useVoicesStore } from '@/stores/voices'
import { useApi } from '@/composables/useApi'
import { useI18n } from '@/composables/useI18n'
import CoverView from '@/views/CoverViewNew.vue'
import TtsView from '@/views/TtsView.vue'
import TrainView from '@/views/TrainView.vue'
import ToastContainer from '@/components/ToastContainer.vue'

const appStore = useAppStore()
const voicesStore = useVoicesStore()
const api = useApi()
const { t } = useI18n()

const activeTab = ref<'cover' | 'tts' | 'train'>('cover')

const tabs = [
  {
    id: 'cover' as const,
    label: 'tabCover' as const,
    icon: () => h('svg', { width: '16', height: '16', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('path', { d: 'M9 18V5l12-2v13' }),
      h('circle', { cx: '6', cy: '18', r: '3' }),
      h('circle', { cx: '18', cy: '16', r: '3' })
    ])
  },
  {
    id: 'tts' as const,
    label: 'tabTts' as const,
    icon: () => h('svg', { width: '16', height: '16', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('path', { d: 'M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z' }),
      h('path', { d: 'M19 10v2a7 7 0 01-14 0v-2' })
    ])
  },
  {
    id: 'train' as const,
    label: 'tabTrain' as const,
    icon: () => h('svg', { width: '16', height: '16', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('path', { d: 'M12 20V10' }),
      h('path', { d: 'M18 20V4' }),
      h('path', { d: 'M6 20v-4' })
    ])
  }
]

const healthDotClass = computed(() => {
  if (appStore.health.status === 'online') return 'health-dot--ok'
  if (appStore.health.status === 'offline') return 'health-dot--error'
  return 'health-dot--checking'
})

const healthStatusText = computed(() => {
  return appStore.health.status === 'online' ? t('backendOnline') : t('backendOffline')
})

function toggleLang() {
  appStore.setLang(appStore.lang === 'zh' ? 'en' : 'zh')
}

async function checkBackendHealth() {
  try {
    const health = await api.checkHealth()
    appStore.health = health
  } catch (error) {
    appStore.health = {
      status: 'offline',
      gpu: { available: false, device: 'Offline' }
    }
  }
}

// ML dependency installation
const mlInstalling = ref(false)
const mlProgress = ref('')
const showInstallMl = computed(() => {
  if (appStore.health.status !== 'online') return false
  const features = appStore.health.features
  if (!features) return false
  return features.missing?.some((f: string) => ['covers', 'training'].includes(f))
})

async function installMlDeps() {
  mlInstalling.value = true
  mlProgress.value = t('installingMl')
  try {
    await fetch(api('/ml/install'), { method: 'POST' })
    // Poll status
    const poll = setInterval(async () => {
      try {
        const res = await fetch(api('/ml/status'))
        const data = await res.json()
        mlProgress.value = data.progress || t('installingMl')
        if (!data.installing) {
          clearInterval(poll)
          mlInstalling.value = false
          if (data.error) {
            mlProgress.value = `Error: ${data.error}`
          } else {
            mlProgress.value = ''
            await checkBackendHealth()
          }
        }
      } catch { /* ignore */ }
    }, 3000)
  } catch (e) {
    mlInstalling.value = false
    mlProgress.value = 'Failed to start installation'
  }
}

onMounted(async () => {
  await checkBackendHealth()
  await voicesStore.loadVoices()

  // Poll health every 30s
  setInterval(checkBackendHealth, 30000)
})
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root {
  --background: 240 10% 3.9%;
  --foreground: 0 0% 98%;
  --card: 240 10% 3.9%;
  --card-foreground: 0 0% 98%;
  --primary: 263 70% 50.4%;
  --primary-foreground: 0 0% 98%;
  --secondary: 240 3.7% 15.9%;
  --secondary-foreground: 0 0% 98%;
  --muted: 240 3.7% 15.9%;
  --muted-foreground: 240 5% 64.9%;
  --border: 240 3.7% 15.9%;
  --ring: 263 70% 50.4%;
  --radius: 0.75rem;
}

*, *::before, *::after {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background-color: hsl(var(--background));
  color: hsl(var(--foreground));
  min-height: 100vh;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app {
  min-height: 100vh;
}

.app {
  padding: 1.5rem;
  max-width: 1400px;
  margin: 0 auto;
}

.app-header {
  text-align: center;
  padding: 2rem 0 1.5rem;
  position: relative;
}

.lang-toggle {
  position: absolute;
  top: 0;
  right: 0;
  background: hsl(var(--secondary));
  border: 1px solid hsl(var(--border));
  border-radius: 9999px;
  padding: 0.25rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  cursor: pointer;
  transition: all 150ms ease;
  font-family: inherit;
}

.lang-toggle:hover {
  background: hsl(var(--muted));
  border-color: hsl(var(--ring));
}

.app-header__logo {
  font-size: 1.875rem;
  font-weight: 700;
  letter-spacing: -0.025em;
  background: linear-gradient(135deg, #667eea, #764ba2);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.app-header__tagline {
  color: hsl(var(--muted-foreground));
  font-size: 0.875rem;
  margin-top: 0.25rem;
  font-weight: 400;
}

.health-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  background: hsla(240, 10%, 6%, 0.5);
  border: 1px solid hsl(var(--border));
  border-radius: 0.5rem;
  margin-bottom: 1.5rem;
  font-size: 0.8125rem;
}

.health-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.health-dot--ok {
  background: hsl(142, 71%, 45%);
  box-shadow: 0 0 6px hsla(142, 71%, 45%, 0.4);
}

.health-dot--error {
  background: hsl(0, 62.8%, 50%);
  box-shadow: 0 0 6px hsla(0, 62.8%, 50%, 0.4);
}

.health-dot--checking {
  background: hsl(var(--muted-foreground));
  animation: pulse 1.5s infinite;
}

.health-text {
  color: hsl(var(--muted-foreground));
}

.health-text strong {
  color: hsl(var(--foreground));
  font-weight: 500;
}

.ml-install-btn {
  margin-left: auto;
  padding: 0.25rem 0.75rem;
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  border: none;
  border-radius: 0.375rem;
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 150ms;
  font-family: inherit;
  white-space: nowrap;
}

.ml-install-btn:hover {
  opacity: 0.9;
}

.ml-install-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.tab-nav {
  display: flex;
  gap: 0.25rem;
  background: hsl(var(--muted));
  border-radius: var(--radius);
  padding: 0.25rem;
  margin-bottom: 1.5rem;
}

.tab-nav__btn {
  flex: 1;
  padding: 0.625rem 1rem;
  border: none;
  background: transparent;
  color: hsl(var(--muted-foreground));
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  border-radius: calc(var(--radius) - 2px);
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  font-family: inherit;
}

.tab-nav__btn:hover {
  color: hsl(var(--foreground));
  background: hsla(0, 0%, 100%, 0.05);
}

.tab-nav__btn.active {
  background: hsl(var(--background));
  color: hsl(var(--foreground));
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

.main-content {
  width: 100%;
}

.tab-placeholder {
  text-align: center;
  padding: 4rem 2rem;
  color: hsl(var(--muted-foreground));
}

.tab-placeholder h2 {
  font-size: 1.5rem;
  margin-bottom: 0.5rem;
  color: hsl(var(--foreground));
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@media (max-width: 768px) {
  .app {
    padding: 1rem;
  }

  .app-header__logo {
    font-size: 1.5rem;
  }

  .tab-nav__btn span {
    display: none;
  }
}
</style>
