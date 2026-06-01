import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

def _load_data(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def search_product(product_name: str):
    """Search product by product name. Input JSON: {\"product_name\": string}."""
    products = _load_data("products.json")
    results = [p for p in products if product_name.lower() in p["name"].lower()]
    return results if results else f"No products found matching '{product_name}'"

def check_stock(product_id: str, quantity: int = 1):
    """Check if a product is in stock with the requested quantity. Input JSON: {\"product_id\": string, \"quantity\": integer}."""
    products = _load_data("products.json")
    for p in products:
        if p["id"] == product_id:
            if p["stock"] >= quantity:
                return {"in_stock": True, "available": p["stock"], "price": p["price"], "weight_kg": p["weight_kg"]}
            else:
                return {"in_stock": False, "available": p["stock"], "message": f"Only {p['stock']} items available"}
    return f"Product ID {product_id} not found"

def get_discount(coupon_code: str, order_value: float):
    """Get discount information for a coupon code and order value. Input JSON: {\"coupon_code\": string, \"order_value\": float}."""
    coupons = _load_data("coupons.json")
    for c in coupons:
        if c["code"].upper() == coupon_code.upper():
            if not c["active"]:
                return {"valid": False, "message": "Coupon has expired"}
            if order_value < c["min_order_value"]:
                return {"valid": False, "message": f"Order value must be at least {c['min_order_value']} to use this coupon"}
            
            discount_amount = (c["discount_percent"] / 100) * order_value
            return {
                "valid": True, 
                "discount_percent": c["discount_percent"], 
                "discount_amount": discount_amount,
                "final_value": order_value - discount_amount
            }
    return {"valid": False, "message": "Invalid coupon code"}

def calc_shipping(weight_kg: float, destination: str):
    """Calculate shipping fee based on total weight and destination city. Input JSON: {\"weight_kg\": float, \"destination\": string}."""
    rules = _load_data("shipping_rules.json")
    for r in rules:
        if r["destination"].lower() == destination.lower():
            fee = r["base_fee"] + (r["per_kg"] * weight_kg)
            return {"destination": r["destination"], "shipping_fee": fee}
    
    # Default for other cities if not found
    fee = 50000 + (10000 * weight_kg)
    return {"destination": destination, "shipping_fee": fee, "note": "City not in list, using default rates"}

# Global variable to simulate a session-based cart
_CART = {"items": [], "total_weight": 0.0, "total_value": 0.0}

def manage_cart(action: str, product_id: str = None, quantity: int = 1, price: float = 0.0, weight_kg: float = 0.0):
    """Manage the shopping cart. Actions: 'add', 'clear', 'show'. Input JSON: {\"action\": string, \"product_id\": string, \"quantity\": integer, \"price\": float, \"weight_kg\": float}."""
    global _CART
    if action == "add":
        _CART["items"].append({"product_id": product_id, "quantity": quantity})
        _CART["total_weight"] += weight_kg * quantity
        _CART["total_value"] += price * quantity
        return {"message": f"Added {quantity} of {product_id} to cart.", "cart_summary": _CART}
    elif action == "clear":
        _CART = {"items": [], "total_weight": 0.0, "total_value": 0.0}
        return {"message": "Cart cleared."}
    elif action == "show":
        return _CART
    return "Invalid action. Use 'add', 'clear', or 'show'."

RETAIL_TOOLS = [
    {
        "name": "search_product",
        "description": "Search product by product name. Useful to find product IDs and prices. Input: {'product_name': string}",
        "function": search_product,
    },
    {
        "name": "check_stock",
        "description": "Check stock and get details for a specific product ID. Input: {'product_id': string, 'quantity': integer}",
        "function": check_stock,
    },
    {
        "name": "get_discount",
        "description": "Apply a coupon code to an order value. Input: {'coupon_code': string, 'order_value': float}",
        "function": get_discount,
    },
    {
        "name": "calc_shipping",
        "description": "Calculate shipping costs. Input MUST be valid JSON: {'weight_kg': float (ONLY numbers), 'destination': string}",
        "function": calc_shipping,
    },
    {
        "name": "manage_cart",
        "description": "Add items to cart or view cart status. Use 'add' to update totals. Input: {'action': 'add'|'clear'|'show', 'product_id': string, 'quantity': int, 'price': float, 'weight_kg': float}",
        "function": manage_cart,
    }
]
