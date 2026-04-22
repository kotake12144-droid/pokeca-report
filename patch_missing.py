"""
patch_missing.py
fallback_ids.csv に追記した新しいIDだけ在庫を即時取得して
snkrdunk_inventory.json を更新し、report.html を再生成する

使い方:
  python3 patch_missing.py          # 未取得カードのみ取得
  python3 patch_missing.py --force  # fallback_ids.csv 全件を強制再取得
"""

import csv, json, os, subprocess, sys

INVENTORY_JSON = os.path.join(os.path.dirname(__file__), "snkrdunk_inventory.json")
FALLBACK_CSV   = os.path.join(os.path.dirname(__file__), "fallback_ids.csv")


def load_fallback_ids():
    if not os.path.exists(FALLBACK_CSV):
        return {}
    result = {}
    with open(FALLBACK_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("slug") and row.get("snkrdunk_id"):
                result[row["slug"].strip()] = {
                    "snkrdunk_id": row["snkrdunk_id"].strip(),
                    "name":        row.get("name", "").strip(),
                }
    return result


def load_inventory():
    if not os.path.exists(INVENTORY_JSON):
        return []
    with open(INVENTORY_JSON, encoding="utf-8") as f:
        return json.load(f)


def fetch_inventory(apparel_id: str) -> dict:
    sys.path.insert(0, os.path.dirname(__file__))
    from snkrdunk_inventory import _fetch_inventory
    a_active,  p10_active = _fetch_inventory(apparel_id, sale_only=True)
    a_all,     p10_all    = _fetch_inventory(apparel_id, sale_only=False)
    return {
        "a_count":         a_active,
        "psa10_count":     p10_active,
        "a_count_all":     a_all,
        "psa10_count_all": p10_all,
    }


def main():
    force = "--force" in sys.argv
    fallback  = load_fallback_ids()
    inventory = load_inventory()

    # snkrdunk_id → インデックス のマップ（IDで照合するのが確実）
    id_to_idx = {
        str(c.get("snkrdunk_id")): i
        for i, c in enumerate(inventory)
        if c.get("snkrdunk_id")
    }

    patched = []

    for slug, info in fallback.items():
        sid  = info["snkrdunk_id"]
        label = info["name"] or slug

        if sid in id_to_idx and not force:
            idx = id_to_idx[sid]
            card = inventory[idx]
            # 在庫データが揃っていればスキップ
            if card.get("a_count") is not None and card.get("a_count_all") is not None:
                print(f"[skip]  {card.get('name', label)} は在庫データ済み")
                continue
            # データ不完全 → 再取得
            print(f"[patch] {card.get('name', label)} (sid={sid}) 在庫取得中...")
            inv_data = fetch_inventory(sid)
            inventory[idx].update(inv_data)
            patched.append(card.get("name", label))

        elif sid in id_to_idx and force:
            idx = id_to_idx[sid]
            card = inventory[idx]
            print(f"[force] {card.get('name', label)} (sid={sid}) 強制再取得中...")
            inv_data = fetch_inventory(sid)
            inventory[idx].update(inv_data)
            patched.append(card.get("name", label))

        else:
            # JSON に存在しない → 新規エントリ追加
            print(f"[new]   {label} (sid={sid}) 在庫取得中...")
            inv_data = fetch_inventory(sid)
            new_entry = {
                "rank":        None,
                "url":         f"https://pokeca-chart.com/{slug}",
                "name":        info["name"],
                "snkrdunk_id": sid,
            }
            new_entry.update(inv_data)
            inventory.append(new_entry)
            id_to_idx[sid] = len(inventory) - 1
            patched.append(info["name"] or slug)

    if not patched:
        print("パッチ対象なし（全IDは既に在庫データ済み）")
        print("強制再取得するには: python3 patch_missing.py --force")
        return

    # JSON 保存
    with open(INVENTORY_JSON, "w", encoding="utf-8") as f:
        json.dump(inventory, f, ensure_ascii=False, indent=2)
    print(f"\n✓ snkrdunk_inventory.json 更新 ({len(patched)}件: {', '.join(patched)})")

    # HTML 再生成
    script = os.path.join(os.path.dirname(__file__), "report_html.py")
    result = subprocess.run(
        [sys.executable, script],
        capture_output=True, text=True,
        cwd=os.path.dirname(__file__)
    )
    if result.returncode == 0:
        print("✓ report.html 再生成完了")
    else:
        print("✗ report_html.py エラー:")
        print(result.stderr)


if __name__ == "__main__":
    main()
