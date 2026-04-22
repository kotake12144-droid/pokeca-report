"""
sync_from_sheets.py
Google スプレッドシートから fallback_ids.csv を同期して
新しいIDだけ在庫を即時取得 → report.html 再生成

使い方:
  1. SHEET_ID を下記に設定（スプレッドシートURLの /d/〇〇〇/ の部分）
  2. python3 sync_from_sheets.py
"""

import csv, io, os, subprocess, sys
import requests

# ─────────────────────────────────────────
# ★ここにスプレッドシートのIDを貼る
#   URL: https://docs.google.com/spreadsheets/d/★ここ★/edit
SHEET_ID = "1REyoQJVnQy9XgKC911RYf_KBaCuCzmV6laTjIPlBv64"
# ─────────────────────────────────────────

FALLBACK_CSV = os.path.join(os.path.dirname(__file__), "fallback_ids.csv")


def fetch_sheet_as_csv(sheet_id: str) -> list[dict]:
    """Google シートをCSV形式で取得してリストで返す"""
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Sheet1"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    reader = csv.DictReader(io.StringIO(resp.text))
    rows = []
    for row in reader:
        slug = row.get("slug", "").strip()
        sid  = row.get("snkrdunk_id", "").strip()
        if slug and sid:
            rows.append({
                "slug":         slug,
                "snkrdunk_id":  sid,
                "name":         row.get("name", "").strip(),
            })
    return rows


def load_local_csv() -> dict:
    """ローカル fallback_ids.csv を slug→行 の辞書で返す"""
    if not os.path.exists(FALLBACK_CSV):
        return {}
    result = {}
    with open(FALLBACK_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("slug"):
                result[row["slug"].strip()] = row
    return result


def save_local_csv(rows: list[dict]):
    with open(FALLBACK_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["slug", "snkrdunk_id", "name"])
        w.writeheader()
        w.writerows(rows)


def main():
    if not SHEET_ID:
        print("エラー: SHEET_ID が設定されていません")
        print(f"  {__file__} を開いて SHEET_ID を貼ってください")
        print("  URL例: https://docs.google.com/spreadsheets/d/1BxiM.../edit")
        print("                                                    ↑ここ")
        sys.exit(1)

    print("Google スプレッドシートからデータ取得中...")
    try:
        sheet_rows = fetch_sheet_as_csv(SHEET_ID)
    except requests.HTTPError as e:
        if e.response.status_code == 403:
            print("エラー: シートへのアクセス権がありません")
            print("  スプレッドシートの共有設定を")
            print("  「リンクを知っている全員が閲覧可能」に変更してください")
        else:
            print(f"エラー: {e}")
        sys.exit(1)

    print(f"  シートから {len(sheet_rows)} 件取得")

    local = load_local_csv()
    new_slugs = []

    for row in sheet_rows:
        slug = row["slug"]
        if slug not in local:
            new_slugs.append(slug)
            print(f"  [新規] {row['name'] or slug}  (snkrdunk_id={row['snkrdunk_id']})")
        elif local[slug].get("snkrdunk_id") != row["snkrdunk_id"]:
            print(f"  [更新] {row['name'] or slug}  ID変更: {local[slug].get('snkrdunk_id')} → {row['snkrdunk_id']}")

    # シートの内容でCSV全体を上書き（シートがマスターデータ）
    save_local_csv(sheet_rows)
    print(f"✓ fallback_ids.csv を更新 ({len(sheet_rows)} 件)")

    if not new_slugs:
        print("\n新規カードなし。在庫取得をスキップします。")
        print("強制再取得するには: python3 patch_missing.py --force")
        return

    # patch_missing.py を呼んで新規カードの在庫を即時取得
    print(f"\n新規 {len(new_slugs)} 件の在庫を取得します...")
    script = os.path.join(os.path.dirname(__file__), "patch_missing.py")
    result = subprocess.run(
        [sys.executable, script],
        cwd=os.path.dirname(__file__)
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
