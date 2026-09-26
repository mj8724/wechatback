<template>
  <div>
    <!-- 微信 Token 未配置引导横幅 -->
    <div
      v-if="!sysConfig.wechat_token?.is_set"
      class="mt-4 p-4 rounded-xl border border-amber-300 bg-amber-50 flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-sm"
    >
      <div>
        <div class="font-bold flex items-center gap-1.5 text-base text-amber-800">
          <span>⚠️</span> 微信 Token 尚未配置
        </div>
        <div class="text-sm text-amber-700 mt-0.5">
          外部公众号目前无法通过接口验签。您无需改动 .env 配置文件，直接在下方【⚙️ 系统参数配置】中设置并保存即可生效。
        </div>
      </div>
      <button @click="scrollToConfig" class="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-sm font-bold whitespace-nowrap">
        立即去配置
      </button>
    </div>

    <!-- 系统参数热更新配置卡片 -->
    <div id="systemConfigCard" class="bg-white rounded-xl shadow p-5 mt-4">
      <div class="flex items-center justify-between border-b pb-3 mb-4">
        <div>
          <h5 class="font-bold text-base text-gray-800 flex items-center gap-1.5">
            <span>⚙️</span> 系统参数配置
          </h5>
          <p class="text-xs text-gray-400 mt-0.5">
            在此修改微信 Token 或管理密码，保存后立即生效，无需改写 .env 或重启服务。
          </p>
        </div>
        <span v-if="configLoading" class="text-xs text-gray-400">正在获取配置…</span>
      </div>

      <form @submit.prevent="onSaveConfig" class="space-y-4">
        <!-- 微信 Token -->
        <div>
          <div class="flex items-center justify-between mb-1">
            <label class="block text-sm font-medium text-gray-700">
              微信 Token (令牌)
              <span v-if="sysConfig.wechat_token?.from_env" class="ml-2 text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600 font-normal">
                🔒 由环境变量托管 (只读)
              </span>
              <span v-else class="ml-2 text-xs px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 font-normal">
                可网页直接修改
              </span>
            </label>
            <span class="text-xs text-gray-400">微信公众平台【服务器配置】中的 Token</span>
          </div>
          <div class="flex gap-2">
            <input
              v-model="configForm.wechat_token"
              :type="showToken ? 'text' : 'password'"
              :disabled="!sysConfig.wechat_token?.editable"
              :placeholder="sysConfig.wechat_token?.from_env ? '已由环境变量配置' : (sysConfig.wechat_token?.is_set ? '输入新 Token 覆盖（留空保持不变）' : '尚未配置，请输入自定义 Token')"
              class="flex-1 border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500 disabled:bg-gray-100 disabled:text-gray-500"
            />
            <button
              type="button"
              @click="showToken = !showToken"
              class="px-3 py-2 border rounded-lg text-xs text-gray-600 hover:bg-gray-50"
            >
              {{ showToken ? '隐藏' : '显示' }}
            </button>
          </div>
          <p v-if="sysConfig.wechat_token?.is_set" class="text-xs text-gray-500 mt-1">
            当前配置状态：已配置（掩码：<code>{{ sysConfig.wechat_token.masked_value }}</code>）
          </p>
          <p v-else class="text-xs text-amber-600 mt-1">
            当前配置状态：未配置
          </p>
        </div>

        <!-- 修改管理员密码 -->
        <div class="pt-2 border-t border-gray-100">
          <div class="flex items-center justify-between mb-1">
            <label class="block text-sm font-medium text-gray-700">
              修改管理员密码
            </label>
            <span class="text-xs text-gray-400">如需修改请输入新密码（≥8位），留空则不修改密码</span>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
            <input
              v-model="configForm.new_password"
              type="password"
              placeholder="输入新管理员密码（留空不改）"
              class="border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500"
            />
            <input
              v-model="configForm.confirm_new_password"
              type="password"
              placeholder="再次输入新管理员密码"
              class="border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>
        </div>

        <div class="pt-2 flex items-center justify-between">
          <div class="text-xs text-gray-400">
            💡 提示：点击保存将热更新数据库配置，正在运行的服务即时生效。
          </div>
          <button
            type="submit"
            :disabled="configSaving"
            class="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-sm disabled:opacity-50 transition"
          >
            {{ configSaving ? '正在保存…' : '保存系统配置' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { getConfig, saveConfig } from '../../api.js'

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
    console.error('获取系统配置失败', e)
  } finally {
    configLoading.value = false
  }
}

async function onSaveConfig() {
  if (configSaving.value) return

  const np = configForm.value.new_password.trim()
  const cp = configForm.value.confirm_new_password.trim()
  if (np || cp) {
    if (np.length < 8) {
      alert('新管理员密码长度至少为 8 位')
      return
    }
    if (np !== cp) {
      alert('两次输入的新密码不一致')
      return
    }
  }

  const payload = {}
  if (sysConfig.value.wechat_token?.editable && configForm.value.wechat_token.trim()) {
    payload.wechat_token = configForm.value.wechat_token.trim()
  }
  if (np) {
    payload.new_admin_password = np
  }

  if (Object.keys(payload).length === 0) {
    alert('未修改任何配置')
    return
  }

  configSaving.value = true
  try {
    const res = await saveConfig(payload)
    alert(res.message || '系统配置保存成功，已立即生效！')
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
  scrollToConfig,
})

onMounted(loadSystemConfig)
</script>
