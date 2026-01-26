# ai-change-watcher
# ai-change-watcher

AIプラットフォーム変更監視 → RSS配信（GitHub Pages）

- `run_multi.py`：取得 / 正規化 / 差分検知 / `state.json` 更新
- `generate_rss.py`：`state.json` → `feed.xml`（Important）/ `feed_all.xml`（All）生成
- `targets.py`：監視対象URL（TARGETS）

## ローカル実行（推奨：Python 3.13 + venv）

このプロジェクトはローカルで **Python 3.13.x** を推奨します（OpenSSL環境で安定運用するため）。

### 初回セットアップ

```bash
# プロジェクト直下で
/usr/local/bin/python3.13 -m venv .venv
source .venv/bin/activate

python -m pip install -U pip
pip install -r requirements.txt
```

### 通常の実行

```bash
# プロジェクト直下で
source .venv/bin/activate
python run_multi.py
python generate_rss.py
```

### 依存の追加・更新

```bash
source .venv/bin/activate
pip install <package>

# 必要に応じて requirements.txt を更新
pip freeze > requirements.lock.txt
```

## 環境確認（トラブル時）

```bash
python --version
python -c "import ssl; print(ssl.OPENSSL_VERSION)"
python -c "import urllib3; print(urllib3.__version__)"
```

## 注意（運用）

- `.venv/` はコミットしない（`.gitignore` 推奨）
- RSS/Atom と OpenAPI YAML は `targets.py` の `normalize` で正規化してノイズを抑えています
