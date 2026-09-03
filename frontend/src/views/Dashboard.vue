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
          <div v-if="importResult" class="mt-3 text-sm">
            <p class="p-2 rounded bg-emerald-50 text-emerald-700">
              ✅ 成功导入 {{ importResult.added }} 个<span v-if="importResult.duplicates?.length">，{{ importResult.duplicates.length }} 个重复已剔除</span>
            </p>
            <p v-if="importResult.duplicates?.length" class="mt-1 p-2 rounded bg-amber-50 text-amber-700 break-all">
              重复码：{{ importResult.duplicates.join('、') }}
            </p>
          </div>
        </div>

        <div class="bg-white rounded-xl shadow p-5 mt-4">
          <h5 class="font-bold mb-3">🔑 激活码库存明细
            <span class="ml-2 text-xs font-normal text-gray-500">待领取 {{ stats.unused ?? 0 }} / 已领取 {{ stats.used ?? 0 }}</span>
          </h5>
          <div class="flex flex-col md:flex-row gap-2 mb-3">
            <input v-model="codeQuery" placeholder="搜索激活码 / 领取人 OpenID…"
              class="flex-1 border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500" />
            <select v-model="codeStatus" class="border rounded-lg px-3 py-2 text-sm outline-none">
              <option value="">全部状态</option>
              <option value="unused">待领取</option>
              <option value="assigned">已领取</option>
            </select>
            <button @click="exportCodes" class="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold">
              导出 CSV
            </button>
          </div>
          <div class="max-h-[500px] overflow-y-auto">
            <table class="w-full text-sm">
              <thead><tr class="text-left text-gray-500"><th class="py-1">#</th><th>激活码</th><th>状态</th><th>领取人</th><th>领取时间</th><th>操作</th></tr></thead>
              <tbody>
                <tr v-if="!filteredCodes.length"><td colspan="6" class="text-center text-gray-400 py-6">无匹配数据</td></tr>
                <tr v-for="r in filteredCodes" :key="r.id" class="border-t hover:bg-gray-50">
                  <td class="py-1">{{ r.id }}</td>
                  <td><code>{{ r.code }}</code></td>
                  <td>
                    <span v-if="r.status === 'assigned'" class="text-xs bg-gray-500 text-white rounded px-2 py-0.5">已领取</span>
                    <span v-else class="text-xs bg-green-600 text-white rounded px-2 py-0.5">待领取</span>
                  </td>
                  <td><small>{{ r.assigned_openid || '-' }}</small></td>
                  <td><small class="text-gray-500">{{ r.assigned_at || '-' }}</small></td>
                  <td>
                    <button v-if="r.status === 'assigned'" @click="onReset(r.code)"
                      class="text-xs px-2 py-1 rounded bg-amber-100 text-amber-700 hover:bg-amber-200">重置</button>
                    <span v-else class="text-gray-300 text-xs">-</span>
                    <button @click="onDelete(r)"
                      class="ml-1 text-xs px-2 py-1 rounded bg-red-50 text-red-600 hover:bg-red-100">删除</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- 用户模块 -->
      <div v-show="active === 'users'">
        <div class="bg-white rounded-xl shadow p-5 mt-4">
          <h5 class="font-bold mb-1">👥 已领取用户 <span class="ml-2 text-xs font-normal text-gray-500">共 {{ usersTotal }} 人，一人一码</span></h5>
          <p class="text-gray-500 text-xs mb-3">重置将收回该用户的激活码（回到待领取），其可重新领取</p>
          <div class="mb-3">
            <input v-model="userQuery" placeholder="搜索 OpenID / 激活码…"
              class="w-full md:w-1/2 border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500" />
          </div>
          <div class="max-h-[500px] overflow-y-auto">
            <table class="w-full text-sm">
              <thead><tr class="text-left text-gray-500"><th class="py-1">OpenID</th><th>激活码</th><th>领取时间</th><th>操作</th></tr></thead>
              <tbody>
                <tr v-if="!filteredUsers.length"><td colspan="4" class="text-center text-gray-400 py-6">无匹配数据</td></tr>
                <tr v-for="u in filteredUsers" :key="u.openid" class="border-t hover:bg-gray-50">
                  <td class="py-1"><small><code>{{ u.openid }}</code></small></td>
                  <td><code>{{ u.code }}</code></td>
                  <td><small class="text-gray-500">{{ u.created_at || '-' }}</small></td>
                  <td>
                    <button @click="onResetUser(u.openid)"
                      class="text-xs px-2 py-1 rounded bg-amber-100 text-amber-700 hover:bg-amber-200">重置</button>
                  </td>
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
          <div class="flex flex-col md:flex-row gap-2 mb-3">
            <input v-model="msgQuery" placeholder="搜索 OpenID / 留言内容…"
              class="flex-1 border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500" />
            <button @click="exportMessages" class="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold">
              导出 CSV
            </button>
          </div>
          <div class="max-h-[500px] overflow-y-auto">
            <table class="w-full text-sm">
              <thead><tr class="text-left text-gray-500"><th class="py-1">#</th><th>OpenID</th><th>内容</th><th>时间</th></tr></thead>
              <tbody>
                <tr v-if="!filteredMessages.length"><td colspan="4" class="text-center text-gray-400 py-6">无匹配数据</td></tr>
                <tr v-for="m in filteredMessages" :key="m.id" class="border-t hover:bg-gray-50">
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
import { clearToken, deleteCode, downloadCSV, fetchStats, importCodes, listUsers, logout, resetCode, resetUser } from '../api.js'

