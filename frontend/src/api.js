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

export async function importCodes(param) {
  // 支持传入数组 codes 或对象 { pool_id, codes, multi_pool_codes }
  const body = Array.isArray(param) ? { codes: param } : param
  const res = await req('/api/import', {
    method: 'POST',
    body: JSON.stringify(body),
  })
  if (res.status === 429) {
    const err = await res.json()
    throw { status: 429, detail: err.detail }
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw { status: res.status, detail: data.detail || '导入失败' }
  return data
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

export async function deleteCode(code) {
  const res = await req('/api/codes/delete', {
    method: 'POST',
    body: JSON.stringify({ code }),
  })
  const data = await res.json().catch(() => ({}))
  if (res.status === 429) throw { status: 429, detail: data.detail }
  if (!res.ok) throw { status: res.status, detail: data.detail || '删除失败' }
  return data
}

export async function listUsers(params = {}) {
  const q = new URLSearchParams({ limit: 100, offset: 0, ...params })
  const res = await req(`/api/users?${q}`)
  if (!res.ok) throw { status: res.status, detail: '无权限访问' }
  return res.json()
}

export async function listCodes(params = {}) {
  const q = new URLSearchParams({ limit: 100, offset: 0, ...params })
  const res = await req(`/api/codes?${q}`)
  if (!res.ok) throw { status: res.status, detail: '无权限访问' }
  return res.json()
}

export async function listMessages(params = {}) {
  const q = new URLSearchParams({ limit: 100, offset: 0, ...params })
  const res = await req(`/api/messages?${q}`)
  if (!res.ok) throw { status: res.status, detail: '无权限访问' }
  return res.json()
}

export async function resetUser(openid) {
  const res = await req('/api/users/reset', {
    method: 'POST',
    body: JSON.stringify({ openid }),
  })
  const data = await res.json().catch(() => ({}))
  if (res.status === 429) throw { status: 429, detail: data.detail }
  if (!res.ok) throw { status: res.status, detail: data.detail || '重置失败' }
  return data
}

export async function listRules() {
  const res = await req('/api/rules')
  if (!res.ok) throw { status: res.status, detail: '无权限访问' }
  return res.json()
}

export async function saveRule(rule) {
  const hasId = !!rule.id
  const res = await req(hasId ? `/api/rules/${rule.id}` : '/api/rules', {
    method: hasId ? 'PUT' : 'POST',
    body: JSON.stringify(rule),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw { status: res.status, detail: data.detail || '保存失败' }
  return data
}

export async function deleteRule(id) {
  const res = await req(`/api/rules/${id}`, { method: 'DELETE' })
  if (!res.ok) throw { status: res.status, detail: '删除失败' }
  return res.json()
}

export async function getSettings() {
  const res = await req('/api/settings')
  if (!res.ok) throw { status: res.status, detail: '无权限访问' }
  return res.json()
}

export async function saveSettings(settings) {
  const res = await req('/api/settings', { method: 'PUT', body: JSON.stringify({ settings }) })
  if (!res.ok) throw { status: res.status, detail: '保存失败' }
  return res.json()
}

export async function resetUsers(openids) {
  const res = await req('/api/users/reset-batch', {
    method: 'POST',
    body: JSON.stringify({ openids }),
  })
  const data = await res.json().catch(() => ({}))
  if (res.status === 429) throw { status: 429, detail: data.detail }
  if (!res.ok) throw { status: res.status, detail: data.detail || '批量重置失败' }
  return data
}

export async function deleteUnusedCodes(pool_id = null) {
  const url = pool_id ? `/api/codes/delete-unused?pool_id=${pool_id}` : '/api/codes/delete-unused'
  const res = await req(url, { method: 'POST' })
  const data = await res.json().catch(() => ({}))
  if (res.status === 429) throw { status: 429, detail: data.detail }
  if (!res.ok) throw { status: res.status, detail: data.detail || '清空失败' }
  return data
}

export async function listPools() {
  const res = await req('/api/pools')
  if (!res.ok) throw { status: res.status, detail: '无权限访问' }
  return res.json()
}

export async function createPool(data) {
  const res = await req('/api/pools', {
    method: 'POST',
    body: JSON.stringify(data),
  })
  const resData = await res.json().catch(() => ({}))
  if (!res.ok) throw { status: res.status, detail: resData.detail || '创建品类失败' }
  return resData
}

export async function updatePool(id, data) {
  const res = await req(`/api/pools/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
  const resData = await res.json().catch(() => ({}))
  if (!res.ok) throw { status: res.status, detail: resData.detail || '修改品类失败' }
  return resData
}

export async function setDefaultPool(id) {
  const res = await req(`/api/pools/${id}/set-default`, { method: 'POST' })
  const resData = await res.json().catch(() => ({}))
  if (!res.ok) throw { status: res.status, detail: resData.detail || '设置主池失败' }
  return resData
}

export async function deletePool(id) {
  const res = await req(`/api/pools/${id}`, { method: 'DELETE' })
  const resData = await res.json().catch(() => ({}))
  if (!res.ok) throw { status: res.status, detail: resData.detail || '删除品类失败' }
  return resData
}

export async function batchDeleteRules(ids) {
  const res = await req('/api/rules/batch-delete', {
    method: 'POST',
    body: JSON.stringify({ ids }),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw { status: res.status, detail: data.detail || '批量删除失败' }
  return data
}

export async function batchToggleRules(ids, enabled) {
  const res = await req('/api/rules/batch-toggle', {
    method: 'POST',
    body: JSON.stringify({ ids, enabled }),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw { status: res.status, detail: data.detail || '批量操作失败' }
  return data
}

export async function batchImportRules(rules, mode = 'skip') {
  const res = await req('/api/rules/batch-import', {
    method: 'POST',
    body: JSON.stringify({ rules, mode }),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw { status: res.status, detail: data.detail || '批量导入失败' }
  return data
}

export async function getSetupStatus() {
  const res = await fetch('/api/setup/status')
  if (!res.ok) return { setup_done: true, wechat_configured: false }
  return res.json()
}

export async function setupInitial(payload) {
  const res = await fetch('/api/setup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw { status: res.status, detail: data.detail || '初始化失败' }
  if (data.token) setToken(data.token)
  return data
}

export async function getConfig() {
  const res = await req('/api/config')
  if (!res.ok) throw { status: res.status, detail: '无权限访问' }
  return res.json()
}

export async function saveConfig(payload) {
  const res = await req('/api/config', {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw { status: res.status, detail: data.detail || '保存配置失败' }
  return data
}

export function downloadCSV(filename, headers, rows) {
  const esc = (v) => {
    let s = String(v ?? '')
    if (/^[=+\-@\t\r]/.test(s)) s = "'" + s
    return `"${s.replace(/"/g, '""')}"`
  }
  const csv = '\ufeff' + [headers, ...rows].map((r) => r.map(esc).join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  a.click()
  URL.revokeObjectURL(a.href)
}
