const $ = s=>document.querySelector(s);
const $$= s=>Array.from(document.querySelectorAll(s));
let cur=null, page=1, size=50;

const u=new URLSearchParams(location.search).get("u");
const p=new URLSearchParams(location.search).get("p");
if(!u||!p) location.href="./index.html";

async function getJSON(path){
  const r=await fetch(path);
  if(!r.ok) throw await r.json().catch(()=>({reason:r.statusText}));
  return r.json();
}

async function postJSON(path, body){
  const r=await fetch(path,{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify(body||{})
  });
  if(!r.ok){
    const data=await r.json().catch(()=>({reason:r.statusText}));
    const e=new Error(data.reason||"error");
    e.status=r.status;
    e.data=data;
    throw e;
  }
  return r.json();
}

function escapeHtml(s){
  return (s??"").replace(/[&<>"']/g,m=>(
    {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]
  ));
}

// 一覧描画
async function reload(){
  const q=$("#role-q")?.value?.trim()||"";
  const data=await getJSON(`/owner/api/role/list?u=${u}&p=${p}&page=${page}&size=${size}&q=${encodeURIComponent(q)}`);
  const tbody=$("#role-list");
  tbody.innerHTML="";

  for(const it of data.items||[]){
    const tr=document.createElement("tr");
    tr.innerHTML=`<td>${it.id}</td><td>${escapeHtml(it.name)}</td>`;
    tr.onclick=()=>select(it.id);

    if(cur?.id===it.id) tr.classList.add("active");

    tbody.appendChild(tr);
  }
}

// 明細
async function select(id){
  const data=await getJSON(`/owner/api/role/get?u=${u}&p=${p}&id=${id}`);

  cur=data;

  $("#role-f-id").value=data.id??"";
  $("#role-f-title").value=data.name??"";

  $$("#role-list tr").forEach(tr=>
    tr.classList.toggle("active",Number(tr.firstChild.textContent)===id)
  );
}

// 新規
function newItem(){
  cur={id:"",name:""};

  $("#role-f-id").value="";
  $("#role-f-title").value="";

  $("#role-f-title").focus();
}

// 保存
async function save(){
  const title=$("#role-f-title").value.trim();
  if(!title) return;

  if(!cur?.id){
    cur=await postJSON(`/owner/api/role/create?u=${u}&p=${p}`,{name:title});
  }else{
    await postJSON(`/owner/api/role/update?u=${u}&p=${p}`,{id:cur.id,name:title});
  }

  await reload();

  window.dispatchEvent(
    new CustomEvent("master-changed",{detail:{kind:"role"}})
  );
}

// 削除
async function del(){
  if(!cur?.id) return;

  if(!confirm(`ID ${cur.id} を削除します。よろしいですか？`)) return;

  await postJSON(`/owner/api/role/delete?u=${u}&p=${p}`,{id:cur.id});

  cur=null;

  newItem();

  await reload();

  window.dispatchEvent(
    new CustomEvent("master-changed",{detail:{kind:"role"}})
  );
}

// ハンドラ
document.getElementById("role-btn-search").onclick=()=>{page=1;reload();};
document.getElementById("role-btn-reload").onclick=()=>reload();
document.getElementById("role-btn-new").onclick=newItem;
document.getElementById("role-btn-save").onclick=save;
document.getElementById("role-btn-delete").onclick=del;

// 初期ロード
reload();
newItem();