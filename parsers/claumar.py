from bs4 import BeautifulSoup
import re

def parse(html):
    soup = BeautifulSoup(html, "lxml")

    # 1. încearcă prețul redus (corect)
    new_price = soup.select_one("p.price .price-new")

    if new_price:
        text = new_price.get_text(strip=True)
    else:
        # fallback pe preț vechi dacă nu există reducere
        old_price = soup.select_one("p.price .price-old .vechi")
        if not old_price:
            return None
        text = old_price.get_text(strip=True)

    # 2. extrage numărul
    match = re.search(r"(\d+[.,]\d+)", text)

    if not match:
        return None

    return float(match.group(1).replace(",", "."))