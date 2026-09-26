"""⚠️ 归档参考文件，禁止直接运行上线。
旧版 Flask 单体实现，仅用于对照历史逻辑；现网入口是 FastAPI（app.py）。
如需临时运行，必须显式提供 WECHAT_TOKEN / ADMIN_PASSWORD 环境变量。"""
import os
import sys
import time
import hashlib
import sqlite3
import secrets
from datetime import datetime
import xml.etree.ElementTree as ET
from flask import Flask, request, jsonify, render_template_string, Response

app = Flask(__name__)

WECHAT_TOKEN = os.environ.get("WECHAT_TOKEN", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
if not WECHAT_TOKEN or not ADMIN_PASSWORD:
    raise RuntimeError("归档文件禁止无密钥运行：请设置 WECHAT_TOKEN / ADMIN_PASSWORD")
DB_PATH = os.environ.get("DB_PATH", "/data/wechat_redeem.db")
REDEEM_URL = os.environ.get("REDEEM_URL", "https://newapi.liubaitech.cn")
WECHAT_ADMIN_ID = "810466205"
LOGIN_FAIL_LIMIT = 5
LOCK_TIME = 900

login_attempts = {}

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS redeem_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            is_used INTEGER DEFAULT 0,
            openid TEXT,
            used_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            openid TEXT NOT NULL,
            msg_type TEXT NOT NULL,
            content TEXT,
            reply_content TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_openid ON redeem_codes(openid)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_is_used ON redeem_codes(is_used)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_msg_openid ON messages(openid)")
    conn.commit()
    conn.close()

init_db()

def verify_signature(signature, timestamp, nonce, token=WECHAT_TOKEN):
    if not signature or not timestamp or not nonce:
        return False
    tmp_list = sorted([token, timestamp, nonce])
    tmp_str = "".join(tmp_list)
    hash_str = hashlib.sha1(tmp_str.encode("utf-8")).hexdigest()
    return hash_str == signature

def is_ip_locked(ip):
    now = time.time()
    if ip in login_attempts:
        fails, lock_until = login_attempts[ip]
        if lock_until > now:
            return True, int(lock_until - now)
        elif lock_until != 0 and lock_until <= now:
            login_attempts[ip] = (0, 0)
    return False, 0

def record_login_fail(ip):
    now = time.time()
    fails, _ = login_attempts.get(ip, (0, 0))
    fails += 1
    if fails >= LOGIN_FAIL_LIMIT:
        login_attempts[ip] = (fails, now + LOCK_TIME)
    else:
        login_attempts[ip] = (fails, 0)

def record_login_success(ip):
    if ip in login_attempts:
        del login_attempts[ip]

def parse_xml_to_dict(xml_str):
    root = ET.fromstring(xml_str)
    return {child.tag: child.text for child in root}

def create_reply_xml(to_user, from_user, content):
    create_time = int(time.time())
    return f"""<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[{from_user}]]></FromUserName>
<CreateTime>{create_time}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""

def log_message(openid, msg_type, content, reply_content=""):
    try:
        conn = get_db()
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO messages (openid, msg_type, content, reply_content, created_at) VALUES (?, ?, ?, ?, ?)",
            (openid, msg_type, content, reply_content, now_str)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Log message error: {e}", file=sys.stderr)

def get_or_assign_code(openid):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT code, used_at FROM redeem_codes WHERE openid = ?", (openid,))
    row = cursor.fetchone()
    if row:
        code = row["code"]
        conn.close()
        return code, False

    cursor.execute("SELECT id, code FROM redeem_codes WHERE is_used = 0 ORDER BY id ASC LIMIT 1")
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None, False

    code_id = row["id"]
    code = row["code"]
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE redeem_codes SET is_used = 1, openid = ?, used_at = ? WHERE id = ? AND is_used = 0", (openid, now_str, code_id))
    if cursor.rowcount > 0:
        conn.commit()
        conn.close()
        return code, True
    else:
        conn.rollback()
        conn.close()
        return get_or_assign_code(openid)

@app.route("/", methods=["GET"])
def root_index():
    return "WeChat Redeem Service is Running", 200

@app.route("/MP_verify_SPZeqMb6e9TacIgg.txt", methods=["GET"])
def mp_verify():
    return "SPZeqMb6e9TacIgg", 200, {"Content-Type": "text/plain; charset=utf-8"}

@app.route("/wechat", methods=["GET", "POST"])
def wechat_endpoint():
    signature = request.args.get("signature", "")
    timestamp = request.args.get("timestamp", "")
    nonce = request.args.get("nonce", "")

    if not verify_signature(signature, timestamp, nonce):
        return "Invalid signature", 403

    if request.method == "GET":
        echostr = request.args.get("echostr", "")
        return echostr, 200

    xml_data = request.data
    if not xml_data:
        return "success", 200

    try:
        msg = parse_xml_to_dict(xml_data)
        msg_type = msg.get("MsgType", "")
        from_user = msg.get("FromUserName", "")
        to_user = msg.get("ToUserName", "")
        content = (msg.get("Content", "") or "").strip()
        event = msg.get("Event", "")

        reply_text = ""

        if msg_type == "event":
            if event == "subscribe":
                reply_text = (
                    "👋 欢迎关注！\n\n"
                    "👉 回复【激活码】：领取专属 NewAPI 激活码\n"
                    "👉 回复【微信群】：获取交流群加群方式\n\n"
                    f"🔗 平台网址：{REDEEM_URL}"
                )
            elif event == "unsubscribe":
                log_message(from_user, "event", f"取消关注: {event}", "")
                return "success", 200
            else:
                reply_text = "欢迎关注！回复【激活码】获取专属激活码，回复【微信群】加入交流群。"
        elif msg_type == "text":
            normalized_content = content.lower()
            if "激活码" in content or "兑换码" in content or "码" == content:
                code, is_new = get_or_assign_code(from_user)
                if code:
                    if is_new:
                        reply_text = f"🎉 感谢支持！\n这是您的专属 NewAPI 激活码：\n👉 {code}\n\n🔗 兑换与使用网址：\n{REDEEM_URL}\n\n请前往上方网址在个人中心兑换使用！"
                    else:
                        reply_text = f"💡 您好！您已领取过激活码：\n👉 {code}\n\n🔗 兑换与使用网址：\n{REDEEM_URL}\n\n（每个微信用户仅可领取一次）"
                else:
                    reply_text = f"😭 抱歉，当前激活码已被领完，请联系管理员补充。\n兑换网址：{REDEEM_URL}"
            elif "微信群" in content or "进群" in content or "加群" in content or "群" == content:
                reply_text = f"👥 欢迎加入交流群！\n\n👉 请添加微信号：{WECHAT_ADMIN_ID}\n📝 备注【进群】，收到后会第一时间拉您进群！"
            else:
                reply_text = (
                    "💡 您好，请问有什么可以帮您？\n\n"
                    "👉 回复【激活码】：领取专属激活码\n"
                    "👉 回复【微信群】：获取加群联系方式\n\n"
                    f"🔗 平台网址：{REDEEM_URL}"
                )

        log_content = content if msg_type == "text" else f"事件: {event}"
        log_message(from_user, msg_type, log_content, reply_text)

        if reply_text:
            reply_xml = create_reply_xml(from_user, to_user, reply_text)
            return Response(reply_xml, mimetype="application/xml")
        return "success", 200

    except Exception as e:
        print(f"Error handling wechat message: {e}", file=sys.stderr)
        return "success", 200

def check_auth(req):
    auth_header = req.headers.get("Authorization", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif "admin_token" in req.cookies:
        token = req.cookies.get("admin_token", "").strip()
    return token == ADMIN_PASSWORD

@app.route("/admin/api/login", methods=["POST"])
def admin_login():
    ip = request.remote_addr or "unknown"
    locked, remaining = is_ip_locked(ip)
    if locked:
        return jsonify({"code": 429, "msg": f"失败次数过多，IP已被锁定，请在 {remaining} 秒后再试"}), 429

    data = request.json or {}
    password = data.get("password", "").strip()
    if password == ADMIN_PASSWORD:
        record_login_success(ip)
        resp = jsonify({"code": 0, "token": ADMIN_PASSWORD, "msg": "登录成功"})
        resp.set_cookie("admin_token", ADMIN_PASSWORD, httponly=True, samesite="Lax", max_age=86400*7)
        return resp
    else:
        record_login_fail(ip)
        fails, _ = login_attempts.get(ip, (0, 0))
        rem = LOGIN_FAIL_LIMIT - fails
        msg = f"密码错误，还可尝试 {rem} 次" if rem > 0 else f"密码错误已达上限，IP已被锁定 15 分钟"
        return jsonify({"code": 401, "msg": msg}), 401

@app.route("/admin/api/stats", methods=["GET"])
def admin_stats():
    if not check_auth(request):
        return jsonify({"code": 401, "msg": "未授权"}), 401
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM redeem_codes")
    total = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) as used FROM redeem_codes WHERE is_used = 1")
    used = cursor.fetchone()["used"]
    cursor.execute("SELECT COUNT(*) as msg_total FROM messages")
    msg_total = cursor.fetchone()["msg_total"]
    conn.close()
    return jsonify({
        "code": 0,
        "data": {
            "total": total,
            "used": used,
            "unused": total - used,
            "msg_total": msg_total,
            "redeem_url": REDEEM_URL
        }
    })

@app.route("/admin/api/codes", methods=["GET"])
def admin_get_codes():
    if not check_auth(request):
        return jsonify({"code": 401, "msg": "未授权"}), 401
    status = request.args.get("status", "all")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("pageSize", 20))
    offset = (page - 1) * page_size

    conn = get_db()
    cursor = conn.cursor()
    where = ""
    params = []
    if status == "used":
        where = "WHERE is_used = 1"
    elif status == "unused":
        where = "WHERE is_used = 0"

    cursor.execute(f"SELECT COUNT(*) as total FROM redeem_codes {where}", params)
    total = cursor.fetchone()["total"]

    cursor.execute(f"SELECT id, code, is_used, openid, used_at, created_at FROM redeem_codes {where} ORDER BY id DESC LIMIT ? OFFSET ?", params + [page_size, offset])
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({"code": 0, "data": {"total": total, "list": rows, "page": page, "pageSize": page_size}})

@app.route("/admin/api/messages", methods=["GET"])
def admin_get_messages():
    if not check_auth(request):
        return jsonify({"code": 401, "msg": "未授权"}), 401
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("pageSize", 20))
    offset = (page - 1) * page_size

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM messages")
    total = cursor.fetchone()["total"]
    cursor.execute("SELECT id, openid, msg_type, content, reply_content, created_at FROM messages ORDER BY id DESC LIMIT ? OFFSET ?", [page_size, offset])
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({"code": 0, "data": {"total": total, "list": rows, "page": page, "pageSize": page_size}})

@app.route("/admin/api/codes/import", methods=["POST"])
def admin_import_codes():
    if not check_auth(request):
        return jsonify({"code": 401, "msg": "未授权"}), 401
    data = request.json or {}
    codes = data.get("codes", [])
    if not codes:
        return jsonify({"code": 400, "msg": "激活码列表不能为空"}), 400

    conn = get_db()
    cursor = conn.cursor()
    success_count = 0
    dup_count = 0
    for code in codes:
        code = str(code).strip()
        if not code:
            continue
        try:
            cursor.execute("INSERT INTO redeem_codes (code) VALUES (?)", (code,))
            success_count += 1
        except sqlite3.IntegrityError:
            dup_count += 1
    conn.commit()
    conn.close()
    return jsonify({"code": 0, "msg": f"成功导入 {success_count} 个，重复跳过 {dup_count} 个"})

ADMIN_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>公众号发码与留言管理系统</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/element-plus@2.4.4/dist/index.css">
    <script src="https://cdn.jsdelivr.net/npm/vue@3.3.11/dist/vue.global.prod.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/element-plus@2.4.4/dist/index.full.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/axios@1.6.2/dist/axios.min.js"></script>
    <style>
        body { margin: 0; background: #f0f2f5; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        .login-box { width: 380px; margin: 120px auto; padding: 35px; background: #fff; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.08); }
        .admin-layout { max-width: 1200px; margin: 30px auto; padding: 0 20px; }
        .card-header { display: flex; justify-content: space-between; align-items: center; font-weight: bold; }
        .stat-card { text-align: center; padding: 10px 0; }
        .stat-value { font-size: 28px; font-weight: bold; margin-top: 8px; color: #409EFF; }
        .stat-unused { color: #67C23A; }
        .stat-used { color: #E6A23C; }
        .stat-msg { color: #909399; }
        .reply-box { white-space: pre-wrap; font-size: 13px; color: #606266; background: #f4f4f5; padding: 6px 10px; border-radius: 6px; }
    </style>
</head>
<body>
    <div id="app">
        <div v-if="!isLoggedIn" class="login-box">
            <h2 style="text-align: center; margin-bottom: 25px; color: #303133;">🔐 管理控制台登录</h2>
            <el-form @submit.prevent="handleLogin">
                <el-form-item>
                    <el-input v-model="password" type="password" placeholder="请输入管理员密码" show-password @keyup.enter="handleLogin" prefix-icon="Lock"></el-input>
                </el-form-item>
                <el-form-item>
                    <el-button type="primary" :loading="loading" style="width: 100%" @click="handleLogin">登 录</el-button>
                </el-form-item>
            </el-form>
        </div>

        <div v-else class="admin-layout">
            <el-card style="margin-bottom: 20px;">
                <div class="card-header">
                    <span style="font-size: 18px;">微信公众号发码 & 粉丝留言管理控制台</span>
                    <div>
                        <el-button type="primary" plain @click="fetchData">🔄 刷新</el-button>
                        <el-button type="danger" plain @click="handleLogout">退出登录</el-button>
                    </div>
                </div>
            </el-card>

            <el-row :gutter="20" style="margin-bottom: 20px;">
                <el-col :span="6">
                    <el-card shadow="hover" class="stat-card">
                        <div>激活码总量</div>
                        <div class="stat-value">{{ stats.total }}</div>
                    </el-card>
                </el-col>
                <el-col :span="6">
                    <el-card shadow="hover" class="stat-card">
                        <div>剩余可用码</div>
                        <div class="stat-value stat-unused">{{ stats.unused }}</div>
                    </el-card>
                </el-col>
                <el-col :span="6">
                    <el-card shadow="hover" class="stat-card">
                        <div>已发放激活码</div>
                        <div class="stat-value stat-used">{{ stats.used }}</div>
                    </el-card>
                </el-col>
                <el-col :span="6">
                    <el-card shadow="hover" class="stat-card">
                        <div>粉丝互动/留言总数</div>
                        <div class="stat-value stat-msg">{{ stats.msg_total }}</div>
                    </el-card>
                </el-col>
            </el-row>

            <el-card>
                <el-tabs v-model="activeTab" @tab-change="handleTabChange">
                    <el-tab-pane label="📋 激活码管理" name="codes">
                        <div style="margin-bottom: 15px; display: flex; justify-content: space-between;">
                            <el-radio-group v-model="statusFilter" @change="fetchCodes">
                                <el-radio-button label="all">全部</el-radio-button>
                                <el-radio-button label="unused">未领取</el-radio-button>
                                <el-radio-button label="used">已领取</el-radio-button>
                            </el-radio-group>
                            <el-button type="success" @click="showImport = true">➕ 批量导入激活码</el-button>
                        </div>
                        <el-table :data="codesList" stripe style="width: 100%" v-loading="loading">
                            <el-table-column prop="id" label="ID" width="70"></el-table-column>
                            <el-table-column prop="code" label="激活码 (兑换密钥)"></el-table-column>
                            <el-table-column prop="is_used" label="状态" width="100">
                                <template #default="scope">
                                    <el-tag :type="scope.row.is_used ? 'warning' : 'success'">
                                        {{ scope.row.is_used ? '已领取' : '未领取' }}
                                    </el-tag>
                                </template>
                            </el-table-column>
                            <el-table-column prop="openid" label="领取粉丝 OpenID" width="280">
                                <template #default="scope">
                                    <code>{{ scope.row.openid || '-' }}</code>
                                </template>
                            </el-table-column>
                            <el-table-column prop="used_at" label="领取时间" width="180">
                                <template #default="scope">
                                    {{ scope.row.used_at || '-' }}
                                </template>
                            </el-table-column>
                        </el-table>
                        <div style="margin-top: 15px; display: flex; justify-content: flex-end;">
                            <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="totalCodes" layout="total, prev, pager, next" @current-change="fetchCodes"></el-pagination>
                        </div>
                    </el-tab-pane>

                    <el-tab-pane label="💬 粉丝留言与消息记录 (持久化)" name="messages">
                        <el-table :data="messagesList" stripe style="width: 100%" v-loading="loading">
                            <el-table-column prop="id" label="ID" width="70"></el-table-column>
                            <el-table-column prop="created_at" label="发送时间" width="170"></el-table-column>
                            <el-table-column prop="openid" label="粉丝 OpenID" width="260">
                                <template #default="scope">
                                    <code>{{ scope.row.openid }}</code>
                                </template>
                            </el-table-column>
                            <el-table-column prop="content" label="粉丝消息 / 触发动作" width="220">
                                <template #default="scope">
                                    <span style="font-weight: bold; color: #303133;">{{ scope.row.content }}</span>
                                </template>
                            </el-table-column>
                            <el-table-column prop="reply_content" label="系统回复内容">
                                <template #default="scope">
                                    <div class="reply-box">{{ scope.row.reply_content }}</div>
                                </template>
                            </el-table-column>
                        </el-table>
                        <div style="margin-top: 15px; display: flex; justify-content: flex-end;">
                            <el-pagination v-model:current-page="msgPage" v-model:page-size="msgPageSize" :total="totalMessages" layout="total, prev, pager, next" @current-change="fetchMessages"></el-pagination>
                        </div>
                    </el-tab-pane>
                </el-tabs>
            </el-card>

            <el-dialog v-model="showImport" title="批量导入 NewAPI 激活码" width="550px">
                <el-input v-model="importText" type="textarea" :rows="8" placeholder="每行一个激活码，例如：&#10;8d892789d5e649a7ac9906c6ba6d96c7&#10;9c1909fea9084bf2a4df7f123bd1152b"></el-input>
                <template #footer>
                    <el-button @click="showImport = false">取消</el-button>
                    <el-button type="primary" :loading="importing" @click="handleImport">确认导入</el-button>
                </template>
            </el-dialog>
        </div>
    </div>

    <script>
        const { createApp, ref, onMounted } = Vue;
        const app = createApp({
            setup() {
                const isLoggedIn = ref(false);
                const password = ref('');
                const loading = ref(false);
                const activeTab = ref('codes');
                const stats = ref({ total: 0, used: 0, unused: 0, msg_total: 0, redeem_url: '' });
                const statusFilter = ref('all');
                const codesList = ref([]);
                const messagesList = ref([]);
                const page = ref(1);
                const pageSize = ref(20);
                const totalCodes = ref(0);
                const msgPage = ref(1);
                const msgPageSize = ref(20);
                const totalMessages = ref(0);
                const showImport = ref(false);
                const importText = ref('');
                const importing = ref(false);

                const handleLogin = async () => {
                    if (!password.value.trim()) return ElementPlus.ElMessage.warning('请输入密码');
                    loading.value = true;
                    try {
                        const res = await axios.post('/admin/api/login', { password: password.value.trim() });
                        if (res.data.code === 0) {
                            localStorage.setItem('admin_token', password.value.trim());
                            isLoggedIn.value = true;
                            fetchData();
                        }
                    } catch (e) {
                        ElementPlus.ElMessage.error(e.response?.data?.msg || '密码错误');
                    } finally {
                        loading.value = false;
                    }
                };

                const handleLogout = () => {
                    localStorage.removeItem('admin_token');
                    isLoggedIn.value = false;
                };

                const getAuthHeader = () => ({ headers: { Authorization: 'Bearer ' + (localStorage.getItem('admin_token') || '') } });

                const fetchData = () => {
                    fetchStats();
                    if (activeTab.value === 'codes') fetchCodes();
                    else fetchMessages();
                };

                const fetchStats = async () => {
                    try {
                        const res = await axios.get('/admin/api/stats', getAuthHeader());
                        if (res.data.code === 0) stats.value = res.data.data;
                    } catch (e) {
                        if (e.response?.status === 401) handleLogout();
                    }
                };

                const fetchCodes = async () => {
                    loading.value = true;
                    try {
                        const res = await axios.get(`/admin/api/codes?status=${statusFilter.value}&page=${page.value}&pageSize=${pageSize.value}`, getAuthHeader());
                        if (res.data.code === 0) {
                            codesList.value = res.data.data.list;
                            totalCodes.value = res.data.data.total;
                        }
                    } finally {
                        loading.value = false;
                    }
                };

                const fetchMessages = async () => {
                    loading.value = true;
                    try {
                        const res = await axios.get(`/admin/api/messages?page=${msgPage.value}&pageSize=${msgPageSize.value}`, getAuthHeader());
                        if (res.data.code === 0) {
                            messagesList.value = res.data.data.list;
                            totalMessages.value = res.data.data.total;
                        }
                    } finally {
                        loading.value = false;
                    }
                };

                const handleTabChange = (tab) => {
                    if (tab === 'codes') fetchCodes();
                    else fetchMessages();
                };

                const handleImport = async () => {
                    const lines = importText.value.split(/\r?\n/).map(l => l.trim()).filter(l => l);
                    if (!lines.length) return ElementPlus.ElMessage.warning('请输入激活码');
                    importing.value = true;
                    try {
                        const res = await axios.post('/admin/api/codes/import', { codes: lines }, getAuthHeader());
                        if (res.data.code === 0) {
                            ElementPlus.ElMessage.success(res.data.msg);
                            showImport.value = false;
                            importText.value = '';
                            fetchData();
                        }
                    } finally {
                        importing.value = false;
                    }
                };

                onMounted(() => {
                    const token = localStorage.getItem('admin_token');
                    if (token) {
                        isLoggedIn.value = true;
                        fetchData();
                    }
                });

                return {
                    isLoggedIn, password, loading, stats, statusFilter, codesList, messagesList,
                    activeTab, page, pageSize, totalCodes, msgPage, msgPageSize, totalMessages,
                    showImport, importText, importing, handleLogin, handleLogout, fetchData,
                    fetchCodes, fetchMessages, handleTabChange, handleImport
                };
            }
        });
        app.use(ElementPlus);
        app.mount('#app');
    </script>
</body>
</html>
"""

@app.route("/admin", methods=["GET"])
def admin_page():
    return render_template_string(ADMIN_HTML)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
