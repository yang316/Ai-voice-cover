<template>
  <div v-if="visible" class="pipeline">
    <div class="pipeline__steps">
      <div
        v-for="(step, index) in steps"
        :key="step.id"
        :class="[
          'pipeline__step',
          { 'pipeline__step--active': currentStep === step.id },
          { 'pipeline__step--done': isDone(step.id) }
        ]"
      >
        <div class="pipeline__step-dot">
          <component :is="step.icon" />
        </div>
        <span class="pipeline__step-label">{{ step.label }}</span>

        <div v-if="index < steps.length - 1" class="pipeline__connector" :class="{ 'pipeline__connector--done': isDone(step.id) }" />
      </div>
    </div>

    <div class="progress-bar__wrapper">
      <div class="progress-bar__header">
        <span>{{ statusText }}</span>
        <span>{{ progress }}%</span>
      </div>
      <div class="progress-bar">
        <div class="progress-bar__fill" :style="{ width: `${progress}%` }" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { h } from 'vue'

const props = defineProps<{
  visible: boolean
  currentStep: 'separating' | 'converting' | 'mixing' | 'complete'
  progress: number
  statusText?: string
}>()

const steps = [
  {
    id: 'separating',
    label: 'Separating',
    icon: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('path', { d: 'M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z' })
    ])
  },
  {
    id: 'converting',
    label: 'Converting',
    icon: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('path', { d: 'M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83' })
    ])
  },
  {
    id: 'mixing',
    label: 'Mixing',
    icon: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('path', { d: 'M9 18V5l12-2v13' }),
      h('circle', { cx: '6', cy: '18', r: '3' }),
      h('circle', { cx: '18', cy: '16', r: '3' })
    ])
  }
]

const stepOrder = ['separating', 'converting', 'mixing', 'complete']

function isDone(stepId: string) {
  const currentIndex = stepOrder.indexOf(props.currentStep)
  const stepIndex = stepOrder.indexOf(stepId)
  return stepIndex < currentIndex || props.currentStep === 'complete'
}
</script>

<style scoped>
.pipeline {
  margin-top: 1rem;
}

.pipeline__steps {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  margin-bottom: 0.75rem;
  position: relative;
}

.pipeline__step {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.375rem;
  position: relative;
}

.pipeline__step-dot {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: hsl(240, 3.7%, 15.9%);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 300ms ease;
  z-index: 1;
}

.pipeline__step-dot svg {
  width: 16px;
  height: 16px;
  color: hsl(240, 5%, 64.9%);
  transition: color 200ms ease;
}

.pipeline__step--active .pipeline__step-dot {
  background: linear-gradient(135deg, #667eea, #764ba2);
  box-shadow: 0 0 12px rgba(102, 126, 234, 0.4);
  animation: pulse 2s infinite;
}

.pipeline__step--active .pipeline__step-dot svg {
  color: white;
  animation: spin 1.5s linear infinite;
}

.pipeline__step--done .pipeline__step-dot {
  background: hsl(142, 71%, 45%);
}

.pipeline__step--done .pipeline__step-dot svg {
  color: white;
}

.pipeline__step-label {
  font-size: 0.6875rem;
  color: hsl(240, 5%, 64.9%);
  font-weight: 500;
  text-transform: capitalize;
  transition: color 200ms ease;
}

.pipeline__step--active .pipeline__step-label {
  color: hsl(0, 0%, 98%);
}

.pipeline__step--done .pipeline__step-label {
  color: hsl(142, 71%, 45%);
}

.pipeline__connector {
  position: absolute;
  left: calc(50% + 16px);
  right: calc(-50% + 16px);
  top: 16px;
  height: 2px;
  background: hsl(240, 3.7%, 15.9%);
  transition: background 300ms ease;
}

.pipeline__connector--done {
  background: hsl(142, 71%, 45%);
}

.progress-bar__wrapper {
  margin-top: 0.75rem;
}

.progress-bar__header {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: hsl(240, 5%, 64.9%);
  margin-bottom: 0.375rem;
}

.progress-bar {
  height: 6px;
  background: hsl(240, 3.7%, 15.9%);
  border-radius: 3px;
  overflow: hidden;
}

.progress-bar__fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  border-radius: 3px;
  transition: width 400ms ease;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.8; }
}
</style>
