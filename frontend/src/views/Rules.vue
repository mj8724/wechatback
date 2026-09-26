<template>
  <div>
    <!-- 主规则卡片 -->
    <div class="bg-white rounded-xl shadow p-5 mt-4">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-4">
        <div>
          <h5 class="font-bold text-lg flex items-center gap-2">
            💬 公众号回复规则中心
            <span class="text-xs font-normal text-gray-500">按优先级升序命中，支持事件、正则、多状态发码</span>
          </h5>
          <p class="text-xs text-gray-400 mt-0.5">
            占位符支持：<code>{code}</code>、<code>{codes}</code>、<code>{code.KEY}</code>、<code>{openid}</code>、<code>{site}</code>、<code>{group}</code> 等全局变量
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
              <th class="py-2.5 pr-2 w-8">
                <input type="checkbox" :checked="isAllSelected" @change="toggleSelectAll" />
              </th>
              <th>触发条件 / 事件</th>
              <th>匹配模式</th>
              <th>动作与详情</th>
              <th>优先级</th>
              <th>启用开关</th>
              <th class="text-right pr-2">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!rules.length">
              <td colspan="7" class="text-center text-gray-400 py-8">暂无回复规则</td>
            </tr>
            <tr v-for="r in rules" :key="r.id" class="border-t hover:bg-gray-50">
              <td class="py-2.5 pr-2">
                <input type="checkbox" :value="r.id" v-model="selectedRuleIds" />
              </td>
              <td class="py-2.5 font-mono font-bold text-gray-800">
                <span v-if="r.action === 'event_subscribe'" class="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-blue-50 text-blue-800 font-sans text-xs border border-blue-200">
                  👋 [系统事件] 关注公众号
                </span>
                <span v-else-if="r.action === 'event_fallback'" class="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-amber-50 text-amber-800 font-sans text-xs border border-amber-200">
                  🤖 [系统事件] 无匹配未识别兜底
                </span>
                <code v-else class="text-sm">{{ r.keyword }}</code>
              </td>
              <td>
                <span v-if="r.action && r.action.startsWith('event_')" class="text-xs px-2 py-0.5 rounded font-medium bg-gray-100 text-gray-600">
                  系统事件
                </span>
                <span v-else-if="r.mode === 'regex'" class="text-xs px-2 py-0.5 rounded font-medium bg-purple-100 text-purple-800 font-mono">
                  🔣 正则匹配
                </span>
                <span v-else-if="r.mode === 'exact'" class="text-xs px-2 py-0.5 rounded font-medium bg-indigo-100 text-indigo-700">
                  完全一致
                </span>
                <span v-else class="text-xs px-2 py-0.5 rounded font-medium bg-blue-100 text-blue-700">
                  包含匹配
                </span>
              </td>
              <td>
                <div v-if="r.action === 'code'" class="flex items-center gap-1.5 flex-wrap">
                  <span class="text-xs bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded">🎟️ 发放激活码</span>
                  <span class="text-xs text-gray-600 font-mono">{{ formatRecipeSummary(r.recipe) }}</span>
                  <span v-if="r.start_time || r.end_time" class="text-[10px] bg-sky-100 text-sky-800 px-1.5 py-0.5 rounded font-medium" title="设置了活动时间限制">
                    ⏱️ 限时
                  </span>
                </div>
                <div v-else-if="r.action === 'event_subscribe'" class="text-xs text-blue-700 font-medium">
                  <span>关注欢迎语</span>
                </div>
                <div v-else-if="r.action === 'event_fallback'" class="text-xs text-amber-700 font-medium">
                  <span>默认未识别留言回复</span>
                </div>
                <div v-else class="text-xs text-gray-500">
                  <span>💬 回复普通文本</span>
                </div>
              </td>
              <td><span class="text-xs font-mono font-medium">{{ r.priority }}</span></td>
              <td>
                <button
                  @click="toggle(r)"
                  class="text-xs px-2.5 py-1 rounded font-bold transition shadow-sm"
                  :class="r.enabled ? 'bg-emerald-100 text-emerald-800 hover:bg-emerald-200' : 'bg-gray-200 text-gray-500 hover:bg-gray-300'"
                >
                  {{ r.enabled ? '✓ 已启用' : '✕ 已停用' }}
                </button>
              </td>
              <td class="text-right pr-2">
                <button @click="startEdit(r)" class="text-xs px-2.5 py-1 rounded bg-sky-50 text-sky-600 hover:bg-sky-100 font-bold">编辑</button>
                <button @click="onDelete(r)" class="ml-1.5 text-xs px-2.5 py-1 rounded bg-red-50 text-red-600 hover:bg-red-100 font-bold">删除</button>
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

    <!-- 全局自定义变量中心组件 -->
    <CustomVariables ref="variablesRef" />
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
import CustomVariables from '../components/rules/CustomVariables.vue'

