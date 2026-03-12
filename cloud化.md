
---

# 🟦 最終的な推奨方式（仕様として明文化するとこう）

### 【1】 認証
- Cloudflare Access などの外部サービス  
- セッション最大数：1  
- ID共有OK（ファン・公式の実態に合わせる）

### 【2】 編集モード突入時
テナントの  
`editing_state = { active: true, started_at, editor_session_id }`  
をセット。

### 【3】 後からアクセスしたセッション
- 同じアカウントでも読み取り専用  
- 編集は不可  
- 奪取不可（精神衛生を守るため）

### 【4】 編集終了ボタン
押すと `editing_state = null` に。

### 【5】 タイムアウト
`started_at` から一定時間（例：1時間）経過したら自動で解除。

### 【6】 これだけでDB破壊リスクは完全に消える

---

# 🟩 指摘は正しい（まとめ）

- **同時セッション不可が本体の安全装置**  
- 編集ロックを強く入れると逆にストレス  
- 後勝ち奪取は最悪  
- 心理的に確実にメンテナが疲れる  
- だから **「軽量の先勝ち＋終了ボタン＋タイムアウト」が最適解**

完全に正しい結論です。

---


---

# 🎯 **結論：  
いま話している “URL の命名仕様” に display_name も自動生成も一切不要。  
必要なのは “URLに使える文字のルール（＝projectname の仕様）だけ”。**

晝間さんの言う通りです。  
本当に **URL の命名だけ** の話をしている現段階では関係ありません。

そして、「自動生成」は **必要ない／使わない**。  
どこから生成する？ → 今の段階では、生成元となる “別フィールド” を作る気が無いのだから当然不要。

完全に理解したので、ここからはシンプルにいきます。

---