const router = useRouter()
const stats = ref({})
const users = ref([])
const usersTotal = ref(0)
const userQuery = ref('')
const importText = ref('')
const importResult = ref(null)
const codeQuery = ref('')
const codeStatus = ref('')
const msgQuery = ref('')
const error = ref('')
const active = ref('overview')

const tabs = computed(() => [
  { key: 'overview', label: '📊 总览', badge: null },
  { key: 'codes', label: '🔑 激活码', badge: stats.value.unused ?? null },
  { key: 'users', label: '👥 用户', badge: usersTotal.value || null },
  { key: 'messages', label: '📝 留言', badge: stats.value.messages_count ?? null },
])

const filteredCodes = computed(() => {
  const q = codeQuery.value.trim().toLowerCase()
  return (stats.value.records || []).filter((r) => {
    if (codeStatus.value && r.status !== codeStatus.value) return false
    if (!q) return true
    return (r.code || '').toLowerCase().includes(q) || (r.assigned_openid || '').toLowerCase().includes(q)
  })
})

const filteredUsers = computed(() => {
  const q = userQuery.value.trim().toLowerCase()
  if (!q) return users.value
  return users.value.filter((u) =>
    (u.openid || '').toLowerCase().includes(q) || (u.code || '').toLowerCase().includes(q)
  )
})

const filteredMessages = computed(() => {
  const q = msgQuery.value.trim().toLowerCase()
  if (!q) return stats.value.messages || []
  return (stats.value.messages || []).filter((m) =>
    (m.openid || '').toLowerCase().includes(q) || (m.content || '').toLowerCase().includes(q)
  )
})

const statCards = computed(() => [
  { label: '总激活码数', value: stats.value.total ?? 0, color: 'text-blue-600' },
  { label: '已领取', value: stats.value.used ?? 0, color: 'text-green-600' },
  { label: '待领取', value: stats.value.unused ?? 0, color: 'text-amber-500' },
  { label: '已服务用户', value: stats.value.users_count ?? 0, color: 'text-red-500' },
])

async function load() {
  try {
    stats.value = await fetchStats()
    const udata = await listUsers()
    users.value = udata.users || []
    usersTotal.value = udata.total ?? users.value.length
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
    importResult.value = data
    importText.value = ''
    await load()
  } catch (e) {
    alert('导入失败：' + (e.detail || '未知错误'))
  }
}

async function onReset(code) {
  if (!confirm(`确定将激活码 ${code} 重置为待领取吗？原领取人可重新领取。`)) return
  try {
    const data = await resetCode(code)
    alert(data.message || '重置成功')
    await load()
  } catch (e) {
    alert('重置失败：' + (e.detail || '未知错误'))
  }
}

async function onDelete(r) {
  const tip = r.status === 'assigned'
    ? `确定删除激活码 ${r.code} 吗？它已被 ${r.assigned_openid} 领取，删除将同时解除绑定。`
    : `确定删除激活码 ${r.code} 吗？`
  if (!confirm(tip)) return
  try {
    const data = await deleteCode(r.code)
    alert(data.message || '删除成功')
    await load()
  } catch (e) {
    alert('删除失败：' + (e.detail || '未知错误'))
  }
}

function stamp() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}`
}

function exportCodes() {
  downloadCSV(
    `激活码库存-${stamp()}.csv`,
    ['ID', '激活码', '状态', '领取人OpenID', '领取时间', '创建时间'],
    filteredCodes.value.map((r) => [r.id, r.code, r.status === 'assigned' ? '已领取' : '待领取', r.assigned_openid, r.assigned_at, r.created_at])
  )
}

function exportMessages() {
  downloadCSV(
    `粉丝留言-${stamp()}.csv`,
    ['ID', 'OpenID', '类型', '内容', '时间'],
    filteredMessages.value.map((m) => [m.id, m.openid, m.msg_type, m.content, m.created_at])
  )
}

async function onResetUser(openid) {
  if (!confirm(`确定收回 ${openid} 的激活码吗？其可重新领取。`)) return
  try {
    const data = await resetUser(openid)
    alert(data.message || '重置成功')
    await load()
  } catch (e) {
    alert('重置失败：' + (e.detail || '未知错误'))
  }
}

async function onLogout() {
  await logout()
  clearToken()
  router.push('/login')
}

onMounted(load)
</script>
