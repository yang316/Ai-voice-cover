<template>
  <Teleport to="body">
    <div class="toast-container">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          :class="['toast', `toast--${toast.type}`]"
        >
          {{ toast.message }}
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useToast } from '@/composables/useToast'

const { toasts } = useToast()
</script>

<style scoped>
.toast-container {
  position: fixed;
  bottom: 1.5rem;
  right: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  z-index: 100;
  pointer-events: none;
}

.toast {
  padding: 0.75rem 1rem;
  background: hsl(240, 10%, 3.9%);
  border: 1px solid hsl(240, 3.7%, 15.9%);
  border-radius: 0.75rem;
  font-size: 0.8125rem;
  color: hsl(0, 0%, 98%);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  pointer-events: auto;
  max-width: 340px;
}

.toast--error {
  border-color: hsla(0, 62.8%, 50%, 0.3);
}

.toast--success {
  border-color: hsla(142, 71%, 45%, 0.3);
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(24px);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(24px);
}
</style>
