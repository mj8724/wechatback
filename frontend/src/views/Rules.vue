<template>
  <div>
    <!-- 主规则卡片 -->
    <div class="bg-white rounded-xl shadow p-5 mt-4">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-4">
        <div>
          <h5 class="font-bold text-lg flex items-center gap-2">
            💬 关键词回复规则
            <span class="text-xs font-normal text-gray-500">按优先级升序首个命中，支持多品类配方发码</span>
          </h5>
          <p class="text-xs text-gray-400 mt-0.5">
            占位符支持：<code>{code}</code>、<code>{codes}</code>、<code>{code.KEY}</code>、<code>{openid}</code>、<code>{date}</code>、<code>{time}</code>、<code>{stock}</code>
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <button @click="downloadTemplate" class="px-3 py-1.5 rounded-lg border border-gray-300 hover:bg-gray-50 text-xs font-bold text-gray-700">
            📄 模板下载
          </button>
          <button @click="showImportModal = true" class="px-3 py-1.5 rounded-lg border border-sky-300 bg-sky-50 hover:bg-sky-100 text-xs font-bold text-sky-700">
            📥 导入 Excel
          </button>
          <button @click="exportToExcel" class="px-3 py-1.5 rounded-lg border border-emerald-300 bg-emerald-50 hover:bg-emerald-100 text-xs font-bold text-emerald-700">
            📤 导出 Excel
          </button>
          <button @click="startAdd" class="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-sm">
            + 新增规则
          </button>
        </div>
      </div>

      <!-- 规则表格 -->
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-left text-gray-500 border-b">
              <th class="py-2 pr-2 w-8">
                <input type="checkbox" :checked="isAllSelected" @change="toggleSelectAll" />
              </th>
              <th>关键词</th>
              <th>匹配</th>
              <th>动作与配方</th>
              <th>优先级</th>
              <th>开关</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!rules.length">
              <td colspan="7" class="text-center text-gray-400 py-8">暂无回复规则</td>
            </tr>
            <tr v-for="r in rules" :key="r.id" class="border-t hover:bg-gray-50">
              <td class="py-2 pr-2">
                <input type="checkbox" :value="r.id" v-model="selectedRuleIds" />
              </td>
              <td class="py-2 font-mono font-bold text-gray-800">
                <code>{{ r.keyword }}</code>
              </td>
              <td>
                <span class="text-xs px-2 py-0.5 rounded font-medium"
                  :class="r.mode === 'exact' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'">
                  {{ r.mode === 'exact' ? '完全一致' : '包含匹配' }}
                </span>
              </td>
              <td>
                <div v-if="r.action === 'code'" class="flex items-center gap-1.5">
                  <span class="text-xs bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded">🎟️ 发码</span>
                  <span class="text-xs text-gray-600">{{ formatRecipeSummary(r.recipe) }}</span>
                </div>
                <div v-else class="text-xs text-gray-500">
                  <span>💬 回复文本</span>
                </div>
              </td>
              <td><span class="text-xs font-mono font-medium">{{ r.priority }}</span></td>
              <td>
                <button @click="toggle(r)" class="text-xs px-2 py-0.5 rounded font-bold"
                  :class="r.enabled ? 'bg-green-100 text-green-700' : 'bg-gray-200 text-gray-500'">
                  {{ r.enabled ? '启用' : '停用' }}
                </button>
              </td>
              <td>
                <button @click="startEdit(r)" class="text-xs px-2 py-1 rounded bg-sky-50 text-sky-600 hover:bg-sky-100 font-bold">编辑</button>
                <button @click="onDelete(r)" class="ml-1 text-xs px-2 py-1 rounded bg-red-50 text-red-600 hover:bg-red-100 font-bold">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 批量操作悬浮条 -->
      <div v-if="selectedRuleIds.length" class="mt-4 p-3 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-between">
        <span class="text-xs text-emerald-800 font-bold">
          已选中 {{ selectedRuleIds.length }} 条规则
        </span>
        <div class="flex gap-2">
          <button @click="batchToggle(true)" class="px-3 py-1 rounded bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold">
            批量启用
          </button>
          <button @click="batchToggle(false)" class="px-3 py-1 rounded bg-gray-600 hover:bg-gray-700 text-white text-xs font-bold">
            批量停用
          </button>
          <button @click="batchDelete" class="px-3 py-1 rounded bg-red-500 hover:bg-red-600 text-white text-xs font-bold">
            批量删除
          </button>
        </div>
      </div>

      <!-- 新增/编辑规则表单组件 -->
      <RuleForm
        :visible="editing"
        :rule-data="currentRule"
        :pools="pools"
        @close="editing = false"
        @saved="onRuleSaved"
      />
    </div>

    <!-- 批量导入规则弹窗组件 -->
    <RuleImportModal
      v-model:visible="showImportModal"
      @imported="load"
    />

    <!-- 固定回复与社群配置组件 -->
    <FixedSettings />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import * as XLSX from 'xlsx'
