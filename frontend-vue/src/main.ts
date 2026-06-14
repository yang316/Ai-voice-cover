import { createApp } from 'vue'
import { createPinia } from 'pinia'
import AppWrapper from './AppWrapper.vue'
import './style.css'

// Naive UI - 直接全局注册不需要 app.use()
// 只需要在组件中通过 Provider 包裹

const app = createApp(AppWrapper)
const pinia = createPinia()

app.use(pinia)
app.mount('#app')
