const $ = s => document.querySelector(s);
const $$ = s => Array.from(document.querySelectorAll(s));

let cur = null, page = 1, size = 50;

function escapeHtml(s){
  return (s??"").replace(/[&<>"']/g,m=>(
    {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]
  ));
}

// 一覧描画
async function reload() {

  const q = $("#songs-q")?.value?.trim() || "";

  const u = new URLSearchParams(location.search).get("u");
  const p = new URLSearchParams(location.search).get("p");

  const data = await fetch(
    `/owner/api/songs/list?u=${u}&p=${p}&page=${page}&size=${size}&q=${encodeURIComponent(q)}`
  ).then(r => r.json());

  const tbody = $("#songs-list");
  tbody.innerHTML = "";

  for (const it of data.items || []) {

    const tr = document.createElement("tr");

    tr.innerHTML = `<td>${it.id}</td><td>${escapeHtml(it.title)}</td>`;

    tr.onclick = () => select(it.id);

    if(cur?.id === it.id) tr.classList.add("active");

    tbody.appendChild(tr);
  }
}

// 明細
async function select(id) {

  const u = new URLSearchParams(location.search).get("u");
  const p = new URLSearchParams(location.search).get("p");

  const data = await fetch(
    `/owner/api/songs/get?u=${u}&p=${p}&id=${id}`
  ).then(r => r.json());

  cur = data;

  $("#songs-f-id").value = data.id;
  $("#songs-f-title").value = data.title;

  $$("#songs-list tr").forEach(tr =>
    tr.classList.toggle("active", Number(tr.firstChild.textContent) === id)
  );
}

// 新規
function newItem(){

  cur = { id:"", title:"" };

  $("#songs-f-id").value = "";
  $("#songs-f-title").value = "";

  $("#songs-f-title").focus();
}

// 保存
async function save(){

  const title = $("#songs-f-title").value.trim();

  if (!title){
    alert("タイトルは必須です");
    $("#songs-f-title").focus();
    return;
  }

  const u = new URLSearchParams(location.search).get("u");
  const p = new URLSearchParams(location.search).get("p");

  if(!cur?.id){

    cur = await fetch(`/owner/api/songs/create?u=${u}&p=${p}`,{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({title})
    }).then(r=>r.json());

  }else{

    await fetch(`/owner/api/songs/update?u=${u}&p=${p}`,{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({id:cur.id,title})
    });

  }

  await reload();

  window.dispatchEvent(
    new CustomEvent('master-changed',{detail:{kind:'songs'}})
  );
}

// 削除
async function del(){

  if(!cur?.id) return;

  if(!confirm(`ID ${cur.id} を削除します。よろしいですか？`)) return;

  const u = new URLSearchParams(location.search).get("u");
  const p = new URLSearchParams(location.search).get("p");

  await fetch(`/owner/api/songs/delete?u=${u}&p=${p}`,{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({id:cur.id})
  });

  cur = null;

  newItem();

  await reload();

  window.dispatchEvent(
    new CustomEvent('master-changed',{detail:{kind:'songs'}})
  );
}

// ハンドラ

document.getElementById("songs-btn-search").onclick = () => { page=1; reload(); };
document.getElementById("songs-btn-reload").onclick = () => reload();
document.getElementById("songs-btn-new").onclick = newItem;
document.getElementById("songs-btn-save").onclick = save;
document.getElementById("songs-btn-delete").onclick = del;


// 初期ロード

reload();
newItem();