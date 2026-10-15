"""Optional sample-data loader. Run with: python seed_data.py

Inserts directory users and food listings only when those collections are empty.
It does not delete existing documents.
"""

from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from food_rescue.config import get_config
from food_rescue.constants import (
    COLLECTION_DONATION_RECORDS,
    COLLECTION_DONATION_REQUESTS,
    COLLECTION_FOOD_LISTINGS,
    COLLECTION_USERS,
)

load_dotenv()
config = get_config()


def main():
    client = MongoClient(config["MONGO_URI"], serverSelectionTimeoutMS=config["MONGO_TIMEOUT_MS"])
    try:
        client.admin.command("ping")
    except PyMongoError as exc:
        print("Could not connect to MongoDB. Start MongoDB or check MONGO_URI in .env.")
        print(f"Details: {exc.__class__.__name__}")
        client.close()
        return 1

    db = client[config["MONGO_DB"]]
    users = db[COLLECTION_USERS]
    foods = db[COLLECTION_FOOD_LISTINGS]
    now = datetime.now(timezone.utc)

    if users.count_documents({}) == 0:
        users.insert_many(
            [
                {
                    "name": "Campus Canteen Desk",
                    "role": "provider",
                    "organization": "Green Campus Canteen",
                    "contact": "canteen@example.org",
                    "location": "Campus Main Gate",
                    "created_at": now,
                },
                {
                    "name": "NGO Coordinator",
                    "role": "recipient",
                    "organization": "City Food Bank",
                    "contact": "coordinator@example.org",
                    "location": "Community Hall",
                    "created_at": now,
                },
                {
                    "name": "Student Volunteer",
                    "role": "volunteer",
                    "organization": "NSS Cell",
                    "contact": "volunteer@example.org",
                    "location": "Campus",
                    "created_at": now,
                },
            ]
        )
        print("Inserted sample users (directory records only; no login).")
    else:
        print("users already has data; no samples inserted.")

    if foods.count_documents({}) == 0:
        foods.insert_many(
            [
                {
                    "title": "Fresh vegetarian lunch boxes",
                    "provider_name": "Green Campus Canteen",
                    "category": "Cooked Meals",
                    "quantity": 25,
                    "unit": "servings",
                    "location": "Campus Main Gate",
                    "expiry_time": "Today, 6:00 PM",
                    "pickup_deadline": "Today, 5:30 PM",
                    "description": "Nutritious sealed vegetarian thali boxes prepared fresh today. Keep refrigerated or consume warm.",
                    "contact": "canteen@example.org",
                    "status": "Available",
                    "created_at": now - timedelta(minutes=15),
                },
                {
                    "title": "Bakery whole wheat bread packs",
                    "provider_name": "Sunrise Bakery",
                    "category": "Bakery",
                    "quantity": 15,
                    "unit": "packs",
                    "location": "North Market Road",
                    "expiry_time": "Today, 8:00 PM",
                    "pickup_deadline": "Today, 7:00 PM",
                    "description": "Freshly baked artisan loaves and buns. Sealed and ready for distribution.",
                    "contact": "donations@sunrisebakery.org",
                    "status": "Available",
                    "created_at": now - timedelta(minutes=30),
                },
                {
                    "title": "Crated Red Apples & Bananas",
                    "provider_name": "Campus Fruit Co-op",
                    "category": "Fruits & Vegetables",
                    "quantity": 10,
                    "unit": "boxes",
                    "location": "Central Dining Complex",
                    "expiry_time": "Tomorrow, 12:00 PM",
                    "pickup_deadline": "Tomorrow, 10:00 AM",
                    "description": "Ripe organic seasonal fruits in clean ventilated crates.",
                    "contact": "fruitcoop@campus.edu",
                    "status": "Available",
                    "created_at": now - timedelta(hours=1),
                },
                {
                    "title": "Unopened Tetra Pack UHT Milk",
                    "provider_name": "Hostel 3 Mess",
                    "category": "Packaged Food",
                    "quantity": 30,
                    "unit": "packs",
                    "location": "Hostel 3 Delivery Dock",
                    "expiry_time": "Next Week, Friday",
                    "pickup_deadline": "Tomorrow, 6:00 PM",
                    "description": "Factory-sealed UHT 1-litre milk cartons with long shelf stability.",
                    "contact": "hostel3mess@campus.edu",
                    "status": "Available",
                    "created_at": now - timedelta(hours=2),
                },
            ]
        )
        print("Inserted sample food listings.")
    else:
        print("food_listings already has data; no samples inserted.")

    print(
        "Collections in use: "
        f"{COLLECTION_USERS}, {COLLECTION_FOOD_LISTINGS}, "
        f"{COLLECTION_DONATION_REQUESTS}, {COLLECTION_DONATION_RECORDS}."
    )
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
