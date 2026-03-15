

// ===== コンテキスト =====
const u = new URLSearchParams(location.search).get("u");
const p = new URLSearchParams(location.search).get("p");
if (!u || !p) location.href = "./index.html";

const API_BASE =
  (location.hostname === "127.0.0.1" || location.hostname === "localhost")
    ? "http://127.0.0.1:8787"
    : "";

// ===== 小物 =====
const $  = s => document.querySelector(s);
const $$ = s => Array.from(document.querySelectorAll(s));
const status = $("#status");
const listTbody = $("#list");
let cur = null, page=1, size=50, order="title.asc", q="";

const getJSON = async (path) => {
  const r = await fetch(`${API_BASE}${path}`);
  if (!r.ok) throw await r.json().catch(()=>({reason:r.statusText}));
  return r.json();
};
const postJSON = async (path, body) => {
  const r = await fetch(`${API_BASE}${path}`, {method:"POST", headers:{'Content-Type':'application/json'}, body: JSON.stringify(body||{})});
  if (!r.ok) {
    const data = await r.json().catch(()=>({reason:r.statusText}));
    const e = new Error(data.reason||"error"); e.status=r.status; e.data=data; throw e;
  }
  return r.json();
};
const setStatus = (msg, cls="") => {};

// ===== 一覧の描画 =====
async function reload() {
  const q = $("#q")?.value?.trim() || "";
  const data = await getJSON(`/owner/api/${MASTER}/list?u=${u}&p=${p}&page=${page}&size=${size}&q=${encodeURIComponent(q)}`);
  listTbody.innerHTML = "";
  for (const it of data.items) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${it.id}</td><td>${escapeHtml(it.title)}</td>`;
    tr.onclick = ()=> select(it.id);
    if (cur?.id === it.id) tr.classList.add("active");
    listTbody.appendChild(tr);
  }
}

function escapeHtml(s){return (s??"").replace(/[&<>"']/g,m=>({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[m]))}

// ===== 明細の取得/セット =====
async function select(id) {
  const data = await getJSON(`/owner/api/${MASTER}/get?u=${u}&p=${p}&id=${id}`);

  // create / update / delete
  // const res = await postJSON(`/owner/api/${MASTER}/create?u=${u}&p=${p}`, { title });
  // await postJSON(`/owner/api/${MASTER}/update?u=${u}&p=${p}`, { id: cur.id, title });
  // await postJSON(`/owner/api/${MASTER}/delete?u=${u}&p=${p}`, { id: cur.id });

  cur = data;
  $("#f-id").value = data.id;
  $("#f-title").value = data.title;
  $$("#list tr").forEach(tr=> tr.classList.toggle("active", Number(tr.firstChild.textContent)===id));
}

// ===== 新規/保存/削除 =====
function newItem(){
  cur = { id:"", title:"" };
  $("#f-id").value = "";
  $("#f-title").value = "";
  $("#f-title").focus();
}

async function save(){
  const title = $("#f-title").value.trim();
  if (!title) { setStatus("タイトルは必須です", "danger"); $("#f-title").focus(); return; }
  try {
    if (!cur?.id) {
      const res = await postJSON(`/owner/api/${MASTER}/create?u=${u}&p=${p}`, { title });
      cur = res;
    } else {
      await postJSON(`/owner/api/${MASTER}/update?u=${u}&p=${p}`, { id: cur.id, title });
    }
    setStatus("保存しました", "success");
    await reload();
    // イベント画面へ通知（曲セレクト更新）
    window.dispatchEvent(new CustomEvent('master-changed', { detail:{ kind:'songs' } }));
  } catch(e) {
    if (e.status === 412) {
      setStatus("他の人が先に変更しました。再読み込みしてやり直してください。", "danger");
    } else if (e.status === 400) {
      setStatus(`入力エラー: ${e.data?.reason||''}`, "danger");
    } else {
      setStatus(`保存に失敗: ${e.message}`, "danger");
    }
  }
}

async function del(){
  if (!cur?.id) return;
  if (!confirm(`ID ${cur.id} を削除します。よろしいですか？`)) return;
  try {
    await postJSON(`/owner/api/${MASTER}/delete?u=${u}&p=${p}`, { id: cur.id });
    setStatus("削除しました", "success");
    cur = null; newItem();
    await reload();
    window.dispatchEvent(new CustomEvent('master-changed', { detail:{ kind:'songs' } }));
  } catch(e) {
    if (e.status === 409) setStatus("この曲はセトリで使用中のため削除できません。", "danger");
    else setStatus(`削除に失敗: ${e.message}`, "danger");
  }
}

// ===== ハンドラ結線 =====
$("#btn-search").onclick = ()=>{ page=1; reload(); };
$("#btn-reload").onclick = ()=> reload();
$("#btn-new").onclick = newItem;
$("#btn-save").onclick = save;
$("#btn-delete").onclick = del;

// ===== 初期ロード =====
await reload();
newItem();