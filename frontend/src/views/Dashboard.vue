<template>
  <div class="min-h-screen pb-10">
    <div class="text-white py-6 px-4" style="background: linear-gradient(135deg, #07c160 0%, #009688 100%)">
      <div class="max-w-5xl mx-auto flex items-center justify-between">
        <div>
          <h2 class="text-xl font-bold">💬 微信公众号激活码分发后台</h2>
          <p class="text-white/70 text-sm">一客一码防刷发放 · 实时库存监控</p>
        </div>
        <button @click="onLogout" class="px-4 py-2 rounded-lg bg-white/20 hover:bg-white/30 text-sm font-bold">
          退出登录
        </button>
      </div>
    </div>

    <div class="max-w-5xl mx-auto px-4">
      <div v-if="error" class="mt-4 p-3 rounded-lg bg-red-50 text-red-700 text-sm">🚫 {{ error }}</div>

      <!-- 模块标签页 -->
      <div class="mt-4 flex gap-1 border-b border-gray-200">
        <button
          v-for="t in tabs"
          :key="t.key"
          @click="active = t.key"
          class="px-5 py-2.5 text-sm font-bold -mb-px border-b-2"
          :class="active === t.key
            ? 'border-emerald-600 text-emerald-700'
            : 'border-transparent text-gray-500 hover:text-gray-800'"
        >
          {{ t.label }}
          <span v-if="t.badge !== null" class="ml-1 text-xs rounded px-1.5 py-0.5"
            :class="active === t.key ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-200 text-gray-600'">{{ t.badge }}</span>
        </button>
      </div>

      <!-- 总览 -->
      <div v-show="active === 'overview'">
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
          <div v-for="s in statCards" :key="s.label" class="bg-white rounded-xl shadow p-4">
            <div class="text-gray-500 text-sm">{{ s.label }}</div>
            <div class="text-3xl font-bold" :class="s.color">{{ s.value }}</div>
          </div>
        </div>
        <div class="bg-white rounded-xl shadow p-5 mt-4 text-sm text-gray-500">
          当前 Token：<code>{{ stats.token || '-' }}</code>
          <span class="ml-4">网站地址：</span><code>{{ stats.website || '-' }}</code>
        </div>
      </div>

      <!-- 激活码模块 -->
      <div v-show="active === 'codes'">
        <div class="bg-white rounded-xl shadow p-5 mt-4">
          <h5 class="font-bold mb-3">📥 批量导入激活码</h5>
          <div class="flex flex-col md:flex-row gap-2">
            <textarea v-model="importText" rows="3" placeholder="每行一个激活码，粘贴到这里..."
              class="flex-1 border rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-emerald-500"></textarea>
            <button @click="onImport" class="px-6 py-2 rounded-lg bg-sky-500 hover:bg-sky-600 text-white font-bold">
              导入
            </button>
          </div>
        </div>

        <div class="bg-white rounded-xl shadow p-5 mt-4">
          <h5 class="font-bold mb-3">🔑 激活码库存明细
            <span class="ml-2 text-xs font-normal text-gray-500">待领取 {{ stats.unused ?? 0 }} / 已领取 {{ stats.used ?? 0 }}</span>
          </h5>
          <div class="max-h-[500px] overflow-y-auto">
            <table class="w-full text-sm">
              <thead><tr class="text-left text-gray-500"><th class="py-1">#</th><th>激活码</th><th>状态</th><th>领取人</th><th>领取时间</th></tr></thead>
              <tbody>
                <tr v-if="!stats.records?.length"><td colspan="5" class="text-center text-gray-400 py-6">暂无激活码数据</td></tr>
                <tr v-for="r in stats.records" :key="r.id" class="border-t hover:bg-gray-50">
                  <td class="py-1">{{ r.id }}</td>
                  <td><code>{{ r.code }}</code></td>
                  <td>
                    <span v-if="r.status === 'assigned'" class="text-xs bg-gray-500 text-white rounded px-2 py-0.5">已领取</span>
                    <span v-else class="text-xs bg-green-600 text-white rounded px-2 py-0.5">待领取</span>
                  </td>
                  <td><small>{{ r.assigned_openid || '-' }}</small></td>
                  <td><small class="text-gray-500">{{ r.assigned_at || '-' }}</small></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- 后台留言模块 -->
      <div v-show="active === 'messages'">
        <div class="bg-white rounded-xl shadow p-5 mt-4">
          <h5 class="font-bold">📝 粉丝留言</h5>
          <p class="text-gray-500 text-xs mb-3">所有粉丝发送内容均持久化记录于此，刷新即可查看最新留言</p>
          <div class="max-h-[500px] overflow-y-auto">
            <table class="w-full text-sm">
              <thead><tr class="text-left text-gray-500"><th class="py-1">#</th><th>OpenID</th><th>内容</th><th>时间</th></tr></thead>
              <tbody>
                <tr v-if="!stats.messages?.length"><td colspan="4" class="text-center text-gray-400 py-6">暂无留言记录</td></tr>
                <tr v-for="m in stats.messages" :key="m.id" class="border-t hover:bg-gray-50">
                  <td class="py-1">{{ m.id }}</td>
                  <td><small><code>{{ m.openid }}</code></small></td>
                  <td>{{ m.content }}</td>
                  <td><small class="text-gray-500">{{ m.created_at }}</small></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { clearToken, fetchStats, importCodes, logout } from '../api.js'

const router = useRouter()
const stats = ref({})
const importText = ref('')
const error = ref('')
const active = ref('overview')

const tabs = computed(() => [
  { key: 'overview', label: '📊 总览', badge: null },
  { key: 'codes', label: '🔑 激活码', badge: stats.value.unused ?? null },
  { key: 'messages', label: '📝 留言', badge: stats.value.messages_count ?? null },
])

const statCards = computed(() => [
  { label: '总激活码数', value: stats.value.total ?? 0, color: 'text-blue-600' },
  { label: '已领取', value: stats.value.used ?? 0, color: 'text-green-600' },
  { label: '待领取', value: stats.value.unused ?? 0, color: 'text-amber-500' },
  { label: '已服务用户', value: stats.value.users_count ?? 0, color: 'text-red-500' },
])

async function load() {
  try {
    stats.value = await fetchStats()
  } catch (e) {
    if (e.status === 401) router.push('/login')
    else error.value = e.detail || '加载失败'
  }
}

async function onImport() {
  const lines = importText.value.split('\n').map((s) => s.trim()).filter(Boolean)
  if (!lines.length) return
  try {
    const data = await importCodes(lines)
    alert(`成功导入 ${data.added} 个新激活码！`)
    importText.value = ''
    await load()
  } catch (e) {
    alert('导入失败：' + (e.detail || '未知错误'))
  }
}

async function onLogout() {
  await logout()
  clearToken()
  router.push('/login')
}

onMounted(load)
</script>
