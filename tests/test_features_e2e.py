import os
import sys
import tempfile
import time
import threading
import hashlib
import json
import xml.etree.ElementTree as ET
import requests
import uvicorn

# 确保在项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 使用临时 DB 运行测试，清空环境变量模拟全新未配置启动
temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
temp_db.close()
os.environ["DB_PATH"] = temp_db.name
os.environ["WECHAT_TOKEN"] = ""
os.environ["ADMIN_PASSWORD"] = ""
os.environ["WEBSITE_URL"] = ""
os.environ["ALLOWED_HOSTS"] = "*"

from app import app
import db.database as d
import core.config_store as cs

print("[Init] Initializing database and running migrations...")
d.init_db()

# 启动后台测试服务器
PORT = 8999
BASE_URL = f"http://127.0.0.1:{PORT}"

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="error")

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

# 等待服务就绪
for _ in range(50):
    try:
        r = requests.get(f"{BASE_URL}/healthz", timeout=1)
        if r.status_code == 200:
            break
    except Exception:
        time.sleep(0.1)

INIT_PWD = "InitialAdminPass123!"
INIT_TOKEN = "dynamic_token_001"
res_setup = requests.post(f"{BASE_URL}/api/setup", json={
    "admin_password": INIT_PWD,
    "wechat_token": INIT_TOKEN,
    "website_url": "https://init.example.com",
    "group_id": "group_helper_01"
})
assert res_setup.status_code == 200, f"Setup failed: {res_setup.text}"
admin_token = res_setup.json()["token"]
headers = {"Authorization": f"Bearer {admin_token}"}
print("[Setup] First-run setup completed, admin token issued")

def gen_wechat_params(current_token: str):
    ts = str(int(time.time()))
    nonce = "12345678"
    items = sorted([current_token, ts, nonce])
    sig = hashlib.sha1("".join(items).encode("utf-8")).hexdigest()
    return {"signature": sig, "timestamp": ts, "nonce": nonce}

wx_params = gen_wechat_params(INIT_TOKEN)

# ==========================================
# E2E-01: 卡池管理 CRUD、唯一性与删除阻断
# ==========================================
print("\n[E2E-01] Testing Code Pools CRUD & constraints...")
# 查询默认池
pools_res = requests.get(f"{BASE_URL}/api/pools", headers=headers)
assert pools_res.status_code == 200
pools = pools_res.json()["pools"]
assert len(pools) >= 1
assert pools[0]["id"] == 1 and pools[0]["key"] == "default"

# 创建新品类 gpt
p_gpt = requests.post(f"{BASE_URL}/api/pools", json={
    "name": "ChatGPT 4.0",
    "key": "gpt",
    "description": "GPT专属池"
}, headers=headers)
assert p_gpt.status_code == 200
gpt_pool_id = p_gpt.json()["id"]

# 创建新品类 mj
p_mj = requests.post(f"{BASE_URL}/api/pools", json={
    "name": "Midjourney 绘图",
    "key": "mj",
    "description": "MJ绘图卡券"
}, headers=headers)
assert p_mj.status_code == 200
mj_pool_id = p_mj.json()["id"]

# 验证重复 key 阻断
dup_res = requests.post(f"{BASE_URL}/api/pools", json={"name": "GPT-Repeat", "key": "gpt"}, headers=headers)
assert dup_res.status_code == 400
assert "已存在" in dup_res.text

# 验证删除默认池阻断
del_def_res = requests.delete(f"{BASE_URL}/api/pools/1", headers=headers)
assert del_def_res.status_code == 400
assert "默认卡券池禁止删除" in del_def_res.text

# 验证手动设置主卡池 (set-default)
set_def_res = requests.post(f"{BASE_URL}/api/pools/{gpt_pool_id}/set-default", headers=headers)
assert set_def_res.status_code == 200
p_list_check = requests.get(f"{BASE_URL}/api/pools", headers=headers).json()["pools"]
gpt_check = next(p for p in p_list_check if p["id"] == gpt_pool_id)
def_check = next(p for p in p_list_check if p["id"] == 1)
assert gpt_check["is_default"] is True
assert def_check["is_default"] is False

