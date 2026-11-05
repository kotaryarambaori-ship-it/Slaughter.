import os, re, random, hmac
from datetime import date
from functools import wraps
import psycopg2, psycopg2.extras
from flask import Flask, jsonify, request, send_from_directory, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  SESSION_COOKIE_SECURE=bool(os.environ.get("RENDER")))
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]
limiter = Limiter(get_remote_address, app=app, default_limits=["300 per hour"])

CATS = {"garbage", "drain", "toilet", "road", "other"}
STATUSES = {"Pending", "In Progress", "Resolved", "Rejected"}
KINDS = {"news", "notice", "schedule", "work", "service", "photo", "video"}
URL_KEYS = {"photo_url", "maps_url", "facebook", "youtube"}
https = lambda u: u == "" or u.lower().startswith("https://")
SKEYS = URL_KEYS | {"about_hi", "about_en", "panchayat_hi", "panchayat_en", "sbm_hi", "sbm_en",
                    "phone", "whatsapp", "email", "address_hi", "address_en"}

def db():
    return psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=psycopg2.extras.RealDictCursor)

with db() as c, c.cursor() as cur:
    cur.execute("""
    CREATE TABLE IF NOT EXISTS complaints(
      id SERIAL PRIMARY KEY, complaint_no VARCHAR(20) UNIQUE NOT NULL, name VARCHAR(100) NOT NULL,
      mobile VARCHAR(10) NOT NULL, category VARCHAR(20) NOT NULL, location VARCHAR(200) NOT NULL,
      description TEXT NOT NULL, status VARCHAR(20) NOT NULL DEFAULT 'Pending', remarks TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now());
    CREATE TABLE IF NOT EXISTS posts(
      id SERIAL PRIMARY KEY, kind VARCHAR(10) NOT NULL, title_hi VARCHAR(200) NOT NULL DEFAULT '',
      title_en VARCHAR(200) NOT NULL DEFAULT '', body_hi TEXT NOT NULL DEFAULT '',
      body_en TEXT NOT NULL DEFAULT '', created_at TIMESTAMPTZ NOT NULL DEFAULT now());
    ALTER TABLE posts ADD COLUMN IF NOT EXISTS media_url VARCHAR(500);
    CREATE TABLE IF NOT EXISTS settings(key VARCHAR(30) PRIMARY KEY, value TEXT NOT NULL DEFAULT '');
    """)

def admin_only(f):
    @wraps(f)
    def w(*a, **k):
        if not session.get("admin"): return jsonify(error="auth"), 401
        return f(*a, **k)
    return w

@app.get("/")
def home():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), "index.html")

@app.get("/api/data")
def data():
    with db() as c, c.cursor() as cur:
        cur.execute("SELECT id,kind,title_hi,title_en,body_hi,body_en,media_url,created_at FROM posts ORDER BY id DESC LIMIT 200")
        posts = cur.fetchall()
        cur.execute("SELECT key,value FROM settings")
        st = {r["key"]: r["value"] for r in cur.fetchall()}
    return jsonify(posts=posts, settings=st)

@app.post("/api/complaints")
@limiter.limit("5 per hour")
def complaint():
    d = request.get_json(silent=True) or {}
    name, mobile = str(d.get("name", "")).strip(), str(d.get("mobile", "")).strip()
    cat, loc, desc = str(d.get("category", "")), str(d.get("location", "")).strip(), str(d.get("description", "")).strip()
    if not 2 <= len(name) <= 100: return jsonify(error="name"), 400
    if not re.fullmatch(r"[6-9]\d{9}", mobile): return jsonify(error="mobile"), 400
    if cat not in CATS: return jsonify(error="category"), 400
    if not 3 <= len(loc) <= 200: return jsonify(error="location"), 400
    if not 10 <= len(desc) <= 2000: return jsonify(error="description"), 400
    for _ in range(5):
        no = f"CL-{date.today():%y%m%d}-{random.randint(10000, 99999)}"
        try:
            with db() as c, c.cursor() as cur:
                cur.execute("INSERT INTO complaints(complaint_no,name,mobile,category,location,description) VALUES(%s,%s,%s,%s,%s,%s)",
                            (no, name, mobile, cat, loc, desc))
            return jsonify(complaint_no=no), 201
        except psycopg2.errors.UniqueViolation:
            continue
    return jsonify(error="server"), 500

