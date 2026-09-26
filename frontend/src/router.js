import { createRouter, createWebHistory } from 'vue-router'
import { getSetupStatus, getToken } from './api.js'
import Login from './views/Login.vue'
import Dashboard from './views/Dashboard.vue'
import Setup from './views/Setup.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/setup', component: Setup },
    { path: '/login', component: Login },
    { path: '/admin', redirect: '/' },
    { path: '/', component: Dashboard },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

let cachedSetupDone = null

export function markSetupDone() {
  cachedSetupDone = true
}

router.beforeEach(async (to) => {
  if (cachedSetupDone === null) {
    try {
      const s = await getSetupStatus()
      cachedSetupDone = !!s.setup_done
    } catch {
      cachedSetupDone = true
    }
  }

  // 1. 系统未初始化：除 /setup 外一律重定向至 /setup
  if (!cachedSetupDone) {
    if (to.path !== '/setup') return '/setup'
    return
  }

  // 2. 系统已初始化：禁止访问 /setup
  if (to.path === '/setup') {
    return getToken() ? '/' : '/login'
  }

  // 3. 常规登录鉴权
  if (to.path !== '/login' && !getToken()) return '/login'
  if (to.path === '/login' && getToken()) return '/'
})

export default router