# 恢复默认卡券池为主池
requests.post(f"{BASE_URL}/api/pools/1/set-default", headers=headers)
p_list_restored = requests.get(f"{BASE_URL}/api/pools", headers=headers).json()["pools"]
assert next(p for p in p_list_restored if p["id"] == 1)["is_default"] is True

print("  -> Code pools CRUD and constraint guards verified OK")

# ==========================================
# E2E-02: 多品类激活码导入与库存统计
# ==========================================
print("\n[E2E-02] Testing multi-pool code import & stats...")
# 导入 default 池激活码
imp_def = requests.post(f"{BASE_URL}/api/import", json={
    "pool_id": 1,
    "codes": ["DEF-101", "DEF-102", "DEF-103"]
}, headers=headers)
assert imp_def.status_code == 200
assert imp_def.json()["added"] == 3

# 使用 multi_pool_codes 导入 gpt 和 mj 激活码
imp_multi = requests.post(f"{BASE_URL}/api/import", json={
    "multi_pool_codes": {
        "gpt": ["GPT-201", "GPT-202", "GPT-203"],
        "mj": ["MJ-301", "MJ-302"]
    }
}, headers=headers)
assert imp_multi.status_code == 200
assert imp_multi.json()["added"] == 5
assert imp_multi.json()["by_pool"]["gpt"] == 3
assert imp_multi.json()["by_pool"]["mj"] == 2

# 验证大盘各池统计
stats_res = requests.get(f"{BASE_URL}/api/stats", headers=headers)
assert stats_res.status_code == 200
p_stats = {p["key"]: p["unused"] for p in stats_res.json()["pools"]}
assert p_stats["default"] == 3
assert p_stats["gpt"] == 3
assert p_stats["mj"] == 2

# 验证池内有码时删除卡池被安全阻断
del_non_empty = requests.delete(f"{BASE_URL}/api/pools/{gpt_pool_id}", headers=headers)
assert del_non_empty.status_code == 400
assert "尚有激活码" in del_non_empty.text
print("  -> Multi-pool code import & inventory stats verified OK")

# ==========================================
# E2E-03: 规则配方创建与查询
# ==========================================
print("\n[E2E-03] Testing keyword rule with dispatch recipe...")
# 创建组合发码规则：发 default×1 + gpt×2
combo_recipe = json.dumps([
    {"pool_id": 1, "key": "default", "count": 1},
    {"pool_id": gpt_pool_id, "key": "gpt", "count": 2}
])
rule_res = requests.post(f"{BASE_URL}/api/rules", json={
    "keyword": "双重好礼",
    "mode": "contains",
    "action": "code",
    "priority": 5,
    "enabled": True,
    "recipe": combo_recipe,
    "content": "恭喜 {openid}！\n首码：{code}\nGPT卡密：{code.gpt}\n所有清单：\n{codes}\n兑换地址：{site}"
}, headers=headers)
assert rule_res.status_code == 200
combo_rule_id = rule_res.json()["id"]

# 查询规则验证 recipe
rules_get = requests.get(f"{BASE_URL}/api/rules", headers=headers)
created_rule = next(r for r in rules_get.json()["rules"] if r["id"] == combo_rule_id)
assert created_rule["recipe"] == combo_recipe
print("  -> Keyword rule with multi-pool recipe created OK")

# ==========================================
# E2E-04: 多品类组合发码（双品类发码）
# ==========================================
print("\n[E2E-04] Testing multi-pool combination dispatch...")
xml_req_user1 = """<xml>
<ToUserName><![CDATA[gh_test]]></ToUserName>
<FromUserName><![CDATA[fan_alice]]></FromUserName>
<CreateTime>12345680</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[我想领双重好礼]]></Content>
</xml>"""
res_wx_1 = requests.post(f"{BASE_URL}/wechat", params=wx_params, data=xml_req_user1.encode("utf-8"))
assert res_wx_1.status_code == 200
root1 = ET.fromstring(res_wx_1.content.decode("utf-8"))
reply1 = root1.findtext("Content") or ""
assert "恭喜 fan_alice" in reply1
assert "DEF-101" in reply1
assert "GPT-201, GPT-202" in reply1 or ("GPT-201" in reply1 and "GPT-202" in reply1)
assert "https://init.example.com" in reply1

