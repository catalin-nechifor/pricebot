from bs4 import BeautifulSoup

def parse(html):
    soup = BeautifulSoup(html, "lxml")

    # 1. BEST: finalPrice (Magento standard)
    final_price = soup.select_one("[data-price-type='finalPrice']")
    if final_price and final_price.get("data-price-amount"):
        try:
            return float(final_price["data-price-amount"])
        except:
            pass

    # 2. fallback: special-price container
    special = soup.select_one(".special-price [data-price-amount]")
    if special and special.get("data-price-amount"):
        try:
            return float(special["data-price-amount"])
        except:
            pass

    # 3. fallback old logic (ULTIM)
    price = soup.select_one(".price, .product-price")
    if price:
        import re
        match = re.search(r"(\d+[.,]\d+|\d+)", price.get_text(" ", strip=True))
        if match:
            return float(match.group(1).replace(",", "."))

    return None