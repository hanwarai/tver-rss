# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

TVer（日本の見逃し配信サービス）のシリーズ番組から Atom フィードを生成し、GitHub Pages (`https://hanwarai.github.io/tver-rss/`) で公開するスクリプト。`main.py` という単一ファイルのジェネレータで、GitHub Actions が毎日 00:00 UTC に再ビルド → デプロイする。

## コマンド

Python は 3.13 系固定 (`pyproject.toml` / `.python-version`)、依存は uv で管理。

```bash
uv sync                     # 依存インストール (本番 CI も同じ。PR チェックだけ --locked 付き)
uv run main.py              # フィード生成: feeds/*.xml と feeds/index.html を出力
SSL_VERIFY=False uv run main.py   # 社内プロキシ等で自己署名証明書しか通らない環境用
```

テストスイートは存在しない。ローカルでの動作確認は `uv run main.py` を走らせて `feeds/` 配下の XML が壊れていないかで見る。

PR に対しては `.github/workflows/pr-check.yaml` がネットワーク非依存の軽量チェックだけ走らせる（`uv sync --locked` と `import main`）。TVer API を叩く実フィード生成は PR では検証されないので、main.py のロジックを変えた場合はローカルで `uv run main.py` を回すこと。

## フィードの追加・削除

`feed.csv` を編集するだけで `main.py` 側の変更は不要。

- 形式: `series_id,表示タイトル` の1行1シリーズ（CSVヘッダなし）
- `series_id` は TVer のシリーズページ URL `https://tver.jp/series/<series_id>` の末尾
- 第2カラム（表示タイトル）は `main.py` からは読まれず、人間が CSV を読むときの注釈用。フィード名もトップページの一覧名も全て TVer API の `series.title` から取る

## アーキテクチャ（`main.py` の流れ）

TVer は3つのホストにわたって API を叩かないと番組情報が揃わないので、この順序が肝。

1. **セッション発行** — `platform-api.tver.jp/v2/api/platform_users/browser/create` に POST して `platform_uid` / `platform_token` を取る。これは後段のエピソード API 認証に必須。
2. **シリーズ → シーズン → エピソード** を `feed.csv` の各行ごとにたどる:
   - `statics.tver.jp/content/series/<id>.json` — シリーズの title / description / share.url（フィードヘッダ用）
   - `service-api.tver.jp/api/v1/callSeriesSeasons/<id>` — シーズン一覧。`x-tver-platform-type: web` ヘッダが必要
   - `platform-api.tver.jp/service/api/v1/callSeasonEpisodes/<season_id>?platform_uid=...&platform_token=...` — シーズン内のエピソード
   - `statics.tver.jp/content/episode/<id>.json` — 個別エピソードの放送日ラベル等
3. `type == 'episode'` 以外（予告編など）は捨てる。
4. `feedgenerator.Atom1Feed` を組み立てて `feeds/<series_id>.xml` に書き出し。
5. 成功したシリーズを `rendered_feeds` に溜め、Jinja2 で `templates/index.html` を `feeds/index.html` にレンダリングしてトップページを生成。

`feeds/*.xml` は `.gitignore` 対象（`/feeds/*.xml`）なので commit されない。Actions ランナー上で生成したものを `actions/upload-pages-artifact` が直接 Pages にアップする。リポジトリに tracked なのは `feeds/.gitkeep` と `feeds/index.html` のみ（`index.html` は CI で毎回上書き生成されるので、git 上のコピーは単なるスナップショット）。

## CI / デプロイ

ワークフローは 2 本。

### `.github/workflows/pr-check.yaml` — PR 時の軽量チェック

- トリガー: `main` 宛の `pull_request`
- `uv sync --locked` で `pyproject.toml` と `uv.lock` の齟齬を検知し、`uv run --no-sync python -c "import main"` で import が通るかだけ見る
- **ネットワーク（TVer API）は叩かない。** `main.py` は実処理が `if __name__ == '__main__'` ガード内にあるので import しても外部通信は発生しない
- 主目的は Dependabot の依存更新をブラインドで merge しないこと。`Resolve uv version` ステップが本番と同一なので、uv ピンの読み取り方式が壊れれば PR 時点で赤くなる

### `.github/workflows/gh-pages.yaml` — 本番ビルドとデプロイ

- トリガー: `main` への push と毎日 00:00 UTC の cron
- `uv run main.py` を実行し `feeds/` を `actions/upload-pages-artifact` で Pages にデプロイ
- 手動で `feeds/` を更新する必要は通常ない。新しいシリーズを追加したら `feed.csv` を commit するだけで Actions がそのうち反映する（即時反映したければ main に push する）

## トップページの `/feed subscribe` ボタン

`templates/index.html` の各行にある「/feed subscribe」ボタンは Discord RSS bot 用のコマンド文字列 (`/feed subscribe https://hanwarai.github.io/tver-rss/<id>.xml`) をクリップボードにコピーする UI。用途を知らずに見ると不可解なので触る前に確認。

## 既存コミットの慣例

- プレフィックス: `fix:` / `ci:` / `feat:` を日本語本文と併用（例: `fix: スクレイピングするファイルを完全に間違えていた`）
- Dependabot は `ci:` プレフィックスで PR を作る設定（`.github/dependabot.yml`）
