from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import sqlite3, subprocess

# ---------- Paths & DB ----------
ROOT = Path(__file__).resolve().parents[2]  # <repo-root> 想定
DBROOT = ROOT / "db"
EXPORTER = ROOT / "cloud_export_json.py"

def db_path(u: str, p: str) -> Path:
    path = DBROOT / u.lower() / f"{p.lower()}.db"
    if not path.exists():
        raise HTTPException(404, f"DB not found: {path}")
    return path

def db_open(u, p):
    con = sqlite3.connect(db_path(u,p))
    con.row_factory = sqlite3.Row  # ← これ必須
    return con

def qall(cur, sql, args=()):
    cur.execute(sql, args)
    # row が tuple の場合でも dict に変換
    if isinstance(cur.description, list) and cur.description:
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    return [dict(row) for row in cur.fetchall()]

# ---------- FastAPI ----------
app = FastAPI(title="Owner API (MVP)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Projects ----------
@app.get("/owner/api/projects")
def list_projects(u: str = Query(..., min_length=1)):
    u2 = u.strip().lower()
    base = DBROOT / u2
    if not base.exists():
        return []
    return [{"project": p.stem.lower(), "display": p.stem.lower()} for p in base.glob("*.db")]

# ---------- Events ----------
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
        rows = qall(cur, "SELECT * FROM v_events ORDER BY date DESC, id DESC")
    return JSONResponse(rows)

@app.put("/owner/api/events/{eid}")
def put_event(eid: int, body: EventUpdate, u: str = Query(...), p: str = Query(...)):
    db = db_path(u, p)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(1) FROM events WHERE id=?", (eid,))
        if cur.fetchone()[0] == 0:
            raise HTTPException(404, f"event not found: {eid}")
        cur.execute("""
            UPDATE events
            SET date=?, title=?, sub_title=?, venue_id=?
            WHERE id=?
        """, (body.date, body.title, body.sub_title, body.venue_id, eid))
        conn.commit()
    return {"ok": True}

@app.post("/owner/api/build")
def post_build(u: str = Query(...), p: str = Query(...)):
    if not EXPORTER.exists():
        raise HTTPException(500, f"exporter not found: {EXPORTER}")
    proc = subprocess.run(["python", str(EXPORTER), u, p],
                          cwd=str(ROOT), capture_output=True, text=True)
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
            WHERE event_id=? AND seq IS NULL
        """, (event_id,))
    return rows

@app.get("/owner/api/bandsevent/{event_id}")
def get_bandsevent(event_id:int, u:str, p:str):
    with db_open(u,p) as con:
        cur = con.cursor()
        rows = qall(cur, """
            SELECT event_id, seq, act_name
            FROM v_bandsevent
            WHERE event_id=?
            ORDER BY seq
        """, (event_id,))
    return rows

@app.get("/owner/api/setlist/{event_id}")
def get_setlist(event_id:int, u:str, p:str):
    with db_open(u,p) as con:
        cur = con.cursor()
        rows = qall(cur, """
            SELECT event_id, seq, song_title, section, version
            FROM v_setlist
            WHERE event_id=?
            ORDER BY seq
        """, (event_id,))
    return rows

# ---------- Master CRUD ----------
class BaseCreate(BaseModel):
    name: str
    memo: str | None = None

class BaseUpdate(BaseModel):
    id: int
    name: str
    memo: str | None = None

def register_master_routes(entity: str, key_name: str = "name"):
    create_model = type(f"{entity.capitalize()}Create", (BaseCreate,), {})
    update_model = type(f"{entity.capitalize()}Update", (BaseUpdate,), {})

    @app.get(f"/owner/api/{entity}/list")
    def list_master(u: str, p: str, q: str = ""):
        db = db_path(u, p)
        with sqlite3.connect(db) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            rows = qall(cur, f"""
                SELECT id, {key_name} AS name
                FROM {entity}
                WHERE (?='' OR {key_name} LIKE '%'||?||'%')
                ORDER BY {key_name} COLLATE NOCASE, id
            """, (q, q))
        return {"items": rows}

    @app.get(f"/owner/api/{entity}/get")
    def get_master(u: str, p: str, id: int):
        db = db_path(u, p)
        with sqlite3.connect(db) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(f"SELECT id, {key_name} AS name, memo FROM {entity} WHERE id=?", (id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, f"{entity} not found: {id}")
            return dict(row)

    @app.post(f"/owner/api/{entity}/create")
    def create_master(body: create_model, u: str, p: str):
        name = (body.name or "").strip()
        if not name:
            raise HTTPException(400, "name is required")
        db = db_path(u, p)
        with sqlite3.connect(db) as conn:
            cur = conn.cursor()
            cur.execute(f"INSERT INTO {entity}({key_name}, memo) VALUES (?, ?)", (name, body.memo))
            conn.commit()
            new_id = cur.lastrowid
        return {"id": new_id, "name": name, "memo": body.memo}

    @app.post(f"/owner/api/{entity}/update")
    def update_master(body: update_model, u: str, p: str):
        name = (body.name or "").strip()
        if not name:
            raise HTTPException(400, "name is required")
        db = db_path(u, p)
        with sqlite3.connect(db) as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(1) FROM {entity} WHERE id=?", (body.id,))
            if cur.fetchone()[0] == 0:
                raise HTTPException(404, f"{entity} not found: {body.id}")
            cur.execute(f"UPDATE {entity} SET {key_name}=?, memo=? WHERE id=?", (name, body.memo, body.id))
            conn.commit()
        return {"ok": True}

    @app.post(f"/owner/api/{entity}/delete")
    def delete_master(u: str, p: str, id: int):
        db = db_path(u, p)
        with sqlite3.connect(db) as conn:
            cur = conn.cursor()
            # 使用中チェックの簡易対応（必要なら追加可能）
            cur.execute(f"DELETE FROM {entity} WHERE id=?", (id,))
            conn.commit()
        return {"ok": True}

# ---------- Register all masters ----------
# key_name は DB 内カラム名。例：roles -> role
master_entities = {
    "people": "name",
    "acts": "name",
    "venues": "name",
    "roles": "role",
    "era": "name",
    "tour": "name",
    "songs": "title",
}

for ent, key in master_entities.items():
    register_master_routes(ent, key)