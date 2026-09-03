"""Admin console HTML — extracted verbatim from app.py (admin_page)."""

ADMIN_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>微信公众号兑换码管理控制台</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { background-color: #f4f6f9; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .card { border-radius: 12px; border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
    .stat-card { transition: transform 0.2s; }
    .stat-card:hover { transform: translateY(-3px); }
    .stat-num { font-size: 2rem; font-weight: 700; }
    .badge-unused { background-color: #28a745; color: white; }
    .badge-assigned { background-color: #6c757d; color: white; }
    .table-container { max-height: 500px; overflow-y: auto; }
    .brand-header { background: linear-gradient(135deg, #07c160 0%, #009688 100%); color: white; padding: 24px 0; margin-bottom: 30px; }
  </style>
</head>
<body>
  <div class="brand-header text-center">
    <h2>💬 微信公众号激活码分发后台</h2>
    <p class="mb-0 text-white-50">一客一码防刷发放 · 实时库存监控 · 粉丝留言持久化记录</p>
  </div>

  <div class="container pb-5">
    <div class="card p-4 mb-4" id="loginCard">
      <div class="row align-items-center">
        <div class="col-md-8">
          <label class="form-label fw-bold">管理员访问密码</label>
          <input type="password" id="adminPwd" class="form-control form-control-lg" placeholder="请输入管理员密码查看数据..." onkeydown="if(event.key==='Enter') loadData()">
          <small class="text-muted">🔒 已启用防暴力破解机制：密码连续输错5次将自动锁定IP 15分钟</small>
        </div>
        <div class="col-md-4 mt-3 mt-md-0 d-grid">
          <button class="btn btn-success btn-lg" onclick="loadData()">解锁 / 刷新控制台</button>
        </div>
      </div>
    </div>

    <div id="mainDashboard" style="display:none;">
      <div class="row g-3 mb-4">
        <div class="col-md-3">
          <div class="card stat-card p-3 bg-white text-dark">
            <div class="text-muted">总激活码数</div>
            <div class="stat-num text-primary" id="statTotal">0</div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="card stat-card p-3 bg-white text-dark">
            <div class="text-muted">已领取</div>
            <div class="stat-num text-success" id="statUsed">0</div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="card stat-card p-3 bg-white text-dark">
            <div class="text-muted">待领取</div>
            <div class="stat-num text-warning" id="statUnused">0</div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="card stat-card p-3 bg-white text-dark">
            <div class="text-muted">已服务用户</div>
            <div class="stat-num text-danger" id="statUsers">0</div>
          </div>
        </div>
      </div>

      <div class="card p-4 mb-4">
        <h5 class="mb-3">📥 批量导入激活码</h5>
        <div class="row g-2">
          <div class="col-md-10">
            <textarea id="importText" class="form-control" rows="3" placeholder="每行一个激活码，粘贴到这里..."></textarea>
          </div>
          <div class="col-md-2 d-grid">
            <button class="btn btn-info text-white" onclick="importCodes()">导入</button>
          </div>
        </div>
        <div class="mt-3">
          <span class="text-muted">当前 Token：</span><code id="tokenShow">-</code>
          <span class="text-muted ms-3">网站地址：</span><code id="siteUrlShow">-</code>
        </div>
      </div>

      <div class="card p-4 mb-4">
        <h5 class="mb-0">📝 粉丝留言 <span class="badge bg-secondary" id="msgCount">0</span></h5>
        <p class="text-muted small mb-3">所有粉丝发送内容均持久化记录于此，刷新即可查看最新留言</p>
        <div class="table-container">
          <table class="table table-sm table-hover">
            <thead><tr><th>#</th><th>OpenID</th><th>内容</th><th>时间</th></tr></thead>
            <tbody id="messagesBody"><tr><td colspan="4" class="text-center text-muted py-4">正在加载...</td></tr></tbody>
          </table>
        </div>
      </div>

      <div class="card p-4">
        <h5 class="mb-3">🔑 激活码库存明细</h5>
        <div class="table-container">
          <table class="table table-sm table-hover">
            <thead>
              <tr><th>#</th><th>激活码</th><th>状态</th><th>领取人OpenID</th><th>领取时间</th></tr>
            </thead>
            <tbody id="codesTableBody"><tr><td colspan="5" class="text-center text-muted py-4">正在加载...</td></tr></tbody>
          </table>
        </div>
      </div>
    </div>
  </div>

  <script>
    const savedPwd = localStorage.getItem('wechat_admin_pwd');
    if (savedPwd) {
      document.getElementById('adminPwd').value = savedPwd;
    }

    async function loadData() {
      const pwd = document.getElementById('adminPwd').value.trim();
      if (!pwd) { alert('请输入管理员密码！'); return; }
      try {
        const res = await fetch(`/api/stats?pwd=${encodeURIComponent(pwd)}`);
        if (res.status === 429) { const err = await res.json(); alert('🚫 ' + err.detail); return; }
        if (!res.ok) { alert('密码错误或无权限访问！'); return; }
        const data = await res.json();
        localStorage.setItem('wechat_admin_pwd', pwd);

        document.getElementById('mainDashboard').style.display = 'block';
        document.getElementById('statTotal').innerText = data.total;
        document.getElementById('statUsed').innerText = data.used;
        document.getElementById('statUnused').innerText = data.unused;
        document.getElementById('statUsers').innerText = data.users_count;
        document.getElementById('tokenShow').innerText = data.token;
        if(data.website) document.getElementById('siteUrlShow').innerText = data.website;
        document.getElementById('msgCount').innerText = data.messages_count || 0;

        const mBody = document.getElementById('messagesBody');
        mBody.innerHTML = '';
        if (!data.messages || data.messages.length === 0) {
          mBody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-4">暂无留言记录</td></tr>';
        } else {
          data.messages.forEach(m => {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td>${m.id}</td><td><small><code>${m.openid||''}</code></small></td><td>${(m.content||'').replace(/</g,'&lt;')}</td><td><small class="text-muted">${m.created_at||''}</small></td>`;
            mBody.appendChild(tr);
          });
        }

        const tbody = document.getElementById('codesTableBody');
        tbody.innerHTML = '';
        if (data.records.length === 0) {
          tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">暂无激活码数据</td></tr>';
          return;
        }
        data.records.forEach((r) => {
          const isUsed = r.status === 'assigned';
          const badge = isUsed ? '<span class="badge badge-assigned">已领取</span>' : '<span class="badge badge-unused">待领取</span>';
          const openid = r.assigned_openid || '<span class="text-muted">-</span>';
          const time = r.assigned_at || '<span class="text-muted">-</span>';
          const tr = document.createElement('tr');
          tr.innerHTML = `<td>${r.id}</td><td><code>${r.code}</code></td><td>${badge}</td><td><small>${openid}</small></td><td><small class="text-muted">${time}</small></td>`;
          tbody.appendChild(tr);
        });
      } catch (err) {
        alert('请求失败: ' + err.message);
      }
    }

    async function importCodes() {
      const pwd = document.getElementById('adminPwd').value.trim();
      const text = document.getElementById('importText').value.trim();
      if (!text) { alert('请先在文本框粘贴要导入的激活码！'); return; }
      const lines = text.split('\\n').map(s => s.trim()).filter(Boolean);
      if (lines.length === 0) return;
      try {
        const res = await fetch('/api/import', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ pwd, codes: lines })
        });
        if (res.status === 429) { const err = await res.json(); alert('🚫 ' + err.detail); return; }
        const json = await res.json();
        alert(`成功导入 ${json.added} 个新激活码！`);
        document.getElementById('importText').value = '';
        loadData();
      } catch (err) {
        alert('导入失败: ' + err.message);
      }
    }

    window.onload = loadData;
  </script>
</body>
</html>
"""
