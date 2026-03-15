const $ = s => document.querySelector(s);
const $$ = s => Array.from(document.querySelectorAll(s));

let cur = null, page = 1, size = 50;

// 一覧描画
async function reload() {
  const q = $("#venues-q")?.value?.trim() || "";
  const u = new URLSearchParams(location.search).get("u");
  const p = new URLSearchParams(location.search).get("p");

  const data = await fetch(`/owner/api/venues/list?u=${u}&p=${p}&page=${page}&size=${size}&q=${encodeURIComponent(q)}`)
    .then(r => r.json());

  const tbody = $("#venues-list");
  tbody.innerHTML = "";

  for (const it of data.items || []) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${it.id}</td><td>${it.name}</td>`;
    tr.onclick = () => select(it.id);

    if(cur?.id === it.id) tr.classList.add("active");

    tbody.appendChild(tr);
  }
}

// 明細セット
async function select(id) {
  const u = new URLSearchParams(location.search).get("u");
  const p = new URLSearchParams(location.search).get("p");

  const data = await fetch(`/owner/api/venues/get?u=${u}&p=${p}&id=${id}`)
    .then(r => r.json());

  cur = data;

  $("#venues-f-id").value     = data.id ?? "";
  $("#venues-f-title").value  = data.name ?? "";
  $("#venues-f-url").value    = data.url ?? "";
  $("#venues-f-note").value   = data.note ?? "";

  $$("#venues-list tr").forEach(tr =>
    tr.classList.toggle("active", Number(tr.firstChild.textContent) === id)
  );
}

// 新規
function newItem() {
  cur = { id:"", name:"", url:"", note:"" };

  $("#venues-f-id").value    = "";
  $("#venues-f-title").value = "";
  $("#venues-f-url").value   = "";
  $("#venues-f-note").value  = "";

  $("#venues-f-title").focus();
}

// 保存
async function save() {
  const name = $("#venues-f-title").value.trim();
  const url  = $("#venues-f-url").value.trim() || null;
  const note = $("#venues-f-note").value.trim() || null;

  if(!name) return;

  const u = new URLSearchParams(location.search).get("u");
  const p = new URLSearchParams(location.search).get("p");

  if(!cur?.id){

    cur = await fetch(`/owner/api/venues/create?u=${u}&p=${p}`, {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({name,url,note})
    }).then(r => r.json());

  } else {

    await fetch(`/owner/api/venues/update?u=${u}&p=${p}`, {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({id:cur.id,name,url,note})
    });

  }

  await reload();
}

// 削除
async function del() {

  if(!cur?.id) return;

  if(!confirm(`ID ${cur.id} を削除します。よろしいですか？`)) return;

  const u = new URLSearchParams(location.search).get("u");
  const p = new URLSearchParams(location.search).get("p");

  await fetch(`/owner/api/venues/delete?u=${u}&p=${p}`, {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({id:cur.id})
  });

  cur = null;

  newItem();
  await reload();
}

// ハンドラ
document.getElementById("venues-btn-search").onclick = () => { page=1; reload(); };
document.getElementById("venues-btn-reload").onclick = () => reload();
document.getElementById("venues-btn-new").onclick    = () => newItem();
document.getElementById("venues-btn-save").onclick   = () => save();
document.getElementById("venues-btn-delete").onclick = () => del();

// 初期ロード
reload();
newItem();