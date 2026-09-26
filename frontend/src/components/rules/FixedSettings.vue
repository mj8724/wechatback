<template>
  <div class="bg-white rounded-xl shadow p-5 mt-4">
    <h5 class="font-bold mb-3">⚙️ 固定回复与公众号设置</h5>
    <div class="grid gap-3">
      <label class="block text-sm font-medium text-gray-700">
        微信群入口微信号
        <input
          v-model="settings.group_id"
          class="mt-1 w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500 font-normal"
        />
      </label>
      <label v-for="item in textSettings" :key="item.key" class="block text-sm font-medium text-gray-700">
        {{ item.label }}
        <textarea
          v-model="settings[item.key]"
          rows="3"
          class="mt-1 w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500 font-normal"
        ></textarea>
      </label>
    </div>
    <button
      @click="onSaveSettings"
      class="mt-3 px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold shadow-sm transition"
    >
      保存设置
    </button>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { getSettings, saveSettings } from '../../api.js'

const emit = defineEmits(['saved'])

const settings = ref({})

const textSettings = [
  { key: 'welcome_reply', label: '关注欢迎语（subscribe/scan 事件）' },
  { key: 'fallback_reply', label: '默认回复（无关键词命中）' },
  { key: 'new_reply', label: '发码成功模板（{code} {codes} {site}）' },
  { key: 'empty_reply', label: '库存领完模板' },
]

async function loadSettings() {
  try {
    const res = await getSettings()
    settings.value = res.settings || {}
  } catch (e) {
    console.error('获取设置失败', e)
  }
}

async function onSaveSettings() {
  try {
    await saveSettings(settings.value)
    alert('设置已保存')
    emit('saved')
  } catch (e) {
    alert('保存失败：' + (e.detail || '未知错误'))
  }
}

defineExpose({
  loadSettings,
})

onMounted(loadSettings)
</script>
