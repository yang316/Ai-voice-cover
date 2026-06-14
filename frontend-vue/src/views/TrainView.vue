<template>
  <div class="space-y-4">
    <Card>
      <CardHeader>
        <CardTitle>{{ t('tabTrain') }}</CardTitle>
      </CardHeader>
      <CardContent class="space-y-4">
        <!-- Model Name -->
        <div class="space-y-2">
          <Label>模型名称</Label>
          <Input v-model="modelName" placeholder="my_voice" />
        </div>

        <!-- Upload Training Audio -->
        <div class="space-y-2">
          <Label>上传训练音频</Label>
          <div
            :class="[
              'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
              isDragover ? 'border-primary bg-primary/5' : 'border-input',
              files.length > 0 ? 'border-green-500 bg-green-500/5' : ''
            ]"
            @click="triggerFileInput"
            @dragover.prevent="isDragover = true"
            @dragleave.prevent="isDragover = false"
            @drop.prevent="handleDrop"
          >
            <input
              ref="fileInput"
              type="file"
              accept="audio/*"
              multiple
              class="hidden"
              @change="handleFileChange"
            />
            <Upload class="h-10 w-10 mx-auto mb-2 text-muted-foreground" />
            <p class="text-sm text-muted-foreground">
              <strong class="text-foreground">点击上传</strong> 或拖放文件
            </p>
            <p class="text-xs text-muted-foreground mt-1">
              支持多个音频文件，建议每个 5-15 秒
            </p>
          </div>

          <!-- File List -->
          <div v-if="files.length > 0" class="space-y-2">
            <div
              v-for="(file, index) in files"
              :key="index"
              class="flex items-center justify-between p-2 rounded-md bg-muted/50"
            >
              <div class="flex items-center gap-2 min-w-0">
                <Music class="h-4 w-4 text-muted-foreground flex-shrink-0" />
                <span class="text-sm truncate">{{ file.name }}</span>
              </div>
              <Button
                variant="ghost"
                size="icon"
                @click="removeFile(index)"
              >
                <X class="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>

        <!-- Training Parameters -->
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-2">
            <Label>训练轮次</Label>
            <Input v-model.number="epochs" type="number" min="10" max="1000" />
          </div>
          <div class="space-y-2">
            <Label>批次大小</Label>
            <Input v-model.number="batchSize" type="number" min="1" max="32" />
          </div>
        </div>

        <Button
          class="w-full"
          :disabled="!canSubmit"
          :loading="isTraining"
          @click="handleStartTraining"
        >
          <Zap class="h-4 w-4" />
          开始训练
        </Button>

        <!-- Training Progress -->
        <div v-if="isTraining" class="space-y-3 p-4 rounded-lg bg-muted/50">
          <div class="flex items-center justify-between">
            <span class="text-sm font-medium">{{ trainingStatus }}</span>
            <span class="text-sm font-bold text-primary">{{ trainingProgress }}%</span>
          </div>
          <div class="h-2 bg-muted rounded-full overflow-hidden">
            <div
              class="h-full bg-gradient-to-r from-primary to-purple-600 transition-all duration-300"
              :style="{ width: `${trainingProgress}%` }"
            />
          </div>
          <div class="grid grid-cols-3 gap-2 text-center">
            <div class="p-2 rounded-md bg-background/50">
              <div class="text-lg font-bold text-primary">{{ currentEpoch }}</div>
              <div class="text-xs text-muted-foreground">Epoch</div>
            </div>
            <div class="p-2 rounded-md bg-background/50">
              <div class="text-lg font-bold text-primary">{{ loss }}</div>
              <div class="text-xs text-muted-foreground">Loss</div>
            </div>
            <div class="p-2 rounded-md bg-background/50">
              <div class="text-lg font-bold text-primary">{{ eta }}</div>
              <div class="text-xs text-muted-foreground">预计剩余</div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- Training History -->
    <Card>
      <CardHeader>
        <CardTitle>训练记录</CardTitle>
      </CardHeader>
      <CardContent>
        <div v-if="trainingHistory.length === 0" class="text-center py-8 text-muted-foreground">
          <History class="h-10 w-10 mx-auto mb-2 opacity-50" />
          <p>暂无训练记录</p>
        </div>
        <div v-else class="space-y-2">
          <div
            v-for="record in trainingHistory"
            :key="record.id"
            class="flex items-center justify-between p-3 rounded-lg border"
          >
            <div class="flex-1 min-w-0">
              <div class="font-medium">{{ record.modelName }}</div>
              <div class="text-sm text-muted-foreground">
                {{ record.date }} • {{ record.epochs }} epochs
              </div>
            </div>
            <div :class="[
              'px-2 py-1 rounded text-xs font-medium',
              record.status === 'completed' ? 'bg-green-500/10 text-green-500' :
              record.status === 'failed' ? 'bg-red-500/10 text-red-500' :
              'bg-yellow-500/10 text-yellow-500'
            ]">
              {{ record.status }}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Upload, Music, X, Zap, History } from 'lucide-vue-next'
