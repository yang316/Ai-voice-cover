<template>
  <div class="cover-workspace">
    <!-- Upload Section -->
    <div class="glass-card">
      <div class="card-header">
        <svg class="card-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
        <h2 class="card-title">{{ t('uploadAudio') }}</h2>
      </div>

      <n-upload
        :max="1"
        accept="audio/*"
        @update:file-list="handleFileChange"
        :show-file-list="false"
      >
        <div class="upload-zone" :class="{ 'has-file': selectedFile }">
          <svg class="upload-icon" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M9 18V5l12-2v13"/>
            <circle cx="6" cy="18" r="3"/>
            <circle cx="18" cy="16" r="3"/>
          </svg>
          <div class="upload-text">
            <strong>{{ selectedFile ? selectedFile.name : t('clickToUpload') }}</strong>
            <span v-if="!selectedFile">{{ t('dragAndDrop') }}</span>
          </div>
          <p class="upload-hint">{{ t('supportedFormats') }}</p>
        </div>
      </n-upload>
    </div>

    <!-- Settings -->
    <div class="glass-card">
      <div class="card-header">
        <svg class="card-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="3"/>
          <path d="M12 1v6m0 6v10M1 12h6m6 0h10"/>
        </svg>
        <h2 class="card-title">{{ t('settings') }}</h2>
      </div>

      <n-form label-placement="top" class="studio-form">
        <n-form-item :label="t('voiceModel')">
          <n-select
            v-model:value="selectedVoiceId"
            :options="voiceOptions"
            :loading="voicesStore.loading"
            :placeholder="t('selectVoice')"
          />
        </n-form-item>

        <n-form-item :label="t('computeBackend')">
          <n-select
            v-model:value="appStore.backend"
            :options="backendOptions"
          />
        </n-form-item>

        <n-form-item v-if="appStore.needsApiKey" :label="t('apiKey')">
          <n-input
            v-model:value="appStore.apiKey"
            type="password"
            :placeholder="t('apiKeyPlaceholder')"
            show-password-on="click"
          />
        </n-form-item>

        <n-form-item v-if="appStore.backend === 'gpt_sovits'" :label="t('gptSovitsUrl')">
          <n-input
            v-model:value="appStore.gptSovitsUrl"
            placeholder="http://127.0.0.1:9880"
          />
        </n-form-item>

        <n-form-item :label="`${t('pitchShift')} (${pitchShift[0]} st)`">
          <n-slider
            v-model:value="pitchShift[0]"
            :min="-12"
            :max="12"
            :step="1"
            :marks="{'-12': '-12', '0': '0', '12': '+12'}"
          />
        </n-form-item>

        <div class="form-row">
          <label class="form-label">{{ t('noiseReduction') }}</label>
          <n-switch v-model:value="denoise" />
        </div>

        <n-divider style="margin: 20px 0" />

        <n-button
          type="primary"
          size="large"
          block
          :disabled="!canSubmit"
          :loading="isProcessing"
          @click="handleCreateCover"
          class="action-button"
        >
          <template #icon>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
          </template>
          {{ t('createCover') }}
        </n-button>

        <!-- Progress -->
        <div v-if="isProcessing" class="progress-section">
          <div class="progress-header">
            <span class="progress-label">{{ statusText }}</span>
            <span class="progress-value">{{ progress }}%</span>
          </div>
          <n-progress
            type="line"
            :percentage="progress"
            :show-indicator="false"
            :height="6"
          />
        </div>
      </n-form>
    </div>

    <!-- Result -->
    <div v-if="resultUrl" class="glass-card result-card">
      <div class="card-header">
        <svg class="card-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <path d="M12 6v6l4 2"/>
        </svg>
        <h2 class="card-title">{{ t('result') }}</h2>
      </div>

      <div class="result-content">
        <audio :src="resultUrl" controls class="audio-player"></audio>
        <n-space>
          <n-button type="primary" @click="downloadResult">
            <template #icon>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
            </template>
            {{ t('download') }}
          </n-button>
          <n-button @click="resetForm">
            {{ t('newCover') }}
          </n-button>
        </n-space>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, inject, watch } from 'vue'
import { NForm, NFormItem, NInput, NSelect, NSlider, NSwitch, NButton, NProgress, NSpace, NUpload, NDivider } from 'naive-ui'
import type { MessageApiInjection } from 'naive-ui/es/message/src/MessageProvider'
import { useAppStore } from '@/stores/app'
import { useVoicesStore } from '@/stores/voices'
import { useTasksStore } from '@/stores/tasks'
import { useApi } from '@/composables/useApi'
import { useI18n } from '@/composables/useI18n'

const emit = defineEmits(['processing-change'])

const message = inject<MessageApiInjection>('message')
const appStore = useAppStore()
const voicesStore = useVoicesStore()
const tasksStore = useTasksStore()
const api = useApi()
const { t } = useI18n()

const selectedFile = ref<File | null>(null)
const selectedVoiceId = computed({
  get: () => voicesStore.selectedVoiceId,
  set: (val) => { voicesStore.selectedVoiceId = val }
})
const pitchShift = ref([0])
const denoise = ref(true)

const isProcessing = ref(false)
const progress = ref(0)
const statusText = ref('')
const resultUrl = ref('')
const currentTaskId = ref('')

