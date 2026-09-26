<template>
  <div v-if="visible" class="mt-5 p-4 rounded-xl bg-gray-50 border border-gray-200 shadow-sm">
    <div class="flex items-center justify-between mb-3 border-b pb-2">
      <h6 class="font-bold text-sm text-gray-800">{{ form.id ? '✏️ 编辑规则' : '➕ 新增规则' }}</h6>
      <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 font-bold">✕</button>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-4 gap-2 mb-3">
      <div>
        <label class="block text-xs font-medium text-gray-600 mb-1">触发关键词</label>
        <input
          v-model="form.keyword"
          placeholder="例如：激活码 或 兑换"
          class="w-full border rounded-lg px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
        />
      </div>
      <div>
        <label class="block text-xs font-medium text-gray-600 mb-1">匹配模式</label>
        <select v-model="form.mode" class="w-full border rounded-lg px-3 py-1.5 text-sm outline-none bg-white">
          <option value="contains">包含匹配 (包含关键词即命中)</option>
          <option value="exact">完全一致 (发送内容需全等)</option>
        </select>
      </div>
      <div>
        <label class="block text-xs font-medium text-gray-600 mb-1">触发动作</label>
        <select v-model="form.action" class="w-full border rounded-lg px-3 py-1.5 text-sm outline-none bg-white">
          <option value="none">仅回复文本内容</option>
          <option value="code">🎟️ 发放激活码（一人一套）</option>
        </select>
      </div>
      <div>
        <label class="block text-xs font-medium text-gray-600 mb-1">优先级 (越小越优先)</label>
        <input
          v-model.number="form.priority"
          type="number"
          placeholder="默认 100"
          class="w-full border rounded-lg px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
        />
      </div>
    </div>

    <!-- 组合发码配方设计器 -->
    <div v-if="form.action === 'code'" class="mb-3 p-3 bg-white rounded-lg border border-emerald-200">
      <div class="flex items-center justify-between mb-2">
        <span class="text-xs font-bold text-emerald-800">🎟️ 发码配方（组合发码）</span>
        <button type="button" @click="addRecipeItem" class="text-xs text-emerald-600 hover:text-emerald-700 font-bold">
          + 添加品类项
        </button>
      </div>
      <div v-if="!form.recipeItems.length" class="text-xs text-gray-400 py-1">
        未配置具体品类，默认将发放 1 张默认卡券池激活码。
      </div>
      <div v-for="(item, idx) in form.recipeItems" :key="idx" class="flex items-center gap-2 mb-2">
        <span class="text-xs text-gray-500">品类：</span>
        <select v-model="item.pool_id" class="border rounded px-2 py-1 text-xs outline-none bg-white">
          <option v-for="p in pools" :key="p.id" :value="p.id">{{ p.name }} (key: {{ p.key }})</option>
        </select>
        <span class="text-xs text-gray-500">数量：</span>
        <input v-model.number="item.count" type="number" min="1" max="100" class="w-20 border rounded px-2 py-1 text-xs outline-none bg-white" />
        <span class="text-xs text-gray-500">张</span>
        <button type="button" @click="removeRecipeItem(idx)" class="text-xs text-red-500 hover:text-red-700 ml-2">
          删除
        </button>
      </div>
    </div>

    <!-- 回复文本与快捷占位符点击器 -->
    <div>
      <div class="flex items-center justify-between mb-1">
        <label class="block text-xs font-medium text-gray-600">回复文本内容</label>
        <span class="text-xs text-gray-400">点击下方标签即可快速插入占位符</span>
      </div>

      <!-- 占位符快捷点选条 -->
      <div class="flex flex-wrap gap-1.5 mb-2">
        <button type="button" @click="insertPlaceholder('{code}')" class="px-2 py-0.5 rounded bg-emerald-100 hover:bg-emerald-200 text-xs text-emerald-800 font-bold border border-emerald-300">
          🎟️ {code} (当前规则卡密)
        </button>
        <button type="button" @click="insertPlaceholder('{codes}')" class="px-2 py-0.5 rounded bg-gray-200 hover:bg-emerald-100 text-xs text-gray-700">
          {codes} (清单)
        </button>
        <button
          v-for="p in pools"
          :key="p.id"
          type="button"
          @click="insertPlaceholder(`{code.${p.key}}`)"
          class="px-2 py-0.5 rounded bg-sky-50 hover:bg-sky-100 text-xs text-sky-700 font-mono"
        >
          {{ '{code.' + p.key + '}' }} ({{ p.name }})
        </button>
        <button type="button" @click="insertPlaceholder('{openid}')" class="px-2 py-0.5 rounded bg-gray-200 hover:bg-emerald-100 text-xs text-gray-700">
          {openid}
        </button>
        <button type="button" @click="insertPlaceholder('{date}')" class="px-2 py-0.5 rounded bg-gray-200 hover:bg-emerald-100 text-xs text-gray-700">
          {date}
        </button>
        <button type="button" @click="insertPlaceholder('{time}')" class="px-2 py-0.5 rounded bg-gray-200 hover:bg-emerald-100 text-xs text-gray-700">
          {time}
        </button>
        <button type="button" @click="insertPlaceholder('{stock}')" class="px-2 py-0.5 rounded bg-gray-200 hover:bg-emerald-100 text-xs text-gray-700">
          {stock}
        </button>
        <button type="button" @click="insertPlaceholder('{site}')" class="px-2 py-0.5 rounded bg-gray-200 hover:bg-emerald-100 text-xs text-gray-700">
          {site}
        </button>
        <button type="button" @click="insertPlaceholder('{group}')" class="px-2 py-0.5 rounded bg-gray-200 hover:bg-emerald-100 text-xs text-gray-700">
          {group}
        </button>
      </div>

      <textarea
        id="ruleContentTextarea"
        v-model="form.content"
        rows="4"
        placeholder="输入回复文本。发码类建议使用 {code} 或 {codes}，支持多行文本与 Emoji 表情。"
        class="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500 font-sans bg-white"
      ></textarea>
    </div>

    <div class="mt-3 flex gap-2">
      <button @click="onSave" class="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold">
        {{ form.id ? '保存更新' : '立即创建' }}
      </button>
      <button @click="$emit('close')" class="px-4 py-2 rounded-lg bg-gray-200 text-sm text-gray-700">
        取消
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { saveRule } from '../../api.js'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false,
  },
  ruleData: {
    type: Object,
    default: () => null,
  },
  pools: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['close', 'saved'])

