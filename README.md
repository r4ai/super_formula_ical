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

予選・決勝の詳細時刻が未発表の大会は、公式レースカレンダーの開催期間を
終日の暫定イベントとして登録します。詳細時刻の公開後は、時刻付きイベントへ
自動的に置き換わります。

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

公式ページの HTML は Lexbor HTML5 パーサで構文木に変換し、レースカードと
スケジュール表を DOM 構造から抽出します。

生成処理は `scripts/sf_calendar/` で責務ごとに分割しています。

- `website.py`: HTTP と公式サイト固有の DOM 構造をドメインモデルへ変換
- `generator.py`: サイト実装に依存しないイベント生成と時刻の正規化
- `ics.py`: イベントを RFC 5545 形式へ直列化
- `models.py`: 境界間で受け渡す不変なデータモデル

公式サイトのマークアップ変更は `website.py` と対応するパーサテストに閉じ込め、
イベント生成や ICS 出力へ波及させない構成です。

テスト:

```bash
uv run python -m unittest discover -s tests -v
```

毎週の自動更新では、生成差分を Copilot CLI でレビューします。レビュー応答が不正な場合は
1 回再試行し、同じ種類の確認事項が継続している場合は既存の open Issue に追記します。
