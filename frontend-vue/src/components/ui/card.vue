<script setup lang="ts">
import { cn } from '@/lib/utils'

defineProps<{
  class?: string
}>()
</script>

<template>
  <div
    :class="cn(
      'rounded-xl border bg-card/50 backdrop-blur-xl text-card-foreground shadow',
      $props.class
    )"
  >
    <slot />
  </div>
</template>
