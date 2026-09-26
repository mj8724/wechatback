<template>
  <div class="bg-white rounded-xl shadow p-5 mt-4">
    <div class="flex items-center justify-between mb-3">
      <h5 class="font-bold">📥 批量导入激活码 <span class="text-xs font-normal text-gray-400">单次最多 2000 个</span></h5>
      <div class="flex gap-2">
        <button
          @click="importTab = 'text'"
          class="px-3 py-1 rounded text-xs font-bold"
          :class="importTab === 'text' ? 'bg-emerald-600 text-white' : 'bg-gray-100 text-gray-600'"
        >
          文本粘贴导入
        </button>
        <button
          @click="importTab = 'excel'"
          class="px-3 py-1 rounded text-xs font-bold"
          :class="importTab === 'excel' ? 'bg-emerald-600 text-white' : 'bg-gray-100 text-gray-600'"
        >
          Excel 多列批量导入
        </button>
      </div>
    </div>

    <!-- 文本粘贴导入模式 -->
    <div v-if="importTab === 'text'">
      <div class="flex items-center gap-3 mb-2">
        <span class="text-xs text-gray-600 font-medium">导入归属品类池：</span>
        <select v-model="targetPoolId" class="border rounded-lg px-2.5 py-1 text-xs outline-none">
          <option v-for="p in poolList" :key="p.id" :value="p.id">{{ p.name }} (key: {{ p.key }})</option>
        </select>
      </div>
      <div class="flex flex-col md:flex-row gap-2">
        <textarea
          v-model="importText"
          rows="3"
          placeholder="每行一个激活码，粘贴到这里..."
          class="flex-1 border rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-emerald-500"
        ></textarea>
        <button @click="onImport" class="px-6 py-2 rounded-lg bg-sky-500 hover:bg-sky-600 text-white font-bold">
          导入
        </button>
      </div>
    </div>

    <!-- Excel 导入模式 -->
    <div v-else class="space-y-3">
      <div class="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center hover:border-emerald-500 transition">
        <input type="file" accept=".xlsx, .xls" @change="handleExcelUpload" class="hidden" id="excelCodesInput" />
        <label for="excelCodesInput" class="cursor-pointer block">
          <p class="text-sm font-medium text-gray-700">点击选择或拖拽包含激活码的 Excel 文件 (.xlsx)</p>
          <p class="text-xs text-gray-400 mt-1">支持多列，每列列头对应品类名称或品类 key（如 gpt、default）</p>
        </label>
      </div>
      <div v-if="excelParsedCodes" class="p-3 bg-gray-50 rounded-lg text-xs space-y-1">
        <div class="font-bold text-gray-700">Excel 解析预览：</div>
        <div v-for="(codes, key) in excelParsedCodes" :key="key">
          品类 [{{ key }}]：共识别 {{ codes.length }} 个激活码（示例: {{ codes.slice(0, 3).join(', ') }}{{ codes.length > 3 ? '...' : '' }}）
        </div>
        <button @click="onImportExcel" class="mt-2 px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold">
          确认导入 Excel 激活码
        </button>
      </div>
    </div>

    <div v-if="importResult" class="mt-3 text-sm">
      <p class="p-2 rounded bg-emerald-50 text-emerald-700">
        ✅ 成功导入 {{ importResult.added }} 个<span v-if="importResult.duplicates?.length">，{{ importResult.duplicates.length }} 个重复已剔除</span>
        <span v-if="importResult.by_pool" class="ml-2 font-mono text-xs">
          ({{ Object.entries(importResult.by_pool).map(([k, v]) => `${k}: +${v}`).join(', ') }})
        </span>
      </p>
      <p v-if="importResult.duplicates?.length" class="mt-1 p-2 rounded bg-amber-50 text-amber-700 break-all">
        重复码：{{ importResult.duplicates.join('、') }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import * as XLSX from 'xlsx'
import { importCodes } from '../../api.js'

const props = defineProps({
  poolList: {
    type: Array,
    default: () => [],
  },
  currentPoolId: {
    type: [Number, String, null],
    default: null,
  },
})

const emit = defineEmits(['imported'])

const importTab = ref('text')
const targetPoolId = ref(props.currentPoolId || 1)
const importText = ref('')
const importResult = ref(null)
const excelParsedCodes = ref(null)

watch(() => props.currentPoolId, (newId) => {
  if (newId) targetPoolId.value = newId
}, { immediate: true })

async function onImport() {
  const lines = importText.value.split('\n').map((s) => s.trim()).filter(Boolean)
  if (!lines.length) return
  try {
    const data = await importCodes({ codes: lines, pool_id: targetPoolId.value })
    importResult.value = data
    importText.value = ''
    emit('imported')
  } catch (e) {
    alert('导入失败：' + (e.detail || '未知错误'))
  }
}

function handleExcelUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (evt) => {
    try {
      const data = new Uint8Array(evt.target.result)
      const workbook = XLSX.read(data, { type: 'array' })
      const firstSheet = workbook.Sheets[workbook.SheetNames[0]]
      const json = XLSX.utils.sheet_to_json(firstSheet, { header: 1 })
      if (!json || json.length < 2) {
        alert('Excel 内容为空或缺少表头')
        return
      }
      const headers = json[0]
      const rows = json.slice(1)
      const result = {}

      headers.forEach((h, colIdx) => {
        if (!h) return
        const headerKey = String(h).trim()
        const pool = props.poolList.find((p) => p.key.toLowerCase() === headerKey.toLowerCase() || p.name === headerKey)
        const targetKey = pool ? pool.key : headerKey.toLowerCase()
        const colCodes = []
        rows.forEach((row) => {
          const val = row[colIdx]
          if (val !== undefined && val !== null && String(val).trim()) {
            colCodes.push(String(val).trim())
          }
        })
        if (colCodes.length) {
          result[targetKey] = colCodes
        }
      })

      if (Object.keys(result).length === 0) {
        alert('未解析到有效激活码列')
        return
      }
      excelParsedCodes.value = result
    } catch (err) {
      alert('Excel 解析失败：' + err.message)
    }
  }
  reader.readAsArrayBuffer(file)
}

async function onImportExcel() {
  if (!excelParsedCodes.value) return
  try {
    const data = await importCodes({ multi_pool_codes: excelParsedCodes.value })
    importResult.value = data
    excelParsedCodes.value = null
    const fileEl = document.getElementById('excelCodesInput')
    if (fileEl) fileEl.value = ''
    emit('imported')
  } catch (e) {
    alert('Excel 导入失败：' + (e.detail || '未知错误'))
  }
}
</script>
