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
      <div class="mt-4 flex gap-1 border-b border-gray-200 overflow-x-auto">
        <button
          v-for="t in tabs"
          :key="t.key"
          @click="active = t.key"
          class="px-5 py-2.5 text-sm font-bold -mb-px border-b-2 whitespace-nowrap"
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
          当前 Token：<code>{{ stats.token_configured ? '已配置（服务端持有，不展示）' : '未配置' }}</code>
          <span class="ml-4">网站地址：</span><code>{{ stats.website || '-' }}</code>
        </div>
      </div>

      <!-- 激活码模块 -->
      <div v-show="active === 'codes'">
        <div class="bg-white rounded-xl shadow p-5 mt-4">
          <h5 class="font-bold mb-3">📥 批量导入激活码 <span class="text-xs font-normal text-gray-400">单次最多 2000 个</span></h5>
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
            <span class="ml-2 text-xs font-normal text-gray-500">待领取 {{ stats.unused ?? 0 }} / 已领取 {{ stats.used ?? 0 }} / 已加载 {{ codeList.length }}/{{ codeTotal }}</span>
          </h5>
          <form @submit.prevent="searchCodes" class="flex flex-col md:flex-row gap-2 mb-3">
            <input v-model="codeQuery" placeholder="搜索激活码 / 领取人 OpenID…"
              class="flex-1 border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500" />
            <select v-model="codeStatus" class="border rounded-lg px-3 py-2 text-sm outline-none">
              <option value="">全部状态</option>
              <option value="unused">待领取</option>
              <option value="assigned">已领取</option>
            </select>
            <button type="submit" class="px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-800 text-white text-sm font-bold">搜索</button>
            <button type="button" @click="exportCodes" class="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold">
              导出 CSV
            </button>
            <button type="button" @click="onClearUnused" class="px-4 py-2 rounded-lg bg-red-500 hover:bg-red-600 text-white text-sm font-bold">
              清空未使用({{ stats.unused ?? 0 }})
            </button>
          </form>
          <div class="max-h-[500px] overflow-y-auto">
            <table class="w-full text-sm">
              <thead><tr class="text-left text-gray-500"><th class="py-1">#</th><th>激活码</th><th>状态</th><th>领取人</th><th>领取时间</th><th>操作</th></tr></thead>
              <tbody>
                <tr v-if="!codeList.length"><td colspan="6" class="text-center text-gray-400 py-6">无匹配数据</td></tr>
                <tr v-for="r in codeList" :key="r.id" class="border-t hover:bg-gray-50">
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
          <button v-if="codeList.length < codeTotal" @click="moreCodes"
            class="mt-3 w-full py-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-sm text-gray-600">
            加载更多（{{ codeList.length }}/{{ codeTotal }}）
          </button>
        </div>
      </div>

      <!-- 回复规则模块 -->
      <div v-show="active === 'rules'">
        <Rules />
      </div>

      <!-- 用户模块 -->
      <div v-show="active === 'users'">
        <div class="bg-white rounded-xl shadow p-5 mt-4">
          <h5 class="font-bold mb-1">👥 已领取用户 <span class="ml-2 text-xs font-normal text-gray-500">共 {{ userTotal }} 人，一人一码，已加载 {{ userList.length }}</span></h5>
          <p class="text-gray-500 text-xs mb-3">重置将收回该用户的激活码（回到待领取），其可重新领取</p>
          <form @submit.prevent="searchUsers" class="mb-3 flex flex-col md:flex-row gap-2">
            <input v-model="userQuery" placeholder="搜索 OpenID / 激活码…"
              class="flex-1 border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500" />
            <button type="submit" class="px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-800 text-white text-sm font-bold">搜索</button>
            <button type="button" @click="onBatchReset" :disabled="!selectedUsers.length"
              class="px-4 py-2 rounded-lg text-white text-sm font-bold"
              :class="selectedUsers.length ? 'bg-amber-500 hover:bg-amber-600' : 'bg-gray-300 cursor-not-allowed'">
              批量重置({{ selectedUsers.length }})
            </button>
          </form>
          <div class="max-h-[500px] overflow-y-auto">
            <table class="w-full text-sm">
              <thead><tr class="text-left text-gray-500">
                <th class="py-1 pr-2"><input type="checkbox" :checked="allSelected" @change="toggleAll" /></th>
                <th>OpenID</th><th>激活码</th><th>领取时间</th><th>操作</th>
              </tr></thead>
              <tbody>
                <tr v-if="!userList.length"><td colspan="5" class="text-center text-gray-400 py-6">无匹配数据</td></tr>
                <tr v-for="u in userList" :key="u.openid" class="border-t hover:bg-gray-50">
                  <td class="py-1 pr-2"><input type="checkbox" :value="u.openid" v-model="selectedUsers" /></td>
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
          <button v-if="userList.length < userTotal" @click="moreUsers"
            class="mt-3 w-full py-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-sm text-gray-600">
            加载更多（{{ userList.length }}/{{ userTotal }}）
          </button>
        </div>
      </div>

      <!-- 后台留言模块 -->
      <div v-show="active === 'messages'">
        <div class="bg-white rounded-xl shadow p-5 mt-4">
          <h5 class="font-bold">📝 粉丝留言 <span class="ml-2 text-xs font-normal text-gray-500">共 {{ msgTotal }} 条，已加载 {{ msgList.length }}</span></h5>
          <p class="text-gray-500 text-xs mb-3">所有粉丝发送内容均持久化记录于此，刷新即可查看最新留言</p>
          <form @submit.prevent="searchMessages" class="flex flex-col md:flex-row gap-2 mb-3">
            <input v-model="msgQuery" placeholder="搜索 OpenID / 留言内容…"
              class="flex-1 border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500" />
            <button type="submit" class="px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-800 text-white text-sm font-bold">搜索</button>
            <button type="button" @click="exportMessages" class="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold">
              导出 CSV
            </button>
          </form>
          <div class="max-h-[500px] overflow-y-auto">
            <table class="w-full text-sm">
              <thead><tr class="text-left text-gray-500"><th class="py-1">#</th><th>OpenID</th><th>内容</th><th>时间</th></tr></thead>
              <tbody>
                <tr v-if="!msgList.length"><td colspan="4" class="text-center text-gray-400 py-6">无匹配数据</td></tr>
                <tr v-for="m in msgList" :key="m.id" class="border-t hover:bg-gray-50">
                  <td class="py-1">{{ m.id }}</td>
                  <td><small><code>{{ m.openid }}</code></small></td>
                  <td>{{ m.content }}</td>
                  <td><small class="text-gray-500">{{ m.created_at }}</small></td>
                </tr>
              </tbody>
            </table>
          </div>
          <button v-if="msgList.length < msgTotal" @click="moreMessages"
            class="mt-3 w-full py-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-sm text-gray-600">
            加载更多（{{ msgList.length }}/{{ msgTotal }}）
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import Rules from './Rules.vue'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  clearToken, deleteCode, deleteUnusedCodes, downloadCSV, fetchStats, importCodes,
  listCodes, listMessages, listUsers, logout, resetCode, resetUser, resetUsers,
} from '../api.js'

