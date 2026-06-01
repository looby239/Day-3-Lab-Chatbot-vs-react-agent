import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _load_data(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def search_product(product_name: str):
    """Search product by product name. Input JSON: {"product_name": string}."""
    coupons = _load_data("coupons.json")
    for coupon in coupons:
        if product_name.strip().upper() == coupon["code"].upper():
            return json.dumps(
                {
                    "status": "error",
                    "message": f"'{product_name}' is a coupon code, not a product.",
                    "suggested_tool": "get_discount",
                    "suggested_action": f"get_discount(coupon_code=\"{coupon['code']}\", order_value=subtotal_vnd)",
                },
                ensure_ascii=False,
            )

    products = _load_data("products.json")
    results = [p for p in products if product_name.lower() in p["name"].lower()]
    query = product_name.lower()
    results.sort(key=lambda p: _product_rank(p["name"], query))
    if results:
        return json.dumps({"status": "success", "products": results}, ensure_ascii=False)
    return json.dumps({"status": "error", "message": f"No products found matching '{product_name}'"}, ensure_ascii=False)


def _product_rank(name: str, query: str):
    lower_name = name.lower()
    exact = lower_name == query
    base_model = query in lower_name and "pro" not in lower_name and "max" not in lower_name
    return (not exact, not base_model, len(lower_name))


def check_stock(product_id: str, quantity: int = 1):
    """Check if a product is in stock with the requested quantity. Input JSON: {"product_id": string, "quantity": integer}."""
    products = _load_data("products.json")
    for p in products:
        if p["id"] == product_id:
            if p["stock"] >= quantity:
                return json.dumps(
                    {"status": "success", "in_stock": True, "available": p["stock"], "price": p["price"], "weight_kg": p["weight_kg"]},
                    ensure_ascii=False,
                )
            return json.dumps(
                {"status": "success", "in_stock": False, "available": p["stock"], "message": f"Only {p['stock']} items available"},
                ensure_ascii=False,
            )
    return json.dumps({"status": "error", "message": f"Product ID {product_id} not found"}, ensure_ascii=False)


def get_discount(coupon_code: str, order_value: float):
    """Get discount information for a coupon code and order value. Input JSON: {"coupon_code": string, "order_value": float}."""
    coupons = _load_data("coupons.json")
    for c in coupons:
        if c["code"].upper() == coupon_code.upper():
            if not c["active"]:
                return json.dumps({"status": "success", "valid": False, "message": "Coupon has expired"}, ensure_ascii=False)
            if order_value < c["min_order_value"]:
                return json.dumps(
                    {"status": "success", "valid": False, "message": f"Order value must be at least {c['min_order_value']} to use this coupon"},
                    ensure_ascii=False,
                )

            discount_amount = (c["discount_percent"] / 100) * order_value
            return json.dumps(
                {
                    "status": "success",
                    "valid": True,
                    "discount_percent": c["discount_percent"],
                    "discount_amount": discount_amount,
                    "final_value": order_value - discount_amount,
                },
                ensure_ascii=False,
            )
    return json.dumps({"status": "success", "valid": False, "message": "Invalid coupon code"}, ensure_ascii=False)


def calc_shipping(weight_kg: float, destination: str):
    """Calculate shipping fee based on total weight and destination city. Input JSON: {"weight_kg": float, "destination": string}."""
    rules = _load_data("shipping_rules.json")
    for r in rules:
        if r["destination"].lower() == destination.lower():
            fee = r["base_fee"] + (r["per_kg"] * weight_kg)
            return json.dumps({"status": "success", "destination": r["destination"], "shipping_fee": fee}, ensure_ascii=False)

    fee = 50000 + (10000 * weight_kg)
    return json.dumps(
        {"status": "success", "destination": destination, "shipping_fee": fee, "note": "City not in list, using default rates"},
        ensure_ascii=False,
    )


# Global variable to simulate a session-based cart
_CART = {"items": [], "total_weight": 0.0, "total_value": 0.0}


def manage_cart(action: str, product_id: str = None, quantity: int = 1, price: float = 0.0, weight_kg: float = 0.0):
    """Manage the shopping cart. Actions: 'add', 'clear', 'show'. Input JSON: {"action": string, "product_id": string, "quantity": integer, "price": float, "weight_kg": float}."""
    global _CART
    if action == "add":
        _CART["items"].append({"product_id": product_id, "quantity": quantity})
        _CART["total_weight"] += weight_kg * quantity
        _CART["total_value"] += price * quantity
        return json.dumps(
            {"status": "success", "message": f"Added {quantity} of {product_id} to cart.", "cart_summary": _CART},
            ensure_ascii=False,
        )
    if action == "clear":
        _CART = {"items": [], "total_weight": 0.0, "total_value": 0.0}
        return json.dumps({"status": "success", "message": "Cart cleared.", "cart_summary": _CART}, ensure_ascii=False)
    if action == "show":
        return json.dumps({"status": "success", "cart_summary": _CART}, ensure_ascii=False)
    return json.dumps({"status": "error", "message": "Invalid action. Use 'add', 'clear', or 'show'."}, ensure_ascii=False)


RETAIL_TOOLS = [
    {
        "name": "search_product",
        "description": (
            "search_product(product_name: str) -> str. Use ONLY to find store products by product name, "
            "for example 'iPhone 15', 'MacBook Air', 'AirPods Pro'. Reads src/data/products.json. "
            "Returns JSON with status and products; each product has id, name, category, price in VND, stock, and weight_kg. "
            "Do NOT use this tool for coupon codes such as WINNER, WELCOME, FREESHIP, EXPIRED, BLACKFRIDAY, STUDENT, BIGSALE."
        ),
        "function": search_product,
        "func": search_product,
    },
    {
        "name": "check_stock",
        "description": (
            "check_stock(product_id: str, quantity: int) -> str. Use after search_product has returned a product id. "
            "Checks whether the requested quantity is available in src/data/products.json. "
            "Input product_id must be an id like 'p003', not a product name. "
            "Returns JSON with in_stock, available, price in VND, and weight_kg. "
            "Use price * quantity as the subtotal before discount and shipping."
        ),
        "function": check_stock,
        "func": check_stock,
    },
    {
        "name": "get_discount",
        "description": (
            "get_discount(coupon_code: str, order_value: float) -> str. Use ONLY for coupon/discount codes. "
            "Reads src/data/coupons.json. coupon_code examples: WINNER, WELCOME, FREESHIP, EXPIRED, BLACKFRIDAY, STUDENT, BIGSALE. "
            "order_value is the product subtotal in VND before shipping, normally price * quantity from check_stock. "
            "Returns JSON with valid, discount_percent, discount_amount, final_value, or a message explaining why the coupon is invalid. "
            "Do NOT use search_product for coupon codes."
        ),
        "function": get_discount,
        "func": get_discount,
    },
    {
        "name": "calc_shipping",
        "description": (
            "calc_shipping(weight_kg: float, destination: str) -> str. Use when the user asks for delivery, shipping, or total order cost with destination. "
            "Reads src/data/shipping_rules.json. weight_kg is total package weight, normally product weight_kg * quantity from check_stock. "
            "destination should be a city such as 'Hanoi', 'Ho Chi Minh City', 'Da Nang', 'Hai Phong', 'Can Tho', 'Hue', 'Nha Trang', or 'Vung Tau'. "
            "For Vietnamese input 'Ha Noi' or 'Ha Noi with accents', use destination='Hanoi'. "
            "Returns JSON with destination and shipping_fee in VND."
        ),
        "function": calc_shipping,
        "func": calc_shipping,
    },
    {
        "name": "manage_cart",
        "description": (
            "manage_cart(action: str, product_id: str = None, quantity: int = 1, price: float = 0.0, weight_kg: float = 0.0) -> str. "
            "Optional cart helper for adding, clearing, or showing cart totals. Use only after product price and weight are known from check_stock. "
            "Actions: 'add', 'clear', 'show'. Returns JSON cart summary."
        ),
        "function": manage_cart,
        "func": manage_cart,
    },
]

TOOLS_METADATA = RETAIL_TOOLS