const canSubmit = computed(() => {
  return selectedFile.value && selectedVoiceId.value && !isProcessing.value
})

const voiceOptions = computed(() => {
  return voicesStore.voices.map(v => ({
    label: v.name,
    value: v.id
  }))
})

const backendOptions = computed(() => [
  { label: t('backendLocal'), value: 'local' },
  { label: t('backendGptSovits'), value: 'gpt_sovits' },
  { label: t('backendElevenLabs'), value: 'elevenlabs' },
  { label: t('backendFishAudio'), value: 'fish_audio' },
])

watch(isProcessing, (val) => {
  emit('processing-change', val)
})

function handleFileChange(fileList: any[]) {
  if (fileList.length > 0) {
    selectedFile.value = fileList[0].file
  } else {
    selectedFile.value = null
  }
}

async function handleCreateCover() {
  if (!selectedFile.value || !selectedVoiceId.value) return

  isProcessing.value = true
  progress.value = 0
  statusText.value = t('processing')
  resultUrl.value = ''

  try {
    const task = await api.createCover({
      audioFile: selectedFile.value,
      voiceId: selectedVoiceId.value,
      backend: appStore.backend,
      pitchShift: pitchShift.value[0],
      denoise: denoise.value,
      apiKey: appStore.apiKey || undefined,
      gptSovitsUrl: appStore.gptSovitsUrl || undefined,
    })

    currentTaskId.value = task.task_id
    tasksStore.addTask(task)

    pollTaskStatus(task.task_id)
    message?.success(t('coverCreated'))
  } catch (error) {
    console.error('Failed to create cover:', error)
    message?.error(t('taskFailed'))
    isProcessing.value = false
  }
}

async function pollTaskStatus(taskId: string) {
  const poll = async () => {
    try {
      const task = await api.getTaskStatus(taskId)
      tasksStore.updateTask(taskId, task)

      progress.value = task.progress
      statusText.value = task.message || t('processing')

      if (task.status === 'completed') {
        isProcessing.value = false
        progress.value = 100
        statusText.value = t('complete')
        resultUrl.value = api.getDownloadUrl(taskId)
        message?.success(t('complete'))
      } else if (task.status === 'failed') {
        isProcessing.value = false
        message?.error(task.error || t('taskFailed'))
      } else if (task.status === 'processing' || task.status === 'pending') {
        setTimeout(poll, 2000)
      }
    } catch (error) {
      console.error('Failed to poll task status:', error)
      isProcessing.value = false
      message?.error(t('error'))
    }
  }

  poll()
}

function downloadResult() {
  if (resultUrl.value) {
    window.open(resultUrl.value, '_blank')
  }
}

function resetForm() {
  selectedFile.value = null
  resultUrl.value = ''
  currentTaskId.value = ''
  progress.value = 0
  isProcessing.value = false
}
</script>

<style scoped>
.cover-workspace {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-top: 16px;
}

/* Glass Card */
.glass-card {
  background: rgba(24, 24, 27, 0.6);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 20px 24px;
  transition: border-color 200ms ease;
}

.glass-card:hover {
  border-color: rgba(255, 255, 255, 0.1);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.card-icon {
  color: #71717a;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #fafafa;
  letter-spacing: -0.01em;
  margin: 0;
}

/* Upload Zone */
.upload-zone {
  border: 2px dashed #27272a;
  border-radius: 8px;
  padding: 40px 24px;
  text-align: center;
  cursor: pointer;
  transition: all 200ms ease;
}

.upload-zone:hover {
  border-color: #3f3f46;
  background: rgba(24, 24, 27, 0.4);
}

.upload-zone.has-file {
  border-color: #22c55e;
  background: rgba(34, 197, 94, 0.05);
}

.upload-icon {
  color: #52525b;
  margin-bottom: 12px;
  transition: color 200ms ease;
}

.upload-zone:hover .upload-icon {
  color: #71717a;
}

.upload-zone.has-file .upload-icon {
  color: #22c55e;
}

.upload-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 14px;
  color: #a1a1aa;
  margin-bottom: 8px;
}

.upload-text strong {
  color: #fafafa;
  font-weight: 500;
}

.upload-hint {
  font-size: 12px;
  color: #71717a;
  margin: 0;
}

/* Form */
.studio-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

:deep(.n-form-item-label) {
  font-size: 13px;
  font-weight: 500;
  color: #a1a1aa !important;
  padding-bottom: 6px;
}

.form-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
}

.form-label {
  font-size: 13px;
  font-weight: 500;
  color: #a1a1aa;
}

/* Action Button */
.action-button {
  margin-top: 4px;
  height: 42px;
  font-weight: 600;
  letter-spacing: -0.01em;
}

/* Progress */
.progress-section {
  margin-top: 16px;
  padding: 16px;
  background: rgba(24, 24, 27, 0.4);
  border: 1px solid #27272a;
  border-radius: 6px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.progress-label {
  font-size: 13px;
  color: #a1a1aa;
  font-weight: 500;
}

.progress-value {
  font-size: 14px;
  color: #22c55e;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

/* Result */
.result-card {
  animation: slideUp 300ms ease;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.result-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.audio-player {
  width: 100%;
  height: 48px;
  border-radius: 6px;
  background: rgba(24, 24, 27, 0.6);
}
</style>