import {
  batchDeleteRules, batchToggleRules,
  deleteRule, listPools, listRules, saveRule,
} from '../api.js'

import RuleForm from '../components/rules/RuleForm.vue'
import RuleImportModal from '../components/rules/RuleImportModal.vue'
import FixedSettings from '../components/rules/FixedSettings.vue'

const router = useRouter()
const rules = ref([])
const pools = ref([])
const editing = ref(false)
const currentRule = ref(null)
const selectedRuleIds = ref([])
const showImportModal = ref(false)

const isAllSelected = computed(() => {
  return rules.value.length > 0 && rules.value.every((r) => selectedRuleIds.value.includes(r.id))
})

function toggleSelectAll() {
  if (isAllSelected.value) {
    selectedRuleIds.value = []
  } else {
    selectedRuleIds.value = rules.value.map((r) => r.id)
  }
}

async function load() {
  try {
    const [rData, pData] = await Promise.all([
      listRules(),
      listPools().catch(() => ({ pools: [] })),
    ])
    rules.value = rData.rules || []
    pools.value = pData.pools || []
  } catch (e) {
    if (e.status === 401) router.push('/login')
  }
}

function formatRecipeSummary(recipeStr) {
  if (!recipeStr) return '(默认池×1)'
  try {
    const list = JSON.parse(recipeStr)
    if (!Array.isArray(list) || !list.length) return '(默认池×1)'
    const parts = list.map((item) => {
      const pool = pools.value.find((p) => p.id === item.pool_id || p.key === item.key)
      const name = pool ? pool.name : (item.key || `池${item.pool_id}`)
      return `${name}×${item.count || 1}`
    })
    return `(${parts.join(', ')})`
  } catch {
    return '(默认池×1)'
  }
}

function startAdd() {
  currentRule.value = null
  editing.value = true
}

function startEdit(r) {
  currentRule.value = r
  editing.value = true
}

async function onRuleSaved() {
  editing.value = false
  currentRule.value = null
  await load()
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

async function batchToggle(enabled) {
  if (!selectedRuleIds.value.length) return
  try {
    await batchToggleRules(selectedRuleIds.value, enabled)
    await load()
  } catch (e) {
    alert('批量操作失败：' + (e.detail || '未知错误'))
  }
}

async function batchDelete() {
  if (!selectedRuleIds.value.length) return
  if (!confirm(`确定批量删除选中的 ${selectedRuleIds.value.length} 条规则吗？`)) return
  try {
    await batchDeleteRules(selectedRuleIds.value)
    selectedRuleIds.value = []
    await load()
  } catch (e) {
    alert('批量删除失败：' + (e.detail || '未知错误'))
  }
}

function exportToExcel() {
  if (!rules.value.length) {
    alert('暂无规则可导出')
    return
  }
  const data = rules.value.map((r) => ({
    关键词: r.keyword,
    匹配模式: r.mode === 'exact' ? '完全一致' : '包含',
    动作: r.action === 'code' ? '发码' : '回复文本',
    发码配方: r.recipe || '',
    回复内容: r.content,
    优先级: r.priority,
    是否启用: r.enabled ? '是' : '否',
  }))
  const ws = XLSX.utils.json_to_sheet(data)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '回复规则')
  XLSX.writeFile(wb, `回复规则-${new Date().toISOString().slice(0, 10)}.xlsx`)
}

function downloadTemplate() {
  const sample = [
    {
      关键词: '激活码',
      匹配模式: '包含',
      动作: '发码',
      发码配方: '[{"key":"default","count":1}]',
      回复内容: '您的专属激活码：{code}',
      优先级: 10,
    },
    {
      关键词: 'AI',
      匹配模式: '完全一致',
      动作: '发码',
      发码配方: '[{"key":"default","count":1},{"key":"gpt","count":2}]',
      回复内容: '领到卡密：\n{codes}',
      优先级: 20,
    },
    {
      关键词: '微信群',
      匹配模式: '包含',
      动作: '回复文本',
      发码配方: '',
      回复内容: '请添加管理员微信：{group}',
      优先级: 30,
    },
  ]
  const ws = XLSX.utils.json_to_sheet(sample)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '规则模板')
  XLSX.writeFile(wb, '关键词回复规则模板.xlsx')
}

onMounted(load)
</script>
