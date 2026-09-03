<template>
  <div>
    <div class="bg-white rounded-xl shadow p-5 mt-4">
      <div class="flex items-center justify-between mb-1">
        <h5 class="font-bold">💬 关键词回复规则 <span class="ml-2 text-xs font-normal text-gray-500">按优先级首个命中，可用占位符 {code} {site} {group}</span></h5>
        <button @click="startAdd" class="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold">+ 新增</button>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead><tr class="text-left text-gray-500"><th class="py-1">关键词</th><th>匹配</th><th>动作</th><th>优先级</th><th>开关</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-if="!rules.length"><td colspan="6" class="text-center text-gray-400 py-6">暂无规则</td></tr>
            <tr v-for="r in rules" :key="r.id" class="border-t hover:bg-gray-50">
              <td class="py-1"><code>{{ r.keyword }}</code></td>
              <td>{{ r.mode === 'exact' ? '完全一致' : '包含' }}</td>
              <td>{{ r.action === 'code' ? '🎟️ 发码' : '回复文本' }}</td>
              <td>{{ r.priority }}</td>
              <td>
                <button @click="toggle(r)" class="text-xs px-2 py-1 rounded"
                  :class="r.enabled ? 'bg-green-100 text-green-700' : 'bg-gray-200 text-gray-500'">
                  {{ r.enabled ? '启用' : '停用' }}
                </button>
              </td>
              <td>
                <button @click="startEdit(r)" class="text-xs px-2 py-1 rounded bg-sky-50 text-sky-600 hover:bg-sky-100">编辑</button>
                <button @click="onDelete(r)" class="ml-1 text-xs px-2 py-1 rounded bg-red-50 text-red-600 hover:bg-red-100">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="editing" class="mt-4 p-4 rounded-lg bg-gray-50 border">
        <h6 class="font-bold text-sm mb-3">{{ form.id ? '编辑规则' : '新增规则' }}</h6>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-2">
          <input v-model="form.keyword" placeholder="关键词，如 邀请码" class="border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500" />
          <select v-model="form.mode" class="border rounded-lg px-3 py-2 text-sm">
            <option value="contains">包含</option>
            <option value="exact">完全一致</option>
          </select>
          <select v-model="form.action" class="border rounded-lg px-3 py-2 text-sm">
            <option value="none">回复文本</option>
            <option value="code">发码（一人一码）</option>
          </select>
          <input v-model.number="form.priority" type="number" placeholder="优先级（越小越先）" class="border rounded-lg px-3 py-2 text-sm" />
        </div>
        <textarea v-model="form.content" rows="4" placeholder="回复内容。发码类可用 {code}（激活码）{site}（兑换地址）；群类可用 {group}（群微信号）"
          class="mt-2 w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500"></textarea>
        <div class="mt-2 flex gap-2">
          <button @click="onSave" class="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold">保存</button>
          <button @click="editing = false" class="px-4 py-1.5 rounded-lg bg-gray-200 text-sm">取消</button>
        </div>
      </div>
    </div>

    <div class="bg-white rounded-xl shadow p-5 mt-4">
      <h5 class="font-bold mb-3">⚙️ 固定回复与公众号设置</h5>
      <div class="grid gap-3">
        <label class="block text-sm">微信群入口微信号
          <input v-model="settings.group_id" class="mt-1 w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500" />
        </label>
        <label v-for="item in textSettings" :key="item.key" class="block text-sm">{{ item.label }}
          <textarea v-model="settings[item.key]" rows="3" class="mt-1 w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500"></textarea>
        </label>
      </div>
      <button @click="onSaveSettings" class="mt-3 px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold">保存设置</button>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { deleteRule, getSettings, listRules, saveRule, saveSettings } from '../api.js'

const router = useRouter()
const rules = ref([])
const settings = ref({})
const editing = ref(false)
const form = ref({ id: null, keyword: '', mode: 'contains', action: 'none', content: '', priority: 100 })

const textSettings = [
  { key: 'welcome_reply', label: '关注欢迎语（subscribe/scan 事件）' },
  { key: 'fallback_reply', label: '默认回复（无关键词命中）' },
  { key: 'new_reply', label: '发码成功模板（{code} {site}）' },
  { key: 'repeat_reply', label: '重复领取模板（{code} {site}）' },
  { key: 'empty_reply', label: '库存领完模板' },
]

async function load() {
  try {
    rules.value = (await listRules()).rules || []
    settings.value = (await getSettings()).settings || {}
  } catch (e) {
    if (e.status === 401) router.push('/login')
  }
}

function startAdd() {
  form.value = { id: null, keyword: '', mode: 'contains', action: 'none', content: '', priority: 100 }
  editing.value = true
}

function startEdit(r) {
  form.value = { id: r.id, keyword: r.keyword, mode: r.mode, action: r.action, content: r.content, priority: r.priority }
  editing.value = true
}

async function onSave() {
  try {
    await saveRule(form.value)
    editing.value = false
    await load()
  } catch (e) {
    alert('保存失败：' + (e.detail || '未知错误'))
  }
}

async function toggle(r) {
  try {
    await saveRule({ ...r, enabled: !r.enabled })
    await load()
  } catch (e) {
    alert('切换失败：' + (e.detail || '未知错误'))
  }
}

async function onDelete(r) {
  if (!confirm(`确定删除关键词【${r.keyword}】吗？`)) return
  try {
    await deleteRule(r.id)
    await load()
  } catch (e) {
    alert('删除失败：' + (e.detail || '未知错误'))
  }
}

async function onSaveSettings() {
  try {
    await saveSettings(settings.value)
    alert('设置已保存')
  } catch (e) {
    alert('保存失败：' + (e.detail || '未知错误'))
  }
}

onMounted(load)
</script>
