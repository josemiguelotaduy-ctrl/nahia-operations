#!/usr/bin/env python3
"""
NAHIA HOME · Operations & Catalog Sync Builder
Generates:
1. chatgpt_products.csv (100% compliant with OpenAI Product Feed Schema)
2. feed_status.json (Live catalog & stock telemetry)
3. index.html (Operations & Catalog Sync Center dashboard)
"""
import urllib.request
import json
import re
import html
import csv
import os
import datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(ROOT, "..", ".env")


def load_env():
    env = dict(os.environ)
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k] = v.strip().strip('"').strip("'")
    return env


ENV = load_env()
STORE_DOMAIN = ENV.get("SHOPIFY_STORE") or "zoraidastore.myshopify.com"
CLIENT_ID = ENV.get("SHOPIFY_CLIENT_ID") or ""
CLIENT_SECRET = ENV.get("SHOPIFY_CLIENT_SECRET") or ""
API_VERSION = "2025-01"
FEED_PUBLIC_URL = "https://josemiguelotaduy-ctrl.github.io/nahia-operations/chatgpt_products.csv"


def get_token():
    data = json.dumps({
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials"
    }).encode("utf-8")
    req = urllib.request.Request(
        f"https://{STORE_DOMAIN}/admin/oauth/access_token",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())["access_token"]


def fetch_all_active_products(token):
    url = f"https://{STORE_DOMAIN}/admin/api/{API_VERSION}/products.json?status=active&limit=250"
    products = []
    while url:
        req = urllib.request.Request(url, headers={"X-Shopify-Access-Token": token})
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read().decode())
            products.extend(body.get("products", []))
            link_header = resp.headers.get("Link", "")
            next_url = None
            if 'rel="next"' in link_header:
                for part in link_header.split(","):
                    if 'rel="next"' in part:
                        next_url = part.split(";")[0].strip().strip("<>")
            url = next_url
    return products


def to_jpg_if_needed(url):
    if not url:
        return ""
    url = re.sub(r'\.(webp|avif)(\?|$)', r'.\1.jpg\2', url, flags=re.I)
    return url.replace(",", "%2C")


def clean_html(raw_html):
    if not raw_html:
        return ""
    text = re.sub(r'<style[^>]*>.*?</style>', ' ', raw_html, flags=re.S | re.I)
    text = re.sub(r'<script[^>]*>.*?</script>', ' ', text, flags=re.S | re.I)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:4900]


def is_valid_gtin(val):
    if not val:
        return False
    digits = val.strip()
    if not digits.isdigit() or len(digits) not in (8, 12, 13, 14):
        return False
    total = 0
    for i, d in enumerate(reversed(digits[:-1])):
        mult = 3 if i % 2 == 0 else 1
        total += int(d) * mult
    check = (10 - (total % 10)) % 10
    return check == int(digits[-1])