@app.get("/api/track")
@limiter.limit("30 per hour")
def track():
    no, mobile = request.args.get("no", "").strip().upper(), request.args.get("mobile", "").strip()
    with db() as c, c.cursor() as cur:
        cur.execute("SELECT complaint_no,status,remarks FROM complaints WHERE complaint_no=%s AND mobile=%s", (no, mobile))
        r = cur.fetchone()
    return (jsonify(r), 200) if r else (jsonify(error="not_found"), 404)

@app.post("/api/admin/login")
@limiter.limit("10 per 15 minutes")
def login():
    pw = str((request.get_json(silent=True) or {}).get("password", ""))
    if not hmac.compare_digest(pw.encode(), ADMIN_PASSWORD.encode()): return jsonify(error="badlogin"), 401
    session["admin"] = True
    return jsonify(ok=True)

@app.post("/api/admin/logout")
def logout():
    session.clear(); return jsonify(ok=True)

@app.get("/api/admin/me")
@admin_only
def me(): return jsonify(ok=True)

@app.get("/api/admin/complaints")
@admin_only
def a_list():
    with db() as c, c.cursor() as cur:
        cur.execute("SELECT complaint_no,name,mobile,category,location,description,status,remarks,created_at FROM complaints ORDER BY id DESC LIMIT 200")
        return jsonify(cur.fetchall())

@app.patch("/api/admin/complaints/<no>")
@admin_only
def a_update(no):
    d = request.get_json(silent=True) or {}
    st, rem = str(d.get("status", "")), str(d.get("remarks", "")).strip()[:500]
    if st not in STATUSES: return jsonify(error="status"), 400
    with db() as c, c.cursor() as cur:
        cur.execute("UPDATE complaints SET status=%s,remarks=%s WHERE complaint_no=%s RETURNING id", (st, rem or None, no))
        if not cur.fetchone(): return jsonify(error="not_found"), 404
    return jsonify(ok=True)

@app.delete("/api/admin/complaints/<no>")
@admin_only
def a_delete(no):
    with db() as c, c.cursor() as cur:
        cur.execute("DELETE FROM complaints WHERE complaint_no=%s", (no,))
    return jsonify(ok=True)

@app.post("/api/admin/posts")
@admin_only
def p_add():
    d = request.get_json(silent=True) or {}
    kind = str(d.get("kind", ""))
    v = [str(d.get(k, "")).strip()[:2000] for k in ("title_hi", "title_en", "body_hi", "body_en")]
    v[0], v[1] = v[0][:200], v[1][:200]
    url = str(d.get("media_url", "")).strip()[:500]
    if kind not in KINDS or not (v[0] or v[1]) or not https(url): return jsonify(error="invalid"), 400
    if kind in ("photo", "video") and not url: return jsonify(error="invalid"), 400
    with db() as c, c.cursor() as cur:
        cur.execute("INSERT INTO posts(kind,title_hi,title_en,body_hi,body_en,media_url) VALUES(%s,%s,%s,%s,%s,%s)", [kind] + v + [url or None])
    return jsonify(ok=True), 201

@app.delete("/api/admin/posts/<int:pid>")
@admin_only
def p_del(pid):
    with db() as c, c.cursor() as cur:
        cur.execute("DELETE FROM posts WHERE id=%s", (pid,))
    return jsonify(ok=True)

@app.put("/api/admin/settings")
@admin_only
def s_put():
    rows = []
    for k, v in (request.get_json(silent=True) or {}).items():
        if k not in SKEYS: continue
        v = str(v).strip()[:3000]
        if k in URL_KEYS and not https(v): return jsonify(error="invalid", field=k), 400
        if k in ("phone", "whatsapp"):
            v = re.sub(r"[\s+-]", "", v)
            if v and not re.fullmatch(r"\d{10,15}", v): return jsonify(error="invalid", field=k), 400
        if k == "email" and v and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v): return jsonify(error="invalid", field=k), 400
        rows.append((k, v))
    with db() as c, c.cursor() as cur:
        for k, v in rows:
            cur.execute("INSERT INTO settings(key,value) VALUES(%s,%s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (k, v))
    return jsonify(ok=True)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
