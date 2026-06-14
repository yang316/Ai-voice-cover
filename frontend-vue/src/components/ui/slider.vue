<script setup lang="ts">
import { SliderRange, SliderRoot, SliderThumb, SliderTrack } from 'radix-vue'
import { cn } from '@/lib/utils'

const modelValue = defineModel<number[]>({
  default: [0],
})

defineProps<{
  max?: number
  min?: number
  step?: number
  disabled?: boolean
  class?: string
}>()
</script>

<template>
  <SliderRoot
    v-model="modelValue"
    :max="max"
    :min="min"
    :step="step"
    :disabled="disabled"
    :class="cn(
      'relative flex w-full touch-none select-none items-center',
      $props.class
    )"
  >
    <SliderTrack class="relative h-1.5 w-full grow overflow-hidden rounded-full bg-primary/20">
      <SliderRange class="absolute h-full bg-primary" />
    </SliderTrack>
    <SliderThumb
      v-for="(_, index) in modelValue"
      :key="index"
      class="block h-4 w-4 rounded-full border border-primary/50 bg-background shadow transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50"
    />
  </SliderRoot>
</template>
