function actsInit(root) {
  // 表示確認（後で本来の描画に差し替え）
  const status = root.querySelector('#status');
  if (status) {
    status.hidden = false;
    status.textContent = 'acts: ready';
  }
  // actsInit(root) の中に追加（status の表示のすぐ下など）
  const setId = (val) => {
    const hidden = root.querySelector('#acts-f-id');           // ← hidden に保持
    const badge  = root.querySelector('#acts-f-id-badge');     // ← 表示用バッジ
    const v = (val ?? '').toString();
    if (hidden) hidden.value = v;
    if (badge)  badge.textContent = v || '—';
  };
  // --- ここから追記：Acts の一覧をロードして #acts-list に描画 ---
  (async () => {
    const tbody = root.querySelector('#acts-list');
    if (!tbody) return;

    // 一覧取得（u/p と API_BASE はあなたの先頭定義をそのまま利用）
    const url = `${API_BASE}/owner/api/acts?u=${encodeURIComponent(u)}&p=${encodeURIComponent(p)}&ts=${Date.now()}`;
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
    const tbody = root.querySelector('#acts-list');
    if (!tbody) return;

    tbody.addEventListener('click', async (e) => {
      const tr = e.target.closest('tr[data-id]');
      if (!tr) return;

      const id = Number(tr.getAttribute('data-id'));
      if (!id) return;

      // 1) 詳細取得
      const url = `${API_BASE}/owner/api/acts/get?u=${encodeURIComponent(u)}&p=${encodeURIComponent(p)}&id=${id}`;
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
      set('#acts-f-id',         d.id);
      set('#acts-f-name',       d.name);
      set('#acts-f-birthday',   d.birthday);
      set('#acts-f-joined_on',  d.joined_on);
      set('#acts-f-left_on',    d.left_on);
      set('#acts-f-x',          d.x);
      set('#acts-f-instagram',  d.instagram);
      set('#acts-f-threads',    d.threads);
      set('#acts-f-facebook',   d.facebook);
      set('#acts-f-youtube',    d.youtube);
      set('#acts-f-tiktok',     d.tiktok);
      setId(d.id);
      // …フォーム反映の最後の後ろに置く（コメントアウトのまま）
      /*
      // TODO: 画像プレビュー有効化（コメント解除で動作）
      if (d?.id != null) {
        trySetActsPreview(root, d.id);  // acts_<id>.webp を探して表示
      }
      */


      const prev = root.querySelector('#acts-preview');
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

  // --- ここから追記：Acts 保存ボタンの最小結線 ---
  (() => {
    const saveBtn = root.querySelector('#acts-btn-save');
    if (!saveBtn) return;

    saveBtn.onclick = async () => {
      // 1) 右フォームの値を root 配下から集める
      const get = (sel) => (root.querySelector(sel)?.value?.trim() || null);
      const id         = root.querySelector('#acts-f-id')?.value?.trim();

      const payload = {
        name:       get('#acts-f-name') || '',
        birthday:   get('#acts-f-birthday'),
        joined_on:  get('#acts-f-joined_on'),
        left_on:    get('#acts-f-left_on'),
        x:          get('#acts-f-x'),
        instagram:  get('#acts-f-instagram'),
        threads:    get('#acts-f-threads'),
        facebook:   get('#acts-f-facebook'),
        youtube:    get('#acts-f-youtube'),
        tiktok:     get('#acts-f-tiktok'),
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
        ? `${API_BASE}/owner/api/acts/update?u=${encodeURIComponent(u)}&p=${encodeURIComponent(p)}`
        : `${API_BASE}/owner/api/acts/create?u=${encodeURIComponent(u)}&p=${encodeURIComponent(p)}`;

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
          reloadActsList();  // ★ 保存後に一覧を再読み込み
          st.textContent = ok ? (isUpdate ? '保存OK（update）' : '保存OK（create）') : '保存失敗';
        }
        // ※ この“1手”では一覧の再読み込みはしません（次の手で入れます）
      } catch (e) {
        const st = root.querySelector('#status');
        if (st) { st.hidden = false; st.textContent = '保存エラー'; }
      }
    };
  })();
  // Acts 検索：ボタン/Enter で一覧リロードを呼ぶ
  (() => {
    const q   = root.querySelector('#acts-q');
    const clear = root.querySelector('#acts-btn-clear');
    const btn = root.querySelector('#acts-btn-search');

    if (btn) btn.onclick = () => reloadActsList();

    if (q) q.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        reloadActsList();
      }
    });
  // クリア（×）
  if (clear) clear.onclick = () => {
    if (q) q.value = '';
    reloadActsList();   // 全件表示
  };
  })();
  // Acts 再読込：通常は検索語を維持して取り直し／Shift+クリックで検索語クリア
  (() => {
    const btn = root.querySelector('#acts-btn-reload');
    if (!btn) return;

    btn.onclick = (e) => {
      if (e.shiftKey) {
        const q = root.querySelector('#acts-q');
        if (q) q.value = '';
      }
      reloadActsList(); // 既存の再取得→正規化→フィルタ→描画が走る
    };
  })();


      // Acts 削除：選択（または右フォームのID）→ 確認 → delete → 一覧再読込＆フォームクリア
  (() => {
    const delBtn = root.querySelector('#acts-btn-delete');
    if (!delBtn) return;

    delBtn.onclick = async () => {
      const st     = root.querySelector('#status');
      const tbody  = root.querySelector('#acts-list');
      const active = tbody?.querySelector('tr[data-id].active');

      // 右フォーム優先→無ければ選択行
      const idStr  = root.querySelector('#acts-f-id')?.value?.trim() || active?.getAttribute('data-id');
      const id     = Number(idStr);
      if (!id) {
        if (st) { st.hidden = false; st.textContent = '削除対象を選択してください'; }
        return;
      }

      if (!confirm(`ID ${id} を削除します。よろしいですか？`)) return;

      try {
        const url = `${API_BASE}/owner/api/acts/delete?u=${encodeURIComponent(u)}&p=${encodeURIComponent(p)}`;
        const res = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type':'application/json' },
          body: JSON.stringify({ id })
        });
        if (!res.ok) throw new Error('delete failed');

        // フォームをクリア
        ['#acts-f-id','#acts-f-name','#acts-f-birthday','#acts-f-joined_on',
        '#acts-f-left_on','#acts-f-x','#acts-f-instagram','#acts-f-threads',
        '#acts-f-facebook','#acts-f-youtube','#acts-f-tiktok'].forEach(sel=>{
          const el = root.querySelector(sel); if (el) el.value = '';
        });
        const prev = root.querySelector('#acts-preview'); if (prev) prev.textContent = '';
        setId('');
        // 選択ハイライト解除
        active?.classList.remove('active');

        // 一覧を再読込（非同期・スクロールは既存の復元処理が働く）
        reloadActsList();

        if (st) { st.hidden = false; st.textContent = '削除OK'; }
      } catch (e) {
        if (st) { st.hidden = false; st.textContent = '削除エラー'; }
      }
    };
  })();


  // Acts 新規：選択解除 → 右フォームをクリア → フォーカスを Name に
  (() => {
    const newBtn = root.querySelector('#acts-btn-new');
    if (!newBtn) return;

    newBtn.onclick = () => {
      // 選択解除（左リストの active を外す）
      const tbody  = root.querySelector('#acts-list');
      tbody?.querySelectorAll('tr[data-id].active').forEach(el => el.classList.remove('active'));

      // フォームクリア（ID空＝保存時は create になる）
      const set = (sel, v='') => { const el = root.querySelector(sel); if (el) el.value = v; };
      set('#acts-f-id');           // ← 空にする（重要）
      set('#acts-f-name');
      set('#acts-f-birthday');
      set('#acts-f-joined_on');
      set('#acts-f-left_on');
      set('#acts-f-x');
      set('#acts-f-instagram');
      set('#acts-f-threads');
      set('#acts-f-facebook');
      set('#acts-f-youtube');
      set('#acts-f-tiktok');

      const prev = root.querySelector('#acts-preview');
      if (prev) prev.textContent = '';
      /*
      // TODO: 新規・削除時はプレビューをクリア
      trySetActsPreview(root, ''); // → onerror で「画像なし」を表示
      */
      // ステータス表示（任意）
      const st = root.querySelector('#status');
      if (st) { st.hidden = false; st.textContent = '新規作成モード'; }

      // 入力開始しやすくフォーカス
      root.querySelector('#acts-f-name')?.focus();
    };
  })();





  // --- ここまで追記 ---





  // --- ここから追記：Acts 一覧の再読み込み（＋スクロール有効化） ---
  let __actsListSeq = 0;  // ★ 追加：一覧リロードの世代カウンタ
  async function reloadActsList() {
    const tbody = root.querySelector('#acts-list');
    if (!tbody) return;


    // スクロール領域を確保（list-scroll に overflow を当てる）
    const scroller = root.querySelector('.list-scroll');
    const mySeq = ++__actsListSeq;
    const prevScroll = scroller ? scroller.scrollTop : 0;
    const prevActive = tbody.querySelector('tr[data-id].active');
    const prevId = prevActive ? Number(prevActive.getAttribute('data-id')) : null;
    // if (scroller) {
    //   scroller.style.minHeight = '0';
    //   scroller.style.overflow  = 'auto';
    // }

    // 一覧取得
    const url = `${API_BASE}/owner/api/acts?u=${encodeURIComponent(u)}&p=${encodeURIComponent(p)}&ts=${Date.now()}`;
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

    // ★ 追加：検索語（#acts-q）で絞り込み（name に含む・大文字小文字無視）
    const q = (root.querySelector('#acts-q')?.value || '').trim().toLowerCase();
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
  reloadActsList();
  // --- ここまで追記 ---

    const list = root.querySelector('#acts-list');
    if (list) {
      list.innerHTML = '<tr><td colspan="2">（仮）ここに一覧が出ます</td></tr>';
    }
  }
