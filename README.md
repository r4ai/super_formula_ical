# SUPER FORMULA iCal

SUPER FORMULA 2025 の予選・決勝スケジュールを iCalendar (.ics) 形式で提供します。Google カレンダーや Apple カレンダーなどに取り込んで、レース日程を管理できます。

## カレンダーファイル

生成済みの iCal ファイル: [`superformula_2025.ics`](./superformula_2025.ics)

収録イベント:

- 予選 (Q1 Gr.A / Q1 Gr.B / Q2)
- 決勝レース

## カレンダーへのインポート方法

### Google カレンダー

1. [Google カレンダー](https://calendar.google.com/) を開く
2. 画面右上の歯車アイコン → **「設定」** をクリック
3. 左メニューの **「インポートとエクスポート」** をクリック
4. **「ファイルを選択」** から `superformula_2025.ics` を選択
5. インポート先のカレンダーを選択して **「インポート」** をクリック

または、ファイルをダウンロードして `.ics` ファイルをダブルクリックすると、既定のカレンダーアプリが起動してインポートが促される場合があります。

### Apple カレンダー (macOS / iOS)

**macOS:**

1. `superformula_2025.ics` をダウンロード
2. ファイルをダブルクリック（または Finder からカレンダー.app へドラッグ）
3. インポートの確認ダイアログで **「インポート」** をクリック

**iOS (iPhone / iPad):**

1. `superformula_2025.ics` を iPhone / iPad へ転送（AirDrop、メール添付、Files アプリなど）
2. ファイルをタップ → **「カレンダーに追加」** をタップ
3. 確認画面で **「すべてのイベントを追加」** をタップ

### Microsoft Outlook

1. `superformula_2025.ics` をダウンロード
2. ファイルをダブルクリックすると Outlook が起動してインポートの確認が表示される
3. **「カレンダーに追加」** または **「インポート」** をクリック

または、Outlook メニューの **「ファイル」→「開く/エクスポート」→「インポート/エクスポート」** からウィザードを使ってインポートすることもできます。

## ICS ファイルの生成 (開発者向け)

スクリプトを実行すると、SUPER FORMULA 公式サイトからスケジュールを取得して ICS ファイルを生成します。

### 必要環境

- Python 3.8 以上

### 実行方法

```bash
python scripts/superformula_2025_to_ics.py > superformula_2025.ics
```

生成された `superformula_2025.ics` を上記の方法でカレンダーアプリへインポートしてください。

## ライセンス

This project is provided as-is. Race schedule data is sourced from the [SUPER FORMULA official website](https://superformula.net/sf3/).
