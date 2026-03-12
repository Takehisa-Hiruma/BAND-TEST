from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import sqlite3, subprocess, os

def db_open(u, p):
    base = Path(__file__).resolve().parent.parent.parent
    db = base / "db" / u / f"{p}.db"
    if not db.exists():
        raise RuntimeError(f"DB not found: {db}")
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    return con



# ---- Master CRUD: 共通モデル ----

class MasterCreate(BaseModel):
    name: str
    memo: str | None = None

class MasterUpdate(BaseModel):
    id: int
    name: str
    memo: str | None = None


ROOT = Path(__file__).resolve().parents[2]  # <repo-root> を想定
DBROOT = ROOT / "db"
EXPORTER = ROOT / "cloud_export_json.py"

app = FastAPI(title="Owner API (MVP)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/owner/api/projects")
def list_projects(u: str = Query(..., min_length=1)):
    """
    username の DB ディレクトリを走査し、<project>.db を列挙する。
    display はひとまず project をそのまま返す（後で表示名を別管理にしてもOK）
    """
    u2 = u.strip().lower()
    base = DBROOT / u2
    if not base.exists():
        return []  # 初期状態は空
    projects = []
    for p in base.glob("*.db"):
        prj = p.stem.lower()
        projects.append({"project": prj, "display": prj})
    return projects

def db_path(u: str, p: str) -> Path:
    u2 = u.lower()
    p2 = p.lower()
    path = DBROOT / u2 / f"{p2}.db"
    if not path.exists():
        raise HTTPException(404, f"DB not found: {path}")
    return path

def qall(cur, sql, args=()):
    cur.execute(sql, args)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]

class EventUpdate(BaseModel):
    date: str | None = None
    title: str | None = None
    sub_title: str | None = None
    venue_id: int | None = None

@app.get("/owner/api/events")
def get_events(u: str = Query(...), p: str = Query(...)):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        rows = qall(cur, """
            SELECT * FROM v_events
            ORDER BY date DESC, id DESC
        """)
    return JSONResponse(rows)

@app.put("/owner/api/events/{eid}")
def put_event(eid: int, body: EventUpdate, u: str = Query(...), p: str = Query(...)):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        # 存在確認（最低限）
        cur.execute("SELECT COUNT(1) FROM events WHERE id=?", (eid,))
        if cur.fetchone()[0] == 0:
            raise HTTPException(404, f"event not found: {eid}")
        cur.execute("""
            UPDATE events
            SET date = ?, title = ?, sub_title = ?, venue_id = ?
            WHERE id = ?
        """, (body.date, body.title, body.sub_title, body.venue_id, eid))
        conn.commit()
    return {"ok": True}

