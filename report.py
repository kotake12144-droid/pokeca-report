"""
総合評価レポート生成
pokeca_scan × snkrdunk_inventory を掛け合わせてスコアリング
"""

import csv, json, glob, os

GRADING       = 12_000
BUDGET        = 1_000_000
PSA10_HIT_RATE = 0.60


def calc_exp_profit(mint, psa10, a_count):
    """pokeca価格 + 在庫数から期待利益を計算（JSONスコア欠損時のフォールバック）"""
    if not mint or not psa10:
        return None
    cost_per_card = mint + GRADING
    num_cards = BUDGET // cost_per_card
    if num_cards == 0:
        return None
    exp_per_card = PSA10_HIT_RATE * (psa10 - mint) - GRADING
    total = num_cards * exp_per_card
    if a_count is None:
        return total
    if   a_count <=  10: return total * 1.20
    elif a_count <=  30: return total * 1.15
    elif a_count <= 100: return total * 1.08
    elif a_count <= 300: return total * 1.03
    else:                return total


# ──────────────────────────────────────────
# データ読み込み
# ──────────────────────────────────────────
def load_pokeca():
    files = sorted(glob.glob("pokeca_scan_*.csv"), reverse=True)
    if not files:
        raise FileNotFoundError("pokeca_scan_*.csv が見つかりません")
    path = files[0]
    print(f"[pokeca] {os.path.basename(path)}")
    cards = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cards[row["name"]] = {
                "rank":   int(row["rank"]),
                "mint":   int(row["mint_price"]),
                "psa10":  int(row["psa10_price"]),
                "diff":   int(row["diff"]),
            }
    return cards


def load_inventory():
    with open("snkrdunk_inventory.json", encoding="utf-8") as f:
        items = json.load(f)
    inv = {}
    for c in items:
        if c.get("name"):
            inv[c["name"]] = {
                "a_count":         c.get("a_count"),       # 出品中のみ → 希少性スコアC
                "psa10_count":     c.get("psa10_count"),   # 出品中のみ → 参考表示
                "a_count_all":     c.get("a_count_all"),   # 売り切れ含む → 参考表示
                "psa10_count_all": c.get("psa10_count_all"), # 売り切れ含む → 流動性スコアD
                "snkr_score":      c.get("score"),
            }
    return inv


# ──────────────────────────────────────────
# 採点基準（100点満点）
# ──────────────────────────────────────────
# A. PSA10差額（30点）: グレーディング後の利益ポテンシャル絶対値
def score_diff(diff):
    if   diff >= 300_000: return 30
    elif diff >= 100_000: return 25
    elif diff >=  50_000: return 20
    elif diff >=  20_000: return 15
    elif diff >=  10_000: return 10
    elif diff >=   5_000: return  5
    else:                 return  2

# B. ROI（25点）: (PSA10 - 美品 - グレード費) / (美品 + グレード費)
def score_roi(mint, psa10):
    cost = mint + GRADING
    roi  = (psa10 - mint - GRADING) / cost * 100
    if   roi >= 150: return 25
    elif roi >= 100: return 21
    elif roi >=  50: return 16
    elif roi >=  20: return 11
    elif roi >=   0: return  6
    else:            return  0

# C. A素体希少性（20点）: 出品中のみの在庫数（現在仕入れられる数）
def score_a(a):
    if a is None:   return  5   # データなし → 中間値
    if   a <=   5:  return 20
    elif a <=  15:  return 16
    elif a <=  30:  return 12
    elif a <= 100:  return  8
    elif a <= 200:  return  4
    else:           return  0

# D. PSA10流動性（15点）: 200〜500件が最適、多すぎると飽和・競合過多で減点
def score_p10(p):
    if p is None:    return  5   # データなし → 中間値
    if   p >= 2000:  return  3   # 飽和・競合過多
    elif p >= 1000:  return  7   # やや多め
    elif p >=  500:  return 12   # 適量
    elif p >=  200:  return 15   # 最適帯
    elif p >=   50:  return 10   # やや薄い
    else:            return  4   # 市場薄い

