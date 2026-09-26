<template>
  <div class="bg-white rounded-xl shadow p-5 mt-4">
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-4">
      <div>
        <h5 class="font-bold text-lg flex items-center gap-2">
          🌐 全局变量中心
          <span class="text-xs font-normal text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded">
            随处调用
          </span>
        </h5>
        <p class="text-xs text-gray-500 mt-1">
          在任意回复文案中输入 <code>{变量名}</code> 即可自动注入对应内容。修改此处变量值，公众号所有规则即时生效。
        </p>
      </div>
      <div>
        <button
          @click="openAddModal"
          class="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-sm transition"
        >
          + 新增变量
        </button>
      </div>
    </div>

    <!-- 变量表格 -->
    <div class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="text-left text-gray-500 border-b">
            <th class="py-2.5">调用占位符</th>
            <th>变量说明</th>
            <th>当前变量值</th>
            <th class="text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!variables.length">
            <td colspan="4" class="text-center text-gray-400 py-6">暂无自定义变量</td>
          </tr>
          <tr v-for="v in variables" :key="v.id" class="border-t hover:bg-gray-50">
            <td class="py-3 font-mono">
              <span
                @click="copyPlaceholder(v.key)"
                class="cursor-pointer inline-flex items-center gap-1 px-2.5 py-1 rounded bg-emerald-50 text-emerald-800 hover:bg-emerald-100 text-xs font-bold border border-emerald-200 transition"
                title="点击快速复制占位符"
              >
                <code>{{ '{' + v.key + '}' }}</code>
                <span class="text-[10px] text-emerald-600">📋</span>
              </span>
            </td>
            <td class="text-gray-700 text-xs">
              <span v-if="v.key === 'site' || v.key === 'group'" class="text-[10px] font-bold px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 mr-1.5">
                核心系统
              </span>
              <span>{{ v.description || '无说明' }}</span>
            </td>
            <td class="text-xs text-gray-800 font-mono max-w-xs md:max-w-md truncate" :title="v.value">
              {{ v.value || '（空）' }}
            </td>
            <td class="text-right py-3 whitespace-nowrap">
              <button
                @click="openEditModal(v)"
                class="text-xs px-2.5 py-1 rounded bg-sky-50 text-sky-700 hover:bg-sky-100 font-bold"
              >
                编辑
              </button>
              <button
                v-if="v.key !== 'site' && v.key !== 'group'"
                @click="onDelete(v)"
                class="ml-1.5 text-xs px-2.5 py-1 rounded bg-red-50 text-red-600 hover:bg-red-100 font-bold"
              >
                删除
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 复制成功浮动提示 -->
    <div
      v-if="copiedTip"
      class="fixed bottom-6 right-6 z-50 px-4 py-2 bg-gray-900 text-white text-xs rounded-lg shadow-lg"
    >
      {{ copiedTip }}
    </div>

    <!-- 新增 / 编辑变量弹窗 -->
    <div
      v-if="showModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
    >
      <div class="bg-white rounded-xl shadow-xl max-w-md w-full p-5">
        <div class="flex items-center justify-between mb-4 border-b pb-2">
          <h6 class="font-bold text-base text-gray-900">
            {{ form.id ? '✏️ 编辑全局变量' : '➕ 新增全局变量' }}
          </h6>
          <button @click="showModal = false" class="text-gray-400 hover:text-gray-600 font-bold">✕</button>
        </div>

        <div class="space-y-3">
          <div>
            <label class="block text-xs font-bold text-gray-700 mb-1">
              变量标识 Key <span class="text-gray-400 font-normal">（模板中以 {key} 形式调用）</span>
            </label>
            <input
              v-model="form.key"
              :disabled="!!form.id"
              placeholder="例如：notice 或 help_url（限英文/数字/下划线）"
              class="w-full border rounded-lg px-3 py-2 text-sm outline-none font-mono focus:ring-2 focus:ring-emerald-500 disabled:bg-gray-100 disabled:text-gray-500"
            />
          </div>

          <div>
            <label class="block text-xs font-bold text-gray-700 mb-1">变量说明</label>
            <input
              v-model="form.description"
              placeholder="例如：兑换教程链接 / 紧急通知"
              class="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>

          <div>
            <label class="block text-xs font-bold text-gray-700 mb-1">变量内容 (Value)</label>
            <textarea
              v-model="form.value"
              rows="3"
              placeholder="填入替换的文本内容、网址或联系方式"
              class="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500"
            ></textarea>
          </div>
        </div>

        <div class="mt-5 flex justify-end gap-2 border-t pt-3">
          <button
            @click="showModal = false"
            class="px-4 py-2 rounded-lg border border-gray-300 text-gray-700 text-xs font-bold hover:bg-gray-50"
          >
            取消
          </button>
          <button
            @click="onSave"
            class="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-sm"
          >
            保存
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { createVariable, deleteVariable, getVariables, updateVariable } from '../../api.js'

const emit = defineEmits(['variables-updated'])

const variables = ref([])
const showModal = ref(false)
const copiedTip = ref('')

const form = ref({
  id: null,
  key: '',
  value: '',
  description: '',
})

async function loadVariables() {
  try {
    const res = await getVariables()
    variables.value = res.variables || []
    emit('variables-updated', variables.value)
  } catch (e) {
    console.error('加载全局变量失败', e)
  }
}

function openAddModal() {
  form.value = {
    id: null,
    key: '',
    value: '',
    description: '',
  }
  showModal.value = true
}

function openEditModal(v) {
  form.value = {
    id: v.id,
    key: v.key,
    value: v.value,
    description: v.description || '',
  }
  showModal.value = true
}

async function onSave() {
  const k = (form.value.key || '').trim().toLowerCase()
  if (!k) {
    alert('变量标识 Key 不能为空')
    return
  }
  if (!/^[a-zA-Z0-9_]{1,32}$/.test(k)) {
    alert('变量标识 Key 只能由字母、数字和下划线组成')
    return
  }

  try {
    if (form.value.id) {
      await updateVariable(form.value.id, {
        value: form.value.value || '',
        description: form.value.description || '',
      })
    } else {
      await createVariable({
        key: k,
        value: form.value.value || '',
        description: form.value.description || '',
      })
    }
    showModal.value = false
    await loadVariables()
  } catch (e) {
    alert('保存失败：' + (e.detail || '未知错误'))
  }
}

async function onDelete(v) {
  if (!confirm(`确定删除自定义变量 {${v.key}} 吗？`)) return
  try {
    await deleteVariable(v.id)
    await loadVariables()
  } catch (e) {
    alert('删除失败：' + (e.detail || '未知错误'))
  }
}

function copyPlaceholder(key) {
  const text = `{${key}}`
  navigator.clipboard?.writeText(text).then(() => {
    copiedTip.value = `已复制 ${text} 到剪贴板`
    setTimeout(() => {
      copiedTip.value = ''
    }, 2000)
  })
}

defineExpose({
  loadVariables,
})

onMounted(loadVariables)
</script>