const form = ref({
  id: null,
  keyword: '',
  mode: 'contains',
  action: 'none',
  content: '',
  priority: 100,
  recipeItems: [],
})

watch(() => props.ruleData, (r) => {
  if (!r) {
    form.value = {
      id: null,
      keyword: '',
      mode: 'contains',
      action: 'none',
      content: '',
      priority: 100,
      recipeItems: props.pools.length ? [{ pool_id: props.pools[0].id, count: 1 }] : [],
    }
    return
  }

  let recipeItems = []
  if (r.recipe) {
    try {
      const parsed = JSON.parse(r.recipe)
      if (Array.isArray(parsed)) {
        recipeItems = parsed.map((it) => ({
          pool_id: it.pool_id || (props.pools.find((p) => p.key === it.key)?.id || 1),
          count: it.count || 1,
        }))
      }
    } catch {}
  }
  if (!recipeItems.length && r.action === 'code') {
    recipeItems = props.pools.length ? [{ pool_id: props.pools[0].id, count: 1 }] : []
  }

  form.value = {
    id: r.id,
    keyword: r.keyword,
    mode: r.mode,
    action: r.action,
    content: r.content,
    priority: r.priority,
    recipeItems,
  }
}, { immediate: true })

function addRecipeItem() {
  const defaultPoolId = props.pools.length ? props.pools[0].id : 1
  form.value.recipeItems.push({ pool_id: defaultPoolId, count: 1 })
}

function removeRecipeItem(idx) {
  form.value.recipeItems.splice(idx, 1)
}

function insertPlaceholder(tag) {
  const el = document.getElementById('ruleContentTextarea')
  if (!el) {
    form.value.content = (form.value.content || '') + tag
    return
  }
  const start = el.selectionStart || 0
  const end = el.selectionEnd || 0
  const txt = form.value.content || ''
  form.value.content = txt.slice(0, start) + tag + txt.slice(end)
  setTimeout(() => {
    el.focus()
    el.setSelectionRange(start + tag.length, start + tag.length)
  }, 10)
}

async function onSave() {
  if (!form.value.keyword.trim()) {
    alert('关键词不能为空')
    return
  }
  let recipeJson = ''
  if (form.value.action === 'code' && form.value.recipeItems.length) {
    const list = form.value.recipeItems.map((it) => {
      const p = props.pools.find((pool) => pool.id === it.pool_id)
      return {
        pool_id: it.pool_id,
        key: p ? p.key : 'default',
        count: Math.max(1, parseInt(it.count || 1)),
      }
    })
    recipeJson = JSON.stringify(list)
  }

  try {
    await saveRule({
      id: form.value.id,
      keyword: form.value.keyword.trim(),
      mode: form.value.mode,
      action: form.value.action,
      content: form.value.content,
      priority: form.value.priority,
      recipe: recipeJson,
    })
    emit('saved')
  } catch (e) {
    alert('保存失败：' + (e.detail || '未知错误'))
  }
}
</script>
