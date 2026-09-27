<template>
  <div class="bg-white rounded-xl shadow p-5 mt-4">
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center gap-1.5">
        <h5 class="font-bold text-base text-gray-800">批量导入激活码</h5>
        <HelpTip text="单次最多导入 2000 个激活码，自动剔除重复项。支持纯文本每行一个，或按品类列头批量导入 Excel。" />
      </div>
      <div class="flex gap-1.5">
        <button
          @click="importTab = 'text'"
          class="px-2.5 py-1 rounded text-xs font-medium transition"
          :class="importTab === 'text' ? 'bg-emerald-600 text-white shadow-sm' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
        >
          文本粘贴
        </button>
        <button
          @click="importTab = 'excel'"
          class="px-2.5 py-1 rounded text-xs font-medium transition flex items-center gap-1"
          :class="importTab === 'excel' ? 'bg-emerald-600 text-white shadow-sm' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
        >
          <span>Excel 导入</span>
          <HelpTip text="第一行为品类名称或 Key，支持单列或多列并排导入不同卡池" />
        </button>
      </div>
    </div>

    <!-- 文本粘贴导入模式 -->
    <div v-if="importTab === 'text'">
      <div class="flex items-center gap-2 mb-2">
        <span class="text-xs text-gray-500">归属品类：</span>
        <select v-model="targetPoolId" class="border rounded-lg px-2 py-1 text-xs outline-none bg-white">
          <option v-for="p in poolList" :key="p.id" :value="p.id">{{ p.name }} ({{ p.key }})</option>
        </select>
      </div>
      <div class="flex flex-col md:flex-row gap-2">
        <textarea
          v-model="importText"
          rows="3"
          placeholder="每行一个激活码..."
          class="flex-1 border rounded-lg px-3 py-1.5 text-xs outline-none focus:ring-2 focus:ring-emerald-500 font-mono"
        ></textarea>
        <button @click="onImport" class="px-5 py-2 rounded-lg bg-sky-500 hover:bg-sky-600 text-white font-bold text-xs shadow-sm whitespace-nowrap">
          导入
        </button>
      </div>
    </div>

    <!-- Excel 导入模式 -->
    <div v-else class="space-y-3">
      <!-- 格式说明与案例卡片 -->
      <div class="p-3 bg-gray-50 border border-gray-200 rounded-lg text-xs">
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center gap-1 text-gray-700 font-bold">
            <span>📋 Excel 格式规范与案例</span>
            <HelpTip text="表头名称支持品类 key（如 default/gpt）或品类全称，大小写不敏感；多列同时导入时将分别归入各自卡池。" />
          </div>
          <button
            type="button"
            @click="downloadSampleExcel"
            class="text-xs font-bold text-emerald-700 hover:text-emerald-800 flex items-center gap-1 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded shadow-xs"
          >
            <span>📥 下载标准模板 (.xlsx)</span>
          </button>
        </div>

        <!-- 案例表格展示 -->
        <div class="overflow-x-auto">
          <table class="w-full text-center border-collapse bg-white font-mono text-[11px] rounded shadow-2xs">
            <thead>
              <tr class="bg-emerald-50 text-emerald-800 border">
                <th class="py-1 px-3 border font-bold">default (默认池)</th>
                <th class="py-1 px-3 border font-bold">gpt (AI算力)</th>
                <th class="py-1 px-3 border font-bold">vip (月卡会员)</th>
              </tr>
            </thead>
            <tbody>
              <tr class="border text-gray-500">
                <td class="py-1 px-3 border">CODE-DEF-001</td>
                <td class="py-1 px-3 border">CODE-GPT-001</td>
                <td class="py-1 px-3 border">CODE-VIP-001</td>
              </tr>
              <tr class="border text-gray-500">
                <td class="py-1 px-3 border">CODE-DEF-002</td>
                <td class="py-1 px-3 border">CODE-GPT-002</td>
                <td class="py-1 px-3 border">CODE-VIP-002</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 文件拖拽上传框 -->
      <div class="border-2 border-dashed border-gray-200 rounded-lg p-4 text-center hover:border-emerald-500 transition bg-white">
        <input type="file" accept=".xlsx, .xls" @change="handleExcelUpload" class="hidden" id="excelCodesInput" />
        <label for="excelCodesInput" class="cursor-pointer block">
          <p class="text-xs font-medium text-gray-700">点击或拖拽包含激活码的 Excel 文件 (.xlsx / .xls)</p>
          <p class="text-[11px] text-gray-400 mt-0.5">支持单列或多列并排，自动剔除空值与重复项</p>
        </label>
      </div>

      <div v-if="excelParsedCodes" class="p-3 bg-gray-50 rounded-lg text-xs space-y-1">
        <div class="font-bold text-gray-700">Excel 解析预览：</div>
        <div v-for="(codes, key) in excelParsedCodes" :key="key" class="text-gray-600">
          品类 [{{ key }}]：共 {{ codes.length }} 个码（示例: {{ codes.slice(0, 3).join(', ') }}{{ codes.length > 3 ? '...' : '' }}）
        </div>
        <button @click="onImportExcel" class="mt-2 px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-sm">
          确认导入 Excel
        </button>
      </div>
    </div>

    <div v-if="importResult" class="mt-2 text-xs">
      <p class="p-2 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
        ✅ 成功导入 {{ importResult.added }} 个<span v-if="importResult.duplicates?.length">（{{ importResult.duplicates.length }} 个重复已过滤）</span>
        <span v-if="importResult.by_pool" class="ml-2 font-mono">
          ({{ Object.entries(importResult.by_pool).map(([k, v]) => `${k}: +${v}`).join(', ') }})
        </span>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import * as XLSX from 'xlsx'
