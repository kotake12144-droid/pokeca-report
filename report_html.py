"""
HTML形式レポート生成
"""

import csv, json, glob, os

GRADING        = 12_000
BUDGET         = 1_000_000
PSA10_HIT_RATE = 0.60


def calc_exp_profit(mint, psa10, a_count):
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


def load_pokeca():
    files = sorted(glob.glob("pokeca_scan_*.csv"), reverse=True)
    if not files:
        raise FileNotFoundError("pokeca_scan_*.csv が見つかりません")
    with open(files[0], newline="", encoding="utf-8") as f:
        cards = {}
        for row in csv.DictReader(f):
            cards[row["name"]] = {
                "rank":  int(row["rank"]),
                "mint":  int(row["mint_price"]),
                "psa10": int(row["psa10_price"]),
                "diff":  int(row["diff"]),
            }
    return cards


def load_inventory():
    if not os.path.exists("snkrdunk_inventory.json"):
        return {}
    with open("snkrdunk_inventory.json", encoding="utf-8") as f:
        items = json.load(f)
    inv = {}
    for c in items:
        if c.get("name"):
            inv[c["name"]] = {
                "a_count":         c.get("a_count"),
                "a_count_all":     c.get("a_count_all"),
                "psa10_count":     c.get("psa10_count"),
                "psa10_count_all": c.get("psa10_count_all"),
                "snkr_score":      c.get("score"),
            }
    return inv


def score_diff(diff):
    if   diff >= 300_000: return 30
    elif diff >= 100_000: return 25
    elif diff >=  50_000: return 20
    elif diff >=  20_000: return 15
    elif diff >=  10_000: return 10
    elif diff >=   5_000: return  5
    else:                 return  2

def score_roi(mint, psa10):
    cost = mint + GRADING
    roi  = (psa10 - mint - GRADING) / cost * 100
    if   roi >= 150: return 25
    elif roi >= 100: return 21
    elif roi >=  50: return 16
    elif roi >=  20: return 11
    elif roi >=   0: return  6
    else:            return  0

def score_a(a):
    if a is None:  return 5
    if   a <=   5: return 20
    elif a <=  15: return 16
    elif a <=  30: return 12
    elif a <= 100: return  8
    elif a <= 200: return  4
    else:          return  0

def score_p10(p):
    if p is None:   return 5
    if   p >= 2000: return  3
    elif p >= 1000: return  7
    elif p >=  500: return 12
    elif p >=  200: return 15
    elif p >=   50: return 10
    else:           return  4

def score_rank(rank):
    if   rank <=  10: return 10
    elif rank <=  20: return  8
    elif rank <=  30: return  6
    elif rank <=  50: return  4
    elif rank <=  70: return  2
    else:             return  0

def roi_pct(mint, psa10):
    roi = (psa10 - mint - GRADING) / (mint + GRADING) * 100
    return f"{roi:+.0f}%"

def inv_str(active, total):
    if active is None:
        return "---"
    if total is not None:
        return f"{active}<small>({total})</small>"
    return str(active)

def exp_str(score):
    if score and score > 0:
        return f"¥{int(score/10_000)}万"
    return "---"


