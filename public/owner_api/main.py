# main.py  — editor.html 準拠 People API（一覧は配列、delete は Body/Query 両対応）
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from typing import Optional, List, Dict, Any
import sqlite3
import subprocess

# ==== 環境・パス規約（既存規約に合わせる） =========================================
ROOT = Path(__file__).resolve().parents[2]  # <repo-root> を想定
DBROOT = ROOT / "db"

def db_path(u: str, p: str) -> Path:
    u2, p2 = (u or "").strip().lower(), (p or "").strip().lower()
    path = DBROOT / u2 / f"{p2}.db"
    if not path.exists():
        raise HTTPException(404, f"DB not found: {path}")
    return path

def qall(cur, sql: str, args=()):
    cur.execute(sql, args)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]

# ==== アプリ本体 / CORS ============================================================
app = FastAPI(title="Owner API (People only)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== Events API (editor.html 準拠) =========================================

# 既に ROOT/DBROOT がある前提。Exporter の場所を指定（例）
EXPORTER = ROOT / "cloud_export_json.py"  # 例：<repo-root>/cloud_export_json.py

# 一覧: GET /owner/api/events?u=&p=[&ts=...]
@app.get("/owner/api/events")
def events_list(u: str = Query(...), p: str = Query(...), ts: str | None = None):
    """
    editor.html は v_events の (id,date,title,sub_title,venue) を使う
    ts はキャッシュ避け用。サーバ側では無視して良い
    """
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = qall(cur, """
            SELECT id, date, title, sub_title, venue
            FROM v_events
            ORDER BY date DESC, id DESC
        """)
    return rows  # 配列

# 更新: PUT /owner/api/events/{event_id}?u=&p=
@app.put("/owner/api/events/{event_id}")
def events_update(event_id: int,
                  u: str = Query(...), p: str = Query(...),
                  body: dict = Body(...)):
    """
    Content-Type: application/json で来る → CORS/OPTIONS 必須（すでにミドルウェアでOK）
    受け取る可能性のあるキー: date, title, sub_title, venue_id など
    """
    allowed_cols = {"date", "title", "sub_title", "venue_id", "form", "era_id", "tour_id"}
    set_cols, values = [], []
    for k, v in body.items():
        if k in allowed_cols:
            set_cols.append(f"{k}=?")
            values.append(v)

    if not set_cols:
        return {"ok": True}  # 変更なし

    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        # 存在確認
        cur.execute("SELECT COUNT(1) FROM events WHERE id=?", (event_id,))
        if cur.fetchone()[0] == 0:
            raise HTTPException(404, f"event not found: {event_id}")
        cur.execute(f"UPDATE events SET {', '.join(set_cols)} WHERE id=?", (*values, event_id))
        conn.commit()
    return {"ok": True}

# ビルド: POST /owner/api/build?u=&p=
@app.post("/owner/api/build")
def build(u: str = Query(...), p: str = Query(...)):
    if not EXPORTER.exists():
        raise HTTPException(500, f"exporter not found: {EXPORTER}")
    # 同期実行（MVP）
    proc = subprocess.run(
        ["python", str(EXPORTER), u, p],
        cwd=str(ROOT),
        capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise HTTPException(500, f"build failed: {proc.stderr}")
    return {"ok": True, "log_tail": proc.stdout[-500:]}

# lineup: GET /owner/api/lineup/{event_id}?u=&p=
@app.get("/owner/api/lineup/{event_id}")
def lineup(event_id: int, u: str = Query(...), p: str = Query(...)):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = qall(cur, """
            SELECT event_id, person, role, position
            FROM v_event_members
            WHERE event_id = ?
              AND seq IS NULL
        """, (event_id,))
    return rows  # 配列

# bandsevent: GET /owner/api/bandsevent/{event_id}?u=&p=
@app.get("/owner/api/bandsevent/{event_id}")
def bandsevent(event_id: int, u: str = Query(...), p: str = Query(...)):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = qall(cur, """
            SELECT event_id, seq, act_name
            FROM v_bandsevent
            WHERE event_id = ?
            ORDER BY seq
        """, (event_id,))
    return rows

# setlist: GET /owner/api/setlist/{event_id}?u=&p=
@app.get("/owner/api/setlist/{event_id}")
def setlist(event_id: int, u: str = Query(...), p: str = Query(...)):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = qall(cur, """
            SELECT event_id, seq, song_title, section, version
            FROM v_setlist
            WHERE event_id = ?
            ORDER BY seq
        """, (event_id,))
    return rows
# ========================================================================



# ==== People: モデル（UIが送る・受けるもの） ======================================
class PeopleCreate(BaseModel):
    name: str
    birthday: Optional[str] = None
    joined_on: Optional[str] = None
    left_on: Optional[str] = None
    # note は「未使用方針」のため扱わない
    x: Optional[str] = None
    instagram: Optional[str] = None
    threads: Optional[str] = None
    facebook: Optional[str] = None
    youtube: Optional[str] = None
    tiktok: Optional[str] = None

class PeopleUpdate(PeopleCreate):
    id: int

class PeopleDeleteBody(BaseModel):
    id: int

# ==== People: 一覧（配列で返す） ===================================================
# GET /owner/api/people?u=&p=
@app.get("/owner/api/people")
def people_list(u: str = Query(...), p: str = Query(...)):
    """
    戻りは配列: [{id,name}, ...]
    editor.html は {items:...} を期待しない（配列そのまま）
    """
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = qall(cur, """
            SELECT id, name
            FROM people
            ORDER BY name COLLATE NOCASE, id
        """)
    return rows

# ==== People: 取得（明細） =========================================================
# GET /owner/api/people/get?u=&p=&id=
@app.get("/owner/api/people/get")
def people_get(u: str = Query(...), p: str = Query(...), id: int = Query(...)):
    """
    戻りキー（UIで使うもののみ）：id, name, birthday, joined_on, left_on,
      x, instagram, threads, facebook, youtube, tiktok
    - preview は UI の表示用で DB 非保存 → 返さない（必要なら "" を UI 内でセット）
    - note は未使用方針 → 返さない
    """
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, birthday, joined_on, left_on,
                   x, instagram, threads, facebook, youtube, tiktok
            FROM people
            WHERE id=?
        """, (id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, f"people not found: {id}")
        return dict(row)

# ==== People: 作成（戻りは明細） ===================================================
# POST /owner/api/people/create?u=&p=
@app.post("/owner/api/people/create")
def people_create(body: PeopleCreate, u: str = Query(...), p: str = Query(...)):
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "name is required")

    # INSERT 対象カラム（note は未使用のため除外）
    cols = ["name", "birthday", "joined_on", "left_on",
            "x", "instagram", "threads", "facebook", "youtube", "tiktok"]
    values = [name,
              body.birthday, body.joined_on, body.left_on,
              body.x, body.instagram, body.threads, body.facebook, body.youtube, body.tiktok]

    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        placeholders = ", ".join(["?"] * len(values))
        cur.execute(f"INSERT INTO people({', '.join(cols)}) VALUES ({placeholders})", values)
        conn.commit()
        new_id = cur.lastrowid

        # 作成後の明細を返す（UIがそのまま使えるように）
        cur.execute("""
            SELECT id, name, birthday, joined_on, left_on,
                   x, instagram, threads, facebook, youtube, tiktok
            FROM people
            WHERE id=?
        """, (new_id,))
        row = cur.fetchone()
        return dict(row)

# ==== People: 更新（戻りは {ok:true}） =============================================
# POST /owner/api/people/update?u=&p=
@app.post("/owner/api/people/update")
def people_update(body: PeopleUpdate, u: str = Query(...), p: str = Query(...)):
    if not body.id:
        raise HTTPException(400, "id is required")
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "name is required")

    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        # 存在確認
        cur.execute("SELECT COUNT(1) FROM people WHERE id=?", (body.id,))
        if cur.fetchone()[0] == 0:
            raise HTTPException(404, f"people not found: {body.id}")

        # 更新対象（note は未使用のため除外）
        cols = ["name", "birthday", "joined_on", "left_on",
                "x", "instagram", "threads", "facebook", "youtube", "tiktok"]
        vals = [ (body.name or "").strip(),
                 body.birthday, body.joined_on, body.left_on,
                 body.x, body.instagram, body.threads, body.facebook, body.youtube, body.tiktok ]

        set_clause = ", ".join([f"{c}=?" for c in cols])
        cur.execute(f"UPDATE people SET {set_clause} WHERE id=?", (*vals, body.id))
        conn.commit()
    return {"ok": True}

# ==== People: 削除（Body/Query 両対応） ===========================================
# POST /owner/api/people/delete?u=&p=  （Body: {id}） ← people.html など個別HTML準拠
# POST /owner/api/people/delete?u=&p=&id=123           ← editor.html の簡易操作互換
@app.post("/owner/api/people/delete")
def people_delete(u: str = Query(...),
                  p: str = Query(...),
                  id_q: Optional[int] = Query(default=None, alias="id"),
                  body: Optional[PeopleDeleteBody] = Body(default=None)):
    # id は Body 優先、なければクエリ（互換）
    target_id = body.id if (body and body.id) else id_q
    if not target_id:
        raise HTTPException(400, "id is required")

    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()

        # 参照チェック（lineup / performer から参照されていれば 409）
        in_use_by: List[str] = []
        try:
            cur.execute("SELECT EXISTS(SELECT 1 FROM lineup WHERE member_id=? LIMIT 1)", (target_id,))
            if cur.fetchone()[0] == 1:
                in_use_by.append("lineup")
        except Exception:
            pass
        try:
            cur.execute("SELECT EXISTS(SELECT 1 FROM performer WHERE member_id=? LIMIT 1)", (target_id,))
            if cur.fetchone()[0] == 1:
                in_use_by.append("performer")
        except Exception:
            pass

        if in_use_by:
            raise HTTPException(status_code=409, detail={"ok": False, "reason": "in_use", "in_use_by": in_use_by})

        # 実削除
        cur.execute("DELETE FROM people WHERE id=?", (target_id,))
        conn.commit()

    return {"ok": True}



# ==== Acts: モデル ================================================================

class ActCreate(BaseModel):
    name: str
    url: Optional[str] = None
    x: Optional[str] = None
    instagram: Optional[str] = None
    threads: Optional[str] = None
    facebook: Optional[str] = None
    youtube: Optional[str] = None
    tiktok: Optional[str] = None

class ActUpdate(ActCreate):
    id: int

class ActDeleteBody(BaseModel):
    id: int

# ==== Acts: 一覧（配列） ==========================================================
# GET /owner/api/acts?u=&p=
@app.get("/owner/api/acts")
def acts_list(u: str = Query(...), p: str = Query(...)):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = qall(cur, """
            SELECT id, name
            FROM acts
            ORDER BY name COLLATE NOCASE, id
        """)
    return rows

# ==== Acts: 取得（明細） ==========================================================
# GET /owner/api/acts/get?u=&p=&id=
@app.get("/owner/api/acts/get")
def acts_get(u: str = Query(...), p: str = Query(...), id: int = Query(...)):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, url, x, instagram, threads, facebook, youtube, tiktok
            FROM acts
            WHERE id=?
        """, (id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, f"acts not found: {id}")
        return dict(row)

# ==== Acts: 作成（重複名は409） ===================================================
# POST /owner/api/acts/create?u=&p=
@app.post("/owner/api/acts/create")
def acts_create(body: ActCreate, u: str = Query(...), p: str = Query(...)):
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "name is required")

    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        # UNIQUE(name) 対応：重複は409
        try:
            cur.execute("""
                INSERT INTO acts(name, url, x, instagram, threads, facebook, youtube, tiktok)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, body.url, body.x, body.instagram, body.threads,
                  body.facebook, body.youtube, body.tiktok))
            conn.commit()
        except sqlite3.IntegrityError as e:
            # name UNIQUE の衝突想定
            raise HTTPException(status_code=409, detail={"ok": False, "reason": "duplicate", "field": "name"}) from e

        new_id = cur.lastrowid
        cur.execute("""
            SELECT id, name, url, x, instagram, threads, facebook, youtube, tiktok
            FROM acts
            WHERE id=?
        """, (new_id,))
        row = cur.fetchone()
        return dict(row)

# ==== Acts: 更新（重複名は409） ===================================================
# POST /owner/api/acts/update?u=&p=
@app.post("/owner/api/acts/update")
def acts_update(body: ActUpdate, u: str = Query(...), p: str = Query(...)):
    if not body.id:
        raise HTTPException(400, "id is required")
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "name is required")

    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        # 存在確認
        cur.execute("SELECT COUNT(1) FROM acts WHERE id=?", (body.id,))
        if cur.fetchone()[0] == 0:
            raise HTTPException(404, f"acts not found: {body.id}")

        try:
            cur.execute("""
                UPDATE acts
                   SET name=?, url=?, x=?, instagram=?, threads=?, facebook=?, youtube=?, tiktok=?
                 WHERE id=?
            """, (name, body.url, body.x, body.instagram, body.threads,
                  body.facebook, body.youtube, body.tiktok, body.id))
            conn.commit()
        except sqlite3.IntegrityError as e:
            # name UNIQUE の衝突想定
            raise HTTPException(status_code=409, detail={"ok": False, "reason": "duplicate", "field": "name"}) from e

    return {"ok": True}

# ==== Acts: 削除（Body/Query 両対応・参照チェック） ================================
# POST /owner/api/acts/delete?u=&p=        （Body: {id}）  … 各HTML準拠
# POST /owner/api/acts/delete?u=&p=&id=123 （Query互換）   … editor.html 簡易操作対応
@app.post("/owner/api/acts/delete")
def acts_delete(u: str = Query(...),
                p: str = Query(...),
                id_q: Optional[int] = Query(default=None, alias="id"),
                body: Optional[ActDeleteBody] = Body(default=None)):
    target_id = body.id if (body and body.id) else id_q
    if not target_id:
        raise HTTPException(400, "id is required")

    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        # 参照チェック：bandsevent.act_id
        try:
            cur.execute("SELECT EXISTS(SELECT 1 FROM bandsevent WHERE act_id=? LIMIT 1)", (target_id,))
            if cur.fetchone()[0] == 1:
                raise HTTPException(status_code=409, detail={
                    "ok": False, "reason": "in_use", "in_use_by": ["bandsevent"]
                })
        except sqlite3.Error:
            # bandsevent テーブルが無いケースでも落ちないよう保護
            pass

        cur.execute("DELETE FROM acts WHERE id=?", (target_id,))
        conn.commit()

    return {"ok": True}




# ==== Venues ==============================================================

class VenueCreate(BaseModel):
    name: str
    url: Optional[str] = None
    note: Optional[str] = None  # UIで使わなければ無視してOK

class VenueUpdate(VenueCreate):
    id: int

class VenueDeleteBody(BaseModel):
    id: int

@app.get("/owner/api/venue")
def venues_list(u: str = Query(...), p: str = Query(...)):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = qall(cur, "SELECT id, name FROM venues ORDER BY name COLLATE NOCASE, id")
    return rows

@app.get("/owner/api/venue/get")
def venues_get(u: str = Query(...), p: str = Query(...), id: int = Query(...)):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id, name, url, note FROM venues WHERE id=?", (id,))
        row = cur.fetchone()
        if not row: raise HTTPException(404, f"venues not found: {id}")
        return dict(row)

@app.post("/owner/api/venue/create")
def venues_create(body: VenueCreate, u: str = Query(...), p: str = Query(...)):
    name = (body.name or "").strip()
    if not name: raise HTTPException(400, "name is required")
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("INSERT INTO venues(name, url, note) VALUES (?,?,?)", (name, body.url, body.note))
        conn.commit()
        new_id = cur.lastrowid
        cur.execute("SELECT id, name, url, note FROM venues WHERE id=?", (new_id,))
        return dict(cur.fetchone())

@app.post("/owner/api/venue/update")
def venues_update(body: VenueUpdate, u: str = Query(...), p: str = Query(...)):
    if not body.id: raise HTTPException(400, "id is required")
    name = (body.name or "").strip()
    if not name: raise HTTPException(400, "name is required")
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(1) FROM venues WHERE id=?", (body.id,))
        if cur.fetchone()[0] == 0: raise HTTPException(404, f"venues not found: {body.id}")
        cur.execute("UPDATE venues SET name=?, url=?, note=? WHERE id=?", (name, body.url, body.note, body.id))
        conn.commit()
    return {"ok": True}

@app.post("/owner/api/venue/delete")
def venues_delete(u: str = Query(...), p: str = Query(...),
                  id_q: Optional[int] = Query(default=None, alias="id"),
                  body: Optional[VenueDeleteBody] = Body(default=None)):
    target_id = body.id if (body and body.id) else id_q
    if not target_id: raise HTTPException(400, "id is required")
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT EXISTS(SELECT 1 FROM events WHERE venue_id=? LIMIT 1)", (target_id,))
        if cur.fetchone()[0] == 1:
            raise HTTPException(status_code=409, detail={"ok": False, "reason": "in_use", "in_use_by": ["events"]})
        cur.execute("DELETE FROM venues WHERE id=?", (target_id,))
        conn.commit()
    return {"ok": True}



# ==== Songs ===============================================================
class SongCreate(BaseModel):
    title: str

class SongUpdate(SongCreate):
    id: int

class SongDeleteBody(BaseModel):
    id: int

@app.get("/owner/api/songs")
def songs_list(u: str = Query(...), p: str = Query(...)):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = qall(cur, "SELECT id, title as name FROM songs ORDER BY title COLLATE NOCASE, id")
    return rows  # ← 配列（nameキーで返す）

@app.get("/owner/api/songs/get")
def songs_get(u: str = Query(...), p: str = Query(...), id: int = Query(...)):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id, title FROM songs WHERE id=?", (id,))
        row = cur.fetchone()
        if not row: raise HTTPException(404, f"songs not found: {id}")
        # 明細は UI 側で title を扱う想定があれば title のまま返す
        return {"id": row["id"], "title": row["title"]}

@app.post("/owner/api/songs/create")
def songs_create(body: SongCreate, u: str = Query(...), p: str = Query(...)):
    title = (body.title or "").strip()
    if not title: raise HTTPException(400, "title is required")
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("INSERT INTO songs(title) VALUES (?)", (title,))
        conn.commit()
        new_id = cur.lastrowid
        cur.execute("SELECT id, title FROM songs WHERE id=?", (new_id,))
        row = cur.fetchone()
        return {"id": row["id"], "title": row["title"]}

@app.post("/owner/api/songs/update")
def songs_update(body: SongUpdate, u: str = Query(...), p: str = Query(...)):
    if not body.id: raise HTTPException(400, "id is required")
    title = (body.title or "").strip()
    if not title: raise HTTPException(400, "title is required")
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(1) FROM songs WHERE id=?", (body.id,))
        if cur.fetchone()[0] == 0: raise HTTPException(404, f"songs not found: {body.id}")
        cur.execute("UPDATE songs SET title=? WHERE id=?", (title, body.id))
        conn.commit()
    return {"ok": True}

@app.post("/owner/api/songs/delete")
def songs_delete(u: str = Query(...), p: str = Query(...),
                 id_q: Optional[int] = Query(default=None, alias="id"),
                 body: Optional[SongDeleteBody] = Body(default=None)):
    target_id = body.id if (body and body.id) else id_q
    if not target_id: raise HTTPException(400, "id is required")
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT EXISTS(SELECT 1 FROM setlist WHERE song_id=? LIMIT 1)", (target_id,))
        if cur.fetchone()[0] == 1:
            raise HTTPException(status_code=409, detail={"ok": False, "reason": "in_use", "in_use_by": ["setlist"]})
        cur.execute("DELETE FROM songs WHERE id=?", (target_id,))
        conn.commit()
    return {"ok": True}



# ==== Roles ===============================================================
class RoleCreate(BaseModel):
    name: str  # UI側は name で送る

class RoleUpdate(RoleCreate):
    id: int

class RoleDeleteBody(BaseModel):
    id: int

@app.get("/owner/api/role")
def role_list(u: str = Query(...), p: str = Query(...)):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = qall(cur, "SELECT id, role as name FROM roles ORDER BY role COLLATE NOCASE, id")
    return rows

@app.get("/owner/api/role/get")
def role_get(u: str = Query(...), p: str = Query(...), id: int = Query(...)):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id, role FROM roles WHERE id=?", (id,))
        row = cur.fetchone()
        if not row: raise HTTPException(404, f"role not found: {id}")
        return {"id": row["id"], "name": row["role"]}

@app.post("/owner/api/role/create")
def role_create(body: RoleCreate, u: str = Query(...), p: str = Query(...)):
    name = (body.name or "").strip()
    if not name: raise HTTPException(400, "name is required")
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO roles(role) VALUES (?)", (name,))
            conn.commit()
        except sqlite3.IntegrityError as e:
            raise HTTPException(status_code=409, detail={"ok": False, "reason": "duplicate", "field": "name"}) from e
        new_id = cur.lastrowid
        return {"id": new_id, "name": name}

@app.post("/owner/api/role/update")
def role_update(body: RoleUpdate, u: str = Query(...), p: str = Query(...)):
    if not body.id: raise HTTPException(400, "id is required")
    name = (body.name or "").strip()
    if not name: raise HTTPException(400, "name is required")
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(1) FROM roles WHERE id=?", (body.id,))
        if cur.fetchone()[0] == 0: raise HTTPException(404, f"role not found: {body.id}")
        try:
            cur.execute("UPDATE roles SET role=? WHERE id=?", (name, body.id))
            conn.commit()
        except sqlite3.IntegrityError as e:
            raise HTTPException(status_code=409, detail={"ok": False, "reason": "duplicate", "field": "name"}) from e
    return {"ok": True}

@app.post("/owner/api/role/delete")
def role_delete(u: str = Query(...), p: str = Query(...),
                id_q: Optional[int] = Query(default=None, alias="id"),
                body: Optional[RoleDeleteBody] = Body(default=None)):
    target_id = body.id if (body and body.id) else id_q
    if not target_id: raise HTTPException(400, "id is required")
    # roles は lineup.role 文字列参照でID参照ではないため、参照チェックは不要（スキーマに合わせる）
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM roles WHERE id=?", (target_id,))
        conn.commit()
    return {"ok": True}



# ==== Era =================================================================

class EraCreate(BaseModel):
    name: str
    start_on: Optional[str] = None
    end_on: Optional[str] = None
    memo: Optional[str] = None

class EraUpdate(EraCreate):
    id: int

class EraDeleteBody(BaseModel):
    id: int

# 一覧（配列） GET /owner/api/era?u=&p=
@app.get("/owner/api/era")
def era_list(u: str = Query(...), p: str = Query(...)):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = qall(cur, "SELECT id, name FROM era ORDER BY name COLLATE NOCASE, id")
    return rows

# 取得 GET /owner/api/era/get?u=&p=&id=
@app.get("/owner/api/era/get")
def era_get(u: str = Query(...), p: str = Query(...), id: int = Query(...)):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id, name, start_on, end_on, memo FROM era WHERE id=?", (id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, f"era not found: {id}")
        return dict(row)

# 作成 POST /owner/api/era/create?u=&p=
@app.post("/owner/api/era/create")
def era_create(body: EraCreate, u: str = Query(...), p: str = Query(...)):
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "name is required")
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO era(name, start_on, end_on, memo) VALUES (?,?,?,?)",
            (name, body.start_on, body.end_on, body.memo)
        )
        conn.commit()
        new_id = cur.lastrowid
        cur.execute("SELECT id, name, start_on, end_on, memo FROM era WHERE id=?", (new_id,))
        return dict(cur.fetchone())

# 更新 POST /owner/api/era/update?u=&p=
@app.post("/owner/api/era/update")
def era_update(body: EraUpdate, u: str = Query(...), p: str = Query(...)):
    if not body.id:
        raise HTTPException(400, "id is required")
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "name is required")
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(1) FROM era WHERE id=?", (body.id,))
        if cur.fetchone()[0] == 0:
            raise HTTPException(404, f"era not found: {body.id}")
        cur.execute(
            "UPDATE era SET name=?, start_on=?, end_on=?, memo=? WHERE id=?",
            (name, body.start_on, body.end_on, body.memo, body.id)
        )
        conn.commit()
    return {"ok": True}

# 削除（Body/Query 両対応・参照チェック） POST /owner/api/era/delete?u=&p=[&id=]
@app.post("/owner/api/era/delete")
def era_delete(u: str = Query(...), p: str = Query(...),
               id_q: Optional[int] = Query(default=None, alias="id"),
               body: Optional[EraDeleteBody] = Body(default=None)):
    target_id = body.id if (body and body.id) else id_q
    if not target_id:
        raise HTTPException(400, "id is required")

    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        # events.era_id に参照があれば 409
        cur.execute("SELECT EXISTS(SELECT 1 FROM events WHERE era_id=? LIMIT 1)", (target_id,))
        if cur.fetchone()[0] == 1:
            raise HTTPException(status_code=409, detail={"ok": False, "reason": "in_use", "in_use_by": ["events"]})
        cur.execute("DELETE FROM era WHERE id=?", (target_id,))
        conn.commit()
    return {"ok": True}



# ==== Tour ================================================================

class TourCreate(BaseModel):
    name: str
    start_on: Optional[str] = None
    end_on: Optional[str] = None
    memo: Optional[str] = None

class TourUpdate(TourCreate):
    id: int

class TourDeleteBody(BaseModel):
    id: int

# 一覧（配列） GET /owner/api/tour?u=&p=
@app.get("/owner/api/tour")
def tour_list(u: str = Query(...), p: str = Query(...)):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = qall(cur, "SELECT id, name FROM tour ORDER BY name COLLATE NOCASE, id")
    return rows

# 取得 GET /owner/api/tour/get?u=&p=&id=
@app.get("/owner/api/tour/get")
def tour_get(u: str = Query(...), p: str = Query(...), id: int = Query(...)):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id, name, start_on, end_on, memo FROM tour WHERE id=?", (id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, f"tour not found: {id}")
        return dict(row)

# 作成 POST /owner/api/tour/create?u=&p=
@app.post("/owner/api/tour/create")
def tour_create(body: TourCreate, u: str = Query(...), p: str = Query(...)):
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "name is required")
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO tour(name, start_on, end_on, memo) VALUES (?,?,?,?)",
            (name, body.start_on, body.end_on, body.memo)
        )
        conn.commit()
        new_id = cur.lastrowid
        cur.execute("SELECT id, name, start_on, end_on, memo FROM tour WHERE id=?", (new_id,))
        return dict(cur.fetchone())

# 更新 POST /owner/api/tour/update?u=&p=
@app.post("/owner/api/tour/update")
def tour_update(body: TourUpdate, u: str = Query(...), p: str = Query(...)):
    if not body.id:
        raise HTTPException(400, "id is required")
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "name is required")
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(1) FROM tour WHERE id=?", (body.id,))
        if cur.fetchone()[0] == 0:
            raise HTTPException(404, f"tour not found: {body.id}")
        cur.execute(
            "UPDATE tour SET name=?, start_on=?, end_on=?, memo=? WHERE id=?",
            (name, body.start_on, body.end_on, body.memo, body.id)
        )
        conn.commit()
    return {"ok": True}

# 削除（Body/Query 両対応・参照チェック） POST /owner/api/tour/delete?u=&p=[&id=]
@app.post("/owner/api/tour/delete")
def tour_delete(u: str = Query(...), p: str = Query(...),
                id_q: Optional[int] = Query(default=None, alias="id"),
                body: Optional[TourDeleteBody] = Body(default=None)):
    target_id = body.id if (body and body.id) else id_q
    if not target_id:
        raise HTTPException(400, "id is required")

    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        # events.tour_id に参照があれば 409
        cur.execute("SELECT EXISTS(SELECT 1 FROM events WHERE tour_id=? LIMIT 1)", (target_id,))
        if cur.fetchone()[0] == 1:
            raise HTTPException(status_code=409, detail={"ok": False, "reason": "in_use", "in_use_by": ["events"]})
        cur.execute("DELETE FROM tour WHERE id=?", (target_id,))
        conn.commit()
    return {"ok": True}
