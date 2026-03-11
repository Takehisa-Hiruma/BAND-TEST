# /owner/api/master_api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3

app = FastAPI(title="Master CRUD API")

# --------------------- 共通 ---------------------
def db_path(u: str, p: str):
    # tenant / project に応じた DB ファイルパス
    return f"../{u}/{p}/db.sqlite"

def qall(cur, sql, params=()):
    cur.execute(sql, params)
    return [dict(row) for row in cur.fetchall()]

# --------------------- Base Models ---------------------
class BaseCreate(BaseModel):
    name: str
    memo: str | None = None

class BaseUpdate(BaseModel):
    id: int
    name: str
    memo: str | None = None

# --------------------- 共通 CRUD ---------------------
def register_master_routes(entity: str):
    create_model = type(f"{entity.capitalize()}Create", (BaseCreate,), {})
    update_model = type(f"{entity.capitalize()}Update", (BaseUpdate,), {})

    @app.get(f"/owner/api/{entity}/list")
    def list_master(u: str, p: str, q: str = ""):
        db = db_path(u, p)
        with sqlite3.connect(db) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            rows = qall(cur, f"""
                SELECT id, name
                FROM {entity}
                WHERE (? = '' OR name LIKE '%' || ? || '%')
                ORDER BY name COLLATE NOCASE, id
            """, (q, q))
        return {"items": rows}

    @app.get(f"/owner/api/{entity}/get")
    def get_master(u: str, p: str, id: int):
        db = db_path(u, p)
        with sqlite3.connect(db) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(f"SELECT id, name, memo FROM {entity} WHERE id=?", (id,))
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
            cur.execute(
                f"INSERT INTO {entity}(name, memo) VALUES (?, ?)",
                (name, body.memo)
            )
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
            cur.execute(
                f"UPDATE {entity} SET name=?, memo=? WHERE id=?",
                (name, body.memo, body.id)
            )
            conn.commit()
        return {"ok": True}

    @app.post(f"/owner/api/{entity}/delete")
    def delete_master(u: str, p: str, id: int):
        db = db_path(u, p)
        with sqlite3.connect(db) as conn:
            cur = conn.cursor()
            # 参照チェックは events だけ簡易対応
            cur.execute(f"SELECT EXISTS(SELECT 1 FROM events WHERE {entity}_id=? LIMIT 1)", (id,))
            if cur.fetchone()[0] == 1:
                raise HTTPException(status_code=409, detail={"ok": False, "reason": "in_use", "in_use_by": ["events"]})
            cur.execute(f"DELETE FROM {entity} WHERE id=?", (id,))
            conn.commit()
        return {"ok": True}

# --------------------- マスター登録 ---------------------
for e in ["people","acts","venue","roles","era","tour","songs"]:
    register_master_routes(e)