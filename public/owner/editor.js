document.addEventListener("DOMContentLoaded", () => {
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


// ▼▼ ここから追加 ▼▼
const app = document.getElementById('app'); // 画面を表示する箱
const view = new URLSearchParams(window.location.search).get('view') || 'event';

if (view === 'people') {
  // People タブを画面に置く
  const tpl = document.getElementById('people-tpl');       // 隠れている部品
  app.appendChild(tpl.content.cloneNode(true));            // 実際に画面に出す
  peopleInit(app);                                         // ボタンや一覧を動かす
}
// ▲▲ ここまで追加 ▲▲



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
// await reload();
newItem();










function peopleInit(root) {
  // 表示確認（後で本来の描画に差し替え）
  const status = root.querySelector('#status');
  if (status) {
    status.hidden = false;
    status.textContent = 'people: ready';
  }
  // peopleInit(root) の中に追加（status の表示のすぐ下など）
  const setId = (val) => {
    const hidden = root.querySelector('#people-f-id');           // ← hidden に保持
    const badge  = root.querySelector('#people-f-id-badge');     // ← 表示用バッジ
    const v = (val ?? '').toString();
    if (hidden) hidden.value = v;
    if (badge)  badge.textContent = v || '—';
  };
  // --- ここから追記：People の一覧をロードして #people-list に描画 ---
  (async () => {
    const tbody = root.querySelector('#people-list');
    if (!tbody) return;

    // 一覧取得（u/p と API_BASE はあなたの先頭定義をそのまま利用）
    const url = `${API_BASE}/owner/api/people?u=${encodeURIComponent(u)}&p=${encodeURIComponent(p)}&ts=${Date.now()}`;
    let items = [];
    try {
      const res = await fetch(url, { cache: 'no-store' });
      items = res.ok ? await res.json() : [];
    } catch (_) {
      items = [];
    }

    // 描画（escapeHtml はあなたの定義をそのまま利用）
    tbody.innerHTML = items.map(it =>
      `<tr data-id="${it.id}"><td style="width:64px">${it.id}</td><td>${escapeHtml(it.name || '')}</td></tr>`
    ).join('') || `<tr><td colspan="2">（0件）</td></tr>`;
  })();
  // --- ここまで追記 ---
    
  // --- ここから追記：一覧クリック → 詳細取得 → 右フォームへ反映 ---
  (() => {
    const tbody = root.querySelector('#people-list');
    if (!tbody) return;

    tbody.addEventListener('click', async (e) => {
      const tr = e.target.closest('tr[data-id]');
      if (!tr) return;

      const id = Number(tr.getAttribute('data-id'));
      if (!id) return;

      // 1) 詳細取得
      const url = `${API_BASE}/owner/api/people/get?u=${encodeURIComponent(u)}&p=${encodeURIComponent(p)}&id=${id}`;
      let d = null;
      try {
        const res = await fetch(url, { cache: 'no-store' });
        if (res.ok) d = await res.json();
      } catch (_) {
        d = null;
      }
      if (!d) return;

      // 2) 右フォームへ反映（root配下のみ）
      const set = (sel, v) => {
        const el = root.querySelector(sel);
        if (el) el.value = v ?? '';
      };
      set('#people-f-id',         d.id);
      set('#people-f-name',       d.name);
      set('#people-f-birthday',   d.birthday);
      set('#people-f-joined_on',  d.joined_on);
      set('#people-f-left_on',    d.left_on);
      set('#people-f-x',          d.x);
      set('#people-f-instagram',  d.instagram);
      set('#people-f-threads',    d.threads);
      set('#people-f-facebook',   d.facebook);
      set('#people-f-youtube',    d.youtube);
      set('#people-f-tiktok',     d.tiktok);
      setId(d.id);
      // …フォーム反映の最後の後ろに置く（コメントアウトのまま）
      /*
      // TODO: 画像プレビュー有効化（コメント解除で動作）
      if (d?.id != null) {
        trySetPeoplePreview(root, d.id);  // people_<id>.webp を探して表示
      }
      */


      const prev = root.querySelector('#people-preview');
      if (prev) {
        prev.textContent = [
          d.name || '',
          d.x ? `X:${d.x}` : '',
          d.instagram ? `IG:${d.instagram}` : '',
          d.youtube ? `YT:${d.youtube}` : ''
        ].filter(Boolean).join(' | ');
      }

      // 3) 選択行の視覚化（任意）
      tbody.querySelectorAll('tr[data-id].active').forEach(el => el.classList.remove('active'));
      tr.classList.add('active');
    });
  })();
  // --- ここまで追記 ---

  // --- ここから追記：People 保存ボタンの最小結線 ---
  (() => {
    const saveBtn = root.querySelector('#people-btn-save');
    if (!saveBtn) return;

    saveBtn.onclick = async () => {
      // 1) 右フォームの値を root 配下から集める
      const get = (sel) => (root.querySelector(sel)?.value?.trim() || null);
      const id         = root.querySelector('#people-f-id')?.value?.trim();

      const payload = {
        name:       get('#people-f-name') || '',
        birthday:   get('#people-f-birthday'),
        joined_on:  get('#people-f-joined_on'),
        left_on:    get('#people-f-left_on'),
        x:          get('#people-f-x'),
        instagram:  get('#people-f-instagram'),
        threads:    get('#people-f-threads'),
        facebook:   get('#people-f-facebook'),
        youtube:    get('#people-f-youtube'),
        tiktok:     get('#people-f-tiktok'),
        // preview はUI専用のため送らない
      };
      if (!payload.name) {
        const st = root.querySelector('#status');
        if (st) { st.hidden = false; st.textContent = 'name は必須です'; }
        return;
      }

      // 2) API にPOST（update or create）
      const isUpdate = !!id;
      const url = isUpdate
        ? `${API_BASE}/owner/api/people/update?u=${encodeURIComponent(u)}&p=${encodeURIComponent(p)}`
        : `${API_BASE}/owner/api/people/create?u=${encodeURIComponent(u)}&p=${encodeURIComponent(p)}`;

      const body = isUpdate ? { id: Number(id), ...payload } : payload;

      try {
        const res = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        const ok = res.ok;
        const st = root.querySelector('#status');
        if (st) {
          st.hidden = false;
          reloadPeopleList();  // ★ 保存後に一覧を再読み込み
          st.textContent = ok ? (isUpdate ? '保存OK（update）' : '保存OK（create）') : '保存失敗';
        }
        // ※ この“1手”では一覧の再読み込みはしません（次の手で入れます）
      } catch (e) {
        const st = root.querySelector('#status');
        if (st) { st.hidden = false; st.textContent = '保存エラー'; }
      }
    };
  })();
  // People 検索：ボタン/Enter で一覧リロードを呼ぶ
  (() => {
    const q   = root.querySelector('#people-q');
    const clear = root.querySelector('#people-btn-clear');
    const btn = root.querySelector('#people-btn-search');

    if (btn) btn.onclick = () => reloadPeopleList();

    if (q) q.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        reloadPeopleList();
      }
    });
  // クリア（×）
  if (clear) clear.onclick = () => {
    if (q) q.value = '';
    reloadPeopleList();   // 全件表示
  };
  })();
  // People 再読込：通常は検索語を維持して取り直し／Shift+クリックで検索語クリア
  (() => {
    const btn = root.querySelector('#people-btn-reload');
    if (!btn) return;

    btn.onclick = (e) => {
      if (e.shiftKey) {
        const q = root.querySelector('#people-q');
        if (q) q.value = '';
      }
      reloadPeopleList(); // 既存の再取得→正規化→フィルタ→描画が走る
    };
  })();


      // People 削除：選択（または右フォームのID）→ 確認 → delete → 一覧再読込＆フォームクリア
  (() => {
    const delBtn = root.querySelector('#people-btn-delete');
    if (!delBtn) return;

    delBtn.onclick = async () => {
      const st     = root.querySelector('#status');
      const tbody  = root.querySelector('#people-list');
      const active = tbody?.querySelector('tr[data-id].active');

      // 右フォーム優先→無ければ選択行
      const idStr  = root.querySelector('#people-f-id')?.value?.trim() || active?.getAttribute('data-id');
      const id     = Number(idStr);
      if (!id) {
        if (st) { st.hidden = false; st.textContent = '削除対象を選択してください'; }
        return;
      }

      if (!confirm(`ID ${id} を削除します。よろしいですか？`)) return;

      try {
        const url = `${API_BASE}/owner/api/people/delete?u=${encodeURIComponent(u)}&p=${encodeURIComponent(p)}`;
        const res = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type':'application/json' },
          body: JSON.stringify({ id })
        });
        if (!res.ok) throw new Error('delete failed');

        // フォームをクリア
        ['#people-f-id','#people-f-name','#people-f-birthday','#people-f-joined_on',
        '#people-f-left_on','#people-f-x','#people-f-instagram','#people-f-threads',
        '#people-f-facebook','#people-f-youtube','#people-f-tiktok'].forEach(sel=>{
          const el = root.querySelector(sel); if (el) el.value = '';
        });
        const prev = root.querySelector('#people-preview'); if (prev) prev.textContent = '';
        setId('');
        // 選択ハイライト解除
        active?.classList.remove('active');

        // 一覧を再読込（非同期・スクロールは既存の復元処理が働く）
        reloadPeopleList();

        if (st) { st.hidden = false; st.textContent = '削除OK'; }
      } catch (e) {
        if (st) { st.hidden = false; st.textContent = '削除エラー'; }
      }
    };
  })();


  // People 新規：選択解除 → 右フォームをクリア → フォーカスを Name に
  (() => {
    const newBtn = root.querySelector('#people-btn-new');
    if (!newBtn) return;

    newBtn.onclick = () => {
      // 選択解除（左リストの active を外す）
      const tbody  = root.querySelector('#people-list');
      tbody?.querySelectorAll('tr[data-id].active').forEach(el => el.classList.remove('active'));

      // フォームクリア（ID空＝保存時は create になる）
      const set = (sel, v='') => { const el = root.querySelector(sel); if (el) el.value = v; };
      set('#people-f-id');           // ← 空にする（重要）
      set('#people-f-name');
      set('#people-f-birthday');
      set('#people-f-joined_on');
      set('#people-f-left_on');
      set('#people-f-x');
      set('#people-f-instagram');
      set('#people-f-threads');
      set('#people-f-facebook');
      set('#people-f-youtube');
      set('#people-f-tiktok');

      const prev = root.querySelector('#people-preview');
      if (prev) prev.textContent = '';
      /*
      // TODO: 新規・削除時はプレビューをクリア
      trySetPeoplePreview(root, ''); // → onerror で「画像なし」を表示
      */
      // ステータス表示（任意）
      const st = root.querySelector('#status');
      if (st) { st.hidden = false; st.textContent = '新規作成モード'; }

      // 入力開始しやすくフォーカス
      root.querySelector('#people-f-name')?.focus();
    };
  })();





  // --- ここまで追記 ---





  // --- ここから追記：People 一覧の再読み込み（＋スクロール有効化） ---
  let __peopleListSeq = 0;  // ★ 追加：一覧リロードの世代カウンタ
  async function reloadPeopleList() {
    const tbody = root.querySelector('#people-list');
    if (!tbody) return;


    // スクロール領域を確保（list-scroll に overflow を当てる）
    const scroller = root.querySelector('.list-scroll');
    const mySeq = ++__peopleListSeq;
    const prevScroll = scroller ? scroller.scrollTop : 0;
    const prevActive = tbody.querySelector('tr[data-id].active');
    const prevId = prevActive ? Number(prevActive.getAttribute('data-id')) : null;
    // if (scroller) {
    //   scroller.style.minHeight = '0';
    //   scroller.style.overflow  = 'auto';
    // }

    // 一覧取得
    const url = `${API_BASE}/owner/api/people?u=${encodeURIComponent(u)}&p=${encodeURIComponent(p)}&ts=${Date.now()}`;
    // ---- ここから置き換え（取得 → 正規化） ----
    let data = null;
    try {
      const res = await fetch(url, { cache: 'no-store' });
      data = res.ok ? await res.json() : null;
    } catch (_) {
      data = null;
    }

    // 配列 or {items:[…]} or {data:[…]} を吸収
    const items = Array.isArray(data)
      ? data
      : (data && Array.isArray(data.items)) ? data.items
      : (data && Array.isArray(data.data))  ? data.data
      : [];

    // ★ 追加：検索語（#people-q）で絞り込み（name に含む・大文字小文字無視）
    const q = (root.querySelector('#people-q')?.value || '').trim().toLowerCase();
    const list = q ? items.filter(it => (it.name || '').toLowerCase().includes(q)) : items;

    // 描画（ここで初めて書き換える）
    // tbody.innerHTML = items.map(it =>
    tbody.innerHTML = list.map(it =>
      `<tr data-id="${it.id}">
        <td style="width:64px">${it.id}</td>
        <td>${escapeHtml(it.name || '')}</td>
      </tr>`
    ).join('');

    // ★ 直後：選択とスクロール位置の復元
    if (prevId != null) {
      const tr = tbody.querySelector(`tr[data-id="${prevId}"]`);
      if (tr) tr.classList.add('active');
    }
    if (scroller) scroller.scrollTop = prevScroll;

  }

  // 初期表示でも一度リロード（一覧→右クリック反映の流れを安定化）
  reloadPeopleList();
  // --- ここまで追記 ---

    const list = root.querySelector('#people-list');
    if (list) {
      list.innerHTML = '<tr><td colspan="2">（仮）ここに一覧が出ます</td></tr>';
    }
  }

});