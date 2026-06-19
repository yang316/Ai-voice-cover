<template>
  <div class="studio-layout">
    <div class="main-workspace">
      <!-- Header with Live Status -->
      <header class="workspace-header">
        <div class="header-left">
          <h1 class="studio-logo">
            <svg class="waveform-icon" :class="{ 'is-active': isProcessing }" width="24" height="24" viewBox="0 0 24 24" fill="none">
              <rect x="2" y="8" width="2" height="8" fill="currentColor" rx="1">
                <animate attributeName="height" values="8;16;8" dur="1.2s" repeatCount="indefinite" begin="0s" />
                <animate attributeName="y" values="8;4;8" dur="1.2s" repeatCount="indefinite" begin="0s" />
              </rect>
              <rect x="6" y="6" width="2" height="12" fill="currentColor" rx="1">
                <animate attributeName="height" values="12;20;12" dur="1.2s" repeatCount="indefinite" begin="0.2s" />
                <animate attributeName="y" values="6;2;6" dur="1.2s" repeatCount="indefinite" begin="0.2s" />
              </rect>
              <rect x="10" y="4" width="2" height="16" fill="currentColor" rx="1">
                <animate attributeName="height" values="16;18;16" dur="1.2s" repeatCount="indefinite" begin="0.4s" />
                <animate attributeName="y" values="4;3;4" dur="1.2s" repeatCount="indefinite" begin="0.4s" />
              </rect>
              <rect x="14" y="6" width="2" height="12" fill="currentColor" rx="1">
                <animate attributeName="height" values="12;20;12" dur="1.2s" repeatCount="indefinite" begin="0.6s" />
                <animate attributeName="y" values="6;2;6" dur="1.2s" repeatCount="indefinite" begin="0.6s" />
              </rect>
              <rect x="18" y="8" width="2" height="8" fill="currentColor" rx="1">
                <animate attributeName="height" values="8;14;8" dur="1.2s" repeatCount="indefinite" begin="0.8s" />
                <animate attributeName="y" values="8;5;8" dur="1.2s" repeatCount="indefinite" begin="0.8s" />
              </rect>
            </svg>
            Voice Cover Studio
          </h1>
          <div class="status-indicator" :class="statusClass">
            <span class="status-dot"></span>
            <span class="status-text">{{ statusText }}</span>
          </div>
          <button
            v-if="showInstallMl"
            class="ml-install-btn"
            :disabled="mlInstalling"
            @click="installMlDeps"
          >
            {{ installMlLabel }}
          </button>
        </div>
        <button class="lang-toggle" @click="toggleLang">
          {{ appStore.lang === 'zh' ? 'EN' : '中文' }}
        </button>
      </header>

      <!-- Main Tabs -->
      <n-tabs v-model:value="activeTab" type="line" animated class="studio-tabs">
        <n-tab-pane name="cover" :tab="t('tabCover')">
          <CoverView @processing-change="handleProcessingChange" />
        </n-tab-pane>
        <n-tab-pane name="tts" :tab="t('tabTts')">
          <TtsView @processing-change="handleProcessingChange" />
        </n-tab-pane>
        <n-tab-pane name="train" :tab="t('tabTrain')">
          <TrainView @processing-change="handleProcessingChange" />
        </n-tab-pane>
      </n-tabs>
    </div>

    <!-- Sidebar -->
    <aside class="studio-sidebar">
      <!-- Voice Models -->
      <section class="sidebar-section">
        <div class="section-header">
          <h3 class="section-title">{{ t('voiceModels') }}</h3>
          <n-button size="small" @click="showUploadModal = true" class="add-button">
            <template #icon>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="12" y1="5" x2="12" y2="19"/>
                <line x1="5" y1="12" x2="19" y2="12"/>
              </svg>
            </template>
          </n-button>
        </div>

        <div class="model-list">
          <div
            v-for="voice in voicesStore.voices"
            :key="voice.id"
            class="model-item"
            @click="selectVoice(voice.id)"
          >
            <div class="model-info">
              <div class="model-name">{{ voice.name }}</div>
              <div class="model-meta">{{ voice.source }}</div>
            </div>
            <button class="model-delete" @click.stop="handleDeleteVoice(voice.id)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
              </svg>
            </button>
          </div>

          <div v-if="voicesStore.voices.length === 0" class="empty-state">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/>
              <path d="M19 10v2a7 7 0 01-14 0v-2"/>
            </svg>
            <p>{{ t('noVoiceModels') }}</p>
          </div>
        </div>
      </section>

      <!-- Recent Tasks -->
      <section class="sidebar-section">
        <h3 class="section-title">{{ t('recentTasks') }}</h3>
        <div class="task-list">
          <div v-if="tasksStore.tasks.length === 0" class="empty-state">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
            <p>{{ t('noTasks') }}</p>
          </div>

          <div v-else class="task-list-items">
            <div
              v-for="task in tasksStore.tasks.slice(0, 5)"
              :key="task.task_id"
              class="task-item"
            >
              <div class="task-info">
                <div class="task-type">{{ getTaskType(task) }}</div>
                <div class="task-status">
                  <span :class="['status-badge', `status-${task.status}`]">
                    {{ getTaskStatusText(task.status) }}
                  </span>
                  <span v-if="task.status === 'processing'" class="task-progress">
                    {{ task.progress }}%
                  </span>
                </div>
              </div>
              <n-button
                v-if="task.status === 'completed'"
                size="tiny"
                @click="downloadTask(task.task_id)"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                  <polyline points="7 10 12 15 17 10"/>
                  <line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
              </n-button>
            </div>
          </div>
        </div>
      </section>
    </aside>

    <!-- Upload Modal -->
    <n-modal v-model:show="showUploadModal">
      <n-card
        style="width: 520px"
        :title="t('importVoiceModel')"
        :bordered="false"
        size="huge"
        role="dialog"
        aria-modal="true"
        class="upload-modal"
      >
        <n-form label-placement="top">
          <n-form-item :label="t('name')">
            <n-input v-model:value="uploadForm.name" :placeholder="t('name')" />
          </n-form-item>
          <n-form-item :label="t('description')">
            <n-input
              v-model:value="uploadForm.description"
              :placeholder="t('descriptionOptional')"
              type="textarea"
              :rows="2"
            />
          </n-form-item>
          <n-form-item label=".pth Model">
            <n-upload
              :max="1"
              accept=".pth"
              @update:file-list="handleModelFileChange"
              :show-file-list="false"
            >
              <n-button secondary>
                {{ uploadForm.modelFile ? uploadForm.modelFile.name : t('selectFile') }}
              </n-button>
            </n-upload>
          </n-form-item>
          <n-form-item label=".index File (Optional)">
            <n-upload
              :max="1"
              accept=".index"
              @update:file-list="handleIndexFileChange"
              :show-file-list="false"
            >
              <n-button secondary>
                {{ uploadForm.indexFile ? uploadForm.indexFile.name : t('selectFile') }}
              </n-button>
            </n-upload>
          </n-form-item>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="showUploadModal = false">{{ t('cancel') }}</n-button>
            <n-button type="primary" @click="handleUploadVoice" :loading="uploading">
              {{ t('upload') }}
            </n-button>
          </n-space>
        </template>
      </n-card>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, inject } from 'vue'
