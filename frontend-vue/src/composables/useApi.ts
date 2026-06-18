import { ref } from 'vue'
import type { Voice, Task, HealthStatus, CreateCoverRequest } from '@/types/api'

// Fixed backend port — matches BACKEND_PORT in lib.rs
const BACKEND_PORT = 9527

const getApiBase = async (): Promise<string> => {
  // In Tauri, use fixed port
  if (window.__TAURI__) {
    try {
      // Try Tauri 2 invoke first
      if (window.__TAURI__?.core?.invoke) {
        const url = await window.__TAURI__.core.invoke('get_backend_url')
        return `${url}/api/v1`
      }
    } catch (e) {
      // fallback to fixed port
    }
    return `http://127.0.0.1:${BACKEND_PORT}/api/v1`
  }
  // Dev mode (Vite proxy)
  return '/api/v1'
}

let apiBase = `/api/v1`
getApiBase().then(base => { apiBase = base })

const api = (path: string) => `${apiBase}${path}`

export function useApi() {
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function checkHealth(): Promise<HealthStatus> {
    try {
      const res = await fetch(api('/health'))
      if (!res.ok) throw new Error('Backend offline')
      return await res.json()
    } catch (e) {
      throw new Error('Backend offline')
    }
  }

  async function getVoices(): Promise<Voice[]> {
    const res = await fetch(api('/voices'))
    if (!res.ok) throw new Error('Failed to load voices')
    const data = await res.json()
    return data.map((v: any) => ({
      id: v.id,
      name: v.name,
      description: v.description || '',
      modelPath: v.model_path || v.modelPath || '',
      indexPath: v.index_path || v.indexPath || null,
    }))
  }

  async function uploadVoice(data: {
    name: string
    description?: string
    modelFile: File
    indexFile?: File
  }): Promise<Voice> {
    const formData = new FormData()
    formData.append('name', data.name)
    if (data.description) formData.append('description', data.description)
    formData.append('model_file', data.modelFile)
    if (data.indexFile) formData.append('index_file', data.indexFile)

    const res = await fetch(api('/voices'), {
      method: 'POST',
      body: formData,
    })
    if (!res.ok) throw new Error('Upload failed')
    return await res.json()
  }

  async function deleteVoice(id: string): Promise<void> {
    const res = await fetch(api(`/voices/${id}`), { method: 'DELETE' })
    if (!res.ok) throw new Error('Delete failed')
  }

  async function createCover(data: CreateCoverRequest): Promise<Task> {
    const formData = new FormData()
    formData.append('audio_file', data.audioFile)
    formData.append('voice_id', data.voiceId)
    formData.append('backend', data.backend)
    formData.append('pitch_shift', data.pitchShift.toString())
    formData.append('denoise', data.denoise.toString())
    if (data.apiKey) formData.append('api_key', data.apiKey)
    if (data.gptSovitsUrl) formData.append('gpt_sovits_url', data.gptSovitsUrl)

    const res = await fetch(api('/covers'), {
      method: 'POST',
      body: formData,
    })
    if (!res.ok) throw new Error('Failed to create cover')
    return await res.json()
  }

  async function getTaskStatus(id: string): Promise<Task> {
    const res = await fetch(api(`/covers/${id}`))
    if (!res.ok) throw new Error('Failed to get task status')
    return await res.json()
  }

  function getDownloadUrl(id: string): string {
    return api(`/covers/${id}/download`)
  }

  return {
    loading,
    error,
    checkHealth,
    getVoices,
    uploadVoice,
    deleteVoice,
    createCover,
    getTaskStatus,
    getDownloadUrl,
  }
}