@app.post("/owner/api/build")
def post_build(u: str = Query(...), p: str = Query(...)):
    if not EXPORTER.exists():
        raise HTTPException(500, f"exporter not found: {EXPORTER}")
    # 同期実行（MVP）。将来は非同期キュー化
    proc = subprocess.run(
        ["python", str(EXPORTER), u, p],
        cwd=str(ROOT),
        capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise HTTPException(500, f"build failed: {proc.stderr}")
    return {"ok": True, "log_tail": proc.stdout[-500:]}

@app.get("/owner/api/lineup/{event_id}")
def get_lineup(event_id:int, u:str, p:str):
    with db_open(u,p) as con:
        cur = con.cursor()

        rows = qall(cur, """
            SELECT event_id, person, role, position
            FROM v_event_members
            WHERE event_id = ?
            AND seq IS NULL
        """,(event_id,))

    return rows


@app.get("/owner/api/bandsevent/{event_id}")
def get_bandsevent(event_id:int, u:str, p:str):
    with db_open(u,p) as con:
        cur = con.cursor()

        rows = qall(cur, """
            SELECT event_id, seq, act_name
            FROM v_bandsevent
            WHERE event_id = ?
            ORDER BY seq
        """,(event_id,))

    return rows


@app.get("/owner/api/setlist/{event_id}")
def get_setlist(event_id:int, u:str, p:str):
    with db_open(u,p) as con:
        cur = con.cursor()

        rows = qall(cur, """
            SELECT event_id, seq, song_title, section, version
            FROM v_setlist
            WHERE event_id = ?
            ORDER BY seq
        """,(event_id,))

    return rows


# ---------- Songs API ----------


class SongCreate(BaseModel):
    title: str

class SongUpdate(BaseModel):
    id: int
    title: str
    # if_unmodified_since: str | None = None  # 使わないなら無視してOK

@app.get("/owner/api/songs/list")
def songs_list(u: str, p: str, q: str = ""):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if q:
            rows = qall(cur, """
                SELECT id, title
                FROM songs
                WHERE title LIKE '%' || ? || '%'
                ORDER BY title COLLATE NOCASE, id
            """, (q,))
        else:
            rows = qall(cur, """
                SELECT id, title
                FROM songs
                ORDER BY title COLLATE NOCASE, id
            """)
    return {"items": rows}

@app.get("/owner/api/songs/get")
def songs_get(u: str, p: str, id: int):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id, title FROM songs WHERE id=?", (id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, f"song not found: {id}")
        # 最終更新メタが無い場合は空で返す（楽観ロックは後で拡張）
        return {"id": row["id"], "title": row["title"], "updated_at": None, "updated_by": None}

@app.post("/owner/api/songs/create")
def songs_create(body: SongCreate, u: str, p: str):
    title = (body.title or "").strip()
    if not title:
        raise HTTPException(400, "title is required")
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO songs(title) VALUES (?)", (title,))
        conn.commit()
        new_id = cur.lastrowid
    return {"id": new_id, "title": title, "updated_at": None}

@app.post("/owner/api/songs/update")
def songs_update(body: SongUpdate, u: str, p: str):
    title = (body.title or "").strip()
    if not title:
        raise HTTPException(400, "title is required")
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(1) FROM songs WHERE id=?", (body.id,))
        if cur.fetchone()[0] == 0:
            raise HTTPException(404, f"song not found: {body.id}")
        cur.execute("UPDATE songs SET title=? WHERE id=?", (title, body.id))
        conn.commit()
    return {"ok": True, "updated_at": None}

@app.post("/owner/api/songs/delete")
def songs_delete(u: str, p: str, id: int):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        # 使用中チェック（setlist に参照があれば 409）
        cur.execute("SELECT EXISTS(SELECT 1 FROM setlist WHERE song_id=?)", (id,))
        in_use = cur.fetchone()[0] == 1
        if in_use:
            # UI側で「セトリで使用中のため削除できません」と出す想定
            raise HTTPException(status_code=409, detail={"ok": False, "reason": "in_use", "in_use_by": ["setlist"]})
        cur.execute("DELETE FROM songs WHERE id=?", (id,))
        conn.commit()
    return {"ok": True}




# ---------- Role API (DB: roles(id, role)) ----------
class RoleCreate(BaseModel):
    name: str

class RoleUpdate(BaseModel):
    id: int
    name: str

@app.get("/owner/api/role/list")
def role_list(u: str, p: str, q: str = ""):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if q:
            rows = qall(cur, """
                SELECT id, role AS name
                FROM roles
                WHERE role LIKE '%' || ? || '%'
                ORDER BY role COLLATE NOCASE, id
            """, (q,))
        else:
            rows = qall(cur, """
                SELECT id, role AS name
                FROM roles
                ORDER BY role COLLATE NOCASE, id
            """)
    return {"items": rows}

@app.get("/owner/api/role/get")
def role_get(u: str, p: str, id: int):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id, role AS name FROM roles WHERE id=?", (id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, f"role not found: {id}")
        return {"id": row["id"], "name": row["name"]}

@app.post("/owner/api/role/create")
def role_create(body: RoleCreate, u: str, p: str):
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "name is required")
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO roles(role) VALUES (?)", (name,))
        conn.commit()
        new_id = cur.lastrowid
    return {"id": new_id, "name": name}

