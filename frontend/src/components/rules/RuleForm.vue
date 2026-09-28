<template>
  <div v-if="visible" class="mt-4 p-4 rounded-xl bg-gray-50 border border-gray-200 shadow-sm">
    <div class="flex items-center justify-between mb-3 border-b pb-2">
      <h6 class="font-bold text-sm text-gray-800">{{ form.id ? '编辑规则' : '新增规则' }}</h6>
      <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 font-bold">✕</button>
    </div>

    <!-- 基础参数配置行 -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-2.5 mb-3">
      <div>
        <label class="block text-xs font-medium text-gray-700 mb-1">
          {{ isEventAction ? '触发事件' : '关键词' }}
          <HelpTip v-if="!isEventAction" text="支持常规关键词或正则表达式" />
        </label>
        <input
          v-if="!isEventAction"
          v-model="form.keyword"
          :placeholder="form.mode === 'regex' ? '^领码\\d*$' : '如：激活码 / 兑换'"
          class="w-full border rounded-lg px-2.5 py-1.5 text-xs outline-none focus:ring-2 focus:ring-emerald-500 bg-white font-mono"
        />
        <div v-else class="px-2.5 py-1.5 rounded-lg bg-gray-200 text-gray-700 text-xs font-medium truncate">
          {{ form.action === 'event_subscribe' ? '关注/扫码事件' : '未匹配兜底回复' }}
        </div>
      </div>

      <div>
        <label class="block text-xs font-medium text-gray-700 mb-1">
          匹配模式
          <HelpTip text="包含：消息中包含该词即命中&#10;全等：消息与关键词必须完全一致&#10;正则：基于正则表达式高级语法匹配" />
        </label>
        <select
          v-model="form.mode"
          :disabled="isEventAction"
          class="w-full border rounded-lg px-2 py-1.5 text-xs outline-none bg-white disabled:bg-gray-100"
        >
          <option value="contains">包含匹配</option>
          <option value="exact">完全匹配</option>
          <option value="regex">正则表达式</option>
        </select>
      </div>

      <div>
        <label class="block text-xs font-medium text-gray-700 mb-1">
          动作
          <HelpTip text="发码：从指定卡池按配方自动扣减卡密发放&#10;文本：仅被动回复普通消息文本" />
        </label>
        <select v-model="form.action" class="w-full border rounded-lg px-2 py-1.5 text-xs outline-none bg-white">
          <option value="code">发放卡密</option>
          <option value="none">文本回复</option>
          <option value="event_subscribe">关注欢迎语</option>
          <option value="event_fallback">默认未匹配回复</option>
        </select>
      </div>

      <div>
        <label class="block text-xs font-medium text-gray-700 mb-1">
          优先级
          <HelpTip text="数字越小越先触发匹配，默认 100" />
        </label>
        <input
          v-model.number="form.priority"
          type="number"
          placeholder="100"
          class="w-full border rounded-lg px-2.5 py-1.5 text-xs outline-none focus:ring-2 focus:ring-emerald-500 bg-white font-mono"
        />
      </div>
    </div>

    <!-- 1. 发码专属：配方设计器 -->
    <div v-if="form.action === 'code'" class="mb-3 p-3 bg-white rounded-lg border border-emerald-100">
      <div class="flex items-center justify-between mb-2">
        <span class="text-xs font-bold text-gray-700 flex items-center">
          发码配方
          <HelpTip text="支持跨品类组合发码（All-or-Nothing 原子事务保障，任一品类缺货安全回滚）。留空默认发放 1 张默认卡池卡密。" />
        </span>
        <button type="button" @click="addRecipeItem" class="text-xs text-emerald-600 hover:text-emerald-700 font-medium">
          + 添加品类
        </button>
      </div>
      <div v-if="!form.recipeItems.length" class="text-xs text-gray-400 py-0.5">
        默认发放 1 张默认卡池卡密。
      </div>
      <div v-for="(item, idx) in form.recipeItems" :key="idx" class="flex items-center gap-2 mb-1.5">
        <select v-model="item.pool_id" class="border rounded px-2 py-1 text-xs outline-none bg-white">
          <option v-for="p in pools" :key="p.id" :value="p.id">{{ p.name }} ({{ p.key }})</option>
        </select>
        <input v-model.number="item.count" type="number" min="1" max="100" class="w-16 border rounded px-2 py-1 text-xs outline-none bg-white font-mono" />
        <span class="text-xs text-gray-400">张</span>
        <button type="button" @click="removeRecipeItem(idx)" class="text-xs text-red-500 hover:text-red-700 ml-1">
          ✕
        </button>
      </div>
    </div>

    <!-- 2. 发码专属：活动时间限制（可选） -->
    <div v-if="form.action === 'code'" class="mb-3 p-2.5 bg-white rounded-lg border border-gray-200">
      <div class="flex items-center justify-between">
        <label class="flex items-center gap-1.5 cursor-pointer">
          <input type="checkbox" v-model="enableTimeLimit" class="rounded text-emerald-600" />
          <span class="text-xs font-bold text-gray-700">活动时间限制</span>
          <HelpTip text="仅在设定的开始至结束时间窗口内允许领码，早于或晚于该时间将自动触发对应提示。" />
        </label>
      </div>

      <div v-if="enableTimeLimit" class="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2 pt-2 border-t text-xs">
        <div>
          <label class="block text-gray-500 mb-0.5">开始时间</label>
          <input
            v-model="form.start_time"
            placeholder="YYYY-MM-DD HH:MM:SS"
            class="w-full border rounded px-2.5 py-1 text-xs outline-none font-mono focus:ring-1 focus:ring-emerald-500"
          />
        </div>
        <div>
          <label class="block text-gray-500 mb-0.5">结束时间</label>
          <input
            v-model="form.end_time"
            placeholder="YYYY-MM-DD HH:MM:SS"
            class="w-full border rounded px-2.5 py-1 text-xs outline-none font-mono focus:ring-1 focus:ring-emerald-500"
          />
        </div>
      </div>
    </div>

    <!-- 3. 回复文案与分支切换 -->
    <div>
      <div class="flex items-center justify-between mb-1.5">
        <label class="text-xs font-bold text-gray-700 flex items-center">
          {{ form.action === 'code' ? '分支回复文案' : '回复文案' }}
          <HelpTip v-if="form.action === 'code'" text="发码规则针对首次领码、重复领取与缺货告罄支持完全独立的不同回复文案。" />
        </label>
      </div>

      <!-- 发码状态子标签页切换 -->
      <div v-if="form.action === 'code'" class="flex gap-1 mb-2 border-b pb-1.5">
        <button
          type="button"
          v-for="st in statusTabs"
          :key="st.key"
          @click="activeStatusTab = st.key"
          class="px-2.5 py-1 rounded text-xs font-medium transition flex items-center gap-1"
          :class="activeStatusTab === st.key ? 'bg-emerald-600 text-white shadow-sm' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
        >
          <span>{{ st.label }}</span>
        </button>
      </div>

      <!-- 快捷占位符点击条（紧凑 Pills） -->
      <div class="flex flex-wrap items-center gap-1 mb-2 p-1.5 bg-white rounded-lg border border-gray-200">
        <span class="text-[10px] text-gray-400 mr-1 select-none">插入占位符:</span>
        <button
          v-if="form.action === 'code'"
          type="button"
          @click="insertPlaceholder('{code}')"
          class="px-1.5 py-0.5 rounded bg-emerald-50 hover:bg-emerald-100 text-emerald-800 text-[11px] font-mono border border-emerald-200"
          title="分配的主激活码"
        >
          {code}
        </button>
        <button
          v-if="form.action === 'code'"
          type="button"
          @click="insertPlaceholder('{codes}')"
          class="px-1.5 py-0.5 rounded bg-gray-100 hover:bg-emerald-50 text-gray-700 text-[11px] font-mono border"
          title="多品类激活码清单"
        >
          {codes}
        </button>
        <button
          v-for="p in pools"
          :key="p.id"
          type="button"
          @click="insertPlaceholder(`{code.${p.key}}`)"
          class="px-1.5 py-0.5 rounded bg-sky-50 hover:bg-sky-100 text-sky-700 text-[11px] font-mono border border-sky-200"
          :title="`品类 ${p.name} 的激活码`"
        >
          {{ '{code.' + p.key + '}' }}
        </button>
        <button type="button" @click="insertPlaceholder('{openid}')" class="px-1.5 py-0.5 rounded bg-gray-100 hover:bg-emerald-50 text-gray-700 text-[11px] font-mono border" title="用户微信 OpenID">
          {openid}
        </button>
        <button type="button" @click="insertPlaceholder('{site}')" class="px-1.5 py-0.5 rounded bg-gray-100 hover:bg-emerald-50 text-gray-700 text-[11px] font-mono border" title="兑换网站地址">
          {site}
        </button>
        <button type="button" @click="insertPlaceholder('{group}')" class="px-1.5 py-0.5 rounded bg-gray-100 hover:bg-emerald-50 text-gray-700 text-[11px] font-mono border" title="客服微信号">
          {group}
        </button>
        <button type="button" @click="insertPlaceholder('{stock}')" class="px-1.5 py-0.5 rounded bg-gray-100 hover:bg-emerald-50 text-gray-700 text-[11px] font-mono border" title="实时库存概况">
          {stock}
        </button>
        <button type="button" @click="insertPlaceholder('{date}')" class="px-1.5 py-0.5 rounded bg-gray-100 hover:bg-emerald-50 text-gray-700 text-[11px] font-mono border" title="当前日期 YYYY-MM-DD">
          {date}
        </button>
        <button type="button" @click="insertPlaceholder('{time}')" class="px-1.5 py-0.5 rounded bg-gray-100 hover:bg-emerald-50 text-gray-700 text-[11px] font-mono border" title="当前时间 HH:MM:SS">
          {time}
        </button>

        <span v-if="availableVariables.length" class="text-gray-300">|</span>
        <button
          v-for="v in availableVariables.filter(x => x.key !== 'site' && x.key !== 'group')"
          :key="v.id"
          type="button"
          @click="insertPlaceholder(`{${v.key}}`)"
          class="px-1.5 py-0.5 rounded bg-purple-50 hover:bg-purple-100 text-purple-700 text-[11px] font-mono border border-purple-200"
          :title="v.description || v.value"
        >
          {{ '{' + v.key + '}' }}
        </button>
      </div>

      <!-- 动态多文本框：发码多状态分支渲染 -->
      <div v-if="form.action === 'code'">
        <div v-show="activeStatusTab === 'new'">
          <textarea
            id="textarea_new"
            v-model="statusReplies.new"
            rows="4"
            placeholder="首次发码成功回复。例如：🎉 您的专属激活码为：【{code}】&#10;👉 兑换地址：{site}"
            class="w-full border rounded-lg px-3 py-2 text-xs outline-none focus:ring-2 focus:ring-emerald-500 font-sans bg-white leading-relaxed"
          ></textarea>
        </div>

        <div v-show="activeStatusTab === 'repeat'">
          <textarea
            id="textarea_repeat"
            v-model="statusReplies.repeat"
            rows="4"
            placeholder="重复领码提醒回复。例如：您之前已领过此码：【{code}】，请前往 {site} 兑换！"
            class="w-full border rounded-lg px-3 py-2 text-xs outline-none focus:ring-2 focus:ring-emerald-500 font-sans bg-white leading-relaxed"
          ></textarea>
        </div>

        <div v-show="activeStatusTab === 'empty'">
          <textarea
            id="textarea_empty"
            v-model="statusReplies.empty"
            rows="4"
            placeholder="库存告罄缺货回复。例如：抱歉，本期激活码已被领完，请稍后再试或联系微信：{group}"
            class="w-full border rounded-lg px-3 py-2 text-xs outline-none focus:ring-2 focus:ring-emerald-500 font-sans bg-white leading-relaxed"
          ></textarea>
        </div>

        <div v-show="activeStatusTab === 'time'" class="space-y-2">
          <div>
            <label class="block text-[11px] text-gray-500 mb-0.5">未开始提示：</label>
            <input
              id="textarea_not_started"
              v-model="statusReplies.not_started"
              placeholder="活动尚未开始提示"
              class="w-full border rounded-lg px-3 py-1.5 text-xs outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
            />
          </div>
          <div>
            <label class="block text-[11px] text-gray-500 mb-0.5">已结束提示：</label>
            <input
              id="textarea_expired"
              v-model="statusReplies.expired"
              placeholder="活动已经结束提示"
              class="w-full border rounded-lg px-3 py-1.5 text-xs outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
            />
          </div>
        </div>
      </div>

      <!-- 单一文本框（普通文本回复 / 关注 / 兜底） -->
      <div v-else>
        <textarea
          id="ruleContentTextarea"
          v-model="form.content"
          rows="4"
          placeholder="输入回复内容，支持多行文本与占位符。"
          class="w-full border rounded-lg px-3 py-2 text-xs outline-none focus:ring-2 focus:ring-emerald-500 font-sans bg-white leading-relaxed"
        ></textarea>
      </div>
    </div>

    <!-- 底部按钮 -->
    <div class="mt-3 flex justify-end gap-2 border-t pt-2.5">
      <button @click="$emit('close')" class="px-3.5 py-1.5 rounded-lg border border-gray-300 text-xs text-gray-600 font-medium hover:bg-gray-100">
        取消
      </button>
      <button @click="onSave" class="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-sm">
        {{ form.id ? '保存修改' : '确认创建' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { getVariables, saveRule } from '../../api.js'
import HelpTip from '../common/HelpTip.vue'

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
    { key: 'new', label: '首次成功' },
    { key: 'repeat', label: '重复领取' },
    { key: 'empty', label: '库存告罄' },
  ]
  if (enableTimeLimit.value) {
    tabs.push({ key: 'time', label: '时限拦截' })
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
      not_started: '抱歉，本期激活码领取活动尚未开始，敬请期待！',
      expired: '抱歉，本期激活码领取活动已经结束，感谢您的关注！',
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
    id: form.value.id || null,
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
