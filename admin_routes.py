from functools import wraps
from flask import jsonify, request

STATUSES = {"Pending", "In Progress", "Resolved", "Rejected"}

def register(app, db, current_user, limiter):
    def admin_required(f):
        @wraps(f)
        def w(*a, **k):
            u = current_user()
            if not u: return jsonify(error="auth"), 401
            with db() as c, c.cursor() as cur:
                cur.execute("SELECT role FROM users WHERE id=%s", (u["id"],))
                r = cur.fetchone()
            if not r or r["role"] != "admin": return jsonify(error="forbidden"), 403
            return f(u, *a, **k)
        return w

    def log(uid, action, detail):
        with db() as c, c.cursor() as cur:
            cur.execute("INSERT INTO activity_logs(user_id,action,detail) VALUES(%s,%s,%s)", (uid, action, detail))

    @app.get("/api/admin/stats")
    @admin_required
    def stats(u):
        with db() as c, c.cursor() as cur:
            cur.execute("SELECT count(*) n FROM users"); users = cur.fetchone()["n"]
            cur.execute("SELECT status, count(*) n FROM complaints GROUP BY status")
            by = {r["status"]: r["n"] for r in cur.fetchall()}
        return jsonify(users=users, total=sum(by.values()), pending=by.get("Pending", 0),
                       progress=by.get("In Progress", 0), resolved=by.get("Resolved", 0), rejected=by.get("Rejected", 0))

    @app.get("/api/admin/complaints")
    @admin_required
    def complaints(u):
        st = request.args.get("status", "")
        q = "SELECT complaint_no,name,mobile,category,location,description,status,remarks,created_at,photo_url FROM complaints"
        args = []
        if st in STATUSES: q += " WHERE status=%s"; args.append(st)
        q += " ORDER BY created_at DESC LIMIT 100"
        with db() as c, c.cursor() as cur:
            cur.execute(q, args); return jsonify(cur.fetchall())

    @app.patch("/api/admin/complaints/<no>")
    @admin_required
    def update(u, no):
        d = request.get_json(silent=True) or {}
        st, rem = str(d.get("status", "")), str(d.get("remarks", "")).strip()[:500]
        if st not in STATUSES: return jsonify(error="status"), 400
        with db() as c, c.cursor() as cur:
            cur.execute("UPDATE complaints SET status=%s, remarks=%s, updated_at=now() WHERE complaint_no=%s RETURNING id",
                        (st, rem or None, no))
            if not cur.fetchone(): return jsonify(error="not_found"), 404
        log(u["id"], "complaint_update", f"{no} -> {st}")
        return jsonify(ok=True)

    @app.delete("/api/admin/complaints/<no>")
    @admin_required
    def delete(u, no):
        with db() as c, c.cursor() as cur:
            cur.execute("DELETE FROM complaints WHERE complaint_no=%s RETURNING id", (no,))
            if not cur.fetchone(): return jsonify(error="not_found"), 404
        log(u["id"], "complaint_delete", no)
        return jsonify(ok=True)

    @app.get("/api/admin/logs")
    @admin_required
    def logs(u):
        with db() as c, c.cursor() as cur:
            cur.execute("SELECT action,detail,created_at FROM activity_logs ORDER BY created_at DESC LIMIT 30")
            return jsonify(cur.fetchall())

    import re as _re
    from datetime import date as _date
    KINDS = {"news", "notice", "schedule", "activity", "photo", "video", "service"}
    URL_KEYS = {"maps_url", "facebook", "youtube", "photo_url"}
    SKEYS = URL_KEYS | {"about_hi", "about_en", "panchayat_hi", "panchayat_en", "sbm_hi", "sbm_en",
                        "phone", "whatsapp", "email", "address_hi", "address_en"}
    https = lambda u: u == "" or u.lower().startswith("https://")

    @app.get("/api/posts")
    def posts_list():
        with db() as c, c.cursor() as cur:
            cur.execute("SELECT id,kind,title_hi,title_en,body_hi,body_en,event_date,media_url,before_url FROM posts "
                        "ORDER BY event_date DESC, id DESC LIMIT 300")
            return jsonify(cur.fetchall())

    @app.get("/api/settings")
    def settings_get():
        with db() as c, c.cursor() as cur:
            cur.execute("SELECT key,value FROM settings")
            return jsonify({r["key"]: r["value"] for r in cur.fetchall()})

    def clean_post(d):
        kind = str(d.get("kind", ""))
        th, te = str(d.get("title_hi", "")).strip()[:200], str(d.get("title_en", "")).strip()[:200]
        bh, be = str(d.get("body_hi", "")).strip()[:2000], str(d.get("body_en", "")).strip()[:2000]
        url = str(d.get("media_url", "")).strip()[:500]
        bu = str(d.get("before_url", "")).strip()[:500]
        try: ed = _date.fromisoformat(str(d.get("event_date", ""))[:10])
        except ValueError: ed = _date.today()
        if kind not in KINDS or not (th or te) or not https(url) or not https(bu): return None
        if kind in ("photo", "video") and not url: return None
        return (kind, th, te, bh, be, ed, url or None, bu or None)

    @app.post("/api/admin/posts")
    @admin_required
    def post_add(u):
        v = clean_post(request.get_json(silent=True) or {})
        if not v: return jsonify(error="invalid"), 400
        with db() as c, c.cursor() as cur:
            cur.execute("INSERT INTO posts(kind,title_hi,title_en,body_hi,body_en,event_date,media_url,before_url) "
                        "VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id", v)
            pid = cur.fetchone()["id"]
        log(u["id"], "post_add", f"{v[0]} #{pid}")
        return jsonify(id=pid), 201

    @app.put("/api/admin/posts/<int:pid>")
    @admin_required
    def post_edit(u, pid):
        v = clean_post(request.get_json(silent=True) or {})
        if not v: return jsonify(error="invalid"), 400
        with db() as c, c.cursor() as cur:
            cur.execute("UPDATE posts SET kind=%s,title_hi=%s,title_en=%s,body_hi=%s,body_en=%s,event_date=%s,media_url=%s,before_url=%s "
                        "WHERE id=%s RETURNING id", v + (pid,))
            if not cur.fetchone(): return jsonify(error="not_found"), 404
        log(u["id"], "post_edit", f"{v[0]} #{pid}")
        return jsonify(ok=True)

    @app.delete("/api/admin/posts/<int:pid>")
    @admin_required
    def post_del(u, pid):
        with db() as c, c.cursor() as cur:
            cur.execute("DELETE FROM posts WHERE id=%s RETURNING kind", (pid,))
            r = cur.fetchone()
            if not r: return jsonify(error="not_found"), 404
        log(u["id"], "post_delete", f"{r['kind']} #{pid}")
        return jsonify(ok=True)

    @app.put("/api/admin/settings")
    @admin_required
    def settings_put(u):
        d = request.get_json(silent=True) or {}
        rows = []
        for k, v in d.items():
            if k not in SKEYS: continue
            v = str(v).strip()[:3000]
            if k in URL_KEYS and not https(v): return jsonify(error="invalid", field=k), 400
            if k in ("phone", "whatsapp"):
                v = _re.sub(r"[\s+-]", "", v)
                if v and not _re.fullmatch(r"\d{10,15}", v): return jsonify(error="invalid", field=k), 400
            if k == "email" and v and not _re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v):
                return jsonify(error="invalid", field=k), 400
            rows.append((k, v))
        with db() as c, c.cursor() as cur:
            for k, v in rows:
                cur.execute("INSERT INTO settings(key,value) VALUES(%s,%s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (k, v))
        log(u["id"], "settings_update", ", ".join(k for k, _ in rows))
        return jsonify(ok=True)

    @app.post("/api/admin/upload")
    @admin_required
    def upload(u):
        import media
        f = request.files.get("file")
        if not f or not media.configured(): return jsonify(error="upload"), 400
        try: url = media.upload(f, "site")
        except Exception: return jsonify(error="upload"), 400
        log(u["id"], "upload", url[-40:])
        return jsonify(url=url)
