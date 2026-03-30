# super_formula_ical

SUPER FORMULA のレーススケジュール（予選・決勝）を Google Calendar などに取り込むための ICS カレンダーです。

## カレンダーの登録方法

URL で登録すると、スケジュールの更新が自動的に反映されます。

### Google Calendar

1. [Google Calendar](https://calendar.google.com) を開く
2. 左サイドバーの「他のカレンダー」横の `+` をクリック
3. 「URL で登録」を選択
4. 以下の URL を入力して「カレンダーを追加」をクリック

```
https://raw.githubusercontent.com/r4ai/super_formula_ical/main/superformula.ics
```

### Apple カレンダー（iPhone / Mac）

上記 URL を Safari で開くか、「ファイル」→「新規カレンダー登録」から URL を入力してください。

### ICS ファイルを直接ダウンロード

自動更新は不要な場合、`superformula.ics` を直接ダウンロードしてカレンダーアプリにインポートできます。

## ローカルでの実行（開発者向け）

依存関係のインストール:

```bash
uv sync
```

ICS ファイルの生成:

```bash
uv run python scripts/superformula_to_ics.py 2025 2026 > superformula.ics
```