const PAGE = 100
const router = useRouter()
const stats = ref({})
const error = ref('')
const active = ref('overview')

const importText = ref('')
const importResult = ref(null)

const codeList = ref([])
const codeTotal = ref(0)
const codeQuery = ref('')
const codeStatus = ref('')

const userList = ref([])
const userTotal = ref(0)
const userQuery = ref('')
const selectedUsers = ref([])

const msgList = ref([])
const msgTotal = ref(0)
const msgQuery = ref('')

const tabs = computed(() => [
  { key: 'overview', label: '📊 总览', badge: null },
  { key: 'codes', label: '🔑 激活码', badge: stats.value.unused ?? null },
  { key: 'users', label: '👥 用户', badge: userTotal.value || null },
  { key: 'rules', label: '💬 回复', badge: null },
  { key: 'messages', label: '📝 留言', badge: stats.value.messages_count ?? null },
])

const statCards = computed(() => [
  { label: '总激活码数', value: stats.value.total ?? 0, color: 'text-blue-600' },
  { label: '已领取', value: stats.value.used ?? 0, color: 'text-green-600' },
  { label: '待领取', value: stats.value.unused ?? 0, color: 'text-amber-500' },
  { label: '已服务用户', value: stats.value.users_count ?? 0, color: 'text-red-500' },
])

async function guard(fn) {
  try {
    return await fn()
  } catch (e) {
    if (e.status === 401) router.push('/login')
    else error.value = e.detail || '加载失败'
  }
}

async function loadOverview() {
  await guard(async () => { stats.value = await fetchStats() })
}

async function searchCodes() {
  await guard(async () => {
    const d = await listCodes({ q: codeQuery.value.trim(), status: codeStatus.value, limit: PAGE, offset: 0 })
    codeList.value = d.codes
    codeTotal.value = d.total
  })
}
async function moreCodes() {
  await guard(async () => {
    const d = await listCodes({ q: codeQuery.value.trim(), status: codeStatus.value, limit: PAGE, offset: codeList.value.length })
    codeList.value.push(...d.codes)
    codeTotal.value = d.total
  })
}

async function searchUsers() {
  selectedUsers.value = []
  await guard(async () => {
    const d = await listUsers({ q: userQuery.value.trim(), limit: PAGE, offset: 0 })
    userList.value = d.users
    userTotal.value = d.total
  })
}
async function moreUsers() {
  await guard(async () => {
    const d = await listUsers({ q: userQuery.value.trim(), limit: PAGE, offset: userList.value.length })
    userList.value.push(...d.users)
    userTotal.value = d.total
  })
}