# E. pokeca-chartランク（10点）: 高騰注目度
def score_rank(rank):
    if   rank <=  10: return 10
    elif rank <=  20: return  8
    elif rank <=  30: return  6
    elif rank <=  50: return  4
    elif rank <=  70: return  2
    else:             return  0


CRITERIA = """
╔════════════════════════════════════════════════════════════════════════════╗
║                総合評価 採点基準（100点満点）                              ║
╠══════╦════════════════════╦═════╦════════════════════════════════════════╣
║ 指標 ║ 内容               ║ 配点║ 点数の目安                             ║
╠══════╬════════════════════╬═════╬════════════════════════════════════════╣
║  A   ║ PSA10差額          ║  30 ║ ≥¥300k:30 / ≥¥100k:25 / ≥¥50k:20     ║
║      ║ （利益ポテンシャル）║     ║ ≥¥20k:15 / ≥¥10k:10 / ≥¥5k:5        ║
╠══════╬════════════════════╬═════╬════════════════════════════════════════╣
║  B   ║ ROI                ║  25 ║ ≥150%:25 / ≥100%:21 / ≥50%:16         ║
║      ║ （投資収益率）      ║     ║ ≥20%:11 / ≥0%:6 / マイナス:0          ║
╠══════╬════════════════════╬═════╬════════════════════════════════════════╣
║  C   ║ A素体希少性        ║  20 ║ ≤5件:20 / ≤15件:16 / ≤30件:12         ║
║      ║ ★出品中のみ        ║     ║ ≤100件:8 / ≤200件:4 / 200件超:0       ║
╠══════╬════════════════════╬═════╬════════════════════════════════════════╣
║  D   ║ PSA10流動性        ║  15 ║ 200-499件:15 / 500-999件:12 / 50-199件:10║
║      ║ ★売り切れ含む累計  ║     ║ 1000-1999件:7 / <50件:4 / ≥2000件:3   ║
╠══════╬════════════════════╬═════╬════════════════════════════════════════╣
║  E   ║ 注目トレンド       ║  10 ║ 1-10位:10 / 11-20位:8 / 21-30位:6     ║
║      ║ （pokecaランク）   ║     ║ 31-50位:4 / 51-70位:2 / 71位以降:0    ║
╚══════╩════════════════════╩═════╩════════════════════════════════════════╝
※ C希少性=今日仕入れられるA素体の出品中数  D流動性=PSA10の過去取引含む市場規模
※ データ未取得項目（C・D）はそれぞれ5点（中間値）で補完
"""


def roi_str(mint, psa10):
    roi = (psa10 - mint - GRADING) / (mint + GRADING) * 100
    return f"{roi:+.0f}%"


def fmt(v, prefix="¥"):
    if v is None: return "---"
    return f"{prefix}{v:,}"


