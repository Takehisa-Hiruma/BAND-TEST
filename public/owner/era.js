const $ = s=>document.querySelector(s);
const $$= s=>Array.from(document.querySelectorAll(s));
let cur=null, page=1, size=50;

// 日付正規化
function normYMD(input){
  if(!input) return null;
  const s=input.trim();
  let m = s.match(/^(\d{4})-(\d{2})-(\d{2})$/); if(m) return `${m[1]}-${m[2]}-${m[3]}`;
  m = s.match(/^(\d{4})\/(\d{1,2})\/(\d{1,2})$/); if(m) return `${m[1]}-${String(m[2]).padStart(2,'0')}-${String(m[3]).padStart(2,'0')}`;
  m = s.match(/^(\d{4})年(\d{1,2})月(\d{1,2})日$/); if(m) return `${m[1]}-${String(m[2]).padStart(2,'0')}-${String(m[3]).padStart(2,'0')}`;
  m = s.match(/^(\d{4})[.\s](\d{1,2})[.\s](\d{1,2})$/); if(m) return `${m[1]}-${String(m[2]).padStart(2,'0')}-${String(m[3]).padStart(2,'0')}`;
  return null;
}
function toInputDate(s){ if(!s) return ""; return /^\d{4}-\d{2}-\d{2}$/.test(s)?s:normYMD(s)||""; }
function escapeHtml(s){ return (s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m])); }

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

// 一覧描画
async function reload(){
  const q=$("#era-q")?.value?.trim()||"";
  const data=await getJSON(`/owner/api/era/list?u=${u}&p=${p}&page=${page}&size=${size}&q=${encodeURIComponent(q)}`);
  const tbody=$("#era-list"); tbody.innerHTML="";
  for(const it of data.items||[]){
    const tr=document.createElement("tr");
    tr.innerHTML=`<td>${it.id}</td><td>${escapeHtml(it.name)}</td>`;
    tr.onclick=()=>select(it.id);
    if(cur?.id===it.id) tr.classList.add("active");
    tbody.appendChild(tr);
  }
}

// 明細セット
async function select(id){
  const data=await getJSON(`/owner/api/era/get?u=${u}&p=${p}&id=${id}`);
  cur=data;
  $("#era-f-id").value=data.id??"";
  $("#era-f-title").value=data.name??"";
  $("#era-f-start").value=toInputDate(data.start_on);
  $("#era-f-end").value=toInputDate(data.end_on);
  $("#era-f-memo").value=data.memo??"";
  $$("#era-list tr").forEach(tr=>tr.classList.toggle("active",Number(tr.firstChild.textContent)===id));
}

// 新規
function newItem(){
  cur={id:"",name:"",start_on:"",end_on:"",memo:""};
  $("#era-f-id").value="";
  $("#era-f-title").value="";
  $("#era-f-start").value="";
  $("#era-f-end").value="";
  $("#era-f-memo").value="";
  $("#era-f-title").focus();
}

// 保存
async function save(){
  const name=$("#era-f-title").value.trim();
  const start=normYMD($("#era-f-start").value);
  const end=normYMD($("#era-f-end").value);
  const memo=$("#era-f-memo").value.trim()||null;
  if(!name) return;
  if(!cur?.id){
    cur=await postJSON(`/owner/api/era/create?u=${u}&p=${p}`,{name,start_on:start,end_on:end,memo});
  } else {
    await postJSON(`/owner/api/era/update?u=${u}&p=${p}`,{id:cur.id,name,start_on:start,end_on:end,memo});
  }
  await reload();
}

// 削除
async function del(){
  if(!cur?.id) return;
  if(!confirm(`ID ${cur.id} を削除します。よろしいですか？`)) return;
  await postJSON(`/owner/api/era/delete?u=${u}&p=${p}`,{id:cur.id});
  cur=null;
  newItem();
  await reload();
  window.dispatchEvent(new CustomEvent("master-changed",{detail:{kind:"era"}}));
}

// ハンドラ
document.getElementById("era-btn-search").onclick=()=>{ page=1; reload(); };
document.getElementById("era-btn-reload").onclick=()=>reload();
document.getElementById("era-btn-new").onclick=newItem;
document.getElementById("era-btn-save").onclick=save;
document.getElementById("era-btn-delete").onclick=del;

// 初期ロード
reload();
newItem();