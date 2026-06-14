<template>
  <div class="train-workspace">
    <!-- Training Setup -->
    <div class="glass-card">
      <div class="card-header">
        <svg class="card-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 20V10"/>
          <path d="M18 20V4"/>
          <path d="M6 20v-4"/>
        </svg>
        <h2 class="card-title">{{ t('trainTitle') }}</h2>
      </div>

      <n-form label-placement="top" class="studio-form">
        <n-form-item :label="t('modelName')">
          <n-input
            v-model:value="modelName"
            :placeholder="t('modelName')"
          />
        </n-form-item>

        <n-form-item :label="t('uploadTrainingAudio')">
          <n-upload
            multiple
            accept="audio/*"
            :max="20"
            @update:file-list="handleFileChange"
          >
            <div class="upload-zone" :class="{ 'has-file': files.length > 0 }">
              <svg class="upload-icon" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
              <div class="upload-text">
                <strong>{{ files.length > 0 ? `${files.length} files selected` : t('clickToUpload') }}</strong>
                <span v-if="files.length === 0">Multiple audio files supported</span>
              </div>
              <p class="upload-hint">Recommended: 5-15 seconds each, 3-10 minutes total</p>
            </div>
          </n-upload>
        </n-form-item>

        <div class="params-grid">
          <n-form-item :label="t('epochs')">
            <n-input-number
              v-model:value="epochs"
              :min="10"
              :max="1000"
              :step="10"
              style="width: 100%"
            />
          </n-form-item>

          <n-form-item :label="t('batchSize')">
            <n-input-number
              v-model:value="batchSize"
              :min="1"
              :max="32"
              :step="1"
              style="width: 100%"
            />
          </n-form-item>
        </div>

        <n-divider style="margin: 20px 0" />

        <n-button
          type="primary"
          size="large"
          block
          :disabled="!canSubmit"
          :loading="isTraining"
          @click="handleStartTraining"
          class="action-button"
        >
          <template #icon>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
          </template>
          {{ t('startTraining') }}
        </n-button>

        <!-- Training Progress -->
        <div v-if="isTraining" class="training-progress">
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

          <div class="stats-grid">
            <div class="stat-item">
              <div class="stat-label">{{ t('currentEpoch') }}</div>
              <div class="stat-value">{{ currentEpoch }} / {{ epochs }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">{{ t('loss') }}</div>
              <div class="stat-value">{{ loss }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">{{ t('eta') }}</div>
              <div class="stat-value">{{ eta }}</div>
            </div>
          </div>
        </div>
      </n-form>
    </div>

    <!-- Training History -->
    <div class="glass-card">
      <div class="card-header">
        <svg class="card-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <polyline points="12 6 12 12 16 14"/>
        </svg>
        <h2 class="card-title">{{ t('trainingHistory') }}</h2>
      </div>

      <div v-if="history.length === 0" class="empty-state">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <p>No training history</p>
      </div>

      <div v-else class="history-list">
        <div v-for="item in history" :key="item.id" class="history-item">
          <div class="history-info">
            <div class="history-name">{{ item.modelName }}</div>
            <div class="history-meta">
              <span :class="['status-badge', `status-${item.status}`]">
                {{ getStatusText(item.status) }}
              </span>
              <span class="history-time">{{ item.createdAt }}</span>
            </div>
          </div>
          <n-space v-if="item.status === 'completed'">
            <n-button size="small" @click="downloadModel(item.id)">
              Download
            </n-button>
          </n-space>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, inject, watch } from 'vue'
import { NForm, NFormItem, NInput, NInputNumber, NButton, NProgress, NSpace, NUpload, NDivider } from 'naive-ui'
import type { MessageApiInjection } from 'naive-ui/es/message/src/MessageProvider'
import { useTasksStore } from '@/stores/tasks'
import { useI18n } from '@/composables/useI18n'

const emit = defineEmits(['processing-change'])

const message = inject<MessageApiInjection>('message')
const tasksStore = useTasksStore()
const { t } = useI18n()

const modelName = ref('')
const files = ref<any[]>([])
const epochs = ref(200)
const batchSize = ref(4)
const isTraining = ref(false)
const progress = ref(0)
const statusText = ref('')
const currentEpoch = ref(0)
const loss = ref('-')
const eta = ref('-')
const history = ref<any[]>([])

const canSubmit = computed(() => {
  return modelName.value.trim() && files.value.length > 0 && !isTraining.value
})

watch(isTraining, (val) => {
  emit('processing-change', val)
})

function handleFileChange(fileList: any[]) {
  files.value = fileList
}

async function handleStartTraining() {
  if (!canSubmit.value) return

  isTraining.value = true
  progress.value = 0
  statusText.value = 'Uploading files...'
  currentEpoch.value = 0

  try {
    // Call real backend API
    const formData = new FormData()
    formData.append('model_name', modelName.value)
    formData.append('epoch', epochs.value.toString())
    formData.append('batch_size', batchSize.value.toString())

    // Add all audio files
    for (const fileWrapper of files.value) {
      if (fileWrapper.file) {
        formData.append('audio_files', fileWrapper.file)
      }
    }

    statusText.value = 'Starting training...'

    const response = await fetch('http://localhost:8000/api/v1/train', {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      throw new Error(`Training failed: ${response.statusText}`)
    }

    const result = await response.json()
    const taskId = result.task_id

    currentTaskId.value = taskId
    statusText.value = result.message

    // Add to local history
    const newItem = {
      id: taskId,
      modelName: modelName.value,
      status: 'processing',
      createdAt: new Date().toLocaleString(),
      type: 'Training'
    }
    history.value.unshift(newItem)

    // Add to global tasks store
    tasksStore.addTask({
      task_id: taskId,
      status: 'processing',
      progress: 0,
      type: 'Training',
      modelName: modelName.value,
      message: result.message,
    } as any)

    message?.success('Training started!')

    // Poll for status
    pollTrainingStatus(taskId)

  } catch (error: any) {
    console.error('Training failed:', error)
    message?.error(error.message || 'Failed to start training')
    isTraining.value = false
  }
}

async function pollTrainingStatus(taskId: string) {
  const poll = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/v1/train/${taskId}`)
      if (!response.ok) {
        throw new Error('Failed to get training status')
      }

      const data = await response.json()

      // Update progress
      currentEpoch.value = data.epoch || 0
      progress.value = data.progress_pct || 0
      statusText.value = data.message || 'Training...'
      loss.value = data.loss ? data.loss.toFixed(4) : '-'

      // Calculate ETA
      if (data.epoch && data.total_epochs) {
        const remaining = data.total_epochs - data.epoch
        eta.value = remaining > 0 ? `${Math.ceil(remaining / 10)} min` : 'Almost done'
      }

      // Update stores
      const historyItem = history.value.find(h => h.id === taskId)
      if (historyItem) {
        historyItem.status = data.status
      }

      tasksStore.updateTask(taskId, {
        status: data.status,
        progress: data.progress_pct,
        message: data.message,
      } as any)

      if (data.status === 'completed') {
        isTraining.value = false
        progress.value = 100
        statusText.value = 'Training complete!'
        message?.success('Model training completed!')
      } else if (data.status === 'failed') {
        isTraining.value = false
        message?.error(data.message || 'Training failed')
      } else if (data.status === 'training' || data.status === 'preparing' || data.status === 'extracting' || data.status === 'pending') {
        setTimeout(poll, 2000)
      }
    } catch (error) {
      console.error('Failed to poll training status:', error)
      isTraining.value = false
      message?.error('Failed to get training status')
    }
  }

  poll()
}

const currentTaskId = ref('')

function getStatusText(status: string) {
  const texts: Record<string, string> = {
    completed: 'Completed',
    training: 'Training',
    failed: 'Failed',
    pending: 'Pending'
  }
  return texts[status] || status
}

function downloadModel(id: string) {
  const item = history.value.find(h => h.id === id)
  if (item && item.status === 'completed') {
    message?.info(`Downloading model: ${item.modelName}`)
    const url = `http://localhost:8000/api/v1/train/download/${id}`
    window.open(url, '_blank')
  } else {
    message?.error('Model not completed or not found')
  }
}
</script>

<style scoped>
.train-workspace {
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

.params-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

@media (max-width: 640px) {
  .params-grid {
    grid-template-columns: 1fr;
  }
}

/* Action Button */
.action-button {
  margin-top: 4px;
  height: 42px;
  font-weight: 600;
  letter-spacing: -0.01em;
}

/* Training Progress */
.training-progress {
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

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 16px;
}

.stat-item {
  text-align: center;
  padding: 12px;
  background: rgba(24, 24, 27, 0.6);
  border-radius: 6px;
}

.stat-label {
  font-size: 11px;
  color: #71717a;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 16px;
  font-weight: 600;
  color: #22c55e;
  font-variant-numeric: tabular-nums;
}

/* History List */
.history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  background: rgba(24, 24, 27, 0.4);
  border: 1px solid #27272a;
  border-radius: 6px;
  transition: all 200ms ease;
}

.history-item:hover {
  border-color: #3f3f46;
  background: rgba(24, 24, 27, 0.6);
}

.history-info {
  flex: 1;
  min-width: 0;
}

.history-name {
  font-size: 14px;
  font-weight: 500;
  color: #fafafa;
  margin-bottom: 4px;
}

.history-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #71717a;
}

.status-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.status-completed {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.status-training {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
}

.status-failed {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.history-time {
  color: #52525b;
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  color: #52525b;
  text-align: center;
}

.empty-state svg {
  margin-bottom: 12px;
  opacity: 0.4;
}

.empty-state p {
  font-size: 13px;
  margin: 0;
}
</style>
