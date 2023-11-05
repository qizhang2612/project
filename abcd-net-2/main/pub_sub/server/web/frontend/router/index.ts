import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import PubSub from '../views/PubSub.vue'
import Sub from '../views/Sub.vue'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'PubSub',
    component: PubSub
  },
  {
    path: '/sub',
    name: 'Sub',
    component: Sub
  },
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
})

export default router
