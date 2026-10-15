"""Shared allowed values for the Food Rescue platform.

These lists are used by forms, validation, and database indexes.
Keep them in one file so a viva explanation stays consistent.
"""

# Directory roles only. This project does not implement login/authentication.
USER_ROLES = ("provider", "recipient", "volunteer")

FOOD_CATEGORIES = (
    "Cooked Meals",
    "Bakery",
    "Fruits & Vegetables",
    "Packaged Food",
    "Other",
)

QUANTITY_UNITS = ("servings", "packs", "kg", "boxes")

# Listing and request statuses used by the platform.
LISTING_STATUSES = (
    "Available",
    "Requested",
    "Accepted",
    "Collected",
    "Cancelled",
    "Expired",
)

REQUEST_STATUSES = (
    "Requested",
    "Accepted",
    "Collected",
    "Cancelled",
)

# Allowed next statuses. Keys are the current status.
LISTING_TRANSITIONS = {
    "Available": ("Requested", "Cancelled", "Expired"),
    "Requested": ("Accepted", "Available", "Cancelled"),
    "Accepted": ("Collected", "Cancelled"),
    "Collected": (),
    "Cancelled": (),
    "Expired": (),
}

REQUEST_TRANSITIONS = {
    "Requested": ("Accepted", "Cancelled"),
    "Accepted": ("Collected", "Cancelled"),
    "Collected": (),
    "Cancelled": (),
}

# When a request moves to this status, the linked listing uses this status.
REQUEST_TO_LISTING_STATUS = {
    "Requested": "Requested",
    "Accepted": "Accepted",
    "Collected": "Collected",
    "Cancelled": "Available",
}

COLLECTION_USERS = "users"
COLLECTION_FOOD_LISTINGS = "food_listings"
COLLECTION_DONATION_REQUESTS = "donation_requests"
COLLECTION_DONATION_RECORDS = "donation_records"

