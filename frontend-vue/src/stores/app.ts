import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { HealthStatus } from '@/types/api'

export const useAppStore = defineStore('app', () => {
  // 语言设置
  const lang = ref<'zh' | 'en'>(
    (localStorage.getItem('lang') as 'zh' | 'en') || 'zh'
  )

  function setLang(newLang: 'zh' | 'en') {
    lang.value = newLang
    localStorage.setItem('lang', newLang)
  }

  // 健康状态
  const health = ref<HealthStatus>({
    status: 'offline',
    gpu: {
      available: false,
      device: 'Checking...',
    },
  })

  // 后端设置
  const backend = ref<'local' | 'gpt_sovits' | 'elevenlabs' | 'fish_audio'>('local')
  const apiKey = ref('')
  const gptSovitsUrl = ref('http://127.0.0.1:9880')

  // 是否需要显示 API Key 输入框
  const needsApiKey = computed(() => {
    return backend.value === 'elevenlabs' || backend.value === 'fish_audio'
  })

  return {
    lang,
    setLang,
    health,
    backend,
    apiKey,
    gptSovitsUrl,
    needsApiKey,
  }
})
