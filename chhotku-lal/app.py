import os, re, random, datetime as dt
from datetime import date
import media
import bcrypt, jwt, psycopg2, psycopg2.extras
from flask import Flask, jsonify, request, send_from_directory, make_response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__, static_folder="static", static_url_path="")
SECRET = os.environ.get("SECRET_KEY", "dev-only-change-me")
PROD = os.environ.get("RENDER") is not None
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per hour"])
app.config["MAX_CONTENT_LENGTH"] = 6 * 1024 * 1024
CATEGORIES = {"garbage", "drain", "toilet", "road", "other"}

def db():
    return psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=psycopg2.extras.RealDictCursor)

def current_user():
    tok = request.cookies.get("token")
    if not tok: return None
    try:
        p = jwt.decode(tok, SECRET, algorithms=["HS256"])
        return {"id": p["id"], "role": p["role"]}
    except jwt.PyJWTError:
        return None

def login_required(f):
    from functools import wraps
    @wraps(f)
    def w(*a, **k):
        u = current_user()
        if not u: return jsonify(error="auth"), 401
        return f(u, *a, **k)
    return w

def set_token(resp, uid, role):
    tok = jwt.encode({"id": uid, "role": role,
                      "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=7)}, SECRET, algorithm="HS256")
    resp.set_cookie("token", tok, httponly=True, secure=PROD, samesite="Lax", max_age=7*86400)
    return resp

def hash_pw(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
def check_pw(p, h): return bcrypt.checkpw(p.encode(), h.encode())
def good_pw(p): return 8 <= len(p) <= 72

@app.errorhandler(413)
def too_big(e): return jsonify(error="photo"), 413

@app.get("/")
def home(): return send_from_directory("static", "index.html")

@app.get("/api/news")
def news():
    with db() as c, c.cursor() as cur:
        cur.execute("SELECT id,title_hi,title_en,body_hi,body_en,published_at FROM news ORDER BY published_at DESC LIMIT 10")
        return jsonify(cur.fetchall())

@app.post("/api/register")
@limiter.limit("10 per hour")
def register():
    d = request.get_json(silent=True) or {}
    name, mobile, pw = str(d.get("name","")).strip(), str(d.get("mobile","")).strip(), str(d.get("password",""))
    if not (2 <= len(name) <= 100): return jsonify(error="name"), 400
    if not re.fullmatch(r"[6-9]\d{9}", mobile): return jsonify(error="mobile"), 400
    if not good_pw(pw): return jsonify(error="password"), 400
    try:
        with db() as c, c.cursor() as cur:
            cur.execute("INSERT INTO users(name,mobile,password_hash) VALUES(%s,%s,%s) RETURNING id,role",
                        (name, mobile, hash_pw(pw)))
            u = cur.fetchone()
    except psycopg2.errors.UniqueViolation:
        return jsonify(error="exists"), 409
    return set_token(make_response(jsonify(ok=True), 201), u["id"], u["role"])

@app.post("/api/login")
@limiter.limit("10 per 15 minutes")
def login():
    d = request.get_json(silent=True) or {}
    mobile, pw = str(d.get("mobile","")).strip(), str(d.get("password",""))
    with db() as c, c.cursor() as cur:
        cur.execute("SELECT id,role,password_hash FROM users WHERE mobile=%s", (mobile,))
        u = cur.fetchone()
    if not u or not check_pw(pw, u["password_hash"]): return jsonify(error="badlogin"), 401
    return set_token(make_response(jsonify(ok=True)), u["id"], u["role"])

@app.post("/api/logout")
def logout():
    r = make_response(jsonify(ok=True)); r.delete_cookie("token"); return r

@app.get("/api/me")
@login_required
def me(u):
    with db() as c, c.cursor() as cur:
        cur.execute("SELECT name,mobile,role FROM users WHERE id=%s", (u["id"],))
        row = cur.fetchone()
    return jsonify(row) if row else (jsonify(error="auth"), 401)

@app.post("/api/change-password")
@login_required
@limiter.limit("10 per hour")
def change_password(u):
    d = request.get_json(silent=True) or {}
    old, new = str(d.get("old","")), str(d.get("new",""))
    if not good_pw(new): return jsonify(error="password"), 400
    with db() as c, c.cursor() as cur:
        cur.execute("SELECT password_hash FROM users WHERE id=%s", (u["id"],))
        row = cur.fetchone()
        if not row or not check_pw(old, row["password_hash"]): return jsonify(error="old"), 400
        cur.execute("UPDATE users SET password_hash=%s WHERE id=%s", (hash_pw(new), u["id"]))
    return jsonify(ok=True)

@app.get("/api/my/complaints")
@login_required
def my_complaints(u):
    with db() as c, c.cursor() as cur:
        cur.execute("SELECT complaint_no,category,location,status,remarks,created_at FROM complaints "
                    "WHERE user_id=%s ORDER BY created_at DESC", (u["id"],))
        return jsonify(cur.fetchall())

@app.post("/api/complaints")
@limiter.limit("5 per hour")
def create_complaint():
    d = request.form if (request.content_type or "").startswith("multipart/") else (request.get_json(silent=True) or {})
    name, mobile = str(d.get("name","")).strip(), str(d.get("mobile","")).strip()
    cat, loc, desc = str(d.get("category","")).strip(), str(d.get("location","")).strip(), str(d.get("description","")).strip()
    if not (2 <= len(name) <= 100): return jsonify(error="name"), 400
    if not re.fullmatch(r"[6-9]\d{9}", mobile): return jsonify(error="mobile"), 400
    if cat not in CATEGORIES: return jsonify(error="category"), 400
    if not (3 <= len(loc) <= 200): return jsonify(error="location"), 400
    if not (10 <= len(desc) <= 2000): return jsonify(error="description"), 400
    u = current_user()
    photo = None
    f = request.files.get("photo")
    if f and f.filename:
        if not media.configured(): return jsonify(error="photo"), 400
        try: photo = media.upload(f, "complaints")
        except Exception: return jsonify(error="photo"), 400
    for _ in range(5):
        no = f"CL-{date.today():%y%m%d}-{random.randint(10000, 99999)}"
        try:
            with db() as c, c.cursor() as cur:
                cur.execute("INSERT INTO complaints(complaint_no,name,mobile,category,location,description,user_id,photo_url)"
                            " VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", (no, name, mobile, cat, loc, desc, u["id"] if u else None, photo))
            return jsonify(complaint_no=no), 201
        except psycopg2.errors.UniqueViolation:
            continue
    return jsonify(error="server"), 500

@app.get("/api/complaints/track")
@limiter.limit("30 per hour")
def track():
    no, mobile = request.args.get("no","").strip().upper(), request.args.get("mobile","").strip()
    with db() as c, c.cursor() as cur:
        cur.execute("SELECT complaint_no,category,location,status,remarks,created_at,updated_at "
                    "FROM complaints WHERE complaint_no=%s AND mobile=%s", (no, mobile))
        row = cur.fetchone()
    return (jsonify(row), 200) if row else (jsonify(error="not_found"), 404)

import admin_routes
admin_routes.register(app, db, current_user, limiter)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
