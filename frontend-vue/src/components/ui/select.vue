<script setup lang="ts">
import { SelectContent, SelectGroup, SelectPortal, SelectRoot, SelectTrigger, SelectValue, SelectViewport } from 'radix-vue'
import { ChevronDown } from 'lucide-vue-next'
import { cn } from '@/lib/utils'

const modelValue = defineModel<string>()
</script>

<template>
  <SelectRoot v-model="modelValue">
    <SelectTrigger
      :class="cn(
        'flex h-9 w-full items-center justify-between whitespace-nowrap rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50 [&>span]:line-clamp-1'
      )"
    >
      <SelectValue placeholder="Select an option" />
      <ChevronDown class="h-4 w-4 opacity-50" />
    </SelectTrigger>

    <SelectPortal>
      <SelectContent
        position="popper"
        :side-offset="4"
        :align="'start'"
        :class="cn(
          'relative z-50 max-h-96 min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-md border bg-popover text-popover-foreground shadow-md data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2'
        )"
      >
        <SelectViewport class="p-1">
          <SelectGroup>
            <slot />
          </SelectGroup>
        </SelectViewport>
      </SelectContent>
    </SelectPortal>
  </SelectRoot>
</template>
