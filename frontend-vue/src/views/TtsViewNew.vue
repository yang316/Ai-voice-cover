<template>
  <div class="tts-workspace">
    <!-- Text Input -->
    <div class="glass-card">
      <div class="card-header">
        <svg class="card-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/>
          <path d="M19 10v2a7 7 0 01-14 0v-2"/>
        </svg>
        <h2 class="card-title">{{ t('ttsTitle') }}</h2>
      </div>

      <n-form label-placement="top" class="studio-form">
        <n-form-item :label="t('enterText')">
          <n-input
            v-model:value="text"
            type="textarea"
            :placeholder="t('textPlaceholder')"
            :rows="4"
          />
        </n-form-item>

        <n-form-item :label="t('selectVoice')">
          <n-select
            v-model:value="selectedVoiceId"
            :options="voiceOptions"
            :loading="voicesStore.loading"
            :placeholder="t('selectVoice')"
          />
        </n-form-item>

        <div class="params-grid">
          <n-form-item :label="`${t('speed')} (${speed.toFixed(1)}x)`">
            <n-slider
              v-model:value="speed"
              :min="0.5"
              :max="2.0"
              :step="0.1"
              :marks="{ 0.5: '0.5x', 1.0: '1.0x', 2.0: '2.0x' }"
            />
          </n-form-item>

          <n-form-item :label="`${t('pitch')} (${pitch})`">
            <n-slider
              v-model:value="pitch"
              :min="-12"
              :max="12"
              :step="1"
              :marks="{ '-12': '-12', '0': '0', '12': '+12' }"
            />
          </n-form-item>
        </div>

        <n-divider style="margin: 20px 0" />

        <n-button
          type="primary"
          size="large"
          block
          :disabled="!canSubmit"
          :loading="isGenerating"
          @click="handleGenerate"
          class="action-button"
        >
          <template #icon>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
          </template>
          {{ t('generateSpeech') }}
        </n-button>

        <!-- Progress -->
        <div v-if="isGenerating" class="progress-section">
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
          <n-button @click="reset">
            {{ t('reset') }}
          </n-button>
        </n-space>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, inject, watch } from 'vue'
import { NForm, NFormItem, NInput, NSelect, NSlider, NButton, NProgress, NSpace, NDivider } from 'naive-ui'
import type { MessageApiInjection } from 'naive-ui/es/message/src/MessageProvider'
import { useVoicesStore } from '@/stores/voices'
import { useI18n } from '@/composables/useI18n'

const emit = defineEmits(['processing-change'])

const message = inject<MessageApiInjection>('message')
const voicesStore = useVoicesStore()
const { t } = useI18n()

const text = ref('')
const selectedVoiceId = ref('')
const speed = ref(1.0)
const pitch = ref(0)
const isGenerating = ref(false)
const progress = ref(0)
const statusText = ref('')
const resultUrl = ref('')

const canSubmit = computed(() => {
  return text.value.trim() && selectedVoiceId.value && !isGenerating.value
})

const voiceOptions = computed(() => {
  return voicesStore.voices.map(v => ({
    label: v.name,
    value: v.id
  }))
})

watch(isGenerating, (val) => {
  emit('processing-change', val)
})

async function handleGenerate() {
  if (!canSubmit.value) return

  isGenerating.value = true
  progress.value = 0
  statusText.value = t('processing')
  resultUrl.value = ''

  try {
    // TODO: Call TTS API
    // Simulate for now
    const interval = setInterval(() => {
      progress.value += 10
      if (progress.value >= 100) {
        clearInterval(interval)
        isGenerating.value = false
        statusText.value = t('complete')
        resultUrl.value = '/api/v1/tts/result/demo.wav'
        message?.success(t('success'))
      }
    }, 300)
  } catch (error) {
    console.error('Failed to generate:', error)
    message?.error(t('error'))
    isGenerating.value = false
  }
}

function downloadResult() {
  if (resultUrl.value) {
    window.open(resultUrl.value, '_blank')
  }
}

function reset() {
  text.value = ''
  resultUrl.value = ''
  progress.value = 0
  isGenerating.value = false
}
</script>

<style scoped>
.tts-workspace {
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
