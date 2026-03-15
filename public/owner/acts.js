function actsInit(root) {

  const $ = s => root.querySelector(s);
  const $$ = s => Array.from(root.querySelectorAll(s));

  const u = new URLSearchParams(location.search).get("u");
  const p = new URLSearchParams(location.search).get("p");

  let cur = null, page = 1, size = 50;

  // 一覧描画
  async function reload() {
    const q = $("#acts-q")?.value?.trim() || "";

    const data = await fetch(
      `/owner/api/acts/list?u=${u}&p=${p}&page=${page}&size=${size}&q=${encodeURIComponent(q)}`
    ).then(r => r.json());

    const tbody = $("#acts-list");
    tbody.innerHTML = "";

    for (const it of data.items || []) {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${it.id}</td><td>${it.name}</td>`;
      tr.onclick = () => select(it.id);

      if (cur?.id === it.id) tr.classList.add("active");

      tbody.appendChild(tr);
    }
  }

  // 明細セット
  async function select(id) {
    const data = await fetch(
      `/owner/api/acts/get?u=${u}&p=${p}&id=${id}`
    ).then(r => r.json());

    cur = data;

    $("#acts-f-id").value        = data.id ?? "";
    $("#acts-f-title").value     = data.name ?? "";
    $("#acts-f-url").value       = data.url ?? "";
    $("#acts-f-x").value         = data.x ?? "";
    $("#acts-f-instagram").value = data.instagram ?? "";
    $("#acts-f-threads").value   = data.threads ?? "";
    $("#acts-f-facebook").value  = data.facebook ?? "";
    $("#acts-f-youtube").value   = data.youtube ?? "";
    $("#acts-f-tiktok").value    = data.tiktok ?? "";
    $("#acts-preview").textContent = data.preview ?? "";

    $$("#acts-list tr").forEach(tr =>
      tr.classList.toggle(
        "active",
        Number(tr.firstChild.textContent) === id
      )
    );
  }

  // 新規
  function newItem() {

    cur = {
      id:"", name:"", url:"",
      x:"", instagram:"", threads:"",
      facebook:"", youtube:"", tiktok:"",
      preview:""
    };

    $("#acts-f-id").value        = "";
    $("#acts-f-title").value     = "";
    $("#acts-f-url").value       = "";
    $("#acts-f-x").value         = "";
    $("#acts-f-instagram").value = "";
    $("#acts-f-threads").value   = "";
    $("#acts-f-facebook").value  = "";
    $("#acts-f-youtube").value   = "";
    $("#acts-f-tiktok").value    = "";
    $("#acts-preview").textContent = "";

    $("#acts-f-title").focus();
  }

  // 保存
  async function save() {

    const name = $("#acts-f-title").value.trim();
    if (!name) return;

    const payload = {
      name,
      url: $("#acts-f-url").value.trim() || null,
      x: $("#acts-f-x").value.trim() || null,
      instagram: $("#acts-f-instagram").value.trim() || null,
      threads: $("#acts-f-threads").value.trim() || null,
      facebook: $("#acts-f-facebook").value.trim() || null,
      youtube: $("#acts-f-youtube").value.trim() || null,
      tiktok: $("#acts-f-tiktok").value.trim() || null,
      preview: $("#acts-preview").textContent || null
    };

    if (!cur?.id) {

      cur = await fetch(
        `/owner/api/acts/create?u=${u}&p=${p}`,
        {
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify(payload)
        }
      ).then(r=>r.json());

    } else {

      await fetch(
        `/owner/api/acts/update?u=${u}&p=${p}`,
        {
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify({ id: cur.id, ...payload })
        }
      );

    }

    await reload();

    window.dispatchEvent(
      new CustomEvent("master-changed", { detail: { kind: "acts" } })
    );
  }

  // 削除
  async function del() {

    if (!cur?.id) return;

    if (!confirm(`ID ${cur.id} を削除します。よろしいですか？`)) return;

    await fetch(
      `/owner/api/acts/delete?u=${u}&p=${p}`,
      {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({ id: cur.id })
      }
    );

    newItem();
    await reload();

    window.dispatchEvent(
      new CustomEvent("master-changed", { detail: { kind: "acts" } })
    );
  }

  // ボタン
  $("#acts-btn-search").onclick = () => { page=1; reload(); };
  $("#acts-btn-reload").onclick = () => reload();
  $("#acts-btn-new").onclick    = () => newItem();
  $("#acts-btn-save").onclick   = () => save();
  $("#acts-btn-delete").onclick = () => del();

  // 初期化
  reload();
  newItem();

}