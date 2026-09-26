<template>
  <div v-if="visible" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
    <div class="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[88vh] overflow-y-auto p-5">
      <div class="flex items-center justify-between mb-3 pb-2 border-b">
        <h5 class="font-bold text-lg">⚙️ 卡券品类池管理</h5>
        <button @click="$emit('update:visible', false)" class="text-gray-400 hover:text-gray-600 text-xl font-bold">×</button>
      </div>

      <!-- 卡池与占位符通俗原理解释 -->
      <div class="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-xl text-xs text-blue-900 leading-relaxed">
        <div class="font-bold flex items-center gap-1 mb-1">
          💡 怎么在自动回复中发这些卡券？（极简易懂）
        </div>
        <p>• <b>单卡池发码（90% 最常用）</b>：在“💬 回复”里新建或编辑规则，配方选择想发的卡池，回复内容中直接写 <code>{code}</code> 即可！规则选了什么池，<code>{code}</code> 就自动发该池的码，简单自然。</p>
        <p>• <b>组合发码（一条规则发多种券）</b>：一条规则同时发多种卡券（如买一送一）时，可用 <code>{code.代号}</code> 分别指定不同卡券，或写 <code>{codes}</code> 自动生成完整清单！</p>
      </div>

      <!-- 已有品类列表 -->
      <div class="mb-5">
        <h6 class="font-bold text-sm text-gray-700 mb-2">已创建品类列表</h6>
        <div class="overflow-x-auto">
          <table class="w-full text-xs">
            <thead>
              <tr class="text-left text-gray-500 border-b">
                <th class="py-1.5">ID</th>
                <th>品类名称</th>
                <th>英文代号 (组合发码占位符)</th>
                <th>总数</th>
                <th>已领</th>
                <th>待领</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in poolList" :key="p.id" class="border-b hover:bg-gray-50">
                <td class="py-2">{{ p.id }}</td>
                <td class="font-bold text-gray-800">{{ p.name }}</td>
                <td>
                  <span class="px-2 py-0.5 rounded bg-sky-50 text-sky-700 font-mono border border-sky-200">
                    {{ '{code.' + p.key + '}' }}
                  </span>
                </td>
                <td>{{ p.total }}</td>
                <td>{{ p.used }}</td>
                <td class="text-emerald-600 font-bold">{{ p.unused }}</td>
                <td>
                  <button
                    v-if="p.id !== 1"
                    @click="onDeletePool(p)"
                    class="px-2 py-0.5 rounded bg-red-50 text-red-600 hover:bg-red-100 font-bold"
                  >
                    删除
                  </button>
                  <span v-else class="text-gray-400">系统默认池</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 新增品类表单 -->
      <div class="p-4 bg-gray-50 border border-gray-200 rounded-xl">
        <h6 class="font-bold text-sm text-gray-800 mb-3 flex items-center gap-1.5">
          <span>➕ 新增卡券品类</span>
          <span class="text-xs font-normal text-gray-500">（创建后即可在自动回复中选择发码）</span>
        </h6>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <div>
            <label class="block text-xs font-bold text-gray-700 mb-1">
              1. 品类名称 <span class="text-red-500">*</span>
            </label>
            <input
              v-model="newPoolForm.name"
              placeholder="例如：ChatGPT 4.0、百度网盘月卡"
              class="w-full border bg-white rounded-lg px-3 py-2 text-xs outline-none focus:ring-2 focus:ring-emerald-500"
            />
            <p class="text-[11px] text-gray-400 mt-1">后台展示及清单【品类名】中对粉丝显示的中文名称</p>
          </div>

          <div>
            <label class="block text-xs font-bold text-gray-700 mb-1">
              2. 英文代号 (Key) <span class="text-red-500">*</span>
            </label>
            <input
              v-model="newPoolForm.key"
              @input="newPoolForm.key = newPoolForm.key.toLowerCase().replace(/[^a-z0-9_]/g, '')"
              placeholder="输入自定义英文/数字代号，如 gpt"
              class="w-full border bg-white rounded-lg px-3 py-2 text-xs font-mono outline-none focus:ring-2 focus:ring-emerald-500"
            />
            <p class="text-[11px] text-gray-400 mt-1">多品类组合发码时通过 {code.代号} 精准区分</p>
          </div>
        </div>

        <div class="mb-3">
          <label class="block text-xs font-medium text-gray-600 mb-1">说明描述备注（可选）</label>
          <input
            v-model="newPoolForm.description"
            placeholder="例如：2026到期采购批次"
            class="w-full border bg-white rounded-lg px-3 py-1.5 text-xs outline-none"
          />
        </div>

        <!-- 实时占位符效果联动预览 -->
        <div class="p-3 bg-emerald-50 border border-emerald-200 rounded-lg mb-3">
          <div class="text-xs font-bold text-emerald-900 mb-1 flex items-center gap-1">
            <span>🎯 发码占位符使用方式：</span>
          </div>
          <div class="text-xs text-emerald-800 space-y-1">
            <p>
              • <b>单卡券发码（推荐）</b>：回复模板直接写 <code class="px-1.5 py-0.5 rounded bg-white font-bold text-emerald-700 border border-emerald-300">{code}</code>，发码时自动扣减本卡池！
            </p>
            <p>
              • <b>多卡券组合发码</b>：若本卡券与其他卡券在同一规则发放，可用 <code class="px-1.5 py-0.5 rounded bg-white font-bold text-emerald-700 border border-emerald-300">{{ '{code.' + (newPoolForm.key || '代号') + '}' }}</code> 精确指定。
            </p>
          </div>
        </div>

        <div class="flex justify-end pt-1">
          <button
            @click="onCreatePool"
            class="px-6 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-sm transition"
          >
            确认创建品类
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { createPool, deletePool } from '../../api.js'

defineProps({
  visible: {
    type: Boolean,
    default: false,
  },
  poolList: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['update:visible', 'changed', 'created'])

const newPoolForm = ref({ name: '', key: '', description: '' })

async function onCreatePool() {
  const name = newPoolForm.value.name.trim()
  const key = newPoolForm.value.key.trim().toLowerCase()
  const desc = newPoolForm.value.description.trim()
  if (!name || !key) {
    alert('请填写品类名称与英文代号(Key)')
    return
  }
  try {
    const res = await createPool({ name, key, description: desc })
    alert(`品类【${name}】创建成功！`)
    newPoolForm.value = { name: '', key: '', description: '' }
    emit('changed')
    if (res.id) {
      emit('created', res.id)
    }
  } catch (e) {
    alert('创建品类失败：' + (e.detail || '未知错误'))
  }
}

async function onDeletePool(p) {
  if (p.id === 1) {
    alert('默认卡券池禁止删除')
    return
  }
  if (!confirm(`确定删除品类【${p.name}】(${p.key}) 吗？若池内有卡密将无法删除。`)) return
  try {
    await deletePool(p.id)
    alert('品类删除成功')
    emit('changed')
  } catch (e) {
    alert('删除失败：' + (e.detail || '未知错误'))
  }
}
</script>
