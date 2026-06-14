<template>
  <div class="space-y-4">
    <!-- Upload Card -->
    <Card>
      <CardHeader>
        <CardTitle>{{ t('uploadAudio') }}</CardTitle>
      </CardHeader>
      <CardContent>
        <UploadZone
          :click-text="t('clickToUpload')"
          :drag-text="t('dragAndDrop')"
          :hint="t('supportedFormats')"
          @file-selected="handleFileSelected"
        />
      </CardContent>
    </Card>

    <!-- Settings Card -->
    <Card>
      <CardHeader>
        <CardTitle>{{ t('settings') }}</CardTitle>
      </CardHeader>
      <CardContent class="space-y-4">
        <!-- Voice Model -->
        <div class="space-y-2">
          <Label>{{ t('voiceModel') }}</Label>
          <Select v-model="selectedVoiceId" :disabled="voicesStore.loading">
            <SelectItem v-if="voicesStore.voices.length === 0" value="none" disabled>
              {{ voicesStore.loading ? t('loadingVoices') : t('noVoices') }}...
            </SelectItem>
            <SelectItem
              v-for="voice in voicesStore.voices"
              :key="voice.id"
              :value="voice.id"
            >
              {{ voice.name }}
            </SelectItem>
          </Select>
        </div>

        <!-- Compute Backend -->
        <div class="space-y-2">
          <Label>{{ t('computeBackend') }}</Label>
          <Select v-model="appStore.backend">
            <SelectItem value="local">{{ t('backendLocal') }}</SelectItem>
            <SelectItem value="gpt_sovits">{{ t('backendGptSovits') }}</SelectItem>
            <SelectItem value="elevenlabs">{{ t('backendElevenLabs') }}</SelectItem>
            <SelectItem value="fish_audio">{{ t('backendFishAudio') }}</SelectItem>
          </Select>
        </div>

        <!-- API Key (conditional) -->
        <div v-if="appStore.needsApiKey" class="space-y-2">
          <Label>{{ t('apiKey') }}</Label>
          <Input
            v-model="appStore.apiKey"
            type="password"
            :placeholder="t('apiKeyPlaceholder')"
          />
          <p class="text-xs text-muted-foreground">{{ t('apiKeyHint') }}</p>
        </div>

        <!-- GPT-SoVITS URL -->
        <div v-if="appStore.backend === 'gpt_sovits'" class="space-y-2">
          <Label>{{ t('gptSovitsUrl') }}</Label>
          <Input
            v-model="appStore.gptSovitsUrl"
            placeholder="http://127.0.0.1:9880"
          />
        </div>

        <!-- Pitch Shift -->
        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <Label>{{ t('pitchShift') }}</Label>
            <span class="text-sm font-medium text-primary">{{ pitchShift[0] }} st</span>
          </div>
          <Slider v-model="pitchShift" :min="-12" :max="12" :step="1" />
          <div class="flex justify-between text-xs text-muted-foreground">
            <span>-12</span>
            <span>0</span>
            <span>+12</span>
          </div>
        </div>

        <!-- Noise Reduction Toggle -->
        <div class="flex items-center justify-between">
          <Label>{{ t('noiseReduction') }}</Label>
          <Switch v-model="denoise" />
        </div>

        <div class="border-t pt-4">
          <Button
            class="w-full"
            size="lg"
            :disabled="!canSubmit"
            @click="handleCreateCover"
          >
            <Play v-if="!isProcessing" class="h-4 w-4" />
            {{ t('createCover') }}
          </Button>
        </div>

        <!-- Progress Pipeline -->
        <Pipeline
          :visible="isProcessing"
          :current-step="currentStep"
          :progress="progress"
          :status-text="statusText"
        />
      </CardContent>
    </Card>

    <!-- Result Card -->
    <Card v-if="resultUrl">
      <CardHeader>
        <CardTitle>{{ t('result') }}</CardTitle>
      </CardHeader>
      <CardContent class="space-y-4">
        <div class="rounded-lg border bg-muted/50 p-4">
          <audio :src="resultUrl" controls preload="metadata" class="w-full"></audio>
        </div>
        <div class="grid grid-cols-2 gap-2">
          <Button @click="downloadResult">
            <Download class="h-4 w-4" />
            {{ t('download') }}
          </Button>
          <Button variant="secondary" @click="resetForm">
            <Plus class="h-4 w-4" />
            {{ t('newCover') }}
          </Button>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Play, Download, Plus } from 'lucide-vue-next'
import { useAppStore } from '@/stores/app'
import { useVoicesStore } from '@/stores/voices'
import { useTasksStore } from '@/stores/tasks'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { useI18n } from '@/composables/useI18n'
import Card from '@/components/ui/card.vue'
import CardHeader from '@/components/ui/card-header.vue'
import CardTitle from '@/components/ui/card-title.vue'
import CardContent from '@/components/ui/card-content.vue'
import Button from '@/components/ui/button.vue'
import Input from '@/components/ui/input.vue'
import Label from '@/components/ui/label.vue'
import Select from '@/components/ui/select.vue'
import SelectItem from '@/components/ui/select-item.vue'
import Switch from '@/components/ui/switch.vue'
import Slider from '@/components/ui/slider.vue'
import UploadZone from '@/components/UploadZone.vue'
import Pipeline from '@/components/Pipeline.vue'

const appStore = useAppStore()
const voicesStore = useVoicesStore()
const tasksStore = useTasksStore()
const api = useApi()
const toast = useToast()
const { t } = useI18n()

// Form state
const selectedFile = ref<File | null>(null)
const selectedVoiceId = computed({
  get: () => voicesStore.selectedVoiceId,
  set: (val) => { voicesStore.selectedVoiceId = val }
})
const pitchShift = ref([0])
const denoise = ref(true)

// Processing state
const isProcessing = ref(false)
const currentStep = ref<'separating' | 'converting' | 'mixing' | 'complete'>('separating')
const progress = ref(0)
const statusText = ref('')
const resultUrl = ref('')
const currentTaskId = ref('')

const canSubmit = computed(() => {
  return selectedFile.value && selectedVoiceId.value && !isProcessing.value
})

function handleFileSelected(file: File) {
  selectedFile.value = file
}

async function handleCreateCover() {
  if (!selectedFile.value || !selectedVoiceId.value) return

  isProcessing.value = true
  progress.value = 0
  currentStep.value = 'separating'
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

    currentTaskId.value = task.id
    tasksStore.addTask(task)

    // Poll for task status
    pollTaskStatus(task.id)

    toast.success(t('coverCreated'))
  } catch (error) {
    console.error('Failed to create cover:', error)
    toast.error(t('taskFailed'))
    isProcessing.value = false
  }
}

async function pollTaskStatus(taskId: string) {
  const poll = async () => {
    try {
      const task = await api.getTaskStatus(taskId)
      tasksStore.updateTask(taskId, task)

      currentStep.value = task.step
      progress.value = task.progress

      if (task.status === 'completed') {
        isProcessing.value = false
        currentStep.value = 'complete'
        progress.value = 100
        statusText.value = t('complete')
        resultUrl.value = api.getDownloadUrl(taskId)
      } else if (task.status === 'failed') {
        isProcessing.value = false
        toast.error(task.error || t('taskFailed'))
      } else if (task.status === 'processing') {
        setTimeout(poll, 2000)
      }
    } catch (error) {
      console.error('Failed to poll task status:', error)
      isProcessing.value = false
      toast.error(t('error'))
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