# 验证已领取用户列表正确聚合全部 3 张卡密
users_res = requests.get(f"{BASE_URL}/api/users", headers=headers)
assert users_res.status_code == 200
alice_data = next(u for u in users_res.json()["users"] if u["openid"] == "fan_alice")
assert alice_data["total_codes"] == 3
assert len(alice_data["claims"]) == 3
claimed_codes = [c["code"] for c in alice_data["claims"]]
assert "DEF-101" in claimed_codes
assert "GPT-201" in claimed_codes and "GPT-202" in claimed_codes
print("  -> User list claims aggregation successfully verified (all 3 codes present)")
print("  -> Combo dispatch successfully issued 1 default code and 2 gpt codes")

# ==========================================
# E2E-05: 一人一套码幂等防重验证
# ==========================================
print("\n[E2E-05] Testing idempotent repeat claim...")
res_wx_1_repeat = requests.post(f"{BASE_URL}/wechat", params=wx_params, data=xml_req_user1.encode("utf-8"))
assert res_wx_1_repeat.status_code == 200
reply1_repeat = ET.fromstring(res_wx_1_repeat.content.decode("utf-8")).findtext("Content") or ""
assert reply1_repeat == reply1, "Expected repeat claim to return identical reply"

# 验证各池库存：default 被领 1 个 (剩 2 个)，gpt 被领 2 个 (剩 1 个)
stats_after_1 = requests.get(f"{BASE_URL}/api/stats", headers=headers).json()
p_after_1 = {p["key"]: p["unused"] for p in stats_after_1["pools"]}
assert p_after_1["default"] == 2
assert p_after_1["gpt"] == 1
print("  -> Idempotent duplicate claim returned existing codes without re-deducting stock")

# ==========================================
# E2E-06: 部分品类缺货时的 All-or-Nothing 原子回滚
# ==========================================
print("\n[E2E-06] Testing out-of-stock atomic rollback...")
# 另一个粉丝 fan_bob 再次申请“双重好礼”（需要 gpt×2，但此时 gpt 仅剩 1 个）
xml_req_user2 = """<xml>
<ToUserName><![CDATA[gh_test]]></ToUserName>
<FromUserName><![CDATA[fan_bob]]></FromUserName>
<CreateTime>12345681</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[双重好礼]]></Content>
</xml>"""
res_wx_2 = requests.post(f"{BASE_URL}/wechat", params=wx_params, data=xml_req_user2.encode("utf-8"))
assert res_wx_2.status_code == 200
reply2 = ET.fromstring(res_wx_2.content.decode("utf-8")).findtext("Content") or ""
assert "已被领完" in reply2, f"Expected empty reply, got: {reply2}"

# 关键原子性验证：default 池必须完全未扣减（依然保持 2 个）！
stats_after_rollback = requests.get(f"{BASE_URL}/api/stats", headers=headers).json()
p_rollback = {p["key"]: p["unused"] for p in stats_after_rollback["pools"]}
assert p_rollback["default"] == 2, f"Expected default pool to retain 2 codes, got: {p_rollback['default']}"
assert p_rollback["gpt"] == 1, f"Expected gpt pool to retain 1 code, got: {p_rollback['gpt']}"
print("  -> All-or-Nothing atomic rollback safely triggered on partial shortage")

# ==========================================
# E2E-07: 增强占位符渲染输出验证
# ==========================================
print("\n[E2E-07] Testing rich placeholder engine...")
# 创建包含全套占位符的规则
requests.post(f"{BASE_URL}/api/rules", json={
    "keyword": "占位符测试",
    "mode": "exact",
    "action": "none",
    "priority": 1,
    "enabled": True,
    "content": "ID:{openid}|D:{date}|T:{time}|S:{stock}|群:{group}"
}, headers=headers)

xml_holder = """<xml>
<ToUserName><![CDATA[gh_test]]></ToUserName>
<FromUserName><![CDATA[fan_tester]]></FromUserName>
<CreateTime>12345682</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[占位符测试]]></Content>
</xml>"""
res_holder = requests.post(f"{BASE_URL}/wechat", params=wx_params, data=xml_holder.encode("utf-8"))
assert res_holder.status_code == 200
root_holder = ET.fromstring(res_holder.content.decode("utf-8"))
holder_reply = root_holder.findtext("Content") or ""
assert "ID:fan_tester" in holder_reply
assert time.strftime("%Y-%m-%d") in holder_reply
assert "群:group_helper_01" in holder_reply
assert "默认卡券池" in holder_reply or "GPT" in holder_reply
print("  -> Rich placeholders ({openid}, {date}, {time}, {stock}, {group}) verified OK")

