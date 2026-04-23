"""
pokeca-chart価格 × Snkrdunk在庫 チェッカー
- 価格: pokeca-chart.com から取得
- 在庫数(A素体/PSA10): Snkrdunk APIから取得
"""

import asyncio
import re
import json
import csv as csv_mod
import requests
from playwright.async_api import async_playwright

TOP_N = 100

# fallback_ids.csv から手動IDを読み込む
def load_fallback_ids():
    import os
    path = os.path.join(os.path.dirname(__file__), "fallback_ids.csv")
    if not os.path.exists(path):
        return {}
    result = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv_mod.DictReader(f):
            if row.get("slug") and row.get("snkrdunk_id"):
                result[row["slug"].strip()] = row["snkrdunk_id"].strip()
    return result

SNKRDUNK_ID_FALLBACK = load_fallback_ids()


def save_fallback_id(slug: str, snkrdunk_id: str, name: str):
    """新たに発見したIDをfallback_ids.csvに追記"""
    import os
    path = os.path.join(os.path.dirname(__file__), "fallback_ids.csv")
    existing = load_fallback_ids()
    if slug in existing:
        return
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv_mod.writer(f)
        writer.writerow([slug, snkrdunk_id, name])
    SNKRDUNK_ID_FALLBACK[slug] = snkrdunk_id
    print(f"    → fallback_ids.csvに保存: {slug} = {snkrdunk_id}")


def parse_price(text: str):
    nums = re.sub(r"[^\d]", "", text)
    return int(nums) if nums else None


async def get_top_card_links(page, top_n: int) -> list[dict]:
    """pokeca-chart mode=5 から上位N件のリンク・カード名を取得"""
    await page.goto("https://pokeca-chart.com/all-card?mode=5", wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(3)

    while True:
        cards = await page.query_selector_all(".cp_card")
        if len(cards) >= top_n:
            break
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)

    results = []
    for card in (await page.query_selector_all(".cp_card"))[:top_n]:
        rank_el = await card.query_selector(".category p")
        rank_text = (await rank_el.inner_text()).strip() if rank_el else ""
        rank = int(re.sub(r"[^\d]", "", rank_text)) if rank_text else 0

        link_el = await card.query_selector("a")
        href = await link_el.get_attribute("href") if link_el else ""

        results.append({"rank": rank, "url": href})

    return results


async def get_card_detail(page, url: str) -> dict:
    """
    pokeca-chartカード詳細ページから
    - カード名・美品価格・PSA10価格 (pokeca-chart価格)
    - Snkrdunk apparel ID
    を一括取得
    """
    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
    await asyncio.sleep(1)

    # カード名
    h1 = await page.query_selector("h1.entry-title")
    name = (await h1.inner_text()).strip() if h1 else url.split("/")[-1]

    # 価格テーブル (pokeca-chart)
    mint_price = None
    psa10_price = None
    tables = await page.query_selector_all("table")
    if tables:
        rows = await tables[0].query_selector_all("tr")
        if len(rows) >= 3:
            header_cells = await rows[0].query_selector_all("th, td")
            headers = [await c.inner_text() for c in header_cells]
            price_cells = await rows[2].query_selector_all("th, td")
            price_texts = [await c.inner_text() for c in price_cells]
            for i, h in enumerate(headers):
                if i < len(price_texts):
                    val = parse_price(price_texts[i])
                    if "美品" in h:
                        mint_price = val
                    elif "PSA10" in h or "PSA" in h:
                        psa10_price = val

    # Snkrdunk apparel ID（ページから取得、なければフォールバック辞書を参照）
    content = await page.content()
    ids = re.findall(r"snkrdunk\.com/apparels/(\d+)", content)
    card_slug = url.rstrip("/").split("/")[-1]
    snkrdunk_id = ids[0] if ids else SNKRDUNK_ID_FALLBACK.get(card_slug)

    return {
        "name": name,
        "mint_price": mint_price,
        "psa10_price": psa10_price,
        "snkrdunk_id": snkrdunk_id,
        "slug": card_slug,
    }



