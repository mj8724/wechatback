<template>
  <div class="min-h-screen flex flex-col">
    <div class="text-center text-white py-10 px-4" style="background: linear-gradient(135deg, #07c160 0%, #009688 100%)">
      <h2 class="text-2xl font-bold">💬 微信公众号激活码分发后台</h2>
      <p class="mt-1 text-white/70 text-sm">一客一码防刷发放 · 实时库存监控 · 粉丝留言持久化记录</p>
    </div>
    <div class="flex-1 flex items-start justify-center px-4 pt-12">
      <div class="w-full max-w-md bg-white rounded-xl shadow-lg p-8">
        <h3 class="text-lg font-bold mb-1">管理员登录</h3>
        <p class="text-sm text-gray-500 mb-6">🔒 防暴力破解：连续输错 5 次将锁定 IP 15 分钟</p>
        <form @submit.prevent="onSubmit">
          <input
            v-model="pwd"
            type="password"
            placeholder="请输入管理员密码"
            autocomplete="current-password"
            class="w-full border rounded-lg px-4 py-3 text-base outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
          />
          <p v-if="error" class="mt-3 text-sm text-red-600">🚫 {{ error }}</p>
          <button
            type="submit"
            :disabled="loading"
            class="mt-5 w-full py-3 rounded-lg text-white font-bold text-base bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50"
          >
            {{ loading ? '登录中…' : '登 录' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login } from '../api.js'

const router = useRouter()
const pwd = ref('')
const error = ref('')
const loading = ref(false)

async function onSubmit() {
  if (!pwd.value.trim() || loading.value) return
  loading.value = true
  error.value = ''
  try {
    await login(pwd.value.trim())
    router.push('/')
  } catch (e) {
    error.value = e.detail || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>