import { NTabs, NTabPane, NButton, NSpace, NModal, NCard, NForm, NFormItem, NInput, NUpload } from 'naive-ui'
import type { MessageApiInjection } from 'naive-ui/es/message/src/MessageProvider'
import { useAppStore } from '@/stores/app'
import { useVoicesStore } from '@/stores/voices'
import { useTasksStore } from '@/stores/tasks'
import { useApi } from '@/composables/useApi'
import { useI18n } from '@/composables/useI18n'
import { defineAsyncComponent } from 'vue'

const CoverView = defineAsyncComponent(() => import('@/views/CoverViewNew.vue'))
const TtsView = defineAsyncComponent(() => import('@/views/TtsViewNew.vue'))
const TrainView = defineAsyncComponent(() => import('@/views/TrainViewNew.vue'))

const message = inject<MessageApiInjection>('message')
const appStore = useAppStore()
const voicesStore = useVoicesStore()
const tasksStore = useTasksStore()
const api = useApi()
const { t } = useI18n()

const activeTab = ref('cover')
const isProcessing = ref(false)
const showUploadModal = ref(false)
const uploading = ref(false)
const uploadForm = ref({
  name: '',
  description: '',
  modelFile: null as any,
  indexFile: null as any,
})

// ML dependency installation
const mlInstalling = ref(false)
const mlProgress = ref('')
const showInstallMl = computed(() => {
  if (appStore.health.status !== 'online') return false
  const features = (appStore.health as any).features
  if (features?.missing?.some((f: string) => ['covers', 'training'].includes(f))) return true
  if ((appStore.health as any).gpu_upgradeable) return true
  return false
})

