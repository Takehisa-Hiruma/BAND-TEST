
    // URLパラメータ取得
    const u = new URLSearchParams(location.search).get("u");
    const p = new URLSearchParams(location.search).get("p");
    if (!u || !p) location.href = "./index.html";

    // API_BASE 判定
    const API_BASE =
      (location.hostname === "127.0.0.1" || location.hostname === "localhost")
        ? "http://127.0.0.1:8787"
        : "";

    // app 初期マウント
    const host = document.getElementById('app');
    // host.innerHTML = '';
    // host.appendChild(document.getElementById('event-editor-tpl').content.cloneNode(true));

    // 画面マウント
    function mountEvent() {
      host.innerHTML = '';
      host.appendChild(
        document.getElementById('event-editor-tpl').content.cloneNode(true)
      );
      const root = host.firstElementChild;
      eventInit(root);
    }

    function eventInit(root) {
      // ここでは表示確認だけ。後で本来の初期化（一覧ロード等）に差し替えます。
      const status = root.querySelector('#status');
      if (status) {
        status.textContent = 'event: ready';
      }
      // Event 画面がマウント済みの時だけ、結線を実行（People等では何もしない）
      const viewName = (root?.closest?.('[data-view]') || root)?.getAttribute?.('data-view')?.trim()?.toLowerCase();
      if (viewName === 'event') {
        wireLeftUi && wireLeftUi();
        wireSplitters && wireSplitters();
      }
    }

    function mountPeople() {
      host.innerHTML = '';
      host.appendChild(
        document.getElementById('people-tpl').content.cloneNode(true)
      );
      const root = host.firstElementChild;
      peopleInit(root);
    }

    function mountActs() {
      host.innerHTML = '';
      host.appendChild(
        document.getElementById('acts-tpl').content.cloneNode(true)
      );
      const root = host.firstElementChild;
      ActsInit(root);
    }

    function mountSongs() {
      host.innerHTML = '';
      host.appendChild(
        document.getElementById('songs-tpl').content.cloneNode(true)
      );
      const root = host.firstElementChild;
      SongsInit(root);
    }

    function mountVenue() {
      host.innerHTML = '';
      host.appendChild(
        document.getElementById('venue-tpl').content.cloneNode(true)
      );
      const root = host.firstElementChild;
      VenueInit(root);
    }

    function mountRoles() {
      host.innerHTML = '';
      host.appendChild(
        document.getElementById('roles-tpl').content.cloneNode(true)
      );
      const root = host.firstElementChild;
      RolesInit(root);
    }

    function mountEra() {
      host.innerHTML = '';
      host.appendChild(
        document.getElementById('era-tpl').content.cloneNode(true)
      );
      const root = host.firstElementChild;
      EraInit(root);
    }

    function mountTour() {
      host.innerHTML = '';
      host.appendChild(
        document.getElementById('tour-tpl').content.cloneNode(true)
      );
      const root = host.firstElementChild;
      TourInit(root);
    }

/*
// TODO: 画像プレビュー（people_<id>.webp があれば表示）
function trySetPeoplePreview(root, id, basePath = '/assets/people') {
  const img = root.querySelector('#people-preview-img');
  const nop = root.querySelector('#people-preview-nop');
  if (!img || !nop) return;

  const url = `${basePath}/people_${id}.webp`;

  // onload / onerror で存在確認 → 切り替え
  img.onload  = () => { img.style.display = '';  nop.style.display = 'none'; };
  img.onerror = () => { img.style.display = 'none'; nop.style.display = ''; img.removeAttribute('src'); };

  // 先に非表示でsrc設定（読み込み完了で表示）
  img.style.display = 'none';
  img.src = url;
}
*/


    // const startView = new URLSearchParams(location.search).get('view') || 'event';
    // (startView === 'people' ? mountPeople : mountEvent)();

    // const startView = new URLSearchParams(location.search).get('view') || 'event';

    // if (startView === 'people') {
    //   mountPeople();
    // } else if (startView === 'acts') {
    //   mountActs();
    // } else if (startView === 'venue') {
    //   mountVenue();
    // } else if (startView === 'songs') {
    //   mountSongs();
    // } else if (startView === 'roles') {
    //   mountRoles();
    // } else if (startView === 'era') {
    //   mountEra();
    // } else if (startView === 'tour') {
    //   mountTour();
    // } else {
    //   mountEvent();
    // }

    const MOUNTS = {
      event: mountEvent,
      people: mountPeople,
      acts: mountActs,
      venue: mountVenue,
      songs: mountSongs,
      roles: mountRoles,
      era: mountEra,
      tour: mountTour
    };

    function loadView() {
      const view = new URLSearchParams(location.search).get("view") || "event";
      (MOUNTS[view] || mountEvent)();
    }

    loadView();

    window.addEventListener("popstate", loadView);
