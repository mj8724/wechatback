<template>
  <div class="bg-white rounded-xl shadow p-5 mt-4">
    <h5 class="font-bold">
      📝 粉丝留言与回复流水
      <span class="ml-2 text-xs font-normal text-gray-500">共 {{ msgTotal }} 条，已加载 {{ msgList.length }}</span>
    </h5>
    <p class="text-gray-500 text-xs mb-3">记录粉丝发送内容与系统自动回复，对话闭环流水审计</p>

    <form @submit.prevent="searchMessages" class="flex flex-col md:flex-row gap-2 mb-3">
      <input
        v-model="msgQuery"
        placeholder="搜索 OpenID / 留言 / 回复内容…"
        class="flex-1 border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500"
      />
      <button type="submit" class="px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-800 text-white text-sm font-bold">
        搜索
      </button>
      <button type="button" @click="exportMessages" class="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold">
        导出 CSV
      </button>
    </form>

    <div class="max-h-[500px] overflow-y-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="text-left text-gray-500">
            <th class="py-1">#</th>
            <th>OpenID</th>
            <th>粉丝发送</th>
            <th>系统回复</th>
            <th>时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!msgList.length"><td colspan="5" class="text-center text-gray-400 py-6">无匹配数据</td></tr>
          <tr v-for="m in msgList" :key="m.id" class="border-t hover:bg-gray-50">
            <td class="py-1">{{ m.id }}</td>
            <td><small><code>{{ m.openid }}</code></small></td>
            <td>{{ m.content }}</td>
            <td class="max-w-xs md:max-w-md truncate" :title="m.reply_content || '无'">
              <span v-if="m.reply_content" class="text-gray-700">{{ m.reply_content }}</span>
              <span v-else class="text-gray-400 italic">无回复 / 纯事件</span>
            </td>
            <td><small class="text-gray-500 whitespace-nowrap">{{ m.created_at }}</small></td>
          </tr>
        </tbody>
      </table>
    </div>

    <button
      v-if="msgList.length < msgTotal"
      @click="moreMessages"
      class="mt-3 w-full py-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-sm text-gray-600"
    >
      加载更多（{{ msgList.length }}/{{ msgTotal }}）
    </button>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { downloadCSV, listMessages } from '../../api.js'

const PAGE = 100

const msgList = ref([])
const msgTotal = ref(0)
const msgQuery = ref('')

async function searchMessages() {
  try {
    const d = await listMessages({ q: msgQuery.value.trim(), limit: PAGE, offset: 0 })
    msgList.value = d.messages || []
    msgTotal.value = d.total || 0
  } catch (e) {
    console.error('搜索留言失败', e)
  }
}

async function moreMessages() {
  try {
    const d = await listMessages({ q: msgQuery.value.trim(), limit: PAGE, offset: msgList.value.length })
    msgList.value.push(...(d.messages || []))
    msgTotal.value = d.total || 0
  } catch (e) {
    console.error('加载更多留言失败', e)
  }
}

async function fetchAllMessages() {
  const out = []
  let offset = 0
  for (;;) {
    const d = await listMessages({ q: msgQuery.value.trim(), limit: 500, offset })
    const rows = d.messages || []
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

async function exportMessages() {
  try {
    const rows = await fetchAllMessages()
    downloadCSV(
      `粉丝留言流水-${stamp()}.csv`,
      ['ID', 'OpenID', '类型', '粉丝发送内容', '系统自动回复', '时间'],
      rows.map((m) => [m.id, m.openid, m.msg_type, m.content, m.reply_content || '', m.created_at])
    )
  } catch (e) {
    alert('导出失败：' + (e.detail || '未知错误'))
  }
}

defineExpose({
  searchMessages,
  msgTotal,
})

onMounted(searchMessages)
</script>