const router = useRouter()
const rules = ref([])
const pools = ref([])
const editing = ref(false)
const currentRule = ref(null)
const selectedRuleIds = ref([])
const showImportModal = ref(false)
const variablesRef = ref(null)

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

async function onDelete(r) {
  const label = r.action?.startsWith('event_') ? (r.action === 'event_subscribe' ? '关注欢迎语' : '未识别兜底回复') : `"${r.keyword}"`
  if (!confirm(`确定删除规则 ${label} 吗？`)) return
  try {
    await deleteRule(r.id)
    await load()
  } catch (e) {
    alert('删除失败：' + (e.detail || '未知错误'))
  }
}

async function toggle(r) {
  try {
    await saveRule({
      keyword: r.keyword,
      mode: r.mode,
      action: r.action,
      content: r.content,
      priority: r.priority,
      enabled: !r.enabled,
      recipe: r.recipe,
      status_replies: r.status_replies,
      start_time: r.start_time,
      end_time: r.end_time,
    }, r.id)
    r.enabled = r.enabled ? 0 : 1
  } catch (e) {
    alert('操作失败：' + (e.detail || '未知错误'))
  }
}

async function batchToggle(enabled) {
  if (!selectedRuleIds.value.length) return
  try {
    await batchToggleRules(selectedRuleIds.value, enabled)
    await load()
    selectedRuleIds.value = []
  } catch (e) {
    alert('操作失败：' + (e.detail || '未知错误'))
  }
}

async function batchDelete() {
  if (!selectedRuleIds.value.length) return
  if (!confirm(`确定批量删除选中的 ${selectedRuleIds.value.length} 条规则吗？`)) return
  try {
    await batchDeleteRules(selectedRuleIds.value)
    await load()
    selectedRuleIds.value = []
  } catch (e) {
    alert('批量删除失败：' + (e.detail || '未知错误'))
  }
}

function onRuleSaved() {
  editing.value = false
  load()
}

function downloadTemplate() {
  const data = [
    {
      '关键词': '测试关键词',
      '匹配模式(contains/exact/regex)': 'contains',
      '动作(none/code)': 'code',
      '回复文案': '🎉 您的专属激活码为：【{code}】\n👉 兑换地址：{site}',
      '优先级(数字越小越先)': 100,
      '启用状态(1启用/0停用)': 1,
      '发码配方(可选格式 key1:数量,key2:数量)': 'default:1',
      '开始时间(可选 YYYY-MM-DD HH:MM:SS)': '',
      '结束时间(可选 YYYY-MM-DD HH:MM:SS)': '',
    },
  ]
  const ws = XLSX.utils.json_to_sheet(data)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '规则导入模板')
  XLSX.writeFile(wb, 'wechat_rules_template.xlsx')
}

function exportToExcel() {
  if (!rules.value.length) {
    alert('暂无规则可导出')
    return
  }
  const rows = rules.value.map((r) => ({
    'ID': r.id,
    '关键词': r.keyword,
    '匹配模式': r.mode,
    '动作': r.action,
    '优先级': r.priority,
    '启用状态': r.enabled ? '已启用' : '已停用',
    '发码配方': r.recipe || '',
    '开始时间': r.start_time || '',
    '结束时间': r.end_time || '',
    '回复内容': r.content || '',
    '创建时间': r.created_at || '',
  }))
  const ws = XLSX.utils.json_to_sheet(rows)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '回复规则列表')
  XLSX.writeFile(wb, `wechat_rules_${Date.now()}.xlsx`)
}

onMounted(load)
</script>
