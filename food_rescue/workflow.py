"""Donation request workflow service and concurrency safety.

This module coordinates requests between recipients and providers:
- Request submission and quantity reservation
- Lifecycle transitions: Requested -> Accepted -> Collected / Cancelled
- Creation of permanent audit records in donation_records
- Standalone MongoDB transaction limitation handling (compensating actions and atomic conditional operations)
"""

from datetime import datetime, timezone
from pymongo import ReturnDocument
from pymongo.errors import PyMongoError, DuplicateKeyError

from food_rescue.constants import (
    COLLECTION_DONATION_RECORDS,
    COLLECTION_DONATION_REQUESTS,
    COLLECTION_FOOD_LISTINGS,
    COLLECTION_USERS,
    REQUEST_STATUSES,
    REQUEST_TO_LISTING_STATUS,
)
from food_rescue.db import (
    donation_records_col,
    donation_requests_col,
    food_listings_col,
    users_col,
)
from food_rescue.validation import (
    ValidationError,
    parse_object_id,
    validate_claimant_role,
    validate_donation_request,
    validate_request_transition,
    validate_listing_transition,
)


def _now():
    return datetime.now(timezone.utc)


def submit_donation_request(food_id_str, form_data, recipient_user_id=None):
    """Submit a donation claim for an available food listing.

    Concurrency & Consistency Strategy:
    In standalone MongoDB deployments, multi-document transactions require a replica set.
    To ensure consistency without a replica set, we use:
    1. Single-document atomic conditional updates (`find_one_and_update`) on the food listing.
       This checks both availability (`status: "Available"`) and quantity (`quantity >= requested`)
       atomically, preventing race conditions or overselling.
    2. Compensating Saga pattern: If the subsequent insertion into `donation_requests`
       encounters any database failure, the listing reservation is immediately reverted to 'Available'.
    """
    listing_oid = parse_object_id(food_id_str, "food id")
    listing = food_listings_col().find_one({"_id": listing_oid})
    if not listing:
        raise ValidationError("Food listing was not found.")

    # 1. Check expiration
    if listing.get("status") == "Expired":
        raise ValidationError("This food listing has expired and cannot be requested for donation safety.")

    # 2. Check for existing active requests for this listing
    active_req = donation_requests_col().find_one(
        {"listing_id": listing_oid, "status": {"$in": ["Requested", "Accepted"]}}
    )
    if active_req:
        raise ValidationError("An active donation request already exists for this food item.")

    # 3. Check current status
    if listing.get("status") != "Available":
        raise ValidationError(
            f"This food listing is not available for request (currently {listing.get('status')})."
        )


    # 4. Validate request inputs & quantity against available
    payload = validate_donation_request(form_data, listing.get("quantity", 0))

    # 5. Validate recipient role if user record link is provided
    recipient_user_oid = None
    if recipient_user_id:
        try:
            recipient_user_oid = parse_object_id(recipient_user_id, "recipient user id")
            user_doc = users_col().find_one({"_id": recipient_user_oid})
            if user_doc:
                validate_claimant_role(user_doc.get("role"))
        except ValidationError:
            raise
        except Exception:
            recipient_user_oid = None

    requested_qty = payload["quantity_requested"]

    # 6. Atomically reserve the food listing (Optimistic Locking via conditional match)
    reserved_listing = food_listings_col().find_one_and_update(
        {
            "_id": listing_oid,
            "status": "Available",
            "quantity": {"$gte": requested_qty},
        },
        {
            "$set": {
                "status": "Requested",
                "updated_at": _now(),
            }
        },
        return_document=ReturnDocument.AFTER,
    )

    if not reserved_listing:
        raise ValidationError(
            "Could not reserve listing: it was claimed concurrently by another recipient, "
            "expired, or the available quantity changed."
        )

    # 7. Insert the donation request document
    now_ts = _now()
    req_doc = {
        "listing_id": listing["_id"],
        "listing_title": listing.get("title", ""),
        "recipient_name": payload["recipient_name"],
        "organization": payload["organization"],
        "contact": payload["contact"],
        "quantity_requested": requested_qty,
        "status": "Requested",
        "created_at": now_ts,
        "updated_at": now_ts,
    }
    if recipient_user_oid:
        req_doc["recipient_user_id"] = recipient_user_oid

    try:
        insert_result = donation_requests_col().insert_one(req_doc)
        req_doc["_id"] = insert_result.inserted_id
    except Exception as exc:
        # Compensating action: revert the listing back to Available if request doc insert fails
        food_listings_col().update_one(
            {"_id": listing_oid, "status": "Requested"},
            {"$set": {"status": "Available", "updated_at": _now()}},
        )
        raise PyMongoError(f"Failed to record request; listing reservation rolled back: {exc}") from exc

    return req_doc