# ==========================================
# E2E-08: 用户重置后的级联清理与二次领码
# ==========================================
print("\n[E2E-08] Testing cascade reset and re-claiming...")
# 重置 fan_alice 用户
reset_user_res = requests.post(f"{BASE_URL}/api/users/reset", json={"openid": "fan_alice"}, headers=headers)
assert reset_user_res.status_code == 200
assert reset_user_res.json()["reset"] is True

# 验证激活码状态恢复为 unused，库存恢复
stats_after_reset = requests.get(f"{BASE_URL}/api/stats", headers=headers).json()
p_reset = {p["key"]: p["unused"] for p in stats_after_reset["pools"]}
assert p_reset["default"] == 3
assert p_reset["gpt"] == 3

# 补充库存后，fan_bob 再次领取成功
res_bob_claim = requests.post(f"{BASE_URL}/wechat", params=wx_params, data=xml_req_user2.encode("utf-8"))
assert res_bob_claim.status_code == 200
bob_reply = ET.fromstring(res_bob_claim.content.decode("utf-8")).findtext("Content") or ""
assert "恭喜 fan_bob" in bob_reply
print("  -> Cascade reset and code re-allocation verified OK")

# ==========================================
# E2E-09: 规则批量操作与导入
# ==========================================
print("\n[E2E-09] Testing rule batch operations...")
# 批量导入规则
batch_imp_res = requests.post(f"{BASE_URL}/api/rules/batch-import", json={
    "mode": "skip",
    "rules": [
        {"keyword": "批量A", "mode": "contains", "action": "none", "content": "内容A", "priority": 50, "enabled": True},
        {"keyword": "批量B", "mode": "exact", "action": "none", "content": "内容B", "priority": 60, "enabled": True}
    ]
}, headers=headers)
assert batch_imp_res.status_code == 200
assert batch_imp_res.json()["added"] == 2

rules_all = requests.get(f"{BASE_URL}/api/rules", headers=headers).json()["rules"]
target_rule_ids = [r["id"] for r in rules_all if r["keyword"] in ("批量A", "批量B")]
assert len(target_rule_ids) == 2

# 批量停用
toggle_off = requests.post(f"{BASE_URL}/api/rules/batch-toggle", json={"ids": target_rule_ids, "enabled": False}, headers=headers)
assert toggle_off.status_code == 200

# 批量删除
del_batch = requests.post(f"{BASE_URL}/api/rules/batch-delete", json={"ids": target_rule_ids}, headers=headers)
assert del_batch.status_code == 200
rules_after_del = requests.get(f"{BASE_URL}/api/rules", headers=headers).json()["rules"]
assert not any(r["id"] in target_rule_ids for r in rules_after_del)
print("  -> Batch import, toggle, and delete rules verified OK")

# ==========================================
# E2E-10: 微信 Token 动态热更新机制回归
# ==========================================
print("\n[E2E-10] Testing WeChat token hot reload regression...")
NEW_HOT_TOKEN = "new_super_token_999"
res_upd = requests.put(f"{BASE_URL}/api/config", json={
    "wechat_token": NEW_HOT_TOKEN
}, headers=headers)
assert res_upd.status_code == 200

# 旧 Token 验签立即失效
old_p = gen_wechat_params(INIT_TOKEN)
res_old = requests.get(f"{BASE_URL}/wechat", params={**old_p, "echostr": "old_test"})
assert res_old.status_code == 403

# 新 Token 验签立即生效
new_p = gen_wechat_params(NEW_HOT_TOKEN)
res_new = requests.get(f"{BASE_URL}/wechat", params={**new_p, "echostr": "hot_reload_success"})
assert res_new.status_code == 200
assert res_new.text == "hot_reload_success"
print("  -> Token hot reload regression verified OK")

# 清理测试临时库
try:
    os.remove(temp_db.name)
except Exception:
    pass

print("\n🎉 ALL E2E SUITE TESTS (E2E-01 -> E2E-10) PASSED SUCCESSFULLY!")
