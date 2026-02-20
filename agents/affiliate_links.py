"""Agent Affiliate - Multi-platform affiliate link generator.
Supports Amazon Associates, ShopStyle Collective, and LTK (LikeToKnow.it).
"""
import os
import re
import urllib.parse
from config import AMAZON_TAG

# ShopStyle Collective PID (set in .env)
SHOPSTYLE_PID = os.environ.get("SHOPSTYLE_PID", "")
# LTK affiliate ID (set in .env)
LTK_ID = os.environ.get("LTK_ID", "")


def amazon_search_link(keyword):
    """Generate Amazon affiliate search link."""
    encoded = urllib.parse.quote_plus(keyword)
    return f"https://www.amazon.com/s?k={encoded}&tag={AMAZON_TAG}"


def amazon_asin_link(asin):
    """Generate Amazon affiliate ASIN link."""
    return f"https://www.amazon.com/dp/{asin}/?tag={AMAZON_TAG}"


def shopstyle_link(keyword):
    """Generate ShopStyle Collective affiliate link."""
    if not SHOPSTYLE_PID:
        return None
    encoded = urllib.parse.quote_plus(keyword)
    return f"https://www.shopstyle.com/browse?fts={encoded}&pid={SHOPSTYLE_PID}"


def ltk_link(keyword):
    """Generate LTK (LikeToKnow.it) affiliate link."""
    if not LTK_ID:
        return None
    encoded = urllib.parse.quote_plus(keyword)
    return f"https://www.shopltk.com/explore/{encoded}"


def generate_affiliate_block(product_name, keyword, asin=None):
    """Generate HTML block with multiple affiliate links for a product."""
    links = []

    # Amazon (primary)
    if asin:
        amazon_url = amazon_asin_link(asin)
    else:
        amazon_url = amazon_search_link(keyword)
    links.append(
        f'<a href="{amazon_url}" target="_blank" rel="nofollow sponsored">'
        f'Shop on Amazon</a>'
    )

    # ShopStyle
    ss_url = shopstyle_link(keyword)
    if ss_url:
        links.append(
            f'<a href="{ss_url}" target="_blank" rel="nofollow sponsored">'
            f'Browse on ShopStyle</a>'
        )

    # LTK
    ltk_url = ltk_link(keyword)
    if ltk_url:
        links.append(
            f'<a href="{ltk_url}" target="_blank" rel="nofollow sponsored">'
            f'Find on LTK</a>'
        )

    separator = ' &bull; '
    return (
        f'<div class="product-card">'
        f'<strong>{product_name}</strong><br>'
        f'{separator.join(links)}'
        f'</div>'
    )


def inject_affiliate_links(html_content, products):
    """Inject multi-platform affiliate links into existing HTML content.

    products: list of dicts with keys: name, keyword, asin (optional)
    """
    if not products:
        return html_content

    # Build "Shop the Look" section
    shop_section = '\n<div class="shop-the-look">\n<h2>Shop the Look</h2>\n'
    for p in products:
        block = generate_affiliate_block(
            p.get("name", p.get("keyword", "")),
            p.get("keyword", ""),
            p.get("asin"),
        )
        shop_section += block + "\n"
    shop_section += "</div>\n"

    # Insert before closing </article> or </body> or append
    if "</article>" in html_content:
        html_content = html_content.replace("</article>", shop_section + "</article>")
    elif "</body>" in html_content:
        html_content = html_content.replace("</body>", shop_section + "</body>")
    else:
        html_content += shop_section

    # Add affiliate disclosure if not present
    disclosure = (
        '<p class="affiliate-disclosure"><em>'
        'This post contains affiliate links. We may earn a commission '
        'at no extra cost to you if you make a purchase through these links. '
        'As an Amazon Associate, ShopStyle Collective member, and LTK creator, '
        'we earn from qualifying purchases.</em></p>'
    )
    if "affiliate-disclosure" not in html_content:
        if "</body>" in html_content:
            html_content = html_content.replace("</body>", disclosure + "\n</body>")
        else:
            html_content += "\n" + disclosure

    return html_content


if __name__ == "__main__":
    print("=== Affiliate Links Test ===")
    print(f"Amazon tag: {AMAZON_TAG}")
    print(f"ShopStyle PID: {'set' if SHOPSTYLE_PID else 'not set'}")
    print(f"LTK ID: {'set' if LTK_ID else 'not set'}")
    print()

    test_products = [
        {"name": "Wide Leg Denim Jeans", "keyword": "wide leg jeans women", "asin": "B0CH1M6X9Q"},
        {"name": "Minimalist Gold Necklace", "keyword": "minimalist gold necklace"},
        {"name": "Oversized Blazer", "keyword": "oversized blazer women 2026"},
    ]

    for p in test_products:
        block = generate_affiliate_block(p["name"], p["keyword"], p.get("asin"))
        print(block)
        print()
