def guess_base_url() -> str:
    """RSS の <channel><link> に使う base URL を決める。

    優先順位:
      1) SITE_URL 環境変数（最優先。ローカル再生成で Pages URL を汚染しないため）
      2) GitHub Actions の GITHUB_REPOSITORY=owner/repo から Pages URL を推測
      3) ローカル開発の既定 http://localhost/
    """

    # 1) 明示指定（最優先）
    site = (os.environ.get("SITE_URL") or "").strip()
    if site:
        return site.rstrip("/") + "/"

    # 2) GitHub Actions では GITHUB_REPOSITORY=owner/repo が入る
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if repo and "/" in repo:
        owner, name = repo.split("/", 1)
        return f"https://{owner}.github.io/{name}/"

    # 3) ローカル開発の既定
    return "http://localhost/"
