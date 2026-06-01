import json
from typing import Dict, Any, List

# Mock Databases
PRODUCTS = {
    "prod_iphone15": {"id": "prod_iphone15", "name": "iPhone 15", "price": 1000, "stock": 10, "weight": 0.2, "category": "electronics"},
    "prod_ipadpro": {"id": "prod_ipadpro", "name": "iPad Pro", "price": 800, "stock": 5, "weight": 0.5, "category": "electronics"},
    "prod_macbookair": {"id": "prod_macbookair", "name": "MacBook Air", "price": 1200, "stock": 0, "weight": 1.2, "category": "electronics"},
    "prod_airpods": {"id": "prod_airpods", "name": "AirPods Pro", "price": 200, "stock": 20, "weight": 0.1, "category": "electronics"},
}

COUPONS = {
    "WINNER": {"code": "WINNER", "discount_percent": 10, "min_spend": 0},
    "WELCOME": {"code": "WELCOME", "discount_percent": 15, "min_spend": 500},
}

def search_product(product_name: str) -> str:
    """
    Search for a product by name. Returns product details if found.
    """
    name_lower = product_name.lower()
    results = []
    for prod in PRODUCTS.values():
        if name_lower in prod["name"].lower():
            results.append(prod)
    if results:
        return json.dumps({"status": "success", "products": results})
    return json.dumps({"status": "error", "message": f"Product '{product_name}' not found."})

def check_stock(product_id: str, quantity: int) -> str:
    """
    Check if a product is in stock for the requested quantity.
    """
    if product_id not in PRODUCTS:
        return json.dumps({"status": "error", "message": f"Product ID '{product_id}' not found."})
    
    prod = PRODUCTS[product_id]
    if prod["stock"] >= quantity:
        return json.dumps({"status": "success", "in_stock": True, "available_stock": prod["stock"]})
    return json.dumps({"status": "success", "in_stock": False, "available_stock": prod["stock"], "message": f"Only {prod['stock']} items available."})

def get_discount(coupon_code: str) -> str:
    """
    Retrieve discount details for a coupon code.
    """
    if coupon_code in COUPONS:
        return json.dumps({"status": "success", "coupon": COUPONS[coupon_code]})
    return json.dumps({"status": "error", "message": f"Coupon code '{coupon_code}' is invalid or expired."})

def calc_shipping(weight: float, destination: str) -> str:
    """
    Calculate shipping cost based on weight (kg) and destination.
    """
    dest_lower = destination.lower()
    # Simple calculation: base rate + weight rate
    if "hà nội" in dest_lower or "ha noi" in dest_lower:
        base_rate = 30
    elif "hồ chí minh" in dest_lower or "ho chi minh" in dest_lower or "hcm" in dest_lower:
        base_rate = 50
    else:
        base_rate = 40
        
    cost = base_rate + (weight * 10)
    return json.dumps({"status": "success", "shipping_cost": round(cost, 2), "destination": destination})

# Metadata list for the agent system prompt
TOOLS_METADATA = [
    {
        "name": "search_product",
        "description": "search_product(product_name: str) -> str: Search for products by name. Returns JSON list of matching products with name, price, stock, weight, and id.",
        "func": search_product
    },
    {
        "name": "check_stock",
        "description": "check_stock(product_id: str, quantity: int) -> str: Check if a product has enough stock. Returns JSON stating if in stock.",
        "func": check_stock
    },
    {
        "name": "get_discount",
        "description": "get_discount(coupon_code: str) -> str: Retrieve coupon details (discount percentage). Returns JSON.",
        "func": get_discount
    },
    {
        "name": "calc_shipping",
        "description": "calc_shipping(weight: float, destination: str) -> str: Calculate shipping fee based on weight in kg and destination city. Returns JSON.",
        "func": calc_shipping
    }
]
