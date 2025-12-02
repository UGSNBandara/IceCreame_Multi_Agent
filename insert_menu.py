#!/usr/bin/env python3
"""
Simple script to add a menu item and trigger sync.
Usage: python insert_menu.py
"""

import requests
import json

BASE_URL = "https://icecreamemultiagent-production.up.railway.app"

def add_menu_item(name: str, description: str, price: float):
    url = f"{BASE_URL}/menu/items"
    payload = {
        "name": name,
        "description": description,
        "price": price
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    if response.status_code == 200:
        print(f"✅ Added menu item: {name}")
        print(f"Response: {response.json()}")
    else:
        print(f"❌ Failed to add {name}: {response.status_code} - {response.text}")

def sync_now():
    url = f"{BASE_URL}/admin/sync-now"
    response = requests.post(url)
    if response.status_code == 200:
        print("✅ Sync triggered successfully")
        print(f"Response: {response.json()}")
    else:
        print(f"❌ Sync failed: {response.status_code} - {response.text}")

if __name__ == "__main__":
    # Example: Add Magic Vanilla Cone
    add_menu_item("Magic Vanilla Cone", "The Magic vanilla cone is a creamy vanilla dairy ice Cream topped with chocolate sauce & cashew. Suitable for vegetarians. Rs. 50 cents from every 1l of fresh milk collected is contributed towards a special welfare fund \"Sarubima\" focused on empowering farmers' children through education.", 150)
    # Trigger sync
    sync_now()