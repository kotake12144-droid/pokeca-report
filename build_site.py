#!/usr/bin/env python3

import csv, json, glob, os, shutil, datetime, secrets

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR  = os.path.join(BASE_DIR, "docs")
ARCH_DIR  = os.path.join(DOCS_DIR, "archive")
DATA_DIR  = os.path.join(DOCS_DIR, "data")
GRADING   = 12_000

TODAY = datetime.date.today().strftime("%Y-%m-%d")
TOKEN = secrets.token_hex(4)  # 例: "a7f3k2c9"


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


def load_pokeca():
    files = sorted(glob.glob(os.path.join(BASE_DIR, "pokeca_scan_*.csv")), reverse=True)
    if not files:
        raise FileNotFoundError("pokeca_scan_*.csv not found")
    cards = {}
    with open(files[0], newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cards[row["name"]] = {
                "rank":  int(row["rank"]),
                "mint":  int(row["mint_price"]),
                "psa10": int(row["psa10_price"]),
                "diff":  int(row["diff"]),
            }
    return cards


def load_inventory():
    path = os.path.join(BASE_DIR, "snkrdunk_inventory.json")
    with open(path, encoding="utf-8") as f:
        items = json.load(f)
    inv = {}
    for c in items:
        if c.get("name"):
            inv[c["name"]] = {
                "a_count":         c.get("a_count"),
                "a_count_all":     c.get("a_count_all"),
                "psa10_count":     c.get("psa10_count"),
                "psa10_count_all": c.get("psa10_count_all"),
            }
    return inv


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
        records.append({
            "name":            name,
            "rank":            p["rank"],
            "mint":            p["mint"],
            "psa10":           p["psa10"],
            "diff":            p["diff"],
            "a_count":         i.get("a_count"),
            "a_count_all":     i.get("a_count_all"),
            "psa10_count":     i.get("psa10_count"),
            "psa10_count_all": i.get("psa10_count_all"),
            "total":           total,
        })
    return records


def update_history(records):
    history_path = os.path.join(DATA_DIR, "history.json")
    if os.path.exists(history_path):
        with open(history_path, encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = []

    history = [d for d in history if d.get("date") != TODAY]

    snapshot_cards = []
    for r in records:
        snapshot_cards.append({
            "name":            r["name"],
            "rank":            r["rank"],
            "mint":            r["mint"],
            "psa10":           r["psa10"],
            "diff":            r["diff"],
            "a_count":         r["a_count"],
            "a_count_all":     r["a_count_all"],
            "psa10_count":     r["psa10_count"],
            "psa10_count_all": r["psa10_count_all"],
            "total":           r["total"],
        })

    history.append({"date": TODAY, "cards": snapshot_cards})
    history.sort(key=lambda x: x["date"])

    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    return history


def generate_archive_index(history):
    dates = sorted([d["date"] for d in history], reverse=True)
    items = "\n".join(
        f'      <li><a href="{date}.html">{date}</a></li>'
        for date in dates
    )
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>レポートアーカイブ</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ background: #fff; color: #111; font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif;
           font-size: 14px; padding: 24px 20px; max-width: 600px; margin: 0 auto; }}
    h1 {{ font-size: 18px; font-weight: 700; margin-bottom: 8px; }}
    nav {{ margin-bottom: 24px; font-size: 13px; color: #555; }}
    nav a {{ color: #1a56db; text-decoration: none; margin-right: 16px; }}
    nav a:hover {{ text-decoration: underline; }}
    ul {{ list-style: none; }}
    li {{ border-bottom: 1px solid #eee; }}
    li a {{ display: block; padding: 12px 4px; color: #1a56db; text-decoration: none; font-size: 15px; }}
    li a:hover {{ background: #f5f5f5; }}
  </style>
</head>
<body>
  <h1>レポートアーカイブ</h1>
  <nav>
    <a href="../r/latest/">← 最新レポート</a>
    <a href="../trends.html">推移グラフ</a>
  </nav>
  <ul>
{items}
  </ul>
</body>
</html>"""
    with open(os.path.join(ARCH_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)


NAV_HTML = """<div style="font-size:13px;color:#555;margin-bottom:20px;">
  <a href="../../archive/index.html" style="color:#1a56db;text-decoration:none;">アーカイブ</a>
  &nbsp;|&nbsp;
  <a href="../../trends.html" style="color:#1a56db;text-decoration:none;">推移グラフ</a>
</div>"""


def inject_nav(html_content):
    return html_content.replace("<body>", "<body>\n" + NAV_HTML, 1)


def generate_trends_html(history):
    top50_names = []
    if history:
        latest = history[-1]
        sorted_cards = sorted(latest["cards"], key=lambda x: x["total"], reverse=True)[:50]
        top50_names = [c["name"] for c in sorted_cards]
        top50_scores = {c["name"]: c["total"] for c in latest["cards"]}
    else:
        top50_scores = {}

    selector_options = "\n".join(
        f'      <option value="{name}">{name}（{top50_scores.get(name, 0)}点）</option>'
        for name in top50_names
    )

    history_json = json.dumps(history, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ポケカPSA10 価格推移グラフ</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      background: #fff;
      color: #111;
      font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif;
      font-size: 14px;
      padding: 24px 20px;
      max-width: 1100px;
      margin: 0 auto;
    }}
    h1 {{ font-size: 18px; font-weight: 700; margin-bottom: 6px; }}
    .subtitle {{ font-size: 12px; color: #666; margin-bottom: 20px; }}
    nav {{ font-size: 13px; color: #555; margin-bottom: 20px; }}
    nav a {{ color: #1a56db; text-decoration: none; margin-right: 16px; }}
    nav a:hover {{ text-decoration: underline; }}
    .selector-wrap {{ margin-bottom: 28px; }}
    .selector-wrap label {{ font-size: 13px; font-weight: 600; margin-right: 10px; }}
    select {{
      font-size: 14px;
      padding: 8px 12px;
      border: 1px solid #ccc;
      border-radius: 6px;
      background: #fff;
      min-width: 300px;
      max-width: 100%;
    }}
    .charts-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
    }}
    .chart-box {{
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      padding: 16px;
    }}
    .chart-title {{
      font-size: 13px;
      font-weight: 700;
      margin-bottom: 12px;
      color: #333;
    }}
    canvas {{ max-width: 100%; }}
    @media (max-width: 700px) {{
      .charts-grid {{ grid-template-columns: 1fr; }}
      select {{ min-width: 100%; }}
    }}
  </style>
</head>
<body>
  <h1>ポケカ PSA10 価格推移グラフ</h1>
  <div class="subtitle">過去データの推移を可視化</div>
  <nav>
    <a href="r/latest/">← 最新レポート</a>
    <a href="archive/index.html">アーカイブ</a>
    <span style="color:#111;font-weight:600;">推移グラフ</span>
  </nav>

  <div class="selector-wrap">
    <label for="cardSelect">カード選択:</label>
    <select id="cardSelect">
{selector_options}
    </select>
  </div>

  <div class="charts-grid">
    <div class="chart-box">
      <div class="chart-title">美品・PSA10 価格推移</div>
      <canvas id="chartPrice"></canvas>
    </div>
    <div class="chart-box">
      <div class="chart-title">差額推移</div>
      <canvas id="chartDiff"></canvas>
    </div>
    <div class="chart-box">
      <div class="chart-title">A素体在庫数推移（出品中）</div>
      <canvas id="chartACount"></canvas>
    </div>
    <div class="chart-box">
      <div class="chart-title">PSA10在庫数推移（累計）</div>
      <canvas id="chartP10Count"></canvas>
    </div>
  </div>

  <script>
  const HISTORY = {history_json};

  const charts = {{}};

  function fmtYen(v) {{
    if (v == null) return '';
    return '¥' + v.toLocaleString('ja-JP');
  }}

  function getCardData(name) {{
    const dates = [];
    const mint = [];
    const psa10 = [];
    const diff = [];
    const aCount = [];
    const p10Count = [];

    for (const snap of HISTORY) {{
      const card = snap.cards.find(c => c.name === name);
      dates.push(snap.date);
      if (card) {{
        mint.push(card.mint != null ? card.mint : null);
        psa10.push(card.psa10 != null ? card.psa10 : null);
        diff.push(card.diff != null ? card.diff : null);
        aCount.push(card.a_count != null ? card.a_count : null);
        p10Count.push(card.psa10_count_all != null ? card.psa10_count_all : null);
      }} else {{
        mint.push(null);
        psa10.push(null);
        diff.push(null);
        aCount.push(null);
        p10Count.push(null);
      }}
    }}
    return {{ dates, mint, psa10, diff, aCount, p10Count }};
  }}

  function buildChart(id, config) {{
    const ctx = document.getElementById(id).getContext('2d');
    if (charts[id]) charts[id].destroy();
    charts[id] = new Chart(ctx, config);
  }}

  function yenTickFormatter(value) {{
    return '¥' + value.toLocaleString('ja-JP');
  }}

  function updateCharts(name) {{
    const d = getCardData(name);

    buildChart('chartPrice', {{
      type: 'line',
      data: {{
        labels: d.dates,
        datasets: [
          {{
            label: '美品',
            data: d.mint,
            borderColor: '#1a56db',
            backgroundColor: 'rgba(26,86,219,0.08)',
            tension: 0.3,
            spanGaps: true,
            pointRadius: 4,
          }},
          {{
            label: 'PSA10',
            data: d.psa10,
            borderColor: '#e3342f',
            backgroundColor: 'rgba(227,52,47,0.08)',
            tension: 0.3,
            spanGaps: true,
            pointRadius: 4,
          }}
        ]
      }},
      options: {{
        responsive: true,
        plugins: {{ legend: {{ position: 'bottom' }} }},
        scales: {{
          y: {{
            ticks: {{ callback: yenTickFormatter }},
          }}
        }}
      }}
    }});

    buildChart('chartDiff', {{
      type: 'line',
      data: {{
        labels: d.dates,
        datasets: [{{
          label: '差額',
          data: d.diff,
          borderColor: '#38a169',
          backgroundColor: 'rgba(56,161,105,0.08)',
          tension: 0.3,
          spanGaps: true,
          pointRadius: 4,
        }}]
      }},
      options: {{
        responsive: true,
        plugins: {{ legend: {{ position: 'bottom' }} }},
        scales: {{
          y: {{
            ticks: {{ callback: yenTickFormatter }},
          }}
        }}
      }}
    }});

    buildChart('chartACount', {{
      type: 'line',
      data: {{
        labels: d.dates,
        datasets: [{{
          label: 'A素体在庫（出品中）',
          data: d.aCount,
          borderColor: '#dd6b20',
          backgroundColor: 'rgba(221,107,32,0.08)',
          tension: 0.3,
          spanGaps: true,
          pointRadius: 4,
        }}]
      }},
      options: {{
        responsive: true,
        plugins: {{ legend: {{ position: 'bottom' }} }},
      }}
    }});

    buildChart('chartP10Count', {{
      type: 'line',
      data: {{
        labels: d.dates,
        datasets: [{{
          label: 'PSA10在庫（累計）',
          data: d.p10Count,
          borderColor: '#805ad5',
          backgroundColor: 'rgba(128,90,213,0.08)',
          tension: 0.3,
          spanGaps: true,
          pointRadius: 4,
        }}]
      }},
      options: {{
        responsive: true,
        plugins: {{ legend: {{ position: 'bottom' }} }},
      }}
    }});
  }}

  const sel = document.getElementById('cardSelect');
  if (sel.options.length > 0) {{
    updateCharts(sel.value);
  }}
  sel.addEventListener('change', () => updateCharts(sel.value));
  </script>
</body>
</html>"""

    with open(os.path.join(DOCS_DIR, "trends.html"), "w", encoding="utf-8") as f:
        f.write(html)


LANDING_HTML = """<!DOCTYPE html>
<html lang="ja">
<head><meta charset="UTF-8"><title>ポケカPSA投資レポート</title>
<style>body{font-family:sans-serif;text-align:center;padding:80px 20px;color:#555;}
h1{font-size:1.2em;margin-bottom:16px;}</style></head>
<body><h1>ポケカ PSA投資レポート</h1>
<p>最新レポートのURLはDiscordでご確認ください。</p>
</body></html>"""


TOKEN_MAP_PATH = os.path.join(DOCS_DIR, "r", "tokens.json")
KEEP_DAYS = 5


def cleanup_old_tokens():
    """5日より古い・tokens.json未記録のトークンフォルダを削除する"""
    r_dir = os.path.join(DOCS_DIR, "r")
    token_map = {}
    if os.path.exists(TOKEN_MAP_PATH):
        with open(TOKEN_MAP_PATH, encoding="utf-8") as f:
            token_map = json.load(f)

    # 有効トークンのセット（直近5日分）
    cutoff = (datetime.date.today() - datetime.timedelta(days=KEEP_DAYS)).isoformat()
    valid_tokens = {tok for date, tok in token_map.items() if date >= cutoff}
    valid_tokens.add("latest")

    # 期限切れをtoken_mapから削除
    expired_dates = [d for d in list(token_map) if d < cutoff]
    for date in expired_dates:
        del token_map[date]

    # docs/r/ 内の全フォルダをチェック → 有効でないものは削除
    if os.path.exists(r_dir):
        for name in os.listdir(r_dir):
            if name in ("tokens.json",):
                continue
            if name not in valid_tokens:
                folder = os.path.join(r_dir, name)
                if os.path.isdir(folder):
                    shutil.rmtree(folder)
                    print(f"✓ 削除: docs/r/{name}/")

    with open(TOKEN_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(token_map, f, ensure_ascii=False, indent=2)


def save_token_map():
    """今日のトークンをマップに記録"""
    os.makedirs(os.path.join(DOCS_DIR, "r"), exist_ok=True)
    token_map = {}
    if os.path.exists(TOKEN_MAP_PATH):
        with open(TOKEN_MAP_PATH, encoding="utf-8") as f:
            token_map = json.load(f)
    token_map[TODAY] = TOKEN
    with open(TOKEN_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(token_map, f, ensure_ascii=False, indent=2)


def main():
    os.makedirs(DOCS_DIR, exist_ok=True)
    os.makedirs(ARCH_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)

    # 5日より古いトークンフォルダを削除
    cleanup_old_tokens()
    save_token_map()

    # トップページはランディングページに（直接アクセス不可）
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(LANDING_HTML)

    # 今日のレポートはランダムトークンフォルダへ
    token_dir = os.path.join(DOCS_DIR, "r", TOKEN)
    os.makedirs(token_dir, exist_ok=True)

    src = os.path.join(BASE_DIR, "report.html")
    with open(src, encoding="utf-8") as f:
        report_content = f.read()
    navified = inject_nav(report_content)

    with open(os.path.join(token_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(navified)

    # アーカイブにも保存
    with open(os.path.join(ARCH_DIR, f"{TODAY}.html"), "w", encoding="utf-8") as f:
        f.write(navified)

    # トークンをファイルに保存（push_to_github.sh が読む）
    with open(os.path.join(DOCS_DIR, "current_token.txt"), "w") as f:
        f.write(TOKEN)

    # /r/latest/ → 今日のトークンURLにリダイレクト
    latest_dir = os.path.join(DOCS_DIR, "r", "latest")
    os.makedirs(latest_dir, exist_ok=True)
    with open(os.path.join(latest_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<meta http-equiv="refresh" content="0;url=/r/{TOKEN}/">
<script>location.replace("/r/{TOKEN}/")</script>
</head><body></body></html>""")

    records = build_records()
    history = update_history(records)

    generate_archive_index(history)
    generate_trends_html(history)

    print(f"docs/r/{TOKEN}/index.html created")
    print(f"docs/archive/{TODAY}.html created")
    print(f"docs/data/history.json updated ({len(history)} days)")
    print(f"TOKEN={TOKEN}")


if __name__ == "__main__":
    main()
