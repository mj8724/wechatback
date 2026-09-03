const KEY = 'wechat_admin_token'

export const getToken = () => localStorage.getItem(KEY) || ''
export const setToken = (t) => localStorage.setItem(KEY, t)
export const clearToken = () => localStorage.removeItem(KEY)

async function req(path, options = {}) {
  const headers = { ...(options.headers || {}) }
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  if (options.body && !headers['Content-Type']) headers['Content-Type'] = 'application/json'
  const res = await fetch(path, { ...options, headers })
  if (res.status === 401 && getToken()) {
    clearToken()
    if (location.pathname !== '/login') location.href = '/login'
  }
  return res
}

export async function login(pwd) {
  const res = await fetch('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pwd }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw { status: res.status, detail: err.detail || '登录失败' }
  }
  const data = await res.json()
  setToken(data.token)
  return data
}

export async function logout() {
  try {
    await req('/api/logout', { method: 'POST' })
  } finally {
    clearToken()
  }
}

export async function fetchStats() {
  const res = await req('/api/stats')
  if (res.status === 429) {
    const err = await res.json()
    throw { status: 429, detail: err.detail }
  }
  if (!res.ok) throw { status: res.status, detail: '无权限访问' }
  return res.json()
}

export async function importCodes(codes) {
  const res = await req('/api/import', {
    method: 'POST',
    body: JSON.stringify({ codes }),
  })
  if (res.status === 429) {
    const err = await res.json()
    throw { status: 429, detail: err.detail }
  }
  if (!res.ok) throw { status: res.status, detail: '导入失败' }
  return res.json()
}

export async function resetCode(code) {
  const res = await req('/api/codes/reset', {
    method: 'POST',
    body: JSON.stringify({ code }),
  })
  const data = await res.json().catch(() => ({}))
  if (res.status === 429) throw { status: 429, detail: data.detail }
  if (!res.ok) throw { status: res.status, detail: data.detail || '重置失败' }
  return data
}