@app.post("/owner/api/role/update")
def role_update(body: RoleUpdate, u: str, p: str):
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "name is required")
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(1) FROM roles WHERE id=?", (body.id,))
        if cur.fetchone()[0] == 0:
            raise HTTPException(404, f"role not found: {body.id}")
        cur.execute("UPDATE roles SET role=? WHERE id=?", (name, body.id))
        conn.commit()
    return {"ok": True}

@app.post("/owner/api/role/delete")
def role_delete(u: str, p: str, id: int):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        # 削除対象の名称を取得（lineup/performerは TEXT 参照）
        cur.execute("SELECT role FROM roles WHERE id=?", (id,))
        r = cur.fetchone()
        if not r:
            raise HTTPException(404, f"role not found: {id}")
        role_name = r["role"]

        # 参照チェック（lineup.role / performer.role）
        cur.execute("SELECT EXISTS(SELECT 1 FROM lineup    WHERE role=? LIMIT 1)", (role_name,))
        if cur.fetchone()[0] == 1:
            raise HTTPException(status_code=409, detail={"ok": False, "reason": "in_use", "in_use_by": ["lineup"]})
        cur.execute("SELECT EXISTS(SELECT 1 FROM performer WHERE role=? LIMIT 1)", (role_name,))
        if cur.fetchone()[0] == 1:
            raise HTTPException(status_code=409, detail={"ok": False, "reason": "in_use", "in_use_by": ["performer"]})

        cur.execute("DELETE FROM roles WHERE id=?", (id,))
        conn.commit()
    return {"ok": True}



# ---------- Tour API ----------
class TourCreate(BaseModel):  name: str
class TourUpdate(BaseModel):  id: int; name: str

@app.get("/owner/api/tour/list")
def tour_list(u: str, p: str, q: str = ""):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row; cur = conn.cursor()
        rows = qall(cur, """
            SELECT id, name FROM tour
            WHERE (? = '' OR name LIKE '%' || ? || '%')
            ORDER BY name COLLATE NOCASE, id
        """, (q, q))
    return {"items": rows}

@app.get("/owner/api/tour/get")
def tour_get(u: str, p: str, id: int):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row; cur = conn.cursor()
        cur.execute("SELECT id, name FROM tour WHERE id=?", (id,))
        r = cur.fetchone()
        if not r: raise HTTPException(404, f"tour not found: {id}")
        return {"id": r["id"], "name": r["name"]}

@app.post("/owner/api/tour/create")
def tour_create(body: TourCreate, u: str, p: str):
    name = (body.name or "").strip()
    if not name: raise HTTPException(400, "name is required")
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor(); cur.execute("INSERT INTO tour(name) VALUES (?)", (name,))
        conn.commit(); return {"id": cur.lastrowid, "name": name}

@app.post("/owner/api/tour/update")
def tour_update(body: TourUpdate, u: str, p: str):
    name = (body.name or "").strip()
    if not name: raise HTTPException(400, "name is required")
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(1) FROM tour WHERE id=?", (body.id,))
        if cur.fetchone()[0] == 0: raise HTTPException(404, f"tour not found: {body.id}")
        cur.execute("UPDATE tour SET name=? WHERE id=?", (name, body.id))
        conn.commit(); return {"ok": True}

@app.post("/owner/api/tour/delete")
def tour_delete(u: str, p: str, id: int):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT EXISTS(SELECT 1 FROM events WHERE tour_id=? LIMIT 1)", (id,))
        if cur.fetchone()[0] == 1:
            raise HTTPException(409, {"ok": False, "reason": "in_use", "in_use_by": ["events"]})
        cur.execute("DELETE FROM tour WHERE id=?", (id,))
        conn.commit(); return {"ok": True}
    


    # ---------- Era API ----------
