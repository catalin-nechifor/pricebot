import json
import yaml
import requests
import smtplib
import ssl
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from bs4 import BeautifulSoup
from parsers import marelepescar, claumar, totalfishing

CONFIG_FILE = "config.yaml"
PRICE_FILE = "prices.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X)"
}


# ---------------- CONFIG / STORAGE ----------------

def load_config():
    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)


def load_prices():
    if not Path(PRICE_FILE).exists():
        return {}
    try:
        with open(PRICE_FILE) as f:
            return json.load(f)
    except:
        return {}


def save_prices(data):
    with open(PRICE_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ---------------- FETCH ----------------

def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            print(f"ERROR {url}: {r.status_code}")
            return None
        return r.text
    except Exception as e:
        print(f"ERROR {url}: {e}")
        return None


# ---------------- PARSERS ----------------

def parse_price(url, html, size=None):
    if not html:
        return None

    if "marelepescar" in url:
        return marelepescar.parse(html, size)

    if "claumar" in url:
        return claumar.parse(html)
    
    if "totalfishing" in url:
        return totalfishing.parse(html)

    return None


# ---------------- EMAIL ----------------

def send_email(cfg, subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = cfg["email"]["username"]
    msg["To"] = cfg["email"]["recipient"]

    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(
        cfg["email"]["smtp_server"],
        cfg["email"]["smtp_port"],
        context=context
    ) as smtp:
        smtp.login(
            cfg["email"]["username"],
            cfg["email"]["app_password"]
        )
        smtp.send_message(msg)


# ---------------- MAIN ----------------

def main():
    cfg = load_config()
    old = load_prices()
    new = {}
    timestamp = datetime.now().isoformat(timespec="seconds")

    report = []
    send_alert = True

    for p in cfg["products"]:
        name = p["name"]
        size = p.get("size")

        site_prices = []

        # ---------------- collect prices ----------------
        for url in p["urls"]:
            html = fetch(url)
            price = parse_price(url, html, size)

            if price is not None:
                site_prices.append({
                    "price": price,
                    "url": url
                })

        if not site_prices:
            report.append(f"{name}: no price found")
            continue

        # ---------------- best price ----------------
        best_item = min(site_prices, key=lambda x: x["price"])
        best_price = best_item["price"]
        best_url = best_item["url"]

        # ---------------- store new structure ----------------
        new[name] = {
            "best_price": best_price,
            "best_url": best_url,
            "best_price_timestamp": timestamp,
            "sites": site_prices
        }

        report.append(f"{name}: {best_price:.2f} RON")
        report.append(f"BEST: {best_url}")

        # ---------------- compare old ----------------
        old_best = old.get(name, {}).get("best_price")

        if old_best and best_price < old_best:
            send_alert = True
            report.append(f"  changed: {old_best} -> {best_price}\n")

    # ---------------- save ----------------
    save_prices(new)

    # ---------------- email ----------------
    if send_alert:
        send_email(cfg, "PriceBot update", "\n".join(report))

    print("\n".join(report))


if __name__ == "__main__":
    main()