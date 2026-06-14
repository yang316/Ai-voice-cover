<template>
  <div
    :class="[
      'upload-zone',
      { 'upload-zone--dragover': isDragover, 'upload-zone--has-file': !!selectedFile }
    ]"
    @click="triggerFileInput"
    @dragover.prevent="isDragover = true"
    @dragleave.prevent="isDragover = false"
    @drop.prevent="handleDrop"
  >
    <input
      ref="fileInput"
      type="file"
      :accept="accept"
      @change="handleFileChange"
      style="display: none"
    />

    <svg class="upload-zone__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
      <path d="M9 18V5l12-2v13"/>
      <circle cx="6" cy="18" r="3"/>
      <circle cx="18" cy="16" r="3"/>
    </svg>

    <p class="upload-zone__text">
      <strong>{{ clickText }}</strong> {{ dragText }}<br>
      <span style="font-size: 0.875rem; color: hsl(240, 5%, 64.9%)">{{ hint }}</span>
    </p>

    <div v-if="selectedFile" class="upload-zone__filename">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
        <polyline points="22 4 12 14.01 9 11.01"/>
      </svg>
      {{ selectedFile.name }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = withDefaults(defineProps<{
  accept?: string
  clickText?: string
  dragText?: string
  hint?: string
}>(), {
  accept: 'audio/*',
  clickText: 'Click to upload',
  dragText: 'or drag and drop',
  hint: 'MP3, WAV, FLAC, OGG up to 50MB',
})

const emit = defineEmits<{
  'file-selected': [file: File]
}>()

const fileInput = ref<HTMLInputElement>()
const selectedFile = ref<File | null>(null)
const isDragover = ref(false)

function triggerFileInput() {
  fileInput.value?.click()
}

function handleFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) {
    selectedFile.value = file
    emit('file-selected', file)
  }
}

function handleDrop(e: DragEvent) {
  isDragover.value = false
  const file = e.dataTransfer?.files[0]
  if (file && file.type.startsWith('audio/')) {
    selectedFile.value = file
    emit('file-selected', file)
  }
}
</script>

<style scoped>
.upload-zone {
  border: 2px dashed hsl(240, 3.7%, 15.9%);
  border-radius: 0.75rem;
  padding: 2.5rem 1.5rem;
  text-align: center;
  cursor: pointer;
  transition: all 200ms ease;
  position: relative;
}

.upload-zone:hover,
.upload-zone--dragover {
  border-color: hsl(263, 70%, 50.4%);
  background: hsla(263, 70%, 50.4%, 0.05);
}

.upload-zone--dragover {
  transform: scale(1.01);
}

.upload-zone--has-file {
  border-color: hsl(142, 71%, 45%);
  background: hsla(142, 71%, 45%, 0.05);
}

.upload-zone__icon {
  width: 48px;
  height: 48px;
  margin: 0 auto 0.75rem;
  opacity: 0.5;
  stroke: currentColor;
}

.upload-zone__text {
  font-size: 0.875rem;
  color: hsl(240, 5%, 64.9%);
}

.upload-zone__text strong {
  color: hsl(0, 0%, 98%);
}

.upload-zone__filename {
  font-size: 0.8125rem;
  font-weight: 500;
  color: hsl(142, 71%, 45%);
  margin-top: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
}
</style>
