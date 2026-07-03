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


def send_discord(webhook_url, subject, body):
    if not webhook_url:
        return

    # Discord accepts up to 2000 chars in a single message.
    content = f"**{subject}**\n{body}"
    if len(content) > 2000:
        content = content[:1990] + "\n..."

    try:
        r = requests.post(
            webhook_url,
            json={"content": content},
            timeout=20
        )
        if r.status_code not in (200, 204):
            print(f"ERROR discord webhook: {r.status_code} {r.text}")
    except Exception as e:
        print(f"ERROR discord webhook: {e}")


# ---------------- MAIN ----------------

def main():
    cfg = load_config()
    discord_webhook_url = cfg.get("discord", {}).get("webhook_url")
    old = load_prices()
    new = {}
    timestamp = datetime.now().isoformat(timespec="seconds")

    report = []
    send_alert = True
    lower_found = False

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
            report.append(f"  changed: {old_best} -> {best_price}\n")
            lower_found = True

        else:
            report.append("  no change\n")

    # ---------------- save ----------------
    save_prices(new)

    # ---------------- email ----------------
    if lower_found and send_alert:
        subject = "PriceBot update (lower price found)"
        body = "\n".join(report)
        send_email(cfg, subject, body)
        send_discord(discord_webhook_url, subject, body)
    else:
        subject = "PriceBot update (same price)"
        body = "\n".join(report)
        send_email(cfg, subject, body)
        send_discord(discord_webhook_url, subject, body)

    print("\n".join(report))


if __name__ == "__main__":
    main()