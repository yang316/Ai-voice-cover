<template>
  <div class="space-y-4">
    <Card>
      <CardHeader>
        <CardTitle>{{ t('tabTts') }}</CardTitle>
      </CardHeader>
      <CardContent class="space-y-4">
        <!-- Text Input -->
        <div class="space-y-2">
          <Label>输入文字</Label>
          <textarea
            v-model="text"
            rows="4"
            placeholder="输入要合成的文字..."
            class="flex min-h-[80px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          />
        </div>

        <!-- Voice Selection -->
        <div class="space-y-2">
          <Label>选择语音</Label>
          <div class="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto p-1">
            <button
              v-for="voice in voicesStore.voices"
              :key="voice.id"
              :class="[
                'p-3 text-left rounded-lg border transition-all',
                selectedVoiceId === voice.id
                  ? 'border-primary bg-primary/10'
                  : 'border-input hover:border-primary/50'
              ]"
              @click="selectedVoiceId = voice.id"
            >
              <div class="font-medium text-sm">{{ voice.name }}</div>
              <div v-if="voice.description" class="text-xs text-muted-foreground truncate">
                {{ voice.description }}
              </div>
            </button>
          </div>
        </div>

        <!-- Speed Control -->
        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <Label>语速</Label>
            <span class="text-sm font-medium text-primary">{{ speed[0] }}x</span>
          </div>
          <Slider v-model="speed" :min="0.5" :max="2" :step="0.1" />
        </div>

        <!-- Pitch Control -->
        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <Label>音调</Label>
            <span class="text-sm font-medium text-primary">{{ pitch[0] }}</span>
          </div>
          <Slider v-model="pitch" :min="-1" :max="1" :step="0.1" />
        </div>

        <Button
          class="w-full"
          :disabled="!canSubmit"
          :loading="isProcessing"
          @click="handleGenerate"
        >
          <Mic class="h-4 w-4" />
          生成语音
        </Button>

        <!-- Result Audio -->
        <div v-if="resultUrl" class="space-y-2">
          <Label>生成结果</Label>
          <div class="rounded-lg border bg-muted/50 p-4">
            <audio :src="resultUrl" controls preload="metadata" class="w-full"></audio>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Mic } from 'lucide-vue-next'
import { useVoicesStore } from '@/stores/voices'
// import { useApi } from '@/composables/useApi' // TODO: 实现 TTS API
import { useToast } from '@/composables/useToast'
import { useI18n } from '@/composables/useI18n'
import Card from '@/components/ui/card.vue'
import CardHeader from '@/components/ui/card-header.vue'
import CardTitle from '@/components/ui/card-title.vue'
import CardContent from '@/components/ui/card-content.vue'
import Button from '@/components/ui/button.vue'
import Label from '@/components/ui/label.vue'
import Slider from '@/components/ui/slider.vue'

const voicesStore = useVoicesStore()
// const api = useApi() // TODO: 实现 TTS API 调用
const toast = useToast()
const { t } = useI18n()

const text = ref('')
const selectedVoiceId = ref('')
const speed = ref([1.0])
const pitch = ref([0])
const isProcessing = ref(false)
const resultUrl = ref('')

const canSubmit = computed(() => {
  return text.value.trim() && selectedVoiceId.value && !isProcessing.value
})

async function handleGenerate() {
  if (!canSubmit.value) return

  isProcessing.value = true
  try {
    // TODO: 实现 TTS API 调用
    // const result = await api.generateTTS({
    //   text: text.value,
    //   voiceId: selectedVoiceId.value,
    //   speed: speed.value[0],
    //   pitch: pitch.value[0],
    // })
    // resultUrl.value = result.audioUrl

    toast.success('语音生成成功！')
  } catch (error) {
    console.error('Failed to generate TTS:', error)
    toast.error('语音生成失败')
  } finally {
    isProcessing.value = false
  }
}
</script>
