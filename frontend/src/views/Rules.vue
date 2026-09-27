<template>
  <div class="mt-4">
    <!-- 二级导航 Tab：规则列表 / 全局变量 -->
    <div class="flex items-center justify-between mb-3">
      <div class="flex gap-2">
        <button
          @click="subTab = 'rules'"
          class="px-3.5 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5"
          :class="subTab === 'rules' ? 'bg-emerald-600 text-white shadow-sm' : 'bg-white text-gray-700 hover:bg-gray-50 border'"
        >
          <span>回复规则</span>
          <span
            class="text-[10px] px-1.5 py-0.5 rounded-full"
            :class="subTab === 'rules' ? 'bg-white/25 text-white' : 'bg-gray-100 text-gray-600'"
          >
            {{ rules.length }}
          </span>
        </button>
        <button
          @click="subTab = 'variables'"
          class="px-3.5 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1"
          :class="subTab === 'variables' ? 'bg-emerald-600 text-white shadow-sm' : 'bg-white text-gray-700 hover:bg-gray-50 border'"
        >
          <span>全局变量</span>
          <HelpTip text="在此集中管理可在回复中随处调用的 {site}、{group} 等自定义变量" />
        </button>
      </div>

      <!-- 规则操作按钮区（仅在 rules Tab 显示） -->
      <div v-show="subTab === 'rules'" class="flex items-center gap-2">
        <button @click="downloadTemplate" class="px-2.5 py-1.5 rounded-lg border border-gray-300 hover:bg-gray-50 text-xs text-gray-700 font-medium">
          模板
        </button>
        <button @click="showImportModal = true" class="px-2.5 py-1.5 rounded-lg border border-sky-200 bg-sky-50 hover:bg-sky-100 text-xs text-sky-700 font-medium">
          导入
        </button>
        <button @click="exportToExcel" class="px-2.5 py-1.5 rounded-lg border border-emerald-200 bg-emerald-50 hover:bg-emerald-100 text-xs text-emerald-700 font-medium">
          导出
        </button>
        <button @click="startAdd" class="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-sm">
          + 新增规则
        </button>
      </div>
    </div>

    <!-- 1. 规则列表卡片 -->
    <div v-show="subTab === 'rules'" class="bg-white rounded-xl shadow p-5">
      <!-- 规则表格 -->
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-left text-gray-500 border-b text-xs">
              <th class="py-2.5 pr-2 w-8">
                <input type="checkbox" :checked="isAllSelected" @change="toggleSelectAll" />
              </th>
              <th>
                触发条件
                <HelpTip text="关键词、正则模式或关注/兜底系统事件" />
              </th>
              <th>模式</th>
              <th>动作与详情</th>
              <th>
                优先级
                <HelpTip text="数字越小越先触发匹配，命中首条即返回回复" />
              </th>
              <th>状态</th>
              <th class="text-right pr-2">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!rules.length">
              <td colspan="7" class="text-center text-gray-400 py-8 text-xs">暂无回复规则</td>
            </tr>
            <tr v-for="r in rules" :key="r.id" class="border-t hover:bg-gray-50">
              <td class="py-2.5 pr-2">
                <input type="checkbox" :value="r.id" v-model="selectedRuleIds" />
              </td>
              <td class="py-2.5 font-mono text-gray-800">
                <span v-if="r.action === 'event_subscribe'" class="px-2 py-0.5 rounded bg-blue-50 text-blue-700 text-xs font-medium border border-blue-200 font-sans">
                  关注欢迎语
                </span>
                <span v-else-if="r.action === 'event_fallback'" class="px-2 py-0.5 rounded bg-amber-50 text-amber-700 text-xs font-medium border border-amber-200 font-sans">
                  默认兜底回复
                </span>
                <code v-else class="text-xs bg-gray-100 px-1.5 py-0.5 rounded text-gray-800 font-bold">{{ r.keyword }}</code>
              </td>
              <td>
                <span v-if="r.action && r.action.startsWith('event_')" class="text-[11px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">
                  事件
                </span>
                <span v-else-if="r.mode === 'regex'" class="text-[11px] px-1.5 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200 font-mono">
                  正则
                </span>
                <span v-else-if="r.mode === 'exact'" class="text-[11px] px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200">
                  全等
                </span>
                <span v-else class="text-[11px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                  包含
                </span>
              </td>
              <td>
                <div v-if="r.action === 'code'" class="flex items-center gap-1.5 flex-wrap">
                  <span class="text-xs bg-emerald-50 text-emerald-800 border border-emerald-200 font-bold px-1.5 py-0.5 rounded">发码</span>
                  <span class="text-xs text-gray-500 font-mono">{{ formatRecipeSummary(r.recipe) }}</span>
                  <span v-if="r.start_time || r.end_time" class="text-[10px] bg-sky-50 text-sky-700 border border-sky-200 px-1 py-0.2 rounded" title="设置了活动时间">
                    限时
                  </span>
                </div>
                <div v-else-if="r.action === 'event_subscribe'" class="text-xs text-blue-600">
                  关注自动回复
                </div>
                <div v-else-if="r.action === 'event_fallback'" class="text-xs text-amber-600">
                  未匹配自动回复
                </div>
                <div v-else class="text-xs text-gray-500">
                  普通文本
                </div>
              </td>
              <td><span class="text-xs font-mono font-medium">{{ r.priority }}</span></td>
              <td>
                <button
                  @click="toggle(r)"
                  class="text-xs px-2 py-0.5 rounded font-bold transition"
                  :class="r.enabled ? 'bg-emerald-100 text-emerald-800 hover:bg-emerald-200' : 'bg-gray-100 text-gray-400 hover:bg-gray-200'"
                >
                  {{ r.enabled ? '启用' : '停用' }}
                </button>
              </td>
              <td class="text-right pr-2 whitespace-nowrap">
                <button @click="startEdit(r)" class="text-xs px-2.5 py-1 rounded bg-sky-50 text-sky-600 hover:bg-sky-100 font-bold">编辑</button>
                <button @click="onDelete(r)" class="ml-1 text-xs px-2.5 py-1 rounded bg-red-50 text-red-600 hover:bg-red-100 font-bold">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 批量操作悬浮条 -->
      <div v-if="selectedRuleIds.length" class="mt-4 p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-between text-xs">
        <span class="text-emerald-800 font-bold">
          已选 {{ selectedRuleIds.length }} 条规则
        </span>
        <div class="flex gap-1.5">
          <button @click="batchToggle(true)" class="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-bold">
            批量启用
          </button>
          <button @click="batchToggle(false)" class="px-2.5 py-1 rounded bg-gray-600 hover:bg-gray-700 text-white font-bold">
            批量停用
          </button>
          <button @click="batchDelete" class="px-2.5 py-1 rounded bg-red-500 hover:bg-red-600 text-white font-bold">
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

    <!-- 2. 全局自定义变量中心组件（切换至 variables Tab 时展示） -->
    <div v-show="subTab === 'variables'">
      <CustomVariables ref="variablesRef" />
    </div>

    <!-- 批量导入规则弹窗组件 -->
    <RuleImportModal
      v-model:visible="showImportModal"
      @imported="load"
    />
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

import HelpTip from '../components/common/HelpTip.vue'
import RuleForm from '../components/rules/RuleForm.vue'
import RuleImportModal from '../components/rules/RuleImportModal.vue'
import CustomVariables from '../components/rules/CustomVariables.vue'

const router = useRouter()
const subTab = ref('rules')
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
