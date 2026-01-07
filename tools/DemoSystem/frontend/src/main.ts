import {createApp} from 'vue'
import './style.css'
import App from './App.vue'
import router from "@/router/index.ts"
import 'element-plus/dist/index.css';
import "@/style/element/index.css"

const app = createApp(App);
app.use(router);
app.config.globalProperties.$app = {
    version: import.meta.env.VITE_APP_VERSION || '1.0.0',
}

// 全局错误处理
app.config.errorHandler = (err, instance, info) => {
    console.error('全局错误:', err)
    console.log('组件实例:', instance)
    console.log('错误信息:', info)
}

app.mount('#app');
