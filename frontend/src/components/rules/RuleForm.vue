<template>
  <div v-if="visible" class="mt-5 p-4 rounded-xl bg-gray-50 border border-gray-200 shadow-sm">
    <div class="flex items-center justify-between mb-3 border-b pb-2">
      <h6 class="font-bold text-sm text-gray-800">{{ form.id ? '✏️ 编辑规则' : '➕ 新增规则' }}</h6>
      <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 font-bold">✕</button>
    </div>

    <!-- 基础参数配置行 -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-2 mb-3">
      <div>
        <label class="block text-xs font-medium text-gray-600 mb-1">
          {{ isEventAction ? '系统触发事件' : '触发关键词' }}
        </label>
        <input
          v-if="!isEventAction"
          v-model="form.keyword"
          :placeholder="form.mode === 'regex' ? '例如：^(领|求)?码\\d*$' : '例如：激活码 或 兑换'"
          class="w-full border rounded-lg px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-emerald-500 bg-white font-mono"
        />
        <div v-else class="px-3 py-1.5 rounded-lg bg-gray-200 text-gray-700 text-xs font-bold">
          {{ form.action === 'event_subscribe' ? '关注/扫码事件 (subscribe)' : '无关键词命中兜底 (fallback)' }}
        </div>
      </div>

      <div>
        <label class="block text-xs font-medium text-gray-600 mb-1">匹配模式</label>
        <select
          v-model="form.mode"
          :disabled="isEventAction"
          class="w-full border rounded-lg px-3 py-1.5 text-sm outline-none bg-white disabled:bg-gray-100"
        >
          <option value="contains">包含匹配 (包含关键词即命中)</option>
          <option value="exact">完全一致 (发送内容需全等)</option>
          <option value="regex">🔣 正则表达式匹配 (Regex)</option>
        </select>
      </div>

      <div>
        <label class="block text-xs font-medium text-gray-600 mb-1">触发动作</label>
        <select v-model="form.action" class="w-full border rounded-lg px-3 py-1.5 text-sm outline-none bg-white">
          <option value="code">🎟️ 发放激活码（一人一套/防超发）</option>
          <option value="none">💬 仅回复文本内容</option>
          <option value="event_subscribe">👋 关注公众号欢迎语（事件）</option>
          <option value="event_fallback">🤖 默认未命中回复（事件）</option>
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

    <!-- 1. 发码专属：多品类配方设计器 -->
    <div v-if="form.action === 'code'" class="mb-3 p-3 bg-white rounded-lg border border-emerald-200">
      <div class="flex items-center justify-between mb-2">
        <span class="text-xs font-bold text-emerald-800">🎟️ 发码配方设置（支持跨卡池组合发码）</span>
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

    <!-- 2. 发码专属：活动时间限制（可选） -->
    <div v-if="form.action === 'code'" class="mb-3 p-3 bg-white rounded-lg border border-gray-200">
      <div class="flex items-center justify-between">
        <label class="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" v-model="enableTimeLimit" class="rounded text-emerald-600" />
          <span class="text-xs font-bold text-gray-800">⏱️ 开启活动领取时间限制（可选）</span>
        </label>
        <span class="text-[11px] text-gray-400">仅在指定时间范围内允许领码</span>
      </div>

      <div v-if="enableTimeLimit" class="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3 pt-2 border-t">
        <div>
          <label class="block text-xs text-gray-600 mb-1">开始时间 (Start Time)</label>
          <input
            v-model="form.start_time"
            placeholder="格式：2026-10-01 00:00:00"
            class="w-full border rounded px-3 py-1.5 text-xs outline-none font-mono focus:ring-1 focus:ring-emerald-500"
          />
        </div>
        <div>
          <label class="block text-xs text-gray-600 mb-1">结束时间 (End Time)</label>
          <input
            v-model="form.end_time"
            placeholder="格式：2026-10-07 23:59:59"
            class="w-full border rounded px-3 py-1.5 text-xs outline-none font-mono focus:ring-1 focus:ring-emerald-500"
          />
        </div>
      </div>
    </div>

    <!-- 3. 回复文案配置：发码多状态分支 VS 普通单文案 -->
    <div>
      <div class="flex items-center justify-between mb-2">
        <label class="block text-xs font-bold text-gray-700">
          {{ form.action === 'code' ? '💬 分支回复文案配置（独立应对不同业务状态）' : '💬 回复文本内容' }}
        </label>
        <span class="text-xs text-gray-400">点击下方占位符直接插入光标位置</span>
      </div>

      <!-- 发码状态子标签页切换 -->
      <div v-if="form.action === 'code'" class="flex gap-1.5 mb-2 border-b pb-2">
        <button
          type="button"
          v-for="st in statusTabs"
          :key="st.key"
          @click="activeStatusTab = st.key"
          class="px-3 py-1 rounded text-xs font-bold transition flex items-center gap-1"
          :class="activeStatusTab === st.key ? 'bg-emerald-600 text-white shadow-sm' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'"
        >
          <span>{{ st.icon }}</span>
          <span>{{ st.label }}</span>
        </button>
      </div>

      <!-- 快捷占位符点击条 -->
      <div class="flex flex-wrap gap-1.5 mb-2 p-2 bg-white rounded-lg border border-gray-200">
        <span class="text-[11px] text-gray-400 py-0.5">常用：</span>
        <button
          v-if="form.action === 'code'"
          type="button"
          @click="insertPlaceholder('{code}')"
          class="px-2 py-0.5 rounded bg-emerald-100 hover:bg-emerald-200 text-xs text-emerald-800 font-bold border border-emerald-300"
        >
          🎟️ {code} (主激活码)
        </button>
        <button
          v-if="form.action === 'code'"
          type="button"
          @click="insertPlaceholder('{codes}')"
          class="px-2 py-0.5 rounded bg-gray-100 hover:bg-emerald-100 text-xs text-gray-700 border"
        >
          {codes} (清单)
        </button>
        <button
          v-for="p in pools"
          :key="p.id"
          type="button"
          @click="insertPlaceholder(`{code.${p.key}}`)"
          class="px-2 py-0.5 rounded bg-sky-50 hover:bg-sky-100 text-xs text-sky-700 font-mono border border-sky-200"
        >
          {{ '{code.' + p.key + '}' }}
        </button>
        <button type="button" @click="insertPlaceholder('{openid}')" class="px-2 py-0.5 rounded bg-gray-100 hover:bg-emerald-100 text-xs text-gray-700 border">
          {openid}
        </button>
        <button type="button" @click="insertPlaceholder('{date}')" class="px-2 py-0.5 rounded bg-gray-100 hover:bg-emerald-100 text-xs text-gray-700 border">
          {date}
        </button>
        <button type="button" @click="insertPlaceholder('{time}')" class="px-2 py-0.5 rounded bg-gray-100 hover:bg-emerald-100 text-xs text-gray-700 border">
          {time}
        </button>
        <button type="button" @click="insertPlaceholder('{stock}')" class="px-2 py-0.5 rounded bg-gray-100 hover:bg-emerald-100 text-xs text-gray-700 border">
          {stock}
        </button>

        <span class="text-[11px] text-gray-400 py-0.5 ml-2">全局变量：</span>
        <button
          v-for="v in availableVariables"
          :key="v.id"
          type="button"
          @click="insertPlaceholder(`{${v.key}}`)"
          class="px-2 py-0.5 rounded bg-purple-50 hover:bg-purple-100 text-xs text-purple-700 font-mono border border-purple-200"
          :title="v.description || v.value"
        >
          {{ '{' + v.key + '}' }}
        </button>
      </div>

      <!-- 动态多文本框：发码多状态分支渲染 -->
      <div v-if="form.action === 'code'">
        <!-- 首次领码成功文案 -->
        <div v-show="activeStatusTab === 'new'">
          <div class="text-[11px] text-emerald-700 font-bold mb-1">
            🟢 首次发码成功文案（用户第一次发送且库存充足时回复）：
          </div>
          <textarea
            id="textarea_new"
            v-model="statusReplies.new"
            rows="4"
            placeholder="🎉 您的专属激活码为：【{code}】\n👉 兑换地址：{site}"
            class="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500 font-sans bg-white"
          ></textarea>
        </div>

        <!-- 重复领取提醒文案 -->
        <div v-show="activeStatusTab === 'repeat'">
          <div class="text-[11px] text-amber-700 font-bold mb-1">
            🟡 重复领码提醒文案（同一用户已经领过此规则时回复）：
          </div>
          <textarea
            id="textarea_repeat"
            v-model="statusReplies.repeat"
            rows="4"
            placeholder="⚠️ 您之前已成功领取过专属激活码：【{code}】\n每个用户限领一次，请前往 {site} 兑换！"
            class="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500 font-sans bg-white"
          ></textarea>
        </div>

        <!-- 库存告罄缺货文案 -->
        <div v-show="activeStatusTab === 'empty'">
          <div class="text-[11px] text-red-700 font-bold mb-1">
            🔴 库存缺货告罄文案（未领过但卡池码已被领完时回复）：
          </div>
          <textarea
            id="textarea_empty"
            v-model="statusReplies.empty"
            rows="4"
            placeholder="😭 抱歉，当前激活码已被领完，请稍后再试或联系微信群：{group}"
            class="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500 font-sans bg-white"
          ></textarea>
        </div>

        <!-- 活动时效状态文案 -->
        <div v-show="activeStatusTab === 'time'">
          <div class="space-y-3">
            <div>
              <div class="text-[11px] text-blue-700 font-bold mb-1">
                ⏳ 活动未开始提示（当前时间早于开始时间时回复）：
              </div>
              <textarea
                id="textarea_not_started"
                v-model="statusReplies.not_started"
                rows="2"
                placeholder="⏰ 抱歉，本期激活码领取活动尚未开始，敬请期待！"
                class="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500 font-sans bg-white"
              ></textarea>
            </div>
            <div>
              <div class="text-[11px] text-gray-700 font-bold mb-1">
                ⌛ 活动已结束提示（当前时间晚于结束时间时回复）：
              </div>
              <textarea
                id="textarea_expired"
                v-model="statusReplies.expired"
                rows="2"
                placeholder="抱歉，本期激活码领取活动已经结束，感谢您的关注！"
                class="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500 font-sans bg-white"
              ></textarea>
            </div>
          </div>
        </div>
      </div>

      <!-- 单一文本框（普通文本回复 / 关注 / 兜底） -->
      <div v-else>
        <textarea
          id="ruleContentTextarea"
          v-model="form.content"
          rows="4"
          placeholder="输入回复文本。支持多行文本、Emoji 表情与占位符。"
          class="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500 font-sans bg-white"
        ></textarea>
      </div>
    </div>

    <!-- 底部按钮 -->
    <div class="mt-4 flex gap-2">
      <button @click="onSave" class="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold shadow-sm">
        {{ form.id ? '保存更新' : '立即创建' }}
      </button>
      <button @click="$emit('close')" class="px-4 py-2 rounded-lg bg-gray-200 text-sm text-gray-700 font-bold hover:bg-gray-300">
        取消
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { getVariables, saveRule } from '../../api.js'

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