class EraCreate(BaseModel):
    name: str
    start_on: str | None = None
    end_on: str | None = None
    memo: str | None = None

class EraUpdate(BaseModel):
    id: int
    name: str
    start_on: str | None = None
    end_on: str | None = None
    memo: str | None = None

@app.get("/owner/api/era/list")
def era_list(u: str, p: str, q: str = ""):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = qall(cur, """
            SELECT id, name
            FROM era
            WHERE (? = '' OR name LIKE '%' || ? || '%')
            ORDER BY name COLLATE NOCASE, id
        """, (q, q))
    return {"items": rows}

@app.get("/owner/api/era/get")
def era_get(u: str, p: str, id: int):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id, name, start_on, end_on, memo FROM era WHERE id=?", (id,))
        r = cur.fetchone()
        if not r:
            raise HTTPException(404, f"era not found: {id}")
        return dict(r)

@app.post("/owner/api/era/create")
def era_create(body: EraCreate, u: str, p: str):
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "name is required")
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO era(name, start_on, end_on, memo) VALUES (?, ?, ?, ?)",
            (name, body.start_on, body.end_on, body.memo),
        )
        conn.commit()
        return {"id": cur.lastrowid, "name": name, "start_on": body.start_on, "end_on": body.end_on, "memo": body.memo}

@app.post("/owner/api/era/update")
def era_update(body: EraUpdate, u: str, p: str):
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
            (name, body.start_on, body.end_on, body.memo, body.id),
        )
        conn.commit()
        return {"ok": True}

@app.post("/owner/api/era/delete")
def era_delete(u: str, p: str, id: int):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT EXISTS(SELECT 1 FROM events WHERE era_id=? LIMIT 1)", (id,))
        if cur.fetchone()[0] == 1:
            raise HTTPException(409, {"ok": False, "reason": "in_use", "in_use_by": ["events"]})
        cur.execute("DELETE FROM era WHERE id=?", (id,))
        conn.commit()
        return {"ok": True}



# ---------- Tour API ----------
class TourCreate(BaseModel):
    name: str
    start_on: str | None = None
    end_on: str | None = None
    memo: str | None = None

class TourUpdate(BaseModel):
    id: int
    name: str
    start_on: str | None = None
    end_on: str | None = None
    memo: str | None = None

@app.get("/owner/api/tour/list")
def tour_list(u: str, p: str, q: str = ""):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = qall(cur, """
            SELECT id, name
            FROM tour
            WHERE (? = '' OR name LIKE '%' || ? || '%')
            ORDER BY name COLLATE NOCASE, id
        """, (q, q))
    return {"items": rows}

@app.get("/owner/api/tour/get")
def tour_get(u: str, p: str, id: int):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id, name, start_on, end_on, memo FROM tour WHERE id=?", (id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, f"tour not found: {id}")
        return dict(row)

@app.post("/owner/api/tour/create")
def tour_create(body: TourCreate, u: str, p: str):
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "name is required")
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO tour(name, start_on, end_on, memo) VALUES (?, ?, ?, ?)",
            (name, body.start_on, body.end_on, body.memo),
        )
        conn.commit()
        new_id = cur.lastrowid
    return {"id": new_id, "name": name, "start_on": body.start_on, "end_on": body.end_on, "memo": body.memo}

@app.post("/owner/api/tour/update")
def tour_update(body: TourUpdate, u: str, p: str):
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
            (name, body.start_on, body.end_on, body.memo, body.id),
        )
        conn.commit()
    return {"ok": True}