def search_snkrdunk_id(name: str, slug: str):
    """
    1. slugからproductNumberを構築してSnkrdunk APIで検索
    2. 見つからない場合はDuckDuckGoで「スニダン {name}」を検索してIDを取得
    """
    headers_api = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
    }

    # --- Step 1: productNumber検索 ---
    if slug:
        parts = slug.split("-")
        if len(parts) >= 3:
            num = parts[-2]
            set_code = "-".join(parts[:-2])
            product_num = f"pkmn-tcg-{set_code}-{num}"
            try:
                resp = requests.get(
                    "https://snkrdunk.com/v1/apparels",
                    params={"productNumber": product_num},
                    headers=headers_api,
                    timeout=8,
                )
                if resp.status_code == 200:
                    items = resp.json().get("apparels", [])
                    if items:
                        cid = str(items[0]["id"])
                        print(f"    productNumber検索「{product_num}」→ id={cid}")
                        return cid
            except Exception as e:
                print(f"    productNumber検索エラー: {e}")

    # --- Step 2: DuckDuckGo検索フォールバック ---
    try:
        query = f"スニダン {name}"
        ddg_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        headers_web = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ja-JP,ja;q=0.9",
        }
        resp = requests.get(ddg_url, headers=headers_web, timeout=10)
        ids = list(dict.fromkeys(re.findall(r"snkrdunk\.com/apparels/(\d+)", resp.text)))
        if ids:
            cid = ids[0]
            print(f"    DuckDuckGo検索「{query}」→ id={cid}")
            return cid
    except Exception as e:
        print(f"    DuckDuckGo検索エラー: {e}")

    return None