// import { useApi } from '@/composables/useApi' // TODO: 实现训练 API
import { useToast } from '@/composables/useToast'
import { useI18n } from '@/composables/useI18n'
import Card from '@/components/ui/card.vue'
import CardHeader from '@/components/ui/card-header.vue'
import CardTitle from '@/components/ui/card-title.vue'
import CardContent from '@/components/ui/card-content.vue'
import Button from '@/components/ui/button.vue'
import Input from '@/components/ui/input.vue'
import Label from '@/components/ui/label.vue'

// const api = useApi() // TODO: 实现训练 API 调用
const toast = useToast()
const { t } = useI18n()

const modelName = ref('')
const files = ref<File[]>([])
const epochs = ref(200)
const batchSize = ref(4)
const isDragover = ref(false)
const fileInput = ref<HTMLInputElement>()

const isTraining = ref(false)
const trainingStatus = ref('准备中...')
const trainingProgress = ref(0)
const currentEpoch = ref(0)
const loss = ref('-')
const eta = ref('-')

const trainingHistory = ref<Array<{
  id: string
  modelName: string
  date: string
  epochs: number
  status: 'completed' | 'failed' | 'training'
}>>([])

const canSubmit = computed(() => {
  return modelName.value.trim() && files.value.length > 0 && !isTraining.value
})

function triggerFileInput() {
  fileInput.value?.click()
}

function handleFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  if (target.files) {
    files.value.push(...Array.from(target.files))
  }
}

function handleDrop(e: DragEvent) {
  isDragover.value = false
  if (e.dataTransfer?.files) {
    files.value.push(...Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('audio/')))
  }
}

function removeFile(index: number) {
  files.value.splice(index, 1)
}

async function handleStartTraining() {
  if (!canSubmit.value) return

  isTraining.value = true
  trainingProgress.value = 0
  trainingStatus.value = '正在训练...'

  try {
    // TODO: 实现训练 API 调用
    // const result = await api.trainModel({
    //   modelName: modelName.value,
    //   audioFiles: files.value,
    //   epochs: epochs.value,
    //   batchSize: batchSize.value,
    // })

    // 模拟训练进度
    const interval = setInterval(() => {
      if (trainingProgress.value < 100) {
        trainingProgress.value += 5
        currentEpoch.value = Math.floor((trainingProgress.value / 100) * epochs.value)
        loss.value = (Math.random() * 0.5 + 0.1).toFixed(3)
        eta.value = `${Math.floor((100 - trainingProgress.value) / 5)}分钟`
      } else {
        clearInterval(interval)
        isTraining.value = false
        toast.success('模型训练完成！')

        // 添加到历史记录
        trainingHistory.value.unshift({
          id: Date.now().toString(),
          modelName: modelName.value,
          date: new Date().toLocaleDateString('zh-CN'),
          epochs: epochs.value,
          status: 'completed',
        })

        // 重置表单
        modelName.value = ''
        files.value = []
      }
    }, 1000)
  } catch (error) {
    console.error('Failed to train model:', error)
    toast.error('训练失败')
    isTraining.value = false
  }
}
</script>