@app.post("/owner/api/tour/delete")
def tour_delete(u: str, p: str, id: int):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        # 参照チェック（events.tour_id に使われていたら409）
        cur.execute("SELECT EXISTS(SELECT 1 FROM events WHERE tour_id=? LIMIT 1)", (id,))
        if cur.fetchone()[0] == 1:
            raise HTTPException(status_code=409, detail={"ok": False, "reason": "in_use", "in_use_by": ["events"]})
        cur.execute("DELETE FROM tour WHERE id=?", (id,))
        conn.commit()
    return {"ok": True}




# # app = FastAPI()

# def db_path(u: str, p: str):
#     # ここに DB パス決定ロジック
#     return f"db/{u}_{p}.sqlite"

# def qall(cur, sql, params=()):
#     cur.execute(sql, params)
#     return [dict(row) for row in cur.fetchall()]

# ---------- People API ----------
class PeopleCreate(BaseModel):
    name: str
    birthday: str | None = None
    joined_on: str | None = None
    left_on: str | None = None
    note: str | None = None
    x: str | None = None
    instagram: str | None = None
    threads: str | None = None
    facebook: str | None = None
    youtube: str | None = None
    tiktok: str | None = None

class PeopleUpdate(PeopleCreate):
    id: int

@app.get("/owner/api/people/list")
def people_list(u: str, p: str, q: str = ""):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = qall(cur, """
            SELECT id, name FROM people
            WHERE (? = '' OR name LIKE '%' || ? || '%')
            ORDER BY name COLLATE NOCASE, id
        """, (q, q))
    return {"items": rows}

@app.get("/owner/api/people/get")
def people_get(u: str, p: str, id: int):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM people WHERE id=?", (id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, f"people not found: {id}")
        return dict(row)

@app.post("/owner/api/people/create")
def people_create(body: PeopleCreate, u: str, p: str):
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "name is required")
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO people(name,birthday,joined_on,left_on,note,x,instagram,threads,facebook,youtube,tiktok)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (name, body.birthday, body.joined_on, body.left_on, body.note,
              body.x, body.instagram, body.threads, body.facebook, body.youtube, body.tiktok))
        conn.commit()
        new_id = cur.lastrowid
    return {"id": new_id, "name": name}

@app.post("/owner/api/people/update")
def people_update(body: PeopleUpdate, u: str, p: str):
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "name is required")
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(1) FROM people WHERE id=?", (body.id,))
        if cur.fetchone()[0] == 0:
            raise HTTPException(404, f"people not found: {body.id}")
        cur.execute("""
            UPDATE people
            SET name=?, birthday=?, joined_on=?, left_on=?, note=?,
                x=?, instagram=?, threads=?, facebook=?, youtube=?, tiktok=?
            WHERE id=?
        """, (name, body.birthday, body.joined_on, body.left_on, body.note,
              body.x, body.instagram, body.threads, body.facebook, body.youtube, body.tiktok, body.id))
        conn.commit()
    return {"ok": True}

@app.post("/owner/api/people/delete")
def people_delete(u: str, p: str, id: int):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        # lineup で使われていたら 409
        cur.execute("SELECT EXISTS(SELECT 1 FROM lineup WHERE member_id=? LIMIT 1)", (id,))
        if cur.fetchone()[0] == 1:
            raise HTTPException(status_code=409, detail={"ok": False, "reason": "in_use", "in_use_by": ["lineup"]})
        cur.execute("DELETE FROM people WHERE id=?", (id,))
        conn.commit()
    return {"ok": True}




# ---------- Acts API ----------
class ActCreate(BaseModel):
    name: str
    url: str | None = None
    x: str | None = None
    instagram: str | None = None
    threads: str | None = None
    facebook: str | None = None
    youtube: str | None = None
    tiktok: str | None = None

class ActUpdate(ActCreate):
    id: int

@app.get("/owner/api/acts/list")
def acts_list(u: str, p: str, q: str = ""):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = qall(cur, """
            SELECT id, name FROM acts
            WHERE (? = '' OR name LIKE '%' || ? || '%')
            ORDER BY name COLLATE NOCASE, id
        """, (q, q))
    return {"items": rows}