const availableVariables = ref([])
const activeStatusTab = ref('new')
const enableTimeLimit = ref(false)

const statusTabs = computed(() => {
  const tabs = [
    { key: 'new', label: '首次发码成功', icon: '🟢' },
    { key: 'repeat', label: '重复领码提醒', icon: '🟡' },
    { key: 'empty', label: '库存缺货告罄', icon: '🔴' },
  ]
  if (enableTimeLimit.value) {
    tabs.push({ key: 'time', label: '活动时限提示', icon: '⏱️' })
  }
  return tabs
})

const isEventAction = computed(() => {
  return form.value.action === 'event_subscribe' || form.value.action === 'event_fallback'
})

const form = ref({
  id: null,
  keyword: '',
  mode: 'contains',
  action: 'none',
  content: '',
  priority: 100,
  start_time: '',
  end_time: '',
  recipeItems: [],
})

const statusReplies = ref({
  new: '',
  repeat: '',
  empty: '',
  not_started: '',
  expired: '',
})

async function fetchVariables() {
  try {
    const res = await getVariables()
    availableVariables.value = res.variables || []
  } catch {}
}

watch(() => props.ruleData, (r) => {
  activeStatusTab.value = 'new'
  if (!r) {
    form.value = {
      id: null,
      keyword: '',
      mode: 'contains',
      action: 'code',
      content: '',
      priority: 100,
      start_time: '',
      end_time: '',
      recipeItems: props.pools.length ? [{ pool_id: props.pools[0].id, count: 1 }] : [],
    }
    enableTimeLimit.value = false
    statusReplies.value = {
      new: '🎉 您的专属激活码为：\n\n【{code}】\n\n👉 兑换地址：{site}\n\n每个用户限领一次，请前往上方兑换地址完成充值兑换！',
      repeat: '您之前已成功领取过专属激活码：\n\n【{code}】\n\n👉 兑换地址：{site}\n每个用户限领一次，已领取的激活码可随时在上方平台完成兑换！',
      empty: '抱歉，当前激活码已被领完，请稍后再试或联系微信号：{group}！',
      not_started: '⏰ 抱歉，本期激活码领取活动尚未开始，敬请期待！',
      expired: '⌛ 抱歉，本期激活码领取活动已经结束，感谢您的关注！',
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

  let sr = {
    new: r.content || '',
    repeat: '',
    empty: '',
    not_started: '',
    expired: '',
  }
  if (r.status_replies) {
    try {
      const parsed = typeof r.status_replies === 'string' ? JSON.parse(r.status_replies) : r.status_replies
      if (parsed && typeof parsed === 'object') {
        sr = { ...sr, ...parsed }
      }
    } catch {}
  }
  if (!sr.new && r.content) sr.new = r.content

  statusReplies.value = sr
  enableTimeLimit.value = !!(r.start_time || r.end_time)

  form.value = {
    id: r.id,
    keyword: r.keyword,
    mode: r.mode || 'contains',
    action: r.action || 'none',
    content: r.content || '',
    priority: r.priority ?? 100,
    start_time: r.start_time || '',
    end_time: r.end_time || '',
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
  let targetId = 'ruleContentTextarea'
  if (form.value.action === 'code') {
    if (activeStatusTab.value === 'time') {
      targetId = 'textarea_not_started'
    } else {
      targetId = `textarea_${activeStatusTab.value}`
    }
  }

  const el = document.getElementById(targetId)
  if (!el) {
    if (form.value.action === 'code') {
      statusReplies.value[activeStatusTab.value] = (statusReplies.value[activeStatusTab.value] || '') + tag
    } else {
      form.value.content = (form.value.content || '') + tag
    }
    return
  }

  const start = el.selectionStart || 0
  const end = el.selectionEnd || 0
  const txt = el.value || ''
  const nextTxt = txt.slice(0, start) + tag + txt.slice(end)

  if (form.value.action === 'code') {
    if (activeStatusTab.value === 'time') {
      statusReplies.value.not_started = nextTxt
    } else {
      statusReplies.value[activeStatusTab.value] = nextTxt
    }
  } else {
    form.value.content = nextTxt
  }

  setTimeout(() => {
    el.focus()
    el.setSelectionRange(start + tag.length, start + tag.length)
  }, 10)
}

async function onSave() {
  if (!isEventAction.value && !form.value.keyword.trim()) {
    alert('关键词不能为空')
    return
  }
  if (form.value.mode === 'regex' && !isEventAction.value) {
    try {
      new RegExp(form.value.keyword.trim())
    } catch (e) {
      alert('正则表达式格式不合法：' + e.message)
      return
    }
  }

  let recipeJson = ''
  if (form.value.action === 'code' && form.value.recipeItems.length) {
    const list = form.value.recipeItems.map((it) => {
      const p = props.pools.find((pool) => pool.id === it.pool_id)
      return {
        pool_id: it.pool_id,
        key: p ? p.key : 'default',
        count: Math.max(1, Math.min(100, it.count || 1)),
      }
    })
    recipeJson = JSON.stringify(list)
  }

  const payload = {
    keyword: isEventAction.value ? `__${form.value.action}__` : form.value.keyword.trim(),
    mode: isEventAction.value ? 'exact' : form.value.mode,
    action: form.value.action,
    content: form.value.action === 'code' ? (statusReplies.value.new || '') : (form.value.content || ''),
    priority: form.value.priority ?? 100,
    recipe: recipeJson,
    status_replies: form.value.action === 'code' ? statusReplies.value : null,
    start_time: (form.value.action === 'code' && enableTimeLimit.value) ? form.value.start_time : '',
    end_time: (form.value.action === 'code' && enableTimeLimit.value) ? form.value.end_time : '',
  }

  try {
    await saveRule(payload, form.value.id)
    emit('saved')
    emit('close')
  } catch (e) {
    alert('保存失败：' + (e.detail || '未知错误'))
  }
}

onMounted(() => {
  fetchVariables()
})
</script>
