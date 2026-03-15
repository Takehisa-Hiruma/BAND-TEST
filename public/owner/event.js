function eventInit(root) {
  if (!root) return;

  // -----------------------
  // ステータス表示
  // -----------------------
  const status = root.querySelector("#status");
  if (status) status.textContent = "event: ready";

  // -----------------------
  // ボタン結線
  // -----------------------
  const btnSave          = root.querySelector("#btn-save");
  const btnBack          = root.querySelector("#btn-back");
  const btnPublish       = root.querySelector("#btn-publish");
  const btnPublish2      = root.querySelector("#btn-publish2");
  const btnNew           = root.querySelector("#btn-new");
  const btnDel           = root.querySelector("#btn-del");
  const btnFilter        = root.querySelector("#btn-filter");
  const btnReloadSetlist  = root.querySelector("#btn-reload-setlist");
  const btnOpenPublic    = root.querySelector("#btn-open-public");

  if (btnSave) btnSave.onclick = () => saveEvent(root);
  if (btnBack) btnBack.onclick = () => backToList(root);
  if (btnPublish) btnPublish.onclick = () => publishEvent(root);
  if (btnPublish2) btnPublish2.onclick = () => publishEventJSON(root);
  if (btnNew) btnNew.onclick = () => newEvent(root);
  if (btnDel) btnDel.onclick = () => deleteEvent(root);
  if (btnFilter) btnFilter.onclick = () => filterEventList(root);
  if (btnReloadSetlist) btnReloadSetlist.onclick = () => reloadSetlist(root);
  if (btnOpenPublic) btnOpenPublic.onclick = () => openEventPublic(root);

  // -----------------------
  // フォーム結線
  // -----------------------
  const fDate     = root.querySelector("#f-date");
  const fTitle    = root.querySelector("#f-title");
  const fSub      = root.querySelector("#f-sub");
  const fVenue    = root.querySelector("#f-venue-select");
  const fEra      = root.querySelector("#f-era-select");
  const fTour     = root.querySelector("#f-tour-select");
  const fForm     = root.querySelector("#f-form-select");

  // 必要に応じて初期値ロード
  if (fVenue) loadVenueOptions(fVenue);
  if (fEra)   loadEraOptions(fEra);
  if (fTour)  loadTourOptions(fTour);

  // -----------------------
  // 左テーブル（イベント一覧）
  // -----------------------
  const tbl       = root.querySelector("#tbl");
  if (tbl) {
    tbl.onclick = (e) => selectEventRow(e, root);
  }

  // -----------------------
  // 右パネル：出演者（lineup）
  // -----------------------
  const lineupBody = root.querySelector("#lineup-body");
  const lnMember   = root.querySelector("#ln-member");
  const lnRole     = root.querySelector("#ln-role");
  const lnAdd      = root.querySelector("#ln-add");
  const lnDel      = root.querySelector("#ln-del");
  const lnUp       = root.querySelector("#ln-up");
  const lnDown     = root.querySelector("#ln-down");
  const lnUpdate   = root.querySelector("#ln-update");

  if (lineupBody) lineupBody.onclick = (e) => selectLineupRow(e, root);
  if (lnAdd) lnAdd.onclick     = () => addLineup(root);
  if (lnDel) lnDel.onclick     = () => deleteLineup(root);
  if (lnUp) lnUp.onclick       = () => moveLineupUp(root);
  if (lnDown) lnDown.onclick   = () => moveLineupDown(root);
  if (lnUpdate) lnUpdate.onclick = () => updateLineup(root);

  // -----------------------
  // 右パネル：対バン（bandsevent）
  // -----------------------
  const bandBody = root.querySelector("#band-body");
  const bandName = root.querySelector("#band-name");
  const bandAdd  = root.querySelector("#band-add");
  const bandDel  = root.querySelector("#band-del");
  const bandUp   = root.querySelector("#band-up");
  const bandDown = root.querySelector("#band-down");

  if (bandBody) bandBody.onclick = (e) => selectBandRow(e, root);
  if (bandAdd) bandAdd.onclick   = () => addBand(root);
  if (bandDel) bandDel.onclick   = () => deleteBand(root);
  if (bandUp)  bandUp.onclick    = () => moveBandUp(root);
  if (bandDown) bandDown.onclick = () => moveBandDown(root);

  // -----------------------
  // 右パネル：セトリ（setlist）
  // -----------------------
  const setlistBody = root.querySelector("#setlist-body");
  const slSong       = root.querySelector("#sl-song");
  const slSection    = root.querySelector("#sl-section");
  const slVersion    = root.querySelector("#sl-version");
  const slAdd        = root.querySelector("#sl-add");
  const slDel        = root.querySelector("#sl-del");
  const slUp         = root.querySelector("#sl-up");
  const slDown       = root.querySelector("#sl-down");
  const slUpdate     = root.querySelector("#sl-update");

  if (setlistBody) setlistBody.onclick = (e) => selectSetlistRow(e, root);
  if (slAdd) slAdd.onclick       = () => addSetlist(root);
  if (slDel) slDel.onclick       = () => deleteSetlist(root);
  if (slUp) slUp.onclick         = () => moveSetlistUp(root);
  if (slDown) slDown.onclick     = () => moveSetlistDown(root);
  if (slUpdate) slUpdate.onclick = () => updateSetlist(root);

  // -----------------------
  // 初期ロード
  // -----------------------
  reloadEventList(root);
}