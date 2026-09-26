<template>
  <div class="bg-white rounded-xl shadow p-5 mt-4">
    <h5 class="font-bold mb-3">
      🔑 【{{ poolName }}】激活码库存明细
      <span class="ml-2 text-xs font-normal text-gray-500">
        待领取 {{ poolStats.unused ?? 0 }} / 已领取 {{ poolStats.used ?? 0 }} / 已加载 {{ codeList.length }}/{{ codeTotal }}
      </span>
    </h5>

    <form @submit.prevent="searchCodes" class="flex flex-col md:flex-row gap-2 mb-3">
      <input
        v-model="codeQuery"
        placeholder="搜索当前卡池激活码 / 领取人 OpenID…"
        class="flex-1 border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500"
      />
      <select v-model="codeStatus" class="border rounded-lg px-3 py-2 text-sm outline-none">
        <option value="">全部状态</option>
        <option value="unused">待领取</option>
        <option value="assigned">已领取</option>
      </select>
      <button type="submit" class="px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-800 text-white text-sm font-bold">
        搜索
      </button>
      <button type="button" @click="exportCodes" class="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold">
        导出 CSV
      </button>
      <button type="button" @click="onClearUnused" class="px-4 py-2 rounded-lg bg-red-500 hover:bg-red-600 text-white text-sm font-bold">
        清空当前池未使用({{ poolStats.unused ?? 0 }})
      </button>
    </form>

    <div class="max-h-[500px] overflow-y-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="text-left text-gray-500">
            <th class="py-1">#</th>
            <th>品类</th>
            <th>激活码</th>
            <th>状态</th>
            <th>领取人</th>
            <th>领取时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!codeList.length">
            <td colspan="7" class="text-center text-gray-400 py-6">无匹配数据</td>
          </tr>
          <tr v-for="r in codeList" :key="r.id" class="border-t hover:bg-gray-50">
            <td class="py-1">{{ r.id }}</td>
            <td>
              <span class="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-700 font-medium">
                {{ r.pool_name || poolName }}
              </span>
            </td>
            <td><code>{{ r.code }}</code></td>
            <td>
              <span v-if="r.status === 'assigned'" class="text-xs bg-gray-500 text-white rounded px-2 py-0.5">已领取</span>
              <span v-else class="text-xs bg-green-600 text-white rounded px-2 py-0.5">待领取</span>
            </td>
            <td><small>{{ r.assigned_openid || '-' }}</small></td>
            <td><small class="text-gray-500">{{ r.assigned_at || '-' }}</small></td>
            <td>
              <button
                v-if="r.status === 'assigned'"
                @click="onReset(r.code)"
                class="text-xs px-2 py-1 rounded bg-amber-100 text-amber-700 hover:bg-amber-200"
              >
                重置
              </button>
              <span v-else class="text-gray-300 text-xs">-</span>
              <button
                @click="onDelete(r)"
                class="ml-1 text-xs px-2 py-1 rounded bg-red-50 text-red-600 hover:bg-red-100"
              >
                删除
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <button
      v-if="codeList.length < codeTotal"
      @click="moreCodes"
      class="mt-3 w-full py-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-sm text-gray-600"
    >
      加载更多（{{ codeList.length }}/{{ codeTotal }}）
    </button>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { deleteCode, deleteUnusedCodes, downloadCSV, listCodes, resetCode } from '../../api.js'

const PAGE = 100

const props = defineProps({
  poolId: {
    type: [Number, String, null],
    default: null,
  },
  poolName: {
    type: String,
    default: '当前卡池',
  },
  poolStats: {
    type: Object,
    default: () => ({ unused: 0, used: 0, total: 0 }),
  },
})

const emit = defineEmits(['changed'])

const codeList = ref([])
const codeTotal = ref(0)
const codeQuery = ref('')
const codeStatus = ref('')

watch(() => props.poolId, () => {
  searchCodes()
})

async function searchCodes() {
  const params = { q: codeQuery.value.trim(), status: codeStatus.value, limit: PAGE, offset: 0 }
  if (props.poolId !== null) params.pool_id = props.poolId
  try {
    const d = await listCodes(params)
    codeList.value = d.codes || []
    codeTotal.value = d.total || 0
  } catch (e) {
    console.error('搜索激活码失败', e)
  }
}

async function moreCodes() {
  const params = { q: codeQuery.value.trim(), status: codeStatus.value, limit: PAGE, offset: codeList.value.length }
  if (props.poolId !== null) params.pool_id = props.poolId
  try {
    const d = await listCodes(params)
    codeList.value.push(...(d.codes || []))
    codeTotal.value = d.total || 0
  } catch (e) {
    console.error('加载更多激活码失败', e)
  }
}

async function onReset(code) {
  if (!confirm(`确定将激活码 ${code} 重置为待领取吗？原领取人可重新领取。`)) return
  try {
    const data = await resetCode(code)
    alert(data.message || '重置成功')
    await searchCodes()
    emit('changed')
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
    await searchCodes()
    emit('changed')
  } catch (e) {
    alert('删除失败：' + (e.detail || '未知错误'))
  }
}

async function onClearUnused() {
  const n = props.poolStats.unused ?? 0
  if (!n) { alert(`【${props.poolName}】没有未使用的激活码`); return }
  if (!confirm(`确定删除【${props.poolName}】全部 ${n} 个未使用激活码吗？此操作不可恢复。`)) return
  try {
    const data = await deleteUnusedCodes(props.poolId)
    alert(data.message || '清空成功')
    await searchCodes()
    emit('changed')
  } catch (e) {
    alert('清空失败：' + (e.detail || '未知错误'))
  }
}

async function fetchAllCodes() {
  const out = []
  let offset = 0
  for (;;) {
    const params = { q: codeQuery.value.trim(), status: codeStatus.value, limit: 500, offset }
    if (props.poolId !== null) params.pool_id = props.poolId
    const d = await listCodes(params)
    const rows = d.codes || []
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

async function exportCodes() {
  try {
    const rows = await fetchAllCodes()
    downloadCSV(
      `激活码库存-${props.poolName}-${stamp()}.csv`,
      ['ID', '激活码', '状态', '领取人OpenID', '领取时间', '创建时间'],
      rows.map((r) => [r.id, r.code, r.status === 'assigned' ? '已领取' : '待领取', r.assigned_openid, r.assigned_at, r.created_at])
    )
  } catch (e) {
    alert('导出失败：' + (e.detail || '未知错误'))
  }
}

defineExpose({
  searchCodes,
})

onMounted(searchCodes)
</script>