def _fetch_inventory(apparel_id: str, sale_only: bool) -> tuple[int, int]:
    """isSaleOnly の設定で在庫を取得し (a_count, psa10_count) を返す"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": f"https://snkrdunk.com/apparels/{apparel_id}/used",
    }
    sale_param = "true" if sale_only else "false"
    a_count = 0
    psa10_count = 0
    page_num = 1

    while True:
        url = (
            f"https://snkrdunk.com/v1/apparels/{apparel_id}/used"
            f"?perPage=100&page={page_num}&order=&withAllColors=false&isSaleOnly={sale_param}&conditionIds=-1"
        )
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            break
        items = resp.json().get("apparelUsedItems", [])
        if not items:
            break
        for item in items:
            cond = item.get("displayShortConditionTitle", "")
            if cond == "A":
                a_count += 1
            elif cond == "PSA10":
                psa10_count += 1
        if len(items) < 100:
            break
        page_num += 1

    return a_count, psa10_count


def get_snkrdunk_inventory(apparel_id: str) -> dict:
    """出品中のみ・売り切れ含む の両方を取得して返す"""
    a_active,   p10_active  = _fetch_inventory(apparel_id, sale_only=True)
    a_all,      p10_all     = _fetch_inventory(apparel_id, sale_only=False)
    return {
        "a_count":       a_active,    # 出品中のみ（希少性スコアに使用）
        "psa10_count":   p10_active,  # 出品中のみ（参考表示）
        "a_count_all":   a_all,       # 売り切れ含む（参考表示）
        "psa10_count_all": p10_all,   # 売り切れ含む（流動性スコアに使用）
    }


BUDGET = 1_000_000       # 運用予算
PSA10_HIT_RATE = 0.60   # PSA10獲得率（A素体から60%想定）
GRADING_COST = 12_000   # グレーディング費用


def calc_roi(mint: int, psa10: int) -> str:
    if not mint or not psa10:
        return "---"
    profit = psa10 - mint - GRADING_COST
    total_cost = mint + GRADING_COST
    roi = profit / total_cost * 100
    return f"{roi:+.0f}%"


def investment_judge(a_count: int, psa10_count: int) -> str:
    if a_count is None or psa10_count is None:
        return "  -"
    if a_count <= 10 and psa10_count >= 30:
        return "◎買い"
    elif a_count <= 30 and psa10_count >= 20:
        return "○検討"
    elif a_count > psa10_count * 1.5:
        return "△様子見"
    else:
        return "  -"


def calc_score(mint: int, psa10: int, a_count: int, psa10_count: int) -> float:
    """
    予算¥1,000,000ベースの期待利益スコア

    計算式:
      1枚あたりコスト = 美品価格 + グレーディング費¥12,000
      購入枚数       = floor(予算 / 1枚あたりコスト)
      1枚期待利益    = PSA10獲得率60% × (PSA10価格 - 美品価格) - ¥12,000
                       ※外れ時は美品価格が戻る前提（グレーディング費のみ損失）
      総期待利益     = 購入枚数 × 1枚期待利益

    希少性ボーナス: A在庫が少ないほど将来の値上がり期待として加算
    """
    if not mint or not psa10 or a_count is None or psa10_count is None:
        return -1

    cost_per_card = mint + GRADING_COST
    num_cards = BUDGET // cost_per_card
    if num_cards == 0:
        return -1

    # 1枚あたり期待利益
    expected_profit_per_card = PSA10_HIT_RATE * (psa10 - mint) - GRADING_COST

    # 総期待利益（メインスコア）
    total_expected = num_cards * expected_profit_per_card

    # 希少性ボーナス（A在庫が少ないほど +0〜20%上乗せ）
    if a_count <= 10:
        scarcity_bonus = 1.20
    elif a_count <= 30:
        scarcity_bonus = 1.15
    elif a_count <= 100:
        scarcity_bonus = 1.08
    elif a_count <= 300:
        scarcity_bonus = 1.03
    else:
        scarcity_bonus = 1.00

    # PSA10流動性ボーナス（売りやすさ）
    if psa10_count >= 500:
        liquidity_bonus = 1.10
    elif psa10_count >= 200:
        liquidity_bonus = 1.06
    elif psa10_count >= 100:
        liquidity_bonus = 1.03
    else:
        liquidity_bonus = 1.00

    return total_expected * scarcity_bonus * liquidity_bonus


async def main():
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print(f"[1/3] pokeca-chart ランキング取得中 (上位{TOP_N}件)...")
        card_links = await get_top_card_links(page, TOP_N)

        print(f"[2/3] 各カードの価格・SnkrdunkID取得中...")
        for i, card in enumerate(card_links, 1):
            detail = await get_card_detail(page, card["url"])

            # IDが見つからない場合はSnkrdunkを直接検索
            if not detail.get("snkrdunk_id"):
                print(f"  {i:>2}位 {detail['name'][:32]:<32} IDなし → Snkrdunk検索中...")
                found_id = search_snkrdunk_id(detail["name"], detail.get("slug", ""))
                if found_id:
                    detail["snkrdunk_id"] = found_id
                    save_fallback_id(detail.get("slug", ""), found_id, detail["name"])

            card.update(detail)
            sid = detail.get("snkrdunk_id") or "IDなし"
            mint = detail.get("mint_price")
            psa10 = detail.get("psa10_price")
            price_str = f"美品¥{mint:,} PSA10¥{psa10:,}" if mint and psa10 else "価格なし"
            print(f"  {i:>2}位 {detail['name'][:32]:<32} {price_str}  Snkrdunk={sid}")

        await browser.close()

    print(f"\n[3/3] Snkrdunk在庫数確認中...")
    for card in card_links:
        sid = card.get("snkrdunk_id")
        if not sid:
            card["a_count"] = None
            card["psa10_count"] = None
            continue
        try:
            inv = get_snkrdunk_inventory(sid)
            card.update(inv)
        except Exception as e:
            card["a_count"] = None
            card["psa10_count"] = None

    # [補完] 投資効率TOP30 / 総合スコアTOP30 で在庫未取得のカードを再検索
    def _roi(c):
        m, p = c.get("mint_price"), c.get("psa10_price")
        if not m or not p: return -999
        return (p - m - GRADING_COST) / (m + GRADING_COST)

    roi_top30 = sorted(
        [c for c in card_links if c.get("mint_price") and c.get("psa10_price")],
        key=_roi, reverse=True
    )[:30]

    for c in card_links:
        c["score"] = calc_score(c.get("mint_price"), c.get("psa10_price"),
                                c.get("a_count"), c.get("psa10_count"))
    score_top30 = sorted([c for c in card_links if c["score"] >= 0],
                         key=lambda x: x["score"], reverse=True)[:30]

    top30_ids = {id(c) for c in roi_top30} | {id(c) for c in score_top30}
    top30_missing = [c for c in card_links if id(c) in top30_ids and c.get("a_count") is None]

    if top30_missing:
        print(f"\n[補完] TOP30カードで在庫未取得: {len(top30_missing)}件 → 再検索")
        for card in top30_missing:
            name = card["name"]
            # 複数クエリで再試行
            found_id = None
            for query_name in [name, name.split("[")[0].strip()]:
                try:
                    q = f"スニダン {query_name}"
                    ddg_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(q)}"
                    resp = requests.get(ddg_url, headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                        "Accept-Language": "ja-JP,ja;q=0.9",
                    }, timeout=10)
                    ids = list(dict.fromkeys(re.findall(r"snkrdunk\.com/apparels/(\d+)", resp.text)))
                    if ids:
                        found_id = ids[0]
                        break
                except Exception:
                    pass
            if found_id:
                card["snkrdunk_id"] = found_id
                save_fallback_id(card.get("slug", ""), found_id, name)
                try:
                    inv = get_snkrdunk_inventory(found_id)
                    card.update(inv)
                    print(f"  ✓ {name[:35]}: A={inv['a_count']} PSA10={inv['psa10_count']}")
                except Exception:
                    print(f"  ✓ {name[:35]}: ID取得済み・在庫取得失敗")
            else:
                print(f"  ✗ {name[:35]}: 取得不可（手動追加が必要）")

    # 結果表示
    print(f"\n{'='*90}")
    print(f"{'カード名':<32} {'差額':>10} {'美品(pokeca)':>13} {'PSA10(pokeca)':>13} {'A在庫':>6} {'PSA10在庫':>9}  ROI   判定")
    print(f"{'-'*90}")

    for card in card_links:
        mint = card.get("mint_price")
        psa10 = card.get("psa10_price")
        diff = (psa10 - mint) if (mint and psa10) else None
        a_cnt = card.get("a_count")
        p10_cnt = card.get("psa10_count")

        diff_str = f"¥{diff:,}" if diff else "---"
        mint_str = f"¥{mint:,}" if mint else "---"
        psa10_str = f"¥{psa10:,}" if psa10 else "---"
        a_str = f"{a_cnt}件" if a_cnt is not None else "---"
        p10_str = f"{p10_cnt}件" if p10_cnt is not None else "---"
        roi_str = calc_roi(mint, psa10) if mint and psa10 else "---"
        judge = investment_judge(a_cnt, p10_cnt)

        print(
            f"{card['name']:<32} "
            f"{diff_str:>10} "
            f"{mint_str:>13} "
            f"{psa10_str:>13} "
            f"{a_str:>6} "
            f"{p10_str:>9}  "
            f"{roi_str:<6} {judge}"
        )
        results.append(card)

    # おすすめランキング（スコア順）
    print(f"\n{'='*105}")
    print("【★ おすすめ投資ランキング（予算¥100万ベース・スコア順）★】")
    print(f"  {'推奨':>3} {'カード名':<32} {'A在庫':>6} {'PSA10在庫':>9} {'購入枚数':>5} {'美品価格':>12} {'PSA10価格':>12} {'差額':>10} {'ROI':>7}  判定  期待利益")
    print(f"  {'-'*102}")

    for r in results:
        r["score"] = calc_score(
            r.get("mint_price"), r.get("psa10_price"),
            r.get("a_count"), r.get("psa10_count")
        )

    ranked = [r for r in results if r["score"] >= 0]
    ranked.sort(key=lambda x: x["score"], reverse=True)

    for i, r in enumerate(ranked, 1):
        mint = r.get("mint_price")
        psa10 = r.get("psa10_price")
        diff = psa10 - mint if mint and psa10 else 0
        roi = calc_roi(mint, psa10)
        a_cnt = r.get("a_count")
        p10_cnt = r.get("psa10_count")
        cost_per = (mint + GRADING_COST) if mint else 0
        num_cards = BUDGET // cost_per if cost_per else 0
        a_str = f"{a_cnt}件" if a_cnt is not None else "---"
        p10_str = f"{p10_cnt}件" if p10_cnt is not None else "---"
        mint_str = f"¥{mint:,}" if mint else "---"
        psa10_str = f"¥{psa10:,}" if psa10 else "---"
        judge = investment_judge(a_cnt, p10_cnt)
        score_万 = int(r["score"] / 10000)
        print(
            f"  {i:>3}位 {r['name'][:32]:<32} "
            f"{a_str:>6} {p10_str:>9} {num_cards:>4}枚 "
            f"{mint_str:>12} {psa10_str:>12} "
            f"¥{diff:>9,} {roi:>7}  {judge}  ¥{score_万}万"
        )

    with open("snkrdunk_inventory.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n保存: snkrdunk_inventory.json")


if __name__ == "__main__":
    asyncio.run(main())
