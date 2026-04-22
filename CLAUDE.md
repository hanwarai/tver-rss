# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

TVer（日本の見逃し配信サービス）のシリーズ番組から Atom フィードを生成し、GitHub Pages (`https://hanwarai.github.io/tver-rss/`) で公開するスクリプト。`main.py` という単一ファイルのジェネレータで、GitHub Actions が毎日 00:00 UTC に再ビルド → デプロイする。

## コマンド

Python は 3.13 系固定 (`pyproject.toml` / `.python-version`)、依存は uv で管理。

```bash
uv sync                     # 依存インストール (CI は --all-extras 付き)
uv run main.py              # フィード生成: feeds/*.xml と feeds/index.html を出力
SSL_VERIFY=False uv run main.py   # 社内プロキシ等で自己署名証明書しか通らない環境用
```

テストスイート・lint 設定は存在しない。動作確認は `uv run main.py` を走らせて `feeds/` 配下の XML が壊れていないかで見る。

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

## デプロイ

`.github/workflows/gh-pages.yaml` が担う:

- トリガー: `main` への push と毎日 00:00 UTC の cron
- `uv run main.py` を実行し `feeds/` を `actions/upload-pages-artifact` で Pages にデプロイ
- 手動で `feeds/` を更新する必要は通常ない。新しいシリーズを追加したら `feed.csv` を commit するだけで Actions がそのうち反映する（即時反映したければ main に push する）

## トップページの `/feed subscribe` ボタン

`templates/index.html` の各行にある「/feed subscribe」ボタンは Discord RSS bot 用のコマンド文字列 (`/feed subscribe https://hanwarai.github.io/tver-rss/<id>.xml`) をクリップボードにコピーする UI。用途を知らずに見ると不可解なので触る前に確認。

## 既存コミットの慣例

- プレフィックス: `fix:` / `ci:` / `feat:` を日本語本文と併用（例: `fix: スクレイピングするファイルを完全に間違えていた`）
- Dependabot は `ci:` プレフィックスで PR を作る設定（`.github/dependabot.yml`）

## 自動 PR レビュー

`.github/workflows/claude.yml` が人間の作成する PR に対して Claude Code による review を自動実行する。Dependabot PR は `github.actor != 'dependabot[bot]'` で除外（trivial bump の review に subscription quota を食わせないため）。

Review 観点は workflow 内の `prompt:` に直書きしてあるので、方針を変えるときはそこを編集。認証は `CLAUDE_CODE_OAUTH_TOKEN` secret（`claude setup-token` で発行したリポジトリオーナーの OAuth トークン）。