@app.get("/owner/api/acts/get")
def acts_get(u: str, p: str, id: int):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM acts WHERE id=?", (id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, f"acts not found: {id}")
        return dict(row)

@app.post("/owner/api/acts/create")
def acts_create(body: ActCreate, u: str, p: str):
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "name is required")
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO acts(name,url,x,instagram,threads,facebook,youtube,tiktok)
            VALUES (?,?,?,?,?,?,?,?)
        """, (name, body.url, body.x, body.instagram, body.threads, body.facebook, body.youtube, body.tiktok))
        conn.commit()
        new_id = cur.lastrowid
    return {"id": new_id, "name": name}

@app.post("/owner/api/acts/update")
def acts_update(body: ActUpdate, u: str, p: str):
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "name is required")
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(1) FROM acts WHERE id=?", (body.id,))
        if cur.fetchone()[0] == 0:
            raise HTTPException(404, f"acts not found: {body.id}")
        cur.execute("""
            UPDATE acts
            SET name=?, url=?, x=?, instagram=?, threads=?, facebook=?, youtube=?, tiktok=?
            WHERE id=?
        """, (name, body.url, body.x, body.instagram, body.threads, body.facebook, body.youtube, body.tiktok, body.id))
        conn.commit()
    return {"ok": True}

@app.post("/owner/api/acts/delete")
def acts_delete(u: str, p: str, id: int):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        # bandsevent で使われていたら 409
        cur.execute("SELECT EXISTS(SELECT 1 FROM bandsevent WHERE act_id=? LIMIT 1)", (id,))
        if cur.fetchone()[0] == 1:
            raise HTTPException(status_code=409, detail={"ok": False, "reason": "in_use", "in_use_by": ["bandsevent"]})
        cur.execute("DELETE FROM acts WHERE id=?", (id,))
        conn.commit()
    return {"ok": True}




# ---------- Venues API ----------
class VenueCreate(BaseModel):
    name: str
    url: str | None = None
    note: str | None = None

class VenueUpdate(VenueCreate):
    id: int

@app.get("/owner/api/venues/list")
def venues_list(u: str, p: str, q: str = ""):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = qall(cur, """
            SELECT id, name FROM venues
            WHERE (? = '' OR name LIKE '%' || ? || '%')
            ORDER BY name COLLATE NOCASE, id
        """, (q, q))
    return {"items": rows}

@app.get("/owner/api/venues/get")
def venues_get(u: str, p: str, id: int):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM venues WHERE id=?", (id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, f"venues not found: {id}")
        return dict(row)

@app.post("/owner/api/venues/create")
def venues_create(body: VenueCreate, u: str, p: str):
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "name is required")
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO venues(name,url,note) VALUES (?,?,?)", (name, body.url, body.note))
        conn.commit()
        new_id = cur.lastrowid
    return {"id": new_id, "name": name}

@app.post("/owner/api/venues/update")
def venues_update(body: VenueUpdate, u: str, p: str):
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "name is required")
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(1) FROM venues WHERE id=?", (body.id,))
        if cur.fetchone()[0] == 0:
            raise HTTPException(404, f"venues not found: {body.id}")
        cur.execute("UPDATE venues SET name=?, url=?, note=? WHERE id=?", (name, body.url, body.note, body.id))
        conn.commit()
    return {"ok": True}

@app.post("/owner/api/venues/delete")
def venues_delete(u: str, p: str, id: int):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        # events.venue_id で使われていたら 409
        cur.execute("SELECT EXISTS(SELECT 1 FROM events WHERE venue_id=? LIMIT 1)", (id,))
        if cur.fetchone()[0] == 1:
            raise HTTPException(status_code=409, detail={"ok": False, "reason": "in_use", "in_use_by": ["events"]})
        cur.execute("DELETE FROM venues WHERE id=?", (id,))
        conn.commit()
    return {"ok": True}