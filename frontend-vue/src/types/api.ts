// API 类型定义
export interface Voice {
  id: string
  name: string
  description?: string
  modelPath: string
  indexPath?: string
}

export interface Task {
  id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  step: 'separating' | 'converting' | 'mixing' | 'complete'
  createdAt: string
  resultUrl?: string
  error?: string
}

export interface HealthStatus {
  status: 'online' | 'offline'
  gpu: {
    available: boolean
    device: string
    memory?: string
  }
}

export interface CreateCoverRequest {
  audioFile: File
  voiceId: string
  backend: 'local' | 'gpt_sovits' | 'elevenlabs' | 'fish_audio'
  pitchShift: number
  denoise: boolean
  apiKey?: string
  gptSovitsUrl?: string
}

export interface TTSRequest {
  text: string
  voiceId: string
  speed: number
  pitch: number
}

export interface TrainRequest {
  modelName: string
  audioFiles: File[]
  epochs: number
  batchSize: number
}
