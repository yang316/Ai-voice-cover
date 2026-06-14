import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { Task } from '@/types/api'

export const useTasksStore = defineStore('tasks', () => {
  const tasks = ref<Task[]>([])

  function addTask(task: Task) {
    tasks.value.unshift(task)
  }

  function updateTask(id: string, updates: Partial<Task>) {
    const index = tasks.value.findIndex(t => t.id === id)
    if (index !== -1) {
      tasks.value[index] = { ...tasks.value[index], ...updates }
    }
  }

  function getTask(id: string) {
    return tasks.value.find(t => t.id === id)
  }

  return {
    tasks,
    addTask,
    updateTask,
    getTask,
  }
})
