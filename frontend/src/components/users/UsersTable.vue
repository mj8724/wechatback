<template>
  <div class="bg-white rounded-xl shadow p-5 mt-4">
    <h5 class="font-bold mb-1">
      👥 已领取用户
      <span class="ml-2 text-xs font-normal text-gray-500">共 {{ userTotal }} 人，已加载 {{ userList.length }}</span>
    </h5>
    <p class="text-gray-500 text-xs mb-3">重置将收回该用户已领取的全部激活码（恢复为待领取状态），其可重新领取</p>

    <form @submit.prevent="searchUsers" class="mb-3 flex flex-col md:flex-row gap-2">
      <input
        v-model="userQuery"
        placeholder="搜索 OpenID / 激活码…"
        class="flex-1 border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500"
      />
      <select v-model="userStatus" class="border rounded-lg px-3 py-2 text-sm outline-none">
        <option value="">全部关注状态</option>
        <option value="subscribe">正常关注</option>
        <option value="unsubscribe">已取关</option>
      </select>
      <button type="submit" class="px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-800 text-white text-sm font-bold">
        搜索
      </button>
      <button type="button" @click="exportUsers" class="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold">
        导出 CSV
      </button>
      <button
        type="button"
        @click="onBatchReset"
        :disabled="!selectedUsers.length"
        class="px-4 py-2 rounded-lg text-white text-sm font-bold"
        :class="selectedUsers.length ? 'bg-amber-500 hover:bg-amber-600' : 'bg-gray-300 cursor-not-allowed'"
      >
        批量重置({{ selectedUsers.length }})
      </button>
    </form>

    <div class="max-h-[500px] overflow-y-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="text-left text-gray-500">
            <th class="py-1 pr-2 w-8"><input type="checkbox" :checked="allSelected" @change="toggleAll" /></th>
            <th>OpenID</th>
            <th>已领卡密明细</th>
            <th>关注状态</th>
            <th>领取时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!userList.length"><td colspan="6" class="text-center text-gray-400 py-6">无匹配数据</td></tr>
          <tr v-for="u in userList" :key="u.openid" class="border-t hover:bg-gray-50">
            <td class="py-2 pr-2"><input type="checkbox" :value="u.openid" v-model="selectedUsers" /></td>
            <td class="py-2"><small><code>{{ u.openid }}</code></small></td>
            <td class="py-2">
              <div v-if="u.claims && u.claims.length" class="space-y-1">
                <div v-for="(c, cIdx) in u.claims" :key="cIdx" class="flex items-center gap-1.5 flex-wrap">
                  <span class="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-700 font-medium">
                    {{ c.pool_name }}
                  </span>
                  <code class="text-xs bg-gray-50 px-1 py-0.5 rounded border">{{ c.code }}</code>
                </div>
              </div>
              <code v-else>{{ u.code }}</code>
            </td>
            <td>
              <span v-if="u.last_event === 'unsubscribe'" class="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-500">已取关</span>
              <span v-else class="text-xs px-2 py-0.5 rounded bg-emerald-100 text-emerald-700">正常关注</span>
            </td>
            <td><small class="text-gray-500">{{ u.created_at || '-' }}</small></td>
            <td>
              <button @click="onResetUser(u.openid)" class="text-xs px-2 py-1 rounded bg-amber-100 text-amber-700 hover:bg-amber-200">
                重置
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <button
      v-if="userList.length < userTotal"
      @click="moreUsers"
      class="mt-3 w-full py-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-sm text-gray-600"
    >
      加载更多（{{ userList.length }}/{{ userTotal }}）
    </button>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { downloadCSV, listUsers, resetUser, resetUsers } from '../../api.js'

const PAGE = 100

const emit = defineEmits(['changed'])

const userList = ref([])
const userTotal = ref(0)
const userQuery = ref('')
const userStatus = ref('')
const selectedUsers = ref([])

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

async function searchUsers() {
  selectedUsers.value = []
  try {
    const d = await listUsers({ q: userQuery.value.trim(), status: userStatus.value, limit: PAGE, offset: 0 })
    userList.value = d.users || []
    userTotal.value = d.total || 0
  } catch (e) {
    console.error('搜索用户失败', e)
  }
}

async function moreUsers() {
  try {
    const d = await listUsers({ q: userQuery.value.trim(), status: userStatus.value, limit: PAGE, offset: userList.value.length })
    userList.value.push(...(d.users || []))
    userTotal.value = d.total || 0
  } catch (e) {
    console.error('加载更多用户失败', e)
  }
}

async function onResetUser(openid) {
  if (!confirm(`确定收回 ${openid} 的激活码吗？其可重新领取。`)) return
  try {
    const data = await resetUser(openid)
    alert(data.message || '重置成功')
    selectedUsers.value = selectedUsers.value.filter((o) => o !== openid)
    await searchUsers()
    emit('changed')
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
    await searchUsers()
    emit('changed')
  } catch (e) {
    alert('批量重置失败：' + (e.detail || '未知错误'))
  }
}

async function fetchAllUsers() {
  const out = []
  let offset = 0
  for (;;) {
    const d = await listUsers({ q: userQuery.value.trim(), status: userStatus.value, limit: 500, offset })
    const rows = d.users || []
    out.push(...rows)
    if (out.length >= d.total || !rows.length) break
    offset += rows.length
  }
  return out
}

function stamp() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}`
}

async function exportUsers() {
  try {
    const rows = await fetchAllUsers()
    downloadCSV(
      `用户列表-${stamp()}.csv`,
      ['OpenID', '已领卡密明细', '关注状态', '领取时间'],
      rows.map((u) => [
        u.openid,
        (u.claims && u.claims.length) ? u.claims.map((c) => `[${c.pool_name}]${c.code}`).join('; ') : u.code,
        u.last_event === 'unsubscribe' ? '已取关' : '正常关注',
        u.created_at,
      ])
    )
  } catch (e) {
    alert('导出失败：' + (e.detail || '未知错误'))
  }
}

defineExpose({
  searchUsers,
  userTotal,
})

onMounted(searchUsers)
</script>