const installMlLabel = computed(() => {
  if (mlInstalling.value) return mlProgress.value
  const gpuDet = (appStore.health as any).gpu_detection
  if (gpuDet?.vendor === 'nvidia') return t('installMlDeps') + ' (NVIDIA)'
  if (gpuDet?.vendor === 'amd') return t('installMlDeps') + ' (AMD)'
  return t('installMlDeps')
})

async function installMlDeps() {
  mlInstalling.value = true
  mlProgress.value = t('installingMl')
  try {
    await api.installMlDeps()
    const poll = setInterval(async () => {
      try {
        const status = await api.getMlStatus()
        mlProgress.value = status.progress || t('installingMl')
        if (status.installed || status.error) {
          clearInterval(poll)
          mlInstalling.value = false
          if (status.installed) {
            message?.success(t('mlInstallSuccess'))
            await checkBackendHealth()
          } else if (status.error) {
            message?.error(status.error)
          }
        }
      } catch { /* ignore */ }
    }, 3000)
  } catch (e: any) {
    mlInstalling.value = false
    message?.error('Failed to start installation')
  }
}

const statusClass = computed(() => {
  if (appStore.health.status === 'offline') return 'status-offline'
  if (isProcessing.value) return 'status-processing'
  return 'status-online'
})

const statusText = computed(() => {
  if (appStore.health.status === 'offline') return t('backendOffline')
  if (isProcessing.value) return t('processing')
  return t('backendOnline')
})

function toggleLang() {
  appStore.setLang(appStore.lang === 'zh' ? 'en' : 'zh')
}

function handleProcessingChange(processing: boolean) {
  isProcessing.value = processing
}

function selectVoice(id: string) {
  voicesStore.selectedVoiceId = id
}

function handleModelFileChange(fileList: any[]) {
  uploadForm.value.modelFile = fileList.length > 0 ? fileList[0].file : null
}

function handleIndexFileChange(fileList: any[]) {
  uploadForm.value.indexFile = fileList.length > 0 ? fileList[0].file : null
}

async function handleUploadVoice() {
  if (!uploadForm.value.name || !uploadForm.value.modelFile) {
    message?.error(t('error'))
    return
  }

  uploading.value = true
  try {
    await voicesStore.addVoice({
      name: uploadForm.value.name,
      description: uploadForm.value.description,
      modelFile: uploadForm.value.modelFile,
      indexFile: uploadForm.value.indexFile,
    })
    message?.success(t('uploadSuccess'))
    showUploadModal.value = false
    uploadForm.value = { name: '', description: '', modelFile: null, indexFile: null }
  } catch (error) {
    console.error('Failed to upload voice:', error)
    message?.error(t('uploadFailed'))
  } finally {
    uploading.value = false
  }
}

async function handleDeleteVoice(id: string) {
  try {
    await voicesStore.removeVoice(id)
    message?.success(t('deleteSuccess'))
  } catch (error) {
    console.error('Failed to delete voice:', error)
    message?.error(t('deleteFailed'))
  }
}

function getTaskType(task: any) {
  if (task.type) return task.type
  return 'Cover'
}

function getTaskStatusText(status: string) {
  const texts: Record<string, string> = {
    pending: 'Pending',
    processing: 'Processing',
    completed: 'Done',
    failed: 'Failed'
  }
  return texts[status] || status
}

