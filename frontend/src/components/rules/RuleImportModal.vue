<template>
  <div v-if="visible" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
    <div class="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[85vh] overflow-y-auto p-5">
      <div class="flex items-center justify-between mb-4 pb-2 border-b">
        <h5 class="font-bold text-lg">📥 批量导入关键词规则 (Excel)</h5>
        <button @click="$emit('update:visible', false)" class="text-gray-400 hover:text-gray-600 text-xl font-bold">✕</button>
      </div>

      <div class="space-y-3">
        <div class="border-2 border-dashed border-gray-300 rounded-lg p-5 text-center hover:border-emerald-500 transition">
          <input type="file" accept=".xlsx, .xls" @change="handleRulesExcelUpload" class="hidden" id="rulesExcelInput" />
          <label for="rulesExcelInput" class="cursor-pointer block">
            <p class="text-sm font-medium text-gray-700">点击选择或拖拽包含规则的 Excel 文件 (.xlsx)</p>
            <p class="text-xs text-gray-400 mt-1">若没有标准格式，可点击右上角「📄 模板下载」获取模版</p>
          </label>
        </div>

        <!-- 解析预览 -->
        <div v-if="parsedRules && parsedRules.length" class="space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-gray-700">已解析 {{ parsedRules.length }} 条规则（展示前 5 条预览）：</span>
            <div class="flex items-center gap-2">
              <span class="text-xs text-gray-500">同名关键词冲突：</span>
              <select v-model="importConflictMode" class="border rounded px-2 py-0.5 text-xs outline-none">
                <option value="skip">跳过已存在</option>
                <option value="overwrite">覆盖更新已有规则</option>
              </select>
            </div>
          </div>

          <div class="overflow-x-auto max-h-48 border rounded">
            <table class="w-full text-xs">
              <thead>
                <tr class="bg-gray-100 text-gray-600 text-left">
                  <th class="p-1">关键词</th>
                  <th>模式</th>
                  <th>动作</th>
                  <th>配方</th>
                  <th>优先级</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(pr, i) in parsedRules.slice(0, 5)" :key="i" class="border-t">
                  <td class="p-1 font-bold">{{ pr.keyword }}</td>
                  <td>{{ pr.mode }}</td>
                  <td>{{ pr.action }}</td>
                  <td>{{ pr.recipe || '-' }}</td>
                  <td>{{ pr.priority }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <button
            @click="submitBatchImport"
            class="w-full py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-sm"
          >
            确认批量导入这 {{ parsedRules.length }} 条规则
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import * as XLSX from 'xlsx'
import { batchImportRules } from '../../api.js'

defineProps({
  visible: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:visible', 'imported'])

const parsedRules = ref([])
const importConflictMode = ref('skip')

function handleRulesExcelUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (evt) => {
    try {
      const data = new Uint8Array(evt.target.result)
      const workbook = XLSX.read(data, { type: 'array' })
      const firstSheet = workbook.Sheets[workbook.SheetNames[0]]
      const rows = XLSX.utils.sheet_to_json(firstSheet)
      if (!rows.length) {
        alert('Excel 内容为空')
        return
      }

      const list = []
      rows.forEach((r) => {
        const kw = r['关键词'] || r['keyword'] || ''
        if (!kw) return
        const mode = (r['匹配模式'] || r['mode'] || 'contains').includes('完全') ? 'exact' : 'contains'
        const action = (r['动作'] || r['action'] || 'none').includes('发码') || (r['动作'] === 'code') ? 'code' : 'none'
        const content = r['回复内容'] || r['content'] || ''
        const priority = parseInt(r['优先级'] || r['priority'] || 100)
        const recipe = r['发码配方'] || r['recipe'] || ''
        list.push({
          keyword: String(kw).trim(),
          mode,
          action,
          content: String(content),
          priority: isNaN(priority) ? 100 : priority,
          enabled: true,
          recipe: typeof recipe === 'object' ? JSON.stringify(recipe) : String(recipe),
        })
      })

      if (!list.length) {
        alert('未解析到包含有效【关键词】的行')
        return
      }
      parsedRules.value = list
    } catch (err) {
      alert('解析 Excel 失败：' + err.message)
    }
  }
  reader.readAsArrayBuffer(file)
}

async function submitBatchImport() {
  if (!parsedRules.value.length) return
  try {
    const res = await batchImportRules(parsedRules.value, importConflictMode.value)
    alert(`导入成功！新增 ${res.added} 条，更新 ${res.updated} 条，跳过 ${res.skipped} 条`)
    parsedRules.value = []
    emit('update:visible', false)
    emit('imported')
  } catch (e) {
    alert('批量导入失败：' + (e.detail || '未知错误'))
  }
}
</script>