def transition_request_status(request_id_str, new_status, actor_role=None):
    """Execute a lifecycle transition for a donation request and synchronize the linked listing.

    Lifecycle:
    - Requested -> Accepted or Cancelled
    - Accepted -> Collected or Cancelled
    - Collected -> Final (creates immutable donation_record)
    - Cancelled -> Final (reverts listing status to Available)
    """
    if new_status not in REQUEST_STATUSES:
        raise ValidationError(f"Invalid request status '{new_status}'. Allowed: {', '.join(REQUEST_STATUSES)}.")

    request_oid = parse_object_id(request_id_str, "request id")
    req_doc = donation_requests_col().find_one({"_id": request_oid})
    if not req_doc:
        raise ValidationError("Donation request not found.")

    current_status = req_doc.get("status")
    validate_request_transition(current_status, new_status)

    # Authorization rules for transitions
    if actor_role:
        role = actor_role.strip().lower()
        if new_status == "Accepted" and role not in ("provider", "coordinator", "admin"):
            raise ValidationError("Only the food provider or designated coordinator can accept requests.")

    listing_status = REQUEST_TO_LISTING_STATUS.get(new_status)
    listing = food_listings_col().find_one({"_id": req_doc["listing_id"]})
    if listing and listing_status:
        validate_listing_transition(listing.get("status"), listing_status)

    now_ts = _now()

    # 1. Atomically update request status
    updated_req = donation_requests_col().find_one_and_update(
        {"_id": request_oid, "status": current_status},
        {"$set": {"status": new_status, "updated_at": now_ts}},
        return_document=ReturnDocument.AFTER,
    )
    if not updated_req:
        raise ValidationError("Request status was updated concurrently. Please refresh the page.")

    # 2. Update linked listing status
    if listing_status:
        food_listings_col().update_one(
            {"_id": req_doc["listing_id"]},
            {"$set": {"status": listing_status, "updated_at": now_ts}},
        )

    # 3. If collected, record permanent audit in donation_records
    if new_status == "Collected":
        _create_donation_record(req_doc, listing, now_ts)

    return updated_req, listing_status


def _create_donation_record(req_doc, listing, timestamp=None):
    """Idempotently log a completed rescue in donation_records."""
    records = donation_records_col()
    existing = records.find_one({"request_id": req_doc["_id"]})
    if existing:
        return existing

    record_doc = {
        "listing_id": req_doc["listing_id"],
        "request_id": req_doc["_id"],
        "listing_title": req_doc.get("listing_title") or (listing.get("title") if listing else "Unknown Item"),
        "provider_name": listing.get("provider_name") if listing else "Unknown Provider",
        "recipient_name": req_doc.get("recipient_name"),
        "organization": req_doc.get("organization"),
        "category": listing.get("category") if listing else "Other",
        "quantity_collected": req_doc.get("quantity_requested"),
        "unit": listing.get("unit") if listing else "units",
        "collected_at": timestamp or _now(),
    }
    try:
        records.insert_one(record_doc)
    except DuplicateKeyError:
        pass  # Guaranteed idempotent via unique index on request_id
    return record_doc


def mark_listing_expired(listing_id_str):
    """Mark an unreserved Available listing as Expired."""
    listing_oid = parse_object_id(listing_id_str, "food id")
    updated = food_listings_col().find_one_and_update(
        {"_id": listing_oid, "status": "Available"},
        {"$set": {"status": "Expired", "updated_at": _now()}},
        return_document=ReturnDocument.AFTER,
    )
    if not updated:
        raise ValidationError("Only 'Available' food listings can be marked as Expired.")
    return updated