# ✔ 今 まとめるべきなのはこれだけ  
- `username` の命名仕様  
- `projectname`（＝URLの変数部分）の命名仕様  
- それだけで **/username/projectname/** が決まる  
- それ以外のフィールド（表示名／バンド名）は **今は関係ない**  

これならブレなくて済むし、晝間さんの意図通り **一番シンプル**。

---

# 📘 **URL の命名仕様（確定版）**

## ■ username（テナントID）
- 許可：  
  `a-z, 0-9`  
  （必要なら `.` も許可だが、無くてもいい）
- 長さ：  
  5〜32 文字 
- 小文字強制（`.lower()` で正規化）
- 予約語不要  
  → `/username/` 以下は静的なので衝突しない  
  → `/admin` や `/api` などは上位階層で運営が管理するため別世界

---

## ■ projectname（URLパスに使う部分）
- 許可：  
  `a-z`, `0-9`, `-`, `_`
- 長さ：  
  1〜50 文字  
  （1文字OK）
- 小文字強制
- 衝突時は suffix 付与（例：`radwimps`, `radwimps-2`）
- **予約語不要**  
  → `/username/xxxx/` という階層にいる限り、  
     `delete` だろうと `database` だろうと影響しない  
  → 静的配信では “名前に意味” は生まれないので安全

---

---

# 🎉最終まとめ（ほんとにこれだけで良い）

### ✔ URLには  
```
/username/projectname/
```

### ✔ username  
- a-z / 0-9  
- 小文字強制  
- 予約語なし

### ✔ projectname  
- a-z / 0-9 / - / _  
- 小文字強制  
- 予約語なし  
- 衝突対応： suffix（`-2` など）

---


---

# 🧭 全体像まとめ（後任向け・一枚で理解できる版）

このサービスは **テナント式のライブアーカイブ SaaS**。  
オーナー（ユーザー）が **複数のバンド（プロジェクト）を管理**し、  
各プロジェクトの **イベント・セトリ・対バン情報**から静的サイトを生成して公開する。

バックエンドでは SQLite→JSON への変換を行うスクリプトを実行し、  
フロントエンド（静的ファイル）では JSON を読み込んで UI 表示する。

---

# 1. URL / ディレクトリ構造（公開物）

```
https://<FQDN>/<username>/<projectname>/index.html
```

公開されるツリーは：

```
public/
  └─ <username>/
       └─ <projectname>/
            ├─ index.html
            ├─ config.json         ← オーナーが編集する設定
            ├─ data/               ← DB から export_json.py が出力
            │     ├─ events.json
            │     ├─ songs.json
            │     ├─ people.json
            │     ├─ lineup.json
            │     ├─ bandsevent.json
            │     └─ acts.json
            └─ image/              ← 画像素材（ロゴ・任意）
```

**ポイント**
- 静的配信では **公開ルート内はすべて公開状態**  
- DB は公開ルートの外（後述）に置く  
- HTML はすべて **相対パスで `./data/*.json` を読むだけ**  
- プロジェクトは **username と projectname の組み合わせで固有**

---

# 2. 命名規則（URLに使う名前）

## username（テナント）
- 許可文字：`a-z`, `0-9`
- 長さ：5〜32文字
- 小文字強制
- 予約語不要（`/<username>/…` 配下で衝突しないため）

## projectname（バンド）
- 許可文字：`a-z`, `0-9`, `-`, `_`
- 長さ：1〜50文字
- 小文字強制
- 予約語不要（テナント内に閉じているため）

> ※ URL として扱うため “ASCII + 小文字” で揃え、**GitHub Pages などの大小区別問題を回避**。

---

# 3. DB（非公開データ）の扱い

オーナーのデータは SQLite として保持：

```
db/
  └─ <username>/
        └─ <projectname>.db
```

**非公開にする理由**
- 公開ルートに置くと URL でダウンロードされるため  
- リポジトリが Public なら GitHub 上で閲覧できてしまう  
→ 必要であれば **別の Private 保管（R2/S3/Private repo）** に移せるように設計

**スクリプトの参照方法**
```python
DB = ROOT / "db" / username / f"{project}.db"
```

---

# 4. export_json.py（サーバーサイド生成スクリプト）

役割：  
SQLite のデータから **data/ 以下の JSON 群**と、  
プロジェクト直下の `index.html`（プレースホルダー）・`config.json`（任意）を生成する。

呼び出し方：

```
python export_json.py <username> <projectname>
```

生成されるのは：

```
public/<username>/<projectname>/data/*.json
public/<username>/<projectname>/index.html
public/<username>/<projectname>/image/
```

**重要な仕様**
- 旧 `site/` 構造は廃止。  
- 生成物は **そのまま公開配信ツリー**として扱える。
- DB 参照は username/projectname から導出（規約パス）。

---

# 5. Owner Console（オーナー向け UI）

オーナーが扱うのは **DB編集 + プロジェクト（バンド）横断管理**。  
ここが重要ポイントで、オペレーターとしっかり分離される。

### オーナーができること
1. **複数プロジェクトの作成・削除・並び替え**
2. 各プロジェクトの設定（projectname / 公開ON/OFF / description 等）
3. イベント・セトリ・対バン・画像の編集  
4. 保存 → **公開反映（ビルド実行）**
5. config.json の編集（タイトル・リンクなど最小設定）

### オーナーができないこと
- HTML/CSS の自由編集  
- テーマビルダー（着せ替え）  
- 任意 JS の注入

**理由：多テナントの安全・安定運用のため**

---

# 6. Operator Console（運営側 UI）

あなた（運営）が扱う画面。  
オーナーには触れさせない領域。

### オペレーターができること
- テナント発行/凍結（username を払い出す）  
- システム設定（メンテ告知など一部）  
- 監査ログ（保存・ビルド履歴）  
- 全体の容量/転送量の簡易メーター

### オペレーターがしないこと
- 個々のオーナーの project 作成/削除  
- イベント/セトリ/対バン編集  
- 公開サイトの見栄え操作  

---

# 7. config.json（プロジェクト毎の軽い設定ファイル）

Owner Console の設定タブで編集され、  
フロントが読み取って反映する。再ビルド不要。

例：

```json
{
  "site_title": "SAMPLE SEARCH",
  "home": { "url": "https://example.com", "label": "戻る" },
  "readme": { "url": "readme.html", "label": "README" },
  "google_form": { "form_id": "...", "entry_id": "..." }
}
```

> これは **settings.js の後継**。  
> フロントの JS が config を読み、title やリンクを差し替える。

---

# 8. 認証と同時編集ルール

- 編集者は **Owner（テナント本人）のみ**  
- 認証は **Cloudflare Access のメールリンク or Passkey**  
- **同時セッションは1つ**  
- **先勝ち制** + 「編集終了ボタン」+ タイムアウト（60分）

---

# 9. ビルド（公開反映）

Owner が「公開反映」を押すと：

```
POST /owner/api/build?u=<username>&p=<projectname>
```

これが裏側で：

```
python export_json.py <username> <projectname>
```

を実行し、**public/<username>/<projectname>/** 以下を再生成。

ビルドは MVP では同期でOK。  
後でキュー化や非同期（バックグラウンドジョブ）にも移行できる設計。

---

# 10. 将来の拡張性（想定済み）

- 画像の署名URLアップロード（S3/R2）  
- フルテキスト検索（lunr.js / fuse.js）  
- プロジェクトのインポート・エクスポート  
- config.json の項目追加（見栄えの軽微なチューニングのみ）  
- 分割JSON（巨大化したら events-0001.json など）

---

# 🧩 後任へ一言まとめ

**あなたが継承する構造は「多テナント × 静的サイト生成」の極めて堅牢な形式です。**

- URL は **/<username>/<projectname>/**
- JSON は `export_json.py` が生成  
- HTML は JSON を読むだけ  
- オーナーは **自分のプロジェクトを自由に増やし編集**できる  
- オペレーターは **テナント発行と監査のみ**  
- DB は **非公開領域**に置き、公開は静的ファイルのみ  
- 見栄え編集は基本 **config.json の最小つまみだけ**  
- 構造はシンプルで壊れにくく、拡張余地も確保されている  

**この構成のまま拡張すれば、SaaS としての長期運用に耐えます。**

---

***

# 🟦 多テナントSSG SaaS — プラットフォーム設計（後任向け・続き）

このサービスは  
**「SQLite → JSON変換 → 静的公開」**  
という超堅牢アーキテクチャを採用しているため、プラットフォーム選定の基準は以下に集約される：

*   **公開配信が静的ファイルで高速・安価**
*   **認証は Cloudflare Access を前段に置く（システム側に Auth を持たない）**
*   **Owner/Operator Console の API は軽い（Workers で十分）**
*   **ビルド（export\_json.py）は Python 前提 → CI で回す方が安定**
*   **DB は非公開領域に保持（公開ツリーには出さない）**

この条件を満たしつつ、無料〜超低額で維持できる構成として、  
**Cloudflare を中心に据える**のが最適解。

***

# 🟩 1. 全体像（Cloudflare 中心の構成）

    ┌──────────────────────────────┐
    │        Cloudflare Access      │ ← 認証（Owner/Operator Console 前段）
    └───────────────┬──────────────┘
                    │
            ┌───────▼────────┐
            │ Owner Console    │ （Workers / Pages / 外部Host どれでも）
            └───────┬────────┘
                    │ API (CRUD / ロック)
            ┌───────▼──────────┐
            │ Cloudflare Workers │ ← Owner API / operator API / locking
            └───────┬──────────┘
                    │ KV（編集ロック / メタ）
                    ▼
          ┌─────────────────┐
          │ Cloudflare KV    │
          └─────────────────┘

    ─── ビルド系（CI） ───────────────────────────

    GitHub Actions（無料）
      └─ export_json.py 実行
          └─ public/<username>/<projectname>/ を生成
              └─ Cloudflare Pages にデプロイ

    ────── 公開配信（静的）─────────────────────────

    Cloudflare Pages
      └─ public/<username>/<projectname>/index.html
      └─ data/*.json
      └─ image/

***

# 🟩 2. 採用基盤（Cloudflare）

## ■ 2-1. Cloudflare Pages（静的配信）

*   現在の GitHub Pages の **完全上位互換**
*   CDN/圧縮/キャッシュ/HTTP/2/3 が自動
*   無料枠で十分
*   `public/` をそのままデプロイするだけ
*   カスタムドメイン対応も簡単

**役割**

*   SaaS の「公開サイト」部分のみ担当
*   `/username/projectname/` ツリーを高速配信

***

## ■ 2-2. Cloudflare Access（認証）

Owner Console / Operator Console の前に置くだけで：

*   認証機能を内製せずに済む（ゼロ実装）
*   メールリンク・Passkey 対応
*   セッション1つ縛りとの相性も良い
*   多テナントでも関係なく運用が楽

***

## ■ 2-3. Cloudflare Workers（API層）

*   Owner Console の **保存・取得API**
*   `editing_state` 用の **ロック管理**
*   後々のバックグラウンド API もここで完結
*   無料枠でほぼ収まる

Workers のみでは Python をネイティブに動かせないため、  
**export\_json.py は CI 側で扱う（現状維持）** のが最適。

***

## ■ 2-4. Cloudflare KV（ロック/メタ情報）

*   `editing_state` の保持（TTL付き）
*   プロジェクト一覧のような軽量メタも置ける
*   料金極小
*   RDB 不要で管理が圧倒的に楽

***

# 🟩 3. ビルド（JSON生成）とCI

### ✔ 現行どおり、GitHub Actions で完了する

Cloudflare Workers は Python が動かない。  
よって、

*   \*\*ビルド（export\_json.py）\*\*は  
    → Cloudflare ではなく **GitHub Actions** で走らせる

*   成果物（public/）は  
    → Cloudflare Pages へデプロイ

これで「無料・高速・安全」のまま保てる。

***

# 🟩 4. DB の扱い（ローカル or Private）

当面これで十分：

    db/
      └─ <username>/
            └─ <projectname>.db

*   非公開領域（GitHub private repo や VPS/ローカル）で保持
*   SaaS の API 層には直接出さない
*   将来必要なら R2 に移行できるが **現段階は不要**

***

# 🟩 5. Owner Console / Operator Console のホスティング

どこでもいいが、最も自然なのは：

*   **Cloudflare Pages にホスト**
*   Access を前段に置く

あるいは：

*   ローカル FastAPI を継続しつつ
*   先に Workers API を完成させて徐々に移行

最終的には Workers API + Pages UI が従来型の SaaS らしい構成。

***

# 🟩 6. この Cloudflare 構成のメリット（後任向けまとめ）

*   **無料枠で余裕**
*   認証を作らないで済む
*   ロックは KV で実装が最も簡単
*   API を Workers で軽く作れる
*   データ生成は GitHub Actions で Python そのまま
*   Cloudflare Pages の CDN が最速
*   シンプルで壊れにくい
*   構成が少ないので後任も理解しやすい
*   徐々に強化できる（Queues, R2, Durable Objects）

特に：

> **公開は静的、編集はAPI、認証は前段で吸収、  
> PythonはCIで回す**

この 4 本柱により維持コスト・実装コストが極小になる。

***

# 🟩 7. 後任のための一言まとめ（プラットフォーム編）

**当サービスは Cloudflare を中核に構築されています。**

*   公開配信は **Cloudflare Pages**
*   API 層は **Cloudflare Workers**
*   ロック等の軽量データは **Cloudflare KV**
*   認証は **Cloudflare Access**
*   ビルド（`export_json.py`）は **GitHub Actions** で実行
*   DB は非公開領域で保持

この構成は無料〜超安価で運用でき、  
多テナントSSG SaaSとしてシンプルかつ堅牢。  
将来拡張も Cloudflare 内で完結させられる。

***