# ──────────────────────────────────────────
# メイン
# ──────────────────────────────────────────
def main():
    pokeca = load_pokeca()
    inv    = load_inventory()

    # マージ
    records = []
    for name, p in pokeca.items():
        i = inv.get(name, {})
        s_diff = score_diff(p["diff"])
        s_roi  = score_roi(p["mint"], p["psa10"])
        s_a    = score_a(i.get("a_count"))            # 出品中のみ → 希少性
        s_p10  = score_p10(i.get("psa10_count_all"))  # 売り切れ含む → 流動性
        s_rank = score_rank(p["rank"])
        total  = s_diff + s_roi + s_a + s_p10 + s_rank
        records.append({
            "name":            name,
            "rank":            p["rank"],
            "mint":            p["mint"],
            "psa10":           p["psa10"],
            "diff":            p["diff"],
            "a_count":         i.get("a_count"),         # 出品中
            "a_count_all":     i.get("a_count_all"),     # 売り切れ含む
            "psa10_count":     i.get("psa10_count"),     # 出品中
            "psa10_count_all": i.get("psa10_count_all"), # 売り切れ含む
            "snkr_score":      i.get("snkr_score") if (i.get("snkr_score") or 0) > 0
                               else calc_exp_profit(p["mint"], p["psa10"], i.get("a_count")),
            "s_diff":          s_diff,
            "s_roi":           s_roi,
            "s_a":             s_a,
            "s_p10":           s_p10,
            "s_rank":          s_rank,
            "total":           total,
        })

    # ──────────────── 採点基準 ────────────────
    print(CRITERIA)

    W = 152

    def a_str(r):
        a, aa = r.get("a_count"), r.get("a_count_all")
        if a is None: return "---"
        return f"{a}({aa})" if aa is not None else f"{a}"

    def p10_str(r):
        p, pa = r.get("psa10_count"), r.get("psa10_count_all")
        if p is None: return "---"
        return f"{p}({pa})" if pa is not None else f"{p}"

    # ──────────────── 投資効率 TOP30（ROI順）────────────────
    def roi_val(r):
        return (r['psa10'] - r['mint'] - GRADING) / (r['mint'] + GRADING) * 100
    top_roi = sorted(records, key=roi_val, reverse=True)[:30]
    print(f"\n{'='*W}")
    print(f"【１】投資効率ランキング TOP30  （ROI順・予算¥100万ベース期待利益付き）")
    print(f"{'='*W}")
    print(f"{'順':>3} {'pokeca':>4} {'カード名':<38} {'ROI':>7} {'差額':>10} {'期待利益':>9} {'美品':>10} {'PSA10':>10}  A在庫(累計)   PSA10在庫(累計)")
    print(f"{'':>90}  ※出品中(売切含)")
    print(f"{'-'*W}")
    for i, r in enumerate(top_roi, 1):
        score = r.get("snkr_score")
        exp_str = f"¥{int(score/10_000)}万" if score and score > 0 else "---"
        print(
            f"{i:>3}位 {r['rank']:>4}位 {r['name'][:38]:<38} "
            f"{roi_str(r['mint'],r['psa10']):>7} "
            f"¥{r['diff']:>9,} "
            f"{exp_str:>9} "
            f"¥{r['mint']:>9,} ¥{r['psa10']:>9,}  "
            f"{a_str(r):>10}  {p10_str(r):>14}"
        )

    # ──────────────── 総合評価 TOP30 ────────────────
    top_total = sorted(records, key=lambda x: x["total"], reverse=True)[:30]
    print(f"\n{'='*W}")
    print(f"【２】総合評価 TOP30  （A:差額30 + B:ROI25 + C:希少性20 + D:流動性15 + E:トレンド10 = 100点満点）")
    print(f"{'':>55}C=A素体出品中 / D=PSA10売切含む累計")
    print(f"{'='*W}")
    print(f"{'順':>3} {'カード名':<40} {'総合':>5}  A  B  C  D  E  {'ROI':>7} {'差額':>10} {'美品':>10} {'PSA10':>10}  A在庫(累計)   PSA10在庫(累計)")
    print(f"{'-'*W}")
    for i, r in enumerate(top_total, 1):
        print(
            f"{i:>3}位 {r['name'][:40]:<40} "
            f"{r['total']:>4}点 "
            f"{r['s_diff']:>2} {r['s_roi']:>2} {r['s_a']:>2} {r['s_p10']:>2} {r['s_rank']:>2}  "
            f"{roi_str(r['mint'],r['psa10']):>7} "
            f"¥{r['diff']:>9,} ¥{r['mint']:>9,} ¥{r['psa10']:>9,}  "
            f"{a_str(r):>10}  {p10_str(r):>14}"
        )

    print(f"\n{'='*W}")
    print("【総合評価 注目カード コメント】")
    top3 = top_total[:3]
    labels = ["◎最優先", "○優先", "△注目"]
    for label, r in zip(labels, top3):
        print(f"  {label} {r['name'][:36]}  {r['total']}点 / ROI{roi_str(r['mint'],r['psa10'])} / 差額¥{r['diff']:,} / A在庫{a_str(r)}")

    print(f"\n※ pokeca-chartランクはmode=5（価格高騰順）の順位")
    print(f"※ A在庫: 出品中のみ(売切含む累計) / C希少性スコア=出品中 / D流動性スコア=累計")
    print(f"※ データ未取得はC(希少性)・D(流動性)ともに5点で補完")


if __name__ == "__main__":
    main()