function downloadTask(taskId: string) {
  const task = tasksStore.getTask(taskId)
  if (task && task.status === 'completed') {
    if (task.type === 'Training') {
      // Training model download
      message?.warning('Training download endpoint not yet implemented. Model ID: ' + taskId)
    } else {
      // Cover/TTS download
      const url = api.getDownloadUrl(taskId)
      window.open(url, '_blank')
    }
  } else {
    message?.error('Task not found or not completed')
  }
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

onMounted(async () => {
  await checkBackendHealth()
  await voicesStore.loadVoices()
  setInterval(checkBackendHealth, 30000)
})
</script>

<style scoped>
.studio-layout {
  display: grid;
  grid-template-columns: 1fr;
  min-height: 100vh;
  background: #0a0a0f;
}

@media (min-width: 1024px) {
  .studio-layout {
    grid-template-columns: 1fr 380px;
  }
}

/* Main Workspace */
.main-workspace {
  padding: 24px;
  max-width: 900px;
  width: 100%;
  margin: 0 auto;
}

@media (min-width: 1024px) {
  .main-workspace {
    padding: 32px;
  }
}

/* Header */
.workspace-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 32px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.studio-logo {
  font-size: 20px;
  font-weight: 600;
  color: #fafafa;
  display: flex;
  align-items: center;
  gap: 10px;
  letter-spacing: -0.01em;
}

.waveform-icon {
  color: #52525b;
  transition: color 300ms ease;
}

.waveform-icon.is-active {
  color: #22c55e;
}

.waveform-icon rect {
  animation-play-state: paused;
}

.waveform-icon.is-active rect {
  animation-play-state: running;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  padding: 6px 12px;
  background: rgba(24, 24, 27, 0.6);
  border: 1px solid #27272a;
  border-radius: 6px;
  backdrop-filter: blur(8px);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #71717a;
  transition: background 300ms ease;
}

.status-online .status-dot {
  background: #22c55e;
  box-shadow: 0 0 8px rgba(34, 197, 94, 0.6);
}

.status-processing .status-dot {
  background: #f59e0b;
  box-shadow: 0 0 8px rgba(245, 158, 11, 0.6);
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.status-offline .status-dot {
  background: #ef4444;
}

.status-text {
  color: #a1a1aa;
  font-weight: 500;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.lang-toggle {
  padding: 6px 12px;
  background: transparent;
  border: 1px solid #27272a;
  border-radius: 6px;
  color: #a1a1aa;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 200ms ease;
  font-family: inherit;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.lang-toggle:hover {
  border-color: #3f3f46;
  color: #fafafa;
  background: rgba(24, 24, 27, 0.4);
}

.ml-install-btn {
  margin-left: 12px;
  padding: 6px 14px;
  border: 1px solid #22c55e;
  border-radius: 6px;
  background: rgba(34, 197, 94, 0.1);
  color: #22c55e;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.ml-install-btn:hover {
  background: rgba(34, 197, 94, 0.2);
  border-color: #16a34a;
}

.ml-install-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Tabs */
.studio-tabs {
  margin-top: 24px;
}

/* Sidebar */
.studio-sidebar {
  border-left: 1px solid #27272a;
  padding: 32px 24px;
  overflow-y: auto;
  max-height: 100vh;
  background: rgba(10, 10, 15, 0.8);
}

@media (max-width: 1023px) {
  .studio-sidebar {
    border-left: none;
    border-top: 1px solid #27272a;
    padding: 24px;
  }
}

.sidebar-section {
  margin-bottom: 32px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #71717a;
}

.add-button {
  padding: 0;
  width: 24px;
  height: 24px;
  min-width: unset;
}

/* Model List */
.model-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.model-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  background: rgba(24, 24, 27, 0.6);
  border: 1px solid #27272a;
  border-radius: 6px;
  cursor: pointer;
  transition: all 200ms ease;
}

.model-item:hover {
  border-color: #3f3f46;
  background: rgba(24, 24, 27, 0.8);
}

.model-info {
  flex: 1;
  min-width: 0;
}

.model-name {
  font-size: 14px;
  font-weight: 500;
  color: #fafafa;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.model-meta {
  font-size: 12px;
  color: #71717a;
  margin-top: 2px;
}

.model-delete {
  padding: 4px;
  background: transparent;
  border: none;
  color: #71717a;
  cursor: pointer;
  transition: color 200ms ease;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
}

.model-delete:hover {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
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

/* Task List */
.task-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.task-list-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.task-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: rgba(24, 24, 27, 0.6);
  border: 1px solid #27272a;
  border-radius: 6px;
  transition: all 200ms ease;
}

.task-item:hover {
  border-color: #3f3f46;
  background: rgba(24, 24, 27, 0.8);
}

.task-info {
  flex: 1;
  min-width: 0;
}

.task-type {
  font-size: 13px;
  font-weight: 500;
  color: #fafafa;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.task-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
}

.status-badge {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.status-pending {
  background: rgba(113, 113, 122, 0.2);
  color: #71717a;
}

.status-processing {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
}

.status-completed {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.status-failed {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.task-progress {
  color: #22c55e;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

/* Upload Modal */
:deep(.upload-modal .n-card) {
  background: rgba(24, 24, 27, 0.98);
  backdrop-filter: blur(16px);
}
</style>