def render_dashboard_html(status):
    brands_rows = ""
    for b in status["brands"][:12]:
        brands_rows += f"""
        <tr>
          <td style="font-weight:500;">{html.escape(b['brand'])}</td>
          <td>{b['variants']}</td>
          <td><span class="pill ok">{b['in_stock']} en stock</span></td>
          <td>{b['out_of_stock'] if b['out_of_stock'] > 0 else '—'}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>NAHIA HOME · Operations & Catalog Sync Center</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,400&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #F7F4EE;
      --card: #FFFFFF;
      --ink: #1C1916;
      --muted: #787065;
      --line: #E5DFD4;
      --line-subtle: #EEE9E0;
      --accent: #3A4436;
      --accent-hover: #2B3328;
      --gold: #9A7B4F;
      --pos: #2F5D41;
      --pos-bg: #E7F0E9;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--ink);
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      min-height: 100vh;
      -webkit-font-smoothing: antialiased;
    }}
    .top-bar {{
      border-bottom: 1px solid var(--line);
      background: var(--card);
      padding: 14px 36px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .top-left {{ display: flex; align-items: center; gap: 12px; }}
    .status-dot {{
      width: 8px; height: 8px; border-radius: 50%;
      background: var(--pos);
      box-shadow: 0 0 0 3px rgba(47, 93, 65, 0.15);
    }}
    .top-title {{
      font-size: 11px; font-weight: 600; letter-spacing: 0.22em;
      text-transform: uppercase; color: var(--muted);
    }}
    .top-right a {{
      color: var(--ink); text-decoration: none; font-size: 12px; font-weight: 500;
    }}
    .wrap {{ max-width: 1180px; margin: 0 auto; padding: 40px 28px 64px; }}
    .kicker {{
      font-size: 11px; letter-spacing: 0.24em; text-transform: uppercase;
      color: var(--gold); font-weight: 600; margin-bottom: 8px;
    }}
    h1 {{
      font-family: 'Cormorant Garamond', Georgia, serif;
      font-size: 40px; font-weight: 600; letter-spacing: 0.06em;
      text-transform: uppercase; margin-bottom: 10px;
    }}
    .sub {{ font-size: 14px; color: var(--muted); margin-bottom: 28px; line-height: 1.6; }}
    .url-box {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 24px 28px;
      margin-bottom: 24px;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }}
    .url-label {{
      font-size: 11px; font-weight: 600; letter-spacing: 0.16em;
      text-transform: uppercase; color: var(--gold); margin-bottom: 6px;
    }}
    .url-code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 13px; background: var(--bg); padding: 10px 14px;
      border-radius: 8px; border: 1px solid var(--line); color: var(--ink);
      word-break: break-all;
    }}
    .btn {{
      background: var(--accent); color: #FFF; border: none;
      padding: 11px 18px; border-radius: 9px; font-size: 13px;
      font-weight: 600; cursor: pointer; text-decoration: none;
      display: inline-flex; align-items: center; gap: 8px;
    }}
    .btn:hover {{ background: var(--accent-hover); }}
    .kpis {{
      display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 28px;
    }}
    .kpi {{
      background: var(--card); border: 1px solid var(--line);
      border-radius: 14px; padding: 20px 22px;
    }}
    .kpi-label {{
      font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase;
      color: var(--muted); margin-bottom: 8px; font-weight: 600;
    }}
    .kpi-val {{
      font-family: 'Cormorant Garamond', Georgia, serif;
      font-size: 34px; font-weight: 600; color: var(--ink);
    }}
    .kpi-note {{ font-size: 12px; color: var(--muted); margin-top: 4px; }}
    .card {{
      background: var(--card); border: 1px solid var(--line);
      border-radius: 16px; padding: 26px 28px;
    }}
    .card h2 {{
      font-family: 'Cormorant Garamond', Georgia, serif;
      font-size: 24px; margin-bottom: 16px;
    }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th {{
      text-align: left; font-size: 11px; text-transform: uppercase;
      letter-spacing: 0.12em; color: var(--muted); padding: 10px 12px;
      border-bottom: 1px solid var(--line);
    }}
    td {{ padding: 12px; border-bottom: 1px solid var(--line-subtle); }}
    .pill.ok {{
      background: var(--pos-bg); color: var(--pos);
      padding: 3px 9px; border-radius: 99px; font-size: 11.5px; font-weight: 600;
    }}
    #loginOverlay {{
      position: fixed; inset: 0; background: var(--bg);
      display: flex; align-items: center; justify-content: center; z-index: 9999;
    }}
    .loginBox {{
      background: var(--card); border: 1px solid var(--line);
      border-radius: 18px; padding: 44px 38px; width: 100%; max-width: 400px; text-align: center;
    }}
    .loginBox input {{
      width: 100%; padding: 12px 14px; border: 1px solid var(--line);
      border-radius: 9px; font-size: 14px; margin: 18px 0 12px;
    }}
    .loginBox button {{
      width: 100%; padding: 12px; background: var(--accent); color: #FFF;
      border: none; border-radius: 9px; font-weight: 600; cursor: pointer;
    }}
    @media (max-width: 820px) {{ .kpis {{ grid-template-columns: 1fr 1fr; }} }}
  </style>
</head>
<body>
  <div id="loginOverlay">
    <div class="loginBox">
      <div style="font-family:'Cormorant Garamond',serif;font-size:26px;font-weight:600;letter-spacing:0.22em;">NAHIA HOME</div>
      <div style="font-size:12px;color:var(--muted);margin-top:4px;">Operations &amp; Catalog Sync Center</div>
      <form onsubmit="handleLogin(event)">
        <input type="password" id="pwdInput" placeholder="Introduce la contraseña" required autofocus />
        <button type="submit">Acceder a Operaciones</button>
        <div id="loginErr" style="color:#B8473A;font-size:12px;margin-top:10px;display:none;">Contraseña incorrecta</div>
      </form>
    </div>
  </div>

  <header class="top-bar">
    <div class="top-left">
      <span class="status-dot"></span>
      <span class="top-title">NAHIA HOME · OPERATIONS &amp; CATALOG HUB</span>
    </div>
    <div class="top-right">
      <a href="https://josemiguelotaduy-ctrl.github.io/">← Volver al Portal Hub</a>
    </div>
  </header>

  <main class="wrap">
    <div class="kicker">AGENTIC COMMERCE &amp; CATALOG OPERATIONS</div>
    <h1>Centro de Operaciones &amp; Feeds</h1>
    <p class="sub">
      Sincronización automática cada hora 24/7 entre Shopify (<code>nahiahome.com</code>) y el feed hospedado para ChatGPT / OpenAI Business Hub.
    </p>

    <div class="url-box">
      <div style="flex:1;min-width:260px;">
        <div class="url-label">Hosted URL para ChatGPT ("Use a hosted URL")</div>
        <div class="url-code" id="feedUrl">{FEED_PUBLIC_URL}</div>
      </div>
      <div style="display:flex;gap:10px;">
        <button class="btn" onclick="copyFeedUrl()" id="copyBtn">📋 Copiar URL</button>
        <a class="btn" style="background:var(--gold);" href="chatgpt_products.csv" download>⬇ Descargar CSV</a>
      </div>
    </div>

    <div class="kpis">
      <div class="kpi">
        <div class="kpi-label">Productos Activos</div>
        <div class="kpi-val">{status["active_products"]}</div>
        <div class="kpi-note">{status["total_variants"]} variantes totales</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">En Stock (in_stock)</div>
        <div class="kpi-val" style="color:var(--pos);">{status["in_stock"]}</div>
        <div class="kpi-note">{status["out_of_stock"]} agotadas (out_of_stock)</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Marcas en Catálogo</div>
        <div class="kpi-val">{len(status["brands"])}</div>
        <div class="kpi-note">Imágenes forzadas a JPEG/PNG</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Última Sincronización</div>
        <div class="kpi-val" style="font-size:22px;margin-top:6px;">{status["updated_at_madrid"]}</div>
        <div class="kpi-note">Frecuencia: Cada hora 24/7</div>
      </div>
    </div>

    <div class="card">
      <h2>Distribución de Catálogo Sincronizado por Marca</h2>
      <table>
        <thead>
          <tr>
            <th>Marca (Vendor)</th>
            <th>Variantes</th>
            <th>Disponibles</th>
            <th>Agotadas</th>
          </tr>
        </thead>
        <tbody>
          {brands_rows}
        </tbody>
      </table>
    </div>
  </main>

  <script>
    const PORTAL_VALID = [
      "8a5d438a1a7fbf354c43b08668bbc5c350566454cdd756fd1d1aa04c43bdd72c",
      "63c57975163ee6a977b657bda190ae0ac927dd341bfda6584cd1922561987e41",
      "b83dc330dab18d589011b5ab637d997011270b1b3cf8a3fa76f92901858d3dad",
      "4b169e92fb51178c90065079408f584a56cdf9f0aefbd08aaac79577e042b63f",
      "3ba6235aed4391d574ccdf945d7d7c694823aa6ab47b3a85e0018e363136dd32",
      "72464de6614d2c2b78668f1479f6ff265a5a05d52d7ba65f7f51935f7e186528",
      "3f9fe0cf8466ed9e8e396636892f82d9e7e26b86c974f012efa21dd85d87296d",
      "8961fada71905662d5c797ed24ce9060935413c0f2f8b9d3787ad0e1ed5141a1"
    ];
    async function sha256(str) {{
      const buf = new TextEncoder().encode(str);
      const hashBuf = await crypto.subtle.digest("SHA-256", buf);
      return Array.from(new Uint8Array(hashBuf)).map(b => b.toString(16).padStart(2, "0")).join("");
    }}
    function checkAuth() {{
      const saved = localStorage.getItem("nahia_portal_auth") || localStorage.getItem("nahia_pnl_auth") || localStorage.getItem("nahia_ads_auth") || localStorage.getItem("nahia_social_auth") || localStorage.getItem("nahia_auth");
      if (PORTAL_VALID.includes(saved)) {{
        document.getElementById("loginOverlay").style.display = "none";
      }}
    }}
    async function handleLogin(e) {{
      e.preventDefault();
      const val = document.getElementById("pwdInput").value.trim();
      const h1 = await sha256(val);
      const h2 = await sha256(val.toLowerCase());
      const matched = PORTAL_VALID.includes(h1) ? h1 : (PORTAL_VALID.includes(h2) ? h2 : null);
      if (matched) {{
        localStorage.setItem("nahia_portal_auth", matched);
        localStorage.setItem("nahia_pnl_auth", matched);
        localStorage.setItem("nahia_ads_auth", matched);
        localStorage.setItem("nahia_social_auth", matched);
        localStorage.setItem("nahia_auth", matched);
        document.getElementById("loginOverlay").style.display = "none";
      }} else {{
        document.getElementById("loginErr").style.display = "block";
      }}
    }}
    function copyFeedUrl() {{
      navigator.clipboard.writeText(document.getElementById("feedUrl").textContent);
      const btn = document.getElementById("copyBtn");
      btn.textContent = "✓ URL Copiada";
      setTimeout(() => btn.textContent = "📋 Copiar URL", 2000);
    }}
    checkAuth();
  </script>
</body>
</html>
"""


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    token = get_token()
    products = fetch_all_active_products(token)

    columns = [
        "item_id",
        "group_id",
        "listing_has_variations",
        "variant_dict",
        "title",
        "description",
        "url",
        "brand",
        "seller_name",
        "seller_url",
        "image_url",
        "additional_image_urls",
        "price",
        "sale_price",
        "availability",
        "condition",
        "product_category",
        "gtin",
        "mpn",
        "accepts_returns",
        "return_deadline_in_days",
        "return_policy",
        "target_countries",
        "store_country",
        "is_eligible_search",
        "is_ads_eligible",
    ]

    rows = []
    brand_stats = {}

    for p in products:
        variants = p.get("variants", [])
        has_vars = len(variants) > 1
        options = p.get("options", [])
        images = p.get("images", [])
        img_by_id = {img["id"]: img["src"] for img in images if "id" in img and "src" in img}
        primary_img = images[0]["src"] if images else ""

        base_title = (p.get("title") or "").strip()
        desc = clean_html(p.get("body_html") or "") or base_title
        brand = (p.get("vendor") or "Nahia Home").strip()
        category = (p.get("product_type") or "").strip()
        handle = p.get("handle") or ""

        if brand not in brand_stats:
            brand_stats[brand] = {"brand": brand, "variants": 0, "in_stock": 0, "out_of_stock": 0}

        for v in variants:
            vid = str(v["id"])
            vtitle = (v.get("title") or "").strip()
            if has_vars and vtitle and vtitle != "Default Title":
                full_title = f"{base_title} — {vtitle}"
                prod_url = f"https://nahiahome.com/products/{handle}?variant={vid}"
            else:
                full_title = base_title
                prod_url = f"https://nahiahome.com/products/{handle}"

            full_title = full_title[:150]

            v_img_id = v.get("image_id")
            main_img_raw = img_by_id.get(v_img_id) or primary_img
            main_img = to_jpg_if_needed(main_img_raw)

            add_imgs = [
                to_jpg_if_needed(img["src"])
                for img in images
                if img.get("src") and img.get("src") != main_img_raw
            ][:10]

            raw_price = float(v.get("price") or 0.0)
            raw_compare = float(v.get("compare_at_price") or 0.0) if v.get("compare_at_price") else 0.0

            if raw_compare > raw_price and raw_price > 0:
                reg_price_str = f"{raw_compare:.2f} EUR"
                sale_price_str = f"{raw_price:.2f} EUR"
            else:
                reg_price_str = f"{raw_price:.2f} EUR"
                sale_price_str = ""

            inv_qty = v.get("inventory_quantity", 0)
            inv_policy = v.get("inventory_policy", "deny")
            inv_mgmt = v.get("inventory_management")
            if inv_mgmt is None or inv_policy == "continue" or (inv_qty is not None and inv_qty > 0):
                avail = "in_stock"
                brand_stats[brand]["in_stock"] += 1
            else:
                avail = "out_of_stock"
                brand_stats[brand]["out_of_stock"] += 1

            brand_stats[brand]["variants"] += 1

            v_dict_str = ""
            if has_vars:
                v_dict = {}
                for idx, opt in enumerate(options, start=1):
                    opt_name = (opt.get("name") or f"Option {idx}").strip()
                    opt_val = (v.get(f"option{idx}") or "").strip()
                    if opt_name and opt_val:
                        v_dict[opt_name] = opt_val
                if v_dict:
                    v_dict_str = json.dumps(v_dict, ensure_ascii=False)

            barcode = (v.get("barcode") or "").strip()
            gtin = barcode if is_valid_gtin(barcode) else ""
            sku = (v.get("sku") or "").strip()

            row = {
                "item_id": vid,
                "group_id": str(p["id"]) if has_vars else "",
                "listing_has_variations": "true" if has_vars else "",
                "variant_dict": v_dict_str,
                "title": full_title,
                "description": desc,
                "url": prod_url,
                "brand": brand,
                "seller_name": "Nahia Home",
                "seller_url": "https://nahiahome.com",
                "image_url": main_img,
                "additional_image_urls": ",".join(add_imgs),
                "price": reg_price_str,
                "sale_price": sale_price_str,
                "availability": avail,
                "condition": "new",
                "product_category": category,
                "gtin": gtin,
                "mpn": sku,
                "accepts_returns": "true",
                "return_deadline_in_days": "14",
                "return_policy": "https://nahiahome.com/policies/refund-policy",
                "target_countries": "ES",
                "store_country": "ES",
                "is_eligible_search": "true",
                "is_ads_eligible": "true",
            }
            rows.append(row)

    out_csv = os.path.join(base_dir, "chatgpt_products.csv")
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    now_madrid = datetime.datetime.now(ZoneInfo("Europe/Madrid")).strftime("%d/%m/%Y %H:%M")
    in_stock_count = sum(1 for r in rows if r["availability"] == "in_stock")
    sorted_brands = sorted(brand_stats.values(), key=lambda x: x["variants"], reverse=True)

    status = {
        "updated_at_madrid": now_madrid,
        "feed_url": FEED_PUBLIC_URL,
        "active_products": len(products),
        "total_variants": len(rows),
        "in_stock": in_stock_count,
        "out_of_stock": len(rows) - in_stock_count,
        "brands": sorted_brands,
    }

    with open(os.path.join(base_dir, "feed_status.json"), "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

    with open(os.path.join(base_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(render_dashboard_html(status))

    print(f"Operations build complete: {len(products)} products, {len(rows)} variants ({in_stock_count} in stock)")


if __name__ == "__main__":
    main()
