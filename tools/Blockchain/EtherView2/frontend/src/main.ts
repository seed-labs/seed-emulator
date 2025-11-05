import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import '@/style/reset.scss'
import 'element-plus/dist/index.css';
import pinia from '@/store';

const app = createApp(App)
app.use(router)
app.use(pinia)
app.mount('#app')