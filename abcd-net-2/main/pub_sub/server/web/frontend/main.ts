import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import store from './store'
import Antd from 'ant-design-vue';
import 'ant-design-vue/dist/antd.css';
import * as Icons from '@ant-design/icons-vue'
import axios from 'axios'

axios.defaults.baseURL = process.env.VUE_APP_SERVER

axios.interceptors.request.use(
    config => {
        console.log('请求参数', config)
        return config
    }
)
axios.interceptors.response.use(
    response => {
        console.log('返回结果', response)
        return response
    },error => {
        return Promise.reject(error)
    }
)

const app = createApp(App).use(store).use(router).use(Antd);
app.mount('#app')

const icons: any = Icons;
for (const i in icons) {
    app.component(i, icons[i]);
}

console.log('env: ', process.env.NODE_ENV)
console.log('server: ', process.env.VUE_APP_SERVER)