import { importCodes } from '../../api.js'
import HelpTip from '../common/HelpTip.vue'

const props = defineProps({
  poolList: {
    type: Array,
    default: () => [],
  },
  currentPoolId: {
    type: Number,
    default: 1,
  },
})

const emit = defineEmits(['imported'])

const importTab = ref('text')
const targetPoolId = ref(1)
const importText = ref('')
const importResult = ref(null)
const excelParsedCodes = ref(null)

watch(() => props.currentPoolId, (id) => {
  if (id) targetPoolId.value = id
}, { immediate: true })

async function onImport() {
  const codes = importText.value
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean)

  if (!codes.length) {
    alert('请输入至少一个激活码')
    return
  }

  try {
    const res = await importCodes({
      pool_id: targetPoolId.value,
      codes,
    })
    importResult.value = res
    importText.value = ''
    emit('imported')
  } catch (e) {
    alert('导入失败：' + (e.detail || '未知错误'))
  }
}

function handleExcelUpload(event) {
  const file = event.target.files[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const data = new Uint8Array(e.target.result)
      const workbook = XLSX.read(data, { type: 'array' })
      const firstSheet = workbook.Sheets[workbook.SheetNames[0]]
      const jsonRows = XLSX.utils.sheet_to_json(firstSheet, { header: 1 })

      if (!jsonRows.length) {
        alert('Excel 内容为空')
        return
      }

      const headers = jsonRows[0].map((h) => String(h || '').trim())
      const parsed = {}

      for (let c = 0; c < headers.length; c++) {
        const rawHeader = headers[c]
        if (!rawHeader) continue

        const matchedPool = props.poolList.find(
          (p) => p.name.toLowerCase() === rawHeader.toLowerCase() || p.key.toLowerCase() === rawHeader.toLowerCase()
        )
        const poolKey = matchedPool ? matchedPool.key : rawHeader.toLowerCase()

        const codesInCol = []
        for (let r = 1; r < jsonRows.length; r++) {
          const val = jsonRows[r] ? jsonRows[r][c] : null
          if (val !== undefined && val !== null && String(val).trim()) {
            codesInCol.push(String(val).trim())
          }
        }

        if (codesInCol.length > 0) {
          parsed[poolKey] = (parsed[poolKey] || []).concat(codesInCol)
        }
      }

      if (!Object.keys(parsed).length) {
        alert('未在 Excel 中识别到有效的列头或激活码数据')
        return
      }

      excelParsedCodes.value = parsed
    } catch (err) {
      alert('解析 Excel 失败：' + err.message)
    }
  }
  reader.readAsArrayBuffer(file)
  event.target.value = ''
}

async function onImportExcel() {
  if (!excelParsedCodes.value) return

  try {
    const res = await importCodes({
      multi_pool_codes: excelParsedCodes.value,
    })
    importResult.value = res
    excelParsedCodes.value = null
    emit('imported')
  } catch (e) {
    alert('导入 Excel 失败：' + (e.detail || '未知错误'))
  }
}

function downloadSampleExcel() {
  // 根据当前系统已有卡池动态生成，或提供标准样例
  const cols = props.poolList.length
    ? props.poolList.map((p) => p.key)
    : ['default', 'gpt', 'vip']

  const sampleRows = [
    cols.map((k) => `SAMPLE-${k.toUpperCase()}-001`),
    cols.map((k) => `SAMPLE-${k.toUpperCase()}-002`),
    cols.map((k) => `SAMPLE-${k.toUpperCase()}-003`),
  ]

  const sheetData = [cols, ...sampleRows]
  const ws = XLSX.utils.aoa_to_sheet(sheetData)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '激活码导入模板')
  XLSX.writeFile(wb, 'codes_import_sample.xlsx')
}
</script>
