from bs4 import BeautifulSoup

def parse(html, target_size="5000"):
    soup = BeautifulSoup(html, "lxml")

    rows = soup.find_all("tr")

    for row in rows:
        if target_size in row.get_text(" ", strip=True):

            # 1. încearcă data-price-amount (best case)
            price_tag = row.select_one("[data-price-amount]")
            if price_tag and price_tag.get("data-price-amount"):
                return float(price_tag["data-price-amount"])

            # 2. fallback: span.price + decimals
            price = row.select_one("span.price")
            if price:
                whole = price.contents[0].strip() if price.contents else None
                dec = price.select_one(".decimals")
                decimals = dec.text.strip() if dec else "00"

                if whole:
                    try:
                        return float(f"{whole}.{decimals}")
                    except:
                        pass

            # 3. fallback generic (ultimă salvare)
            import re
            text = row.get_text(" ", strip=True)
            m = re.search(r"(\d+[.,]\d+)", text)

            if m:
                return float(m.group(1).replace(",", "."))

    return None