<template>
  <div class="min-h-screen bg-gray-100 text-gray-800">
    <div class="max-w-6xl mx-auto p-4 md:p-6">
      <!-- 顶部 Header -->
      <div class="flex items-center justify-between py-2">
        <h3 class="text-xl md:text-2xl font-bold text-gray-900 flex items-center gap-2">
          <span>WeChat Redeem Hub</span>
          <span class="text-xs px-2 py-0.5 rounded font-normal bg-emerald-100 text-emerald-800">
            v2.0 运行中
          </span>
        </h3>
        <button
          @click="onLogout"
          class="px-3 py-1.5 rounded-lg border border-red-200 text-red-600 hover:bg-red-50 text-sm font-bold"
        >
          退出登录
        </button>
      </div>

      <div v-if="error" class="mt-2 p-3 rounded-lg bg-red-100 text-red-700 text-sm flex justify-between items-center">
        <span>{{ error }}</span>
        <button @click="error = ''" class="text-red-500 font-bold ml-2">✕</button>
      </div>

      <!-- Tab 导航 -->
      <div class="flex gap-2 mt-4 border-b pb-2 overflow-x-auto">
        <button
          v-for="t in tabs"
          :key="t.key"
          @click="active = t.key"
          class="px-4 py-2 rounded-lg text-sm font-bold transition flex items-center gap-1.5 whitespace-nowrap"
          :class="active === t.key ? 'bg-emerald-600 text-white shadow-sm' : 'bg-white text-gray-700 hover:bg-gray-50'"
        >
          <span>{{ t.label }}</span>
          <span
            v-if="t.badge !== null && t.badge !== undefined"
            class="text-xs px-1.5 py-0.5 rounded-full"
            :class="active === t.key ? 'bg-white/25 text-white' : 'bg-gray-200 text-gray-700'"
          >
            {{ t.badge }}
          </span>
        </button>
      </div>

      <!-- 1. 总览模块 -->
      <div v-show="active === 'overview'">
        <StatCards :stats="stats" />
        <SystemConfig ref="sysConfigRef" @updated="refreshAll" />
      </div>

      <!-- 2. 激活码模块 -->
      <div v-show="active === 'codes'">
        <CodePoolTabs
          :pool-list="poolList"
          :selected-pool-id="selectedPoolId"
          @select-pool="onSelectPool"
          @open-pool-modal="showPoolModal = true"
        />

        <CodeImport
          :pool-list="poolList"
          :current-pool-id="selectedPoolId"
          @imported="refreshAll"
        />

        <CodeTable
          ref="codeTableRef"
          :pool-id="selectedPoolId"
          :pool-name="currentPoolName"
          :pool-stats="currentPoolStats"
          @changed="refreshAll"
        />

        <PoolModal
          v-model:visible="showPoolModal"
          :pool-list="poolList"
          @changed="refreshAll"
          @created="onPoolCreated"
        />
      </div>

      <!-- 3. 回复规则模块 -->
      <div v-show="active === 'rules'">
        <Rules />
      </div>

      <!-- 4. 用户模块 -->
      <div v-show="active === 'users'">
        <UsersTable ref="usersTableRef" @changed="refreshAll" />
      </div>

      <!-- 5. 留言模块 -->
      <div v-show="active === 'messages'">
        <MessagesTable ref="messagesTableRef" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { clearToken, fetchStats, listPools, logout } from '../api.js'

import StatCards from '../components/overview/StatCards.vue'
import SystemConfig from '../components/overview/SystemConfig.vue'
import CodePoolTabs from '../components/codes/CodePoolTabs.vue'
import CodeImport from '../components/codes/CodeImport.vue'
import CodeTable from '../components/codes/CodeTable.vue'
import PoolModal from '../components/codes/PoolModal.vue'
import UsersTable from '../components/users/UsersTable.vue'
import MessagesTable from '../components/messages/MessagesTable.vue'
import Rules from './Rules.vue'

const router = useRouter()
const active = ref('overview')
const error = ref('')

const stats = ref({})
const poolList = ref([])
const selectedPoolId = ref(null)
const showPoolModal = ref(false)

const sysConfigRef = ref(null)
const codeTableRef = ref(null)
const usersTableRef = ref(null)
const messagesTableRef = ref(null)

const currentPoolName = computed(() => {
  const p = poolList.value.find((item) => item.id === selectedPoolId.value)
  return p ? p.name : '当前卡池'
})

const currentPoolStats = computed(() => {
  const found = poolList.value.find((p) => p.id === selectedPoolId.value)
  return found ? { unused: found.unused, used: found.used, total: found.total } : { unused: 0, used: 0, total: 0 }
})

const tabs = computed(() => [
  { key: 'overview', label: '📊 总览', badge: null },
  { key: 'codes', label: '🔑 激活码', badge: currentPoolStats.value.unused ?? stats.value.unused ?? null },
  { key: 'users', label: '👥 用户', badge: usersTableRef.value?.userTotal ?? stats.value.users_count ?? null },
  { key: 'rules', label: '💬 回复', badge: null },
  { key: 'messages', label: '📝 留言', badge: messagesTableRef.value?.msgTotal ?? stats.value.messages_count ?? null },
])

async function guard(fn) {
  try {
    return await fn()
  } catch (e) {
    if (e.status === 401) {
      clearToken()
      router.push('/login')
    } else {
      error.value = e.detail || '加载失败'
    }
  }
}

async function loadStats() {
  await guard(async () => {
    stats.value = await fetchStats()
  })
}

async function loadPools() {
  await guard(async () => {
    const res = await listPools()
    poolList.value = res.pools || []
    const defPool = poolList.value.find((p) => p.is_default) || poolList.value[0]
    if (!selectedPoolId.value || !poolList.value.some((p) => p.id === selectedPoolId.value)) {
      if (defPool) {
        selectedPoolId.value = defPool.id
      }
    }
  })
}

function onSelectPool(id) {
  selectedPoolId.value = id
}

function onPoolCreated(newId) {
  selectedPoolId.value = newId
}

async function refreshAll() {
  await Promise.all([
    loadStats(),
    loadPools(),
  ])
  codeTableRef.value?.searchCodes()
  usersTableRef.value?.searchUsers()
}

async function onLogout() {
  try {
    await logout()
  } finally {
    clearToken()
    router.push('/login')
  }
}

onMounted(async () => {
  await Promise.all([
    loadStats(),
    loadPools(),
  ])
})
</script>
