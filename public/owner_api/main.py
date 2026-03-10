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
    con = db_open(u,p)
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
    con = db_open(u,p)
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
    con = db_open(u,p)
    cur = con.cursor()

    rows = qall(cur, """
        SELECT event_id, seq, song_title, section, version
        FROM v_setlist
        WHERE event_id = ?
        ORDER BY seq
    """,(event_id,))

    return rows