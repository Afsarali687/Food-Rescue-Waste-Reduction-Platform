"""Server-side validation helpers.

These functions do not talk to MongoDB. Routes call them before insert/update.
"""

from bson.errors import InvalidId
from bson.objectid import ObjectId

from food_rescue.constants import (
    FOOD_CATEGORIES,
    LISTING_STATUSES,
    LISTING_TRANSITIONS,
    QUANTITY_UNITS,
    REQUEST_STATUSES,
    REQUEST_TRANSITIONS,
    USER_ROLES,
)


class ValidationError(ValueError):
    """Raised when input cannot be stored safely."""


def require_fields(data, field_names):
    """Return a list of missing/blank required field names."""
    missing = []
    for name in field_names:
        value = data.get(name)
        if value is None:
            missing.append(name)
            continue
        if isinstance(value, str) and not value.strip():
            missing.append(name)
    return missing


def parse_positive_int(value, field_name="quantity"):
    """Parse a quantity that must be an integer greater than zero."""
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field_name} must be a whole number.") from exc
    if number < 1:
        raise ValidationError(f"{field_name} must be at least 1.")
    return number


def parse_object_id(value, field_name="id"):
    try:
        return ObjectId(value)
    except (InvalidId, TypeError) as exc:
        raise ValidationError(f"Invalid {field_name}.") from exc


def validate_category(category):
    if category not in FOOD_CATEGORIES:
        raise ValidationError("Please choose a valid food category.")
    return category


def validate_unit(unit):
    cleaned = (unit or "servings").strip() or "servings"
    if cleaned not in QUANTITY_UNITS:
        raise ValidationError("Please choose a valid quantity unit.")
    return cleaned


def validate_user_role(role):
    if role not in USER_ROLES:
        raise ValidationError("Please choose a valid user role: provider, recipient, or volunteer.")
    return role


def can_transition(current_status, new_status, transitions):
    allowed = transitions.get(current_status, ())
    return new_status in allowed


def validate_listing_transition(current_status, new_status):
    if current_status not in LISTING_STATUSES:
        raise ValidationError("Unknown listing status.")
    if new_status not in LISTING_STATUSES:
        raise ValidationError("Invalid listing status.")
    if current_status == new_status:
        return new_status
    if not can_transition(current_status, new_status, LISTING_TRANSITIONS):
        raise ValidationError(
            f"Cannot change listing status from {current_status} to {new_status}."
        )
    return new_status


def validate_request_transition(current_status, new_status):
    if current_status not in REQUEST_STATUSES:
        raise ValidationError("Unknown request status.")
    if new_status not in REQUEST_STATUSES:
        raise ValidationError("Invalid request status.")
    if current_status == new_status:
        return new_status
    if not can_transition(current_status, new_status, REQUEST_TRANSITIONS):
        raise ValidationError(
            f"Cannot change request status from {current_status} to {new_status}."
        )
    return new_status


def allowed_request_next_statuses(current_status):
    return list(REQUEST_TRANSITIONS.get(current_status, ()))


def validate_food_listing(form):
    """Validate a surplus-food listing from a Flask request.form mapping."""
    missing = require_fields(
        form,
        ("title", "provider_name", "category", "location", "expiry_time", "quantity"),
    )
    if missing:
        raise ValidationError("Please complete all required fields: " + ", ".join(missing) + ".")

    expiry_time = form.get("expiry_time", "").strip()
    pickup_deadline = form.get("pickup_deadline", "").strip()
    if not pickup_deadline:
        pickup_deadline = expiry_time

    return {
        "title": form.get("title", "").strip(),
        "provider_name": form.get("provider_name", "").strip(),
        "category": validate_category(form.get("category", "").strip()),
        "quantity": parse_positive_int(form.get("quantity"), "quantity"),
        "unit": validate_unit(form.get("unit")),
        "location": form.get("location", "").strip(),
        "expiry_time": expiry_time,
        "pickup_deadline": pickup_deadline,
        "description": form.get("description", "").strip(),
        "contact": form.get("contact", "").strip(),
    }


def validate_donation_request(form, available_quantity):
    missing = require_fields(form, ("recipient_name", "organization", "contact"))
    if missing:
        raise ValidationError(
            "Please enter your name, organization, and contact details."
        )

    quantity_requested = parse_positive_int(
        form.get("quantity_requested", 1), "quantity_requested"
    )
    if quantity_requested > available_quantity:
        raise ValidationError(
            f"Requested quantity cannot exceed available quantity ({available_quantity})."
        )

    return {
        "recipient_name": form.get("recipient_name", "").strip(),
        "organization": form.get("organization", "").strip(),
        "contact": form.get("contact", "").strip(),
        "quantity_requested": quantity_requested,
    }


def validate_claimant_role(role):
    """Ensure a user role is authorized to request food (recipient or volunteer)."""
    cleaned = (role or "").strip().lower()
    if cleaned not in ("recipient", "volunteer"):
        raise ValidationError("Only authorized recipient organizations or volunteers can claim food donations.")
    return cleaned


def validate_user_record(data):
    missing = require_fields(data, ("name", "role", "organization"))
    if missing:
        raise ValidationError("User records need name, role, and organization.")
    return {
        "name": data.get("name", "").strip(),
        "role": validate_user_role(data.get("role", "").strip()),
        "organization": data.get("organization", "").strip(),
        "contact": data.get("contact", "").strip(),
        "location": data.get("location", "").strip(),
    }

