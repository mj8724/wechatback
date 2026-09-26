<template>
  <div class="min-h-screen flex flex-col bg-slate-50">
    <div class="text-center text-white py-10 px-4" style="background: linear-gradient(135deg, #07c160 0%, #009688 100%)">
      <h2 class="text-2xl font-bold">🚀 系统首次启动初始化向导</h2>
      <p class="mt-1 text-white/80 text-sm">欢迎使用微信公众号激活码分发后台！请设置管理员密码并配置基础信息</p>
    </div>
    <div class="flex-1 flex items-start justify-center px-4 pt-8 pb-12">
      <div class="w-full max-w-lg bg-white rounded-xl shadow-lg p-8">
        <h3 class="text-lg font-bold mb-1 text-gray-800">首次启动配置</h3>
        <p class="text-sm text-gray-500 mb-6">无需改写配置文件，在此配置后立即生效保存在数据库中。</p>

        <form @submit.prevent="onSubmit" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              管理员登录密码 <span class="text-red-500">*</span>
              <span class="text-xs text-gray-400 font-normal">（至少 8 位，务必牢记）</span>
            </label>
            <input
              v-model="form.admin_password"
              type="password"
              required
              placeholder="请输入管理员密码（≥8位）"
              class="w-full border rounded-lg px-3.5 py-2.5 text-sm outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              确认管理员密码 <span class="text-red-500">*</span>
            </label>
            <input
              v-model="form.confirm_password"
              type="password"
              required
              placeholder="请再次输入管理员密码"
              class="w-full border rounded-lg px-3.5 py-2.5 text-sm outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
            />
          </div>

          <div class="pt-2 border-t border-gray-100">
            <label class="block text-sm font-medium text-gray-700 mb-1">
              微信 Token (令牌)
              <span class="text-xs text-gray-400 font-normal">（选填，与微信公众号基本配置一致）</span>
            </label>
            <input
              v-model="form.wechat_token"
              type="text"
              placeholder="自定义Token，如 wechat_token_888（稍后可在后台配置）"
              class="w-full border rounded-lg px-3.5 py-2.5 text-sm outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
            />
            <p class="text-xs text-gray-400 mt-1">在公众号后台「服务器配置」填入相同的 Token 进行接口校验。</p>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              兑换网站地址
              <span class="text-xs text-gray-400 font-normal">（选填，回复消息中的 {site} 变量）</span>
            </label>
            <input
              v-model="form.website_url"
              type="url"
              placeholder="https://newapi.liubaitech.cn"
              class="w-full border rounded-lg px-3.5 py-2.5 text-sm outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              微信群入口微信号
              <span class="text-xs text-gray-400 font-normal">（选填，群回复中的 {group} 变量）</span>
            </label>
            <input
              v-model="form.group_id"
              type="text"
              placeholder="如微信号或客服号（稍后可在后台配置）"
              class="w-full border rounded-lg px-3.5 py-2.5 text-sm outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
            />
          </div>

          <p v-if="error" class="text-sm text-red-600 bg-red-50 p-2.5 rounded-lg">🚫 {{ error }}</p>

          <button
            type="submit"
            :disabled="loading"
            class="w-full py-3 rounded-lg text-white font-bold text-sm bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 transition"
          >
            {{ loading ? '正在初始化…' : '完成初始化并进入控制台' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { setupInitial } from '../api.js'
import { markSetupDone } from '../router.js'

const router = useRouter()
const form = ref({
  admin_password: '',
  confirm_password: '',
  wechat_token: '',
  website_url: 'https://newapi.liubaitech.cn',
  group_id: '',
})
const error = ref('')
const loading = ref(false)

async function onSubmit() {
  if (loading.value) return
  error.value = ''

  const pwd = form.value.admin_password.trim()
  if (pwd.length < 8) {
    error.value = '管理员密码长度至少为 8 位'
    return
  }
  if (pwd !== form.value.confirm_password.trim()) {
    error.value = '两次输入的密码不一致'
    return
  }

  loading.value = true
  try {
    await setupInitial({
      admin_password: pwd,
      wechat_token: form.value.wechat_token.trim(),
      website_url: form.value.website_url.trim(),
      group_id: form.value.group_id.trim(),
    })
    markSetupDone()
    router.push('/')
  } catch (e) {
    error.value = e.detail || '初始化失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>
