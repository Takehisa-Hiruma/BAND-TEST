**Prompt [おー、一発目にしてはイメージの再現性高いな。すごい。

**「各所の値の調整」＝幅・比率・見栄え・検索やソートの細部**は“場所がわかれば一瞬”なので、**探さずにすぐ当てられる**ように **編集ポイントマップ**を置きます。  
（**前後3行つき**の最小置換／追記だけ。コピペで当ててOK）

---

## 🔎 調整ポイント・マップ（値だけ変えれば反映）

> すべて `public/owner/editor.html` 内。**検索→その行だけ差し替え**で終わります。

---

### 1) 2カラムの幅（左ペインの横幅）
**探す**
```css
#wrap{display:grid;grid-template-columns: 520px 1fr; gap:0; height:calc(100vh - 44px)}
```
**値だけ変更（例：560pxに）**
```css
#wrap{display:grid;grid-template-columns: 560px 1fr; gap:0; height:calc(100vh - 44px)}
```

---

### 2) 右ペインの縦比率（lineup / band / setlist）
**探す**
```css
#right{display:grid;grid-template-rows: 35% 35% 1fr; min-height:0}
```
**例：lineup 30% / band 30% / setlist 40%**
```css
#right{display:grid;grid-template-rows: 30% 30% 1fr; min-height:0}
```

---

### 3) 一覧テーブルの列幅
**探す（thead の `<th style="width:...">`）**
```html
<thead><tr><th style="width:90px">日付</th><th>タイトル</th><th style="width:160px">会場</th><th style="width:80px">形態</th></tr></thead>
```
**例：日付100 / 会場200 / 形態90**
```html
<thead><tr><th style="width:100px">日付</th><th>タイトル</th><th style="width:200px">会場</th><th style="width:90px">形態</th></tr></thead>
```

---

### 4) 一覧行のハイライト色／ホバー色
**探す**
```css
tbody tr[data-id].sel{background:#f0f9ff}
tbody tr[data-id]:hover{background:#f7fbff}
```
**例：もう少し濃い色へ**
```css
tbody tr[data-id].sel{background:#e6f2ff}
tbody tr[data-id]:hover{background:#eef7ff}
```

---

### 5) フォーム2列の割り付け（左項目群／右項目群の幅比）
**探す**
```css
.grid2{display:grid;grid-template-columns: 1fr 1fr;gap:10px}
```
**例：左 3 / 右 2 の比率**
```css
.grid2{display:grid;grid-template-columns: 3fr 2fr;gap:10px}
```

---

### 6) コンボの横幅（Venue / Era / Tour / 形態）
**探す（セレクトの `style="min-width:..."`）**
```html
<select id="f-venue-select" style="min-width:220px"></select>
<select id="f-era-select"   style="min-width:160px"></select>
<select id="f-tour-select"  style="min-width:160px"></select>
<select id="f-form-select"  style="min-width:120px">
```
**例：Venue 260px**
```html
<select id="f-venue-select" style="min-width:260px"></select>
```

---

### 7) 検索ボックスの幅
**探す**
```html
<input id="q" type="text" placeholder="タイトル / 会場" style="width:200px">
```
**例：240px**
```html
<input id="q" type="text" placeholder="タイトル / 会場" style="width:240px">
```

---

### 8) 検索の挙動（大文字小文字を無視）
**探す（`render(arr)` 内のこの塊）**
```js
const q = $("#q").value.trim();
const filtered = q ? arr.filter(x => (x.title||"").includes(q) || (resolveVenueName(x)||"").includes(q)) : arr;
```
**置換（小文字化して比較）**
```js
const q = $("#q").value.trim().toLowerCase();
const filtered = q
  ? arr.filter(x =>
      (x.title||"").toLowerCase().includes(q) ||
      (resolveVenueName(x)||"").toLowerCase().includes(q)
    )
  : arr;
```

---

### 9) ソートのタイブレーク（同日ならタイトルで）
**探す（`render(arr)` 内）**
```js
const sorted = [...filtered].sort((a,b)=>{
  const da=new Date(a.date||"0000-00-00"), db=new Date(b.date||"0000-00-00");
  return db - da; // 降順
});
```
**置換（同日の場合タイトル昇順）**
```js
const sorted = [...filtered].sort((a,b)=>{
  const da=new Date(a.date||"0000-00-00"), db=new Date(b.date||"0000-00-00");
  if (db - da !== 0) return db - da;                   // 日付降順
  return (a.title||"").localeCompare(b.title||"");     // タイトル昇順
});
```

---

### 10) 保存後の“選択行を維持”したい
**探す（`save()` の成功時）**
```js
if(r.ok){ Object.assign(cur, body); render(events); }
```
**置換（再描画後に同じID行を再選択）**
```js
if(r.ok){
  const keepId = cur.id;
  Object.assign(cur, body);
  render(events);
  const keepTr = document.querySelector(`tbody#tbl tr[data-id="${keepId}"]`);
  if (keepTr) { keepTr.classList.add("sel"); }
}
```

---

### 11) 「セトリ」「対バン」「出演者」テーブルの列幅
**lineup（右上）**
```html
<thead><tr><th style="width:160px">メンバー</th><th style="width:160px">役割</th></tr></thead>
```
**bandsevent（右中）**
```html
<thead><tr><th style="width:40px">#</th><th>バンド名</th></tr></thead>
```
**setlist（右下）**
```html
<thead><tr><th style="width:40px">#</th><th>曲名</th><th style="width:180px">補足</th></tr></thead>
```
→ **数値を好みで増減**するだけでOK。

---

### 12) ボタン文言／ラベルの文言
**探す（一例）**
```html
<button id="btn-reload-setlist">セトリをリロード</button>
```
**好きな文言に変更**
```html
<button id="btn-reload-setlist">セトリ再読込</button>
```
他のラベルも同様に**テキストだけ差し替え**で反映。

---

## 🧩（オプション）値の“集約”もできる
何度も触る値（左幅・右比率・列幅）を**CSS変数に集約**すると、今後は上の数値を「1か所」だけ触る運用にできます。後でやりたくなったら言って。  
例：
```css
:root{
  --left-col: 560px;
  --right-rows: 30% 30% 1fr;
  --col-date: 100px; --col-venue: 200px; --col-form: 90px;
}
#wrap{grid-template-columns: var(--left-col) 1fr;}
#right{grid-template-rows: var(--right-rows);}
```
（この方式に張り替えるパッチも用意できます）

---

## 次どうする？
- **「この値をこうしたい」**のリストをそのまま書いてくれれば、**前後3行つきの差し替え行**で返す（探す時間ゼロ）。
- もしくは、**こちらでCSS変数化した“集中調整版”**を1本出すことも可能（上の12項目を一か所に集約）。

まずは「左幅・右比率・テーブル列幅」の3点から詰めるのが体感差大きい。  
やりたい数値（px/%）を教えて。**該当行だけ**返す。