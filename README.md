# super_formula_ical

SUPER FORMULA のレーススケジュール（予選・決勝）を Google Calendar などに取り込むための ICS カレンダーです。

## Google Calendar に登録する

1. [Google Calendar](https://calendar.google.com) を開く
2. 左サイドバーの「他のカレンダー」横の `+` をクリック
3. 「URL で登録」を選択
4. 以下の URL を入力して「カレンダーを追加」をクリック

```
https://raw.githubusercontent.com/r4ai/super_formula_ical/main/superformula.ics
```

URL で登録するとスケジュールの更新が自動的に反映されます。

## Apple カレンダーに登録する（iPhone / Mac）

1. Safari で以下の URL を開く
2. 「カレンダーに登録」のダイアログが表示されたら「登録」をタップ／クリック

```
https://raw.githubusercontent.com/r4ai/super_formula_ical/main/superformula.ics
```

または、Mac のカレンダーアプリから「ファイル」→「新規カレンダー登録」で上記 URL を入力しても登録できます。

URL で登録するとスケジュールの更新が自動的に反映されます。

## 開発者向け

### ICS ファイルの生成

依存関係のインストール:

```bash
uv sync
```

ICS ファイルの生成:

```bash
uv run python scripts/superformula_to_ics.py 2025 2026 > superformula.ics
```
