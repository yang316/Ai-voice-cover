import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { Voice } from '@/types/api'
import { useApi } from '@/composables/useApi'

export const useVoicesStore = defineStore('voices', () => {
  const voices = ref<Voice[]>([])
  const loading = ref(false)
  const selectedVoiceId = ref<string>('')

  const api = useApi()

  async function loadVoices() {
    loading.value = true
    try {
      voices.value = await api.getVoices()
      // 如果有声音且没有选中，自动选中第一个
      if (voices.value.length > 0 && !selectedVoiceId.value) {
        selectedVoiceId.value = voices.value[0].id
      }
    } catch (e) {
      console.error('Failed to load voices:', e)
    } finally {
      loading.value = false
    }
  }

  async function addVoice(data: {
    name: string
    description?: string
    modelFile: File
    indexFile?: File
  }) {
    const voice = await api.uploadVoice(data)
    voices.value.push(voice)
    return voice
  }

  async function removeVoice(id: string) {
    await api.deleteVoice(id)
    voices.value = voices.value.filter(v => v.id !== id)
    // 如果删除的是当前选中的，重置选择
    if (selectedVoiceId.value === id) {
      selectedVoiceId.value = voices.value[0]?.id || ''
    }
  }

  return {
    voices,
    loading,
    selectedVoiceId,
    loadVoices,
    addVoice,
    removeVoice,
  }
})
