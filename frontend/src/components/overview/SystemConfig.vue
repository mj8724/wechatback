<template>
  <div>
    <!-- 微信 Token 未配置轻量提醒 -->
    <div
      v-if="!sysConfig.wechat_token?.is_set"
      class="mt-4 px-3.5 py-2 rounded-lg border border-amber-200 bg-amber-50 flex items-center justify-between text-xs text-amber-800 shadow-sm"
    >
      <div class="flex items-center gap-1.5">
        <span class="font-bold">⚠️ 微信 Token 尚未配置</span>
        <span class="text-amber-600">公众号接口目前无法验签</span>
      </div>
      <button @click="scrollToConfig" class="text-xs font-bold text-amber-700 hover:text-amber-900 underline">
        去配置
      </button>
    </div>

    <!-- 系统参数配置卡片 -->
    <div id="systemConfigCard" class="bg-white rounded-xl shadow p-5 mt-4">
      <div class="flex items-center justify-between border-b pb-3 mb-4">
        <div class="flex items-center gap-1.5">
          <h5 class="font-bold text-base text-gray-800">系统配置</h5>
          <HelpTip text="在此修改微信 Token 与管理员密码，保存后即时生效。" />
        </div>
        <span v-if="configLoading" class="text-xs text-gray-400">加载中…</span>
      </div>

      <form @submit.prevent="onSaveConfig" class="space-y-3.5">
        <!-- 微信 Token -->
        <div>
          <div class="flex items-center justify-between mb-1">
            <label class="text-xs font-medium text-gray-700 flex items-center">
              微信 Token
              <HelpTip text="须与微信公众平台「基本配置-服务器配置」填写的 Token 保持完全一致" />
              <span v-if="sysConfig.wechat_token?.from_env" class="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 font-normal">
                环境变量托管
              </span>
            </label>
            <span v-if="sysConfig.wechat_token?.is_set" class="text-xs text-gray-400 font-mono">
              已设置: <code>{{ sysConfig.wechat_token.masked_value }}</code>
            </span>
            <span v-else class="text-xs text-amber-600 font-medium">未设置</span>
          </div>
          <div class="flex gap-2">
            <input
              v-model="configForm.wechat_token"
              :type="showToken ? 'text' : 'password'"
              :disabled="!sysConfig.wechat_token?.editable"
              :placeholder="sysConfig.wechat_token?.from_env ? '由环境变量配置' : (sysConfig.wechat_token?.is_set ? '输入新 Token 覆盖（留空不改）' : '请输入微信 Token')"
              class="flex-1 border rounded-lg px-3 py-1.5 text-xs outline-none focus:ring-2 focus:ring-emerald-500 disabled:bg-gray-100 disabled:text-gray-500 font-mono"
            />
            <button
              type="button"
              @click="showToken = !showToken"
              class="px-3 py-1.5 border rounded-lg text-xs text-gray-600 hover:bg-gray-50"
            >
              {{ showToken ? '隐藏' : '显示' }}
            </button>
          </div>
        </div>

        <!-- 修改管理员密码 -->
        <div class="pt-2 border-t border-gray-100">
          <div class="flex items-center justify-between mb-1">
            <label class="text-xs font-medium text-gray-700 flex items-center">
              管理员密码
              <HelpTip text="至少 8 位，留空则保持当前密码不变" />
            </label>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
            <input
              v-model="configForm.new_password"
              type="password"
              placeholder="输入新密码（留空不改）"
              class="border rounded-lg px-3 py-1.5 text-xs outline-none focus:ring-2 focus:ring-emerald-500"
            />
            <input
              v-model="configForm.confirm_new_password"
              type="password"
              placeholder="确认新密码"
              class="border rounded-lg px-3 py-1.5 text-xs outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>
        </div>

        <div class="pt-2 flex justify-end">
          <button
            type="submit"
            :disabled="configSaving"
            class="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs disabled:opacity-50 transition shadow-sm"
          >
            {{ configSaving ? '正在保存…' : '保存配置' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { getConfig, saveConfig } from '../../api.js'
import HelpTip from '../common/HelpTip.vue'

const emit = defineEmits(['updated'])

const sysConfig = ref({})
const configLoading = ref(false)
const configSaving = ref(false)
const showToken = ref(false)
const configForm = ref({
  wechat_token: '',
  new_password: '',
  confirm_new_password: '',
})

function scrollToConfig() {
  document.getElementById('systemConfigCard')?.scrollIntoView({ behavior: 'smooth' })
}

async function loadSystemConfig() {
  configLoading.value = true
  try {
    const d = await getConfig()
    sysConfig.value = d.config || {}
    configForm.value.wechat_token = ''
    configForm.value.new_password = ''
    configForm.value.confirm_new_password = ''
  } catch (e) {
    console.error('获取配置失败', e)
  } finally {
    configLoading.value = false
  }
}

async function onSaveConfig() {
  const payload = {}

  if (configForm.value.wechat_token.trim()) {
    payload.wechat_token = configForm.value.wechat_token.trim()
  }

  const np = configForm.value.new_password
  const cnp = configForm.value.confirm_new_password
  if (np || cnp) {
    if (np.length < 8) {
      alert('新密码长度不能少于 8 位')
      return
    }
    if (np !== cnp) {
      alert('两次输入的新密码不一致')
      return
    }
    payload.new_admin_password = np
  }

  if (Object.keys(payload).length === 0) {
    alert('未做任何修改')
    return
  }

  configSaving.value = true
  try {
    await saveConfig(payload)
    alert('系统配置已成功保存并即时生效')
    configForm.value.wechat_token = ''
    configForm.value.new_password = ''
    configForm.value.confirm_new_password = ''
    await loadSystemConfig()
    emit('updated')
  } catch (e) {
    alert('保存失败：' + (e.detail || '未知错误'))
  } finally {
    configSaving.value = false
  }
}

defineExpose({
  loadSystemConfig,
})

onMounted(loadSystemConfig)
</script>