async function searchMessages() {
  await guard(async () => {
    const d = await listMessages({ q: msgQuery.value.trim(), limit: PAGE, offset: 0 })
    msgList.value = d.messages
    msgTotal.value = d.total
  })
}
async function moreMessages() {
  await guard(async () => {
    const d = await listMessages({ q: msgQuery.value.trim(), limit: PAGE, offset: msgList.value.length })
    msgList.value.push(...d.messages)
    msgTotal.value = d.total
  })
}

const allSelected = computed(() => userList.value.length > 0 && userList.value.every((u) => selectedUsers.value.includes(u.openid)))

function toggleAll() {
  if (allSelected.value) {
    const vis = new Set(userList.value.map((u) => u.openid))
    selectedUsers.value = selectedUsers.value.filter((o) => !vis.has(o))
  } else {
    const cur = new Set(selectedUsers.value)
    userList.value.forEach((u) => cur.add(u.openid))
    selectedUsers.value = [...cur]
  }
}

async function refreshLists() {
  await Promise.all([loadOverview(), searchCodes(), searchUsers(), searchMessages()])
}

async function onImport() {
  const lines = importText.value.split('\n').map((s) => s.trim()).filter(Boolean)
  if (!lines.length) return
  try {
    const data = await importCodes(lines)
    importResult.value = data
    importText.value = ''
    await refreshLists()
  } catch (e) {
    alert('导入失败：' + (e.detail || '未知错误'))
  }
}

async function onReset(code) {
  if (!confirm(`确定将激活码 ${code} 重置为待领取吗？原领取人可重新领取。`)) return
  try {
    const data = await resetCode(code)
    alert(data.message || '重置成功')
    await refreshLists()
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
    await refreshLists()
  } catch (e) {
    alert('删除失败：' + (e.detail || '未知错误'))
  }
}

function stamp() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}`
}

async function fetchAll(listFn, params) {
  const out = []
  let offset = 0
  for (;;) {
    const d = await listFn({ ...params, limit: 500, offset })
    const rows = d.codes || d.users || d.messages || []
    out.push(...rows)
    if (out.length >= d.total || !rows.length) break
    offset += rows.length
  }
  return out
}

async function exportCodes() {
  try {
    const rows = await fetchAll(listCodes, { q: codeQuery.value.trim(), status: codeStatus.value })
    downloadCSV(
      `激活码库存-${stamp()}.csv`,
      ['ID', '激活码', '状态', '领取人OpenID', '领取时间', '创建时间'],
      rows.map((r) => [r.id, r.code, r.status === 'assigned' ? '已领取' : '待领取', r.assigned_openid, r.assigned_at, r.created_at])
    )
  } catch (e) {
    alert('导出失败：' + (e.detail || '未知错误'))
  }
}

async function exportMessages() {
  try {
    const rows = await fetchAll(listMessages, { q: msgQuery.value.trim() })
    downloadCSV(
      `粉丝留言-${stamp()}.csv`,
      ['ID', 'OpenID', '类型', '内容', '时间'],
      rows.map((m) => [m.id, m.openid, m.msg_type, m.content, m.created_at])
    )
  } catch (e) {
    alert('导出失败：' + (e.detail || '未知错误'))
  }
}

async function onResetUser(openid) {
  if (!confirm(`确定收回 ${openid} 的激活码吗？其可重新领取。`)) return
  try {
    const data = await resetUser(openid)
    alert(data.message || '重置成功')
    selectedUsers.value = selectedUsers.value.filter((o) => o !== openid)
    await refreshLists()
  } catch (e) {
    alert('重置失败：' + (e.detail || '未知错误'))
  }
}

async function onBatchReset() {
  if (!selectedUsers.value.length) return
  if (!confirm(`确定批量收回 ${selectedUsers.value.length} 位用户的激活码吗？他们可重新领取。`)) return
  try {
    const data = await resetUsers(selectedUsers.value)
    alert(data.message || '批量重置成功')
    selectedUsers.value = []
    await refreshLists()
  } catch (e) {
    alert('批量重置失败：' + (e.detail || '未知错误'))
  }
}

async function onClearUnused() {
  const n = stats.value.unused ?? 0
  if (!n) { alert('没有未使用的激活码'); return }
  if (!confirm(`确定删除全部 ${n} 个未使用激活码吗？此操作不可恢复。`)) return
  try {
    const data = await deleteUnusedCodes()
    alert(data.message || '清空成功')
    await refreshLists()
  } catch (e) {
    alert('清空失败：' + (e.detail || '未知错误'))
  }
}

async function onLogout() {
  await logout()
  clearToken()
  router.push('/login')
}

onMounted(refreshLists)
</script>