HTML_STYLE = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    background: #fff;
    color: #111;
    font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif;
    font-size: 13px;
    padding: 20px 16px;
    max-width: 1200px;
    margin: 0 auto;
}
h1 {
    font-size: 18px;
    font-weight: 700;
    margin-bottom: 4px;
    letter-spacing: 0.02em;
}
.subtitle {
    font-size: 12px;
    color: #555;
    margin-bottom: 20px;
}
.section {
    margin-bottom: 40px;
}
.section-title {
    font-size: 14px;
    font-weight: 700;
    padding: 10px 12px;
    background: #111;
    color: #fff;
    margin-bottom: 0;
    letter-spacing: 0.03em;
}
.section-note {
    font-size: 11px;
    color: #555;
    padding: 5px 12px 8px;
    background: #f5f5f5;
    border-bottom: 1px solid #ddd;
}
.table-wrap {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
}
table {
    width: 100%;
    border-collapse: collapse;
    min-width: 680px;
}
thead th {
    background: #f5f5f5;
    font-weight: 600;
    font-size: 11px;
    padding: 8px 10px;
    text-align: left;
    border-bottom: 2px solid #111;
    white-space: nowrap;
    position: sticky;
    top: 0;
}
tbody tr {
    border-bottom: 1px solid #e8e8e8;
}
tbody tr:active {
    background: #f0f0f0;
}
tbody td {
    padding: 10px 10px;
    vertical-align: middle;
    white-space: nowrap;
}
.rank { font-weight: 700; color: #111; width: 32px; }
.top3 td { background: #fffdf0; }
.name { font-weight: 600; white-space: normal; line-height: 1.5; min-width: 160px; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.roi-pos { color: #1a6e2e; font-weight: 700; }
.roi-neg { color: #b91c1c; }
.score-total { font-weight: 700; font-size: 15px; }
.score-cell { font-size: 11px; color: #555; }
small { font-size: 10px; color: #999; }
.medal-1::before { content: "🥇 "; }
.medal-2::before { content: "🥈 "; }
.medal-3::before { content: "🥉 "; }
.criteria {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 10px;
    margin-bottom: 36px;
}
.criteria-card {
    border: 1px solid #ddd;
    padding: 12px;
    border-radius: 6px;
}
.criteria-label {
    font-size: 11px;
    font-weight: 700;
    color: #555;
    margin-bottom: 4px;
}
.criteria-title {
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 6px;
}
.criteria-pts {
    font-size: 11px;
    color: #333;
    line-height: 1.9;
}
.criteria-note {
    font-size: 10px;
    color: #888;
    margin-top: 6px;
}
.footer {
    font-size: 11px;
    color: #999;
    margin-top: 20px;
    line-height: 2.2;
    border-top: 1px solid #eee;
    padding-top: 16px;
}

@media (max-width: 600px) {
    body { padding: 16px 12px; font-size: 13px; }
    h1 { font-size: 16px; }
    .criteria {
        grid-template-columns: repeat(2, 1fr);
    }
    .criteria:last-child { grid-column: span 2; }
    .section-title { font-size: 13px; padding: 10px 12px; }
    .section-note { font-size: 10px; }
    thead th { font-size: 10px; padding: 7px 8px; }
    tbody td { padding: 10px 8px; font-size: 12px; }
    .score-total { font-size: 14px; }
    .footer { font-size: 10px; }
}
"""


def build_records():
    pokeca = load_pokeca()
    inv    = load_inventory()
    records = []
    for name, p in pokeca.items():
        i = inv.get(name, {})
        s_diff = score_diff(p["diff"])
        s_roi  = score_roi(p["mint"], p["psa10"])
        s_a    = score_a(i.get("a_count"))
        s_p10  = score_p10(i.get("psa10_count_all"))
        s_rank = score_rank(p["rank"])
        total  = s_diff + s_roi + s_a + s_p10 + s_rank
        roi_val = (p["psa10"] - p["mint"] - GRADING) / (p["mint"] + GRADING) * 100
        records.append({
            "name":            name,
            "rank":            p["rank"],
            "mint":            p["mint"],
            "psa10":           p["psa10"],
            "diff":            p["diff"],
            "roi_val":         roi_val,
            "a_count":         i.get("a_count"),
            "a_count_all":     i.get("a_count_all"),
            "psa10_count":     i.get("psa10_count"),
            "psa10_count_all": i.get("psa10_count_all"),
            "snkr_score":      i.get("snkr_score") if (i.get("snkr_score") or 0) > 0
                               else calc_exp_profit(p["mint"], p["psa10"], i.get("a_count")),
            "s_diff": s_diff, "s_roi": s_roi,
            "s_a": s_a, "s_p10": s_p10, "s_rank": s_rank,
            "total": total,
        })
    return records


def roi_class(mint, psa10):
    roi = (psa10 - mint - GRADING) / (mint + GRADING) * 100
    return "roi-pos" if roi >= 0 else "roi-neg"


def render_ranking1(records):
    top = sorted(records, key=lambda x: x["roi_val"], reverse=True)[:30]
    rows = []
    for i, r in enumerate(top, 1):
        tr_class = "top3" if i <= 3 else ""
        name_class = f"name medal-{i}" if i <= 3 else "name"
        rows.append(f"""
        <tr class="{tr_class}">
          <td class="rank num">{i}</td>
          <td class="{name_class}">{r['name']}</td>
          <td class="num {roi_class(r['mint'], r['psa10'])}">{roi_pct(r['mint'], r['psa10'])}</td>
          <td class="num">¥{r['diff']:,}</td>
          <td class="num">{exp_str(r.get('snkr_score'))}</td>
          <td class="num">¥{r['mint']:,}</td>
          <td class="num">¥{r['psa10']:,}</td>
          <td class="num">{inv_str(r['a_count'], r['a_count_all'])}</td>
          <td class="num">{inv_str(r['psa10_count'], r['psa10_count_all'])}</td>
        </tr>""")

    return f"""
    <div class="section">
      <div class="section-title">【１】投資効率ランキング TOP30</div>
      <div class="section-note">ROI順 ／ 期待利益は予算¥100万・PSA10獲得率60%・グレード費¥12,000想定</div>
      <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>カード名</th>
            <th class="num">ROI</th>
            <th class="num">差額</th>
            <th class="num">期待利益</th>
            <th class="num">美品</th>
            <th class="num">PSA10</th>
            <th class="num">A在庫<small>(累計)</small></th>
            <th class="num">PSA10在庫<small>(累計)</small></th>
          </tr>
        </thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
      </div>
    </div>"""


def render_ranking2(records):
    top = sorted(records, key=lambda x: x["total"], reverse=True)[:30]
    rows = []
    for i, r in enumerate(top, 1):
        tr_class = "top3" if i <= 3 else ""
        name_class = f"name medal-{i}" if i <= 3 else "name"
        scores = f"{r['s_diff']}/{r['s_roi']}/{r['s_a']}/{r['s_p10']}/{r['s_rank']}"
        rows.append(f"""
        <tr class="{tr_class}">
          <td class="rank num">{i}</td>
          <td class="{name_class}">{r['name']}</td>
          <td class="num score-total">{r['total']}点</td>
          <td class="num score-cell">{scores}</td>
          <td class="num {roi_class(r['mint'], r['psa10'])}">{roi_pct(r['mint'], r['psa10'])}</td>
          <td class="num">¥{r['diff']:,}</td>
          <td class="num">¥{r['mint']:,}</td>
          <td class="num">¥{r['psa10']:,}</td>
          <td class="num">{inv_str(r['a_count'], r['a_count_all'])}</td>
          <td class="num">{inv_str(r['psa10_count'], r['psa10_count_all'])}</td>
        </tr>""")

    return f"""
    <div class="section">
      <div class="section-title">【２】総合評価ランキング TOP30</div>
      <div class="section-note">A:差額30 + B:ROI25 + C:希少性20 + D:流動性15 + E:トレンド10 = 100点満点　／　スコア列はA/B/C/D/E内訳</div>
      <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>カード名</th>
            <th class="num">総合</th>
            <th class="num">A/B/C/D/E</th>
            <th class="num">ROI</th>
            <th class="num">差額</th>
            <th class="num">美品</th>
            <th class="num">PSA10</th>
            <th class="num">A在庫<small>(累計)</small></th>
            <th class="num">PSA10在庫<small>(累計)</small></th>
          </tr>
        </thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
      </div>
    </div>"""


def render_criteria():
    items = [
        ("A", "PSA10差額", "30点", "利益ポテンシャル",
         "≥¥300k: 30点<br>≥¥100k: 25点<br>≥¥50k: 20点<br>≥¥20k: 15点<br>≥¥10k: 10点<br>≥¥5k: 5点", ""),
        ("B", "ROI", "25点", "投資収益率",
         "≥150%: 25点<br>≥100%: 21点<br>≥50%: 16点<br>≥20%: 11点<br>≥0%: 6点<br>マイナス: 0点", ""),
        ("C", "A素体希少性", "20点", "出品中のみ",
         "≤5件: 20点<br>≤15件: 16点<br>≤30件: 12点<br>≤100件: 8点<br>≤200件: 4点<br>200件超: 0点", "今日仕入れられる実数"),
        ("D", "PSA10流動性", "15点", "売り切れ含む累計",
         "200〜499件: 15点<br>500〜999件: 12点<br>50〜199件: 10点<br>1000〜1999件: 7点<br>＜50件: 4点<br>≥2000件: 3点", "多すぎは競合過多で減点"),
        ("E", "注目トレンド", "10点", "pokecaランク",
         "1〜10位: 10点<br>11〜20位: 8点<br>21〜30位: 6点<br>31〜50位: 4点<br>51〜70位: 2点<br>71位以降: 0点", ""),
    ]
    cards = []
    for label, title, pts, note, detail, caution in items:
        caution_html = f'<div class="criteria-note">※ {caution}</div>' if caution else ""
        cards.append(f"""
        <div class="criteria-card">
          <div class="criteria-label">指標 {label}　{pts}</div>
          <div class="criteria-title">{title}</div>
          <div class="criteria-note">{note}</div>
          <div class="criteria-pts">{detail}</div>
          {caution_html}
        </div>""")
    return f'<div class="criteria">{"".join(cards)}</div>'


def main():
    import datetime
    records  = build_records()
    today    = datetime.date.today().strftime("%Y年%m月%d日")
    r1       = render_ranking1(records)
    r2       = render_ranking2(records)
    criteria = render_criteria()

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ポケカPSA10投資レポート {today}</title>
  <style>{HTML_STYLE}</style>
</head>
<body>
  <h1>ポケカ PSA10投資レポート</h1>
  <div class="subtitle">{today} ／ pokeca-chart × Snkrdunk</div>

  {criteria}
  {r1}
  {r2}

  <div class="footer">
    ※ A在庫: 出品中のみ（括弧内は売り切れ含む累計）<br>
    ※ PSA10在庫: 出品中のみ（括弧内は売り切れ含む累計）<br>
    ※ C希少性スコア = A素体出品中のみ　／　D流動性スコア = PSA10売り切れ含む累計<br>
    ※ データ未取得項目は C・D ともに 5点（中間値）で補完
  </div>
</body>
</html>"""

    out = "report.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"保存: {out}")


if __name__ == "__main__":
    main()
