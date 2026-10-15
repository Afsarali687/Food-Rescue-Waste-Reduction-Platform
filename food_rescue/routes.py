"""HTML routes for listings, requests, and reports.

Existing pages and behaviour are preserved. Validation, safe concurrency workflow,
and MongoDB aggregation pipelines power the platform.
"""

from datetime import datetime, timezone
import re

from flask import Blueprint, flash, redirect, render_template, request, url_for
from pymongo import DESCENDING
from pymongo.errors import PyMongoError

from food_rescue.aggregations import get_full_dashboard_reports, get_listings_overview
from food_rescue.constants import (
    FOOD_CATEGORIES,
    LISTING_STATUSES,
    QUANTITY_UNITS,
    REQUEST_STATUSES,
    REQUEST_TO_LISTING_STATUS,
)
from food_rescue.db import (
    db_error_message,
    donation_records_col,
    donation_requests_col,
    food_listings_col,
    ping_db,
    users_col,
)
from food_rescue.validation import (
    ValidationError,
    allowed_request_next_statuses,
    parse_object_id,
    validate_food_listing,
)
from food_rescue.workflow import (
    mark_listing_expired,
    submit_donation_request,
    transition_request_status,
)

main_bp = Blueprint("main", __name__)


def _now():
    return datetime.now(timezone.utc)


def _empty_stats():
    return {
        "available": 0,
        "requested": 0,
        "collected": 0,
        "total": 0,
        "rescued_units": 0,
    }


@main_bp.route("/")
def index():
    """Homepage: Mission statement, live summary cards, and recently added listings."""
    search = request.args.get("q", "")[:100].strip()
    category = request.args.get("category", "")[:50].strip()
    location = request.args.get("location", "")[:100].strip()

    # If user submitted search or filter from home, redirect to dedicated listings page
    if search or category or location:
        return redirect(
            url_for("main.listings", q=search, category=category, location=location)
        )

    try:
        ping_db()
        foods = food_listings_col()
        requests_col = donation_requests_col()
        records_col = donation_records_col()

        # Retrieve the latest 6 available food listings
        recent_listings = list(
            foods.find({"status": "Available"}).sort("created_at", DESCENDING).limit(6)
        )

        overview = get_listings_overview()

        # Rescued volume from completed records
        rescued_sum = list(
            records_col.aggregate(
                [{"$group": {"_id": None, "total": {"$sum": "$quantity_collected"}}}]
            )
        )
        rescued_units = rescued_sum[0]["total"] if rescued_sum else 0

        stats = {
            "available": overview.get("available_listings", 0),
            "requested": requests_col.count_documents(
                {"status": {"$in": ["Requested", "Accepted"]}}
            ),
            "collected": overview.get("collected_listings", 0),
            "total": overview.get("total_listings", 0),
            "rescued_units": rescued_units,
        }
        db_ready = True
    except PyMongoError:
        recent_listings, stats, db_ready = [], _empty_stats(), False

    return render_template(
        "index.html",
        listings=recent_listings,
        stats=stats,
        db_ready=db_ready,
        categories=FOOD_CATEGORIES,
    )


@main_bp.route("/listings")
def listings():
    """Directory of all food listings with multi-attribute search and filters."""
    search = request.args.get("q", "")[:100].strip()
    category = request.args.get("category", "")[:50].strip()
    location = request.args.get("location", "")[:100].strip()
    status = request.args.get("status", "Available")[:30].strip()

    query = {}
    if status and status != "all":
        query["status"] = status

    if search:
        escaped_search = re.escape(search)
        query["$or"] = [
            {"title": {"$regex": escaped_search, "$options": "i"}},
            {"provider_name": {"$regex": escaped_search, "$options": "i"}},
            {"description": {"$regex": escaped_search, "$options": "i"}},
        ]
    if category and category != "all":
        query["category"] = category
    if location:
        query["location"] = {"$regex": re.escape(location), "$options": "i"}

    try:
        ping_db()
        items = list(
            food_listings_col().find(query).sort("created_at", DESCENDING).limit(100)
        )
        total_count = len(items)
        db_ready = True
    except PyMongoError:
        items, total_count, db_ready = [], 0, False

    return render_template(
        "listings.html",
        listings=items,
        total_count=total_count,
        categories=FOOD_CATEGORIES,
        statuses=LISTING_STATUSES,
        search=search,
        selected_category=category,
        selected_location=location,
        selected_status=status,
        db_ready=db_ready,
    )


@main_bp.route("/food/new", methods=["GET", "POST"])
def create_food():
    if request.method == "POST":
        try:
            payload = validate_food_listing(request.form)
            now_ts = _now()
            document = {
                **payload,
                "status": "Available",
                "created_at": now_ts,
                "updated_at": now_ts,
            }
            ping_db()
            food_listings_col().insert_one(document)
            flash("Food donation listing created successfully.", "success")
            return redirect(url_for("main.listings"))
        except ValidationError as exc:
            flash(str(exc), "error")
            return render_template(
                "food_form.html",
                categories=FOOD_CATEGORIES,
                units=QUANTITY_UNITS,
                form=request.form,
            )
        except PyMongoError as exc:
            flash(db_error_message(exc), "error")

    return render_template(
        "food_form.html",
        categories=FOOD_CATEGORIES,
        units=QUANTITY_UNITS,
        form={},
    )


@main_bp.route("/food/<food_id>")
def food_detail(food_id):
    try:
        ping_db()
        item = food_listings_col().find_one({"_id": parse_object_id(food_id, "food id")})
        recipient_users = list(
            users_col().find({"role": {"$in": ["recipient", "volunteer"]}})
        )
    except (ValidationError, PyMongoError):
        item = None
        recipient_users = []

    if not item:
        flash("Food listing was not found.", "error")
        return redirect(url_for("main.listings"))

    return render_template(
        "food_detail.html",
        item=item,
        recipient_users=recipient_users,
    )


@main_bp.route("/food/<food_id>/request", methods=["POST"])
def request_donation(food_id):
    """Workflow: Authorized recipient or NGO submits a donation request."""
    try:
        ping_db()
        recipient_user_id = request.form.get("recipient_user_id", "").strip() or None
        req_doc = submit_donation_request(
            food_id, request.form, recipient_user_id=recipient_user_id
        )
        flash(
            f"Donation request submitted for {req_doc['quantity_requested']} portions of "
            f"'{req_doc['listing_title']}'. The provider can review and accept it.",
            "success",
        )
        return redirect(url_for("main.requests_page"))
    except ValidationError as exc:
        flash(str(exc), "error")
        return redirect(url_for("main.food_detail", food_id=food_id))
    except PyMongoError as exc:
        flash(db_error_message(exc), "error")
        return redirect(url_for("main.food_detail", food_id=food_id))


@main_bp.route("/food/<food_id>/expire", methods=["POST"])
def expire_food_listing(food_id):
    """Mark an unreserved Available listing as Expired."""
    try:
        ping_db()
        mark_listing_expired(food_id)
        flash("Food listing has been marked as Expired.", "success")
    except ValidationError as exc:
        flash(str(exc), "error")
    except PyMongoError as exc:
        flash(db_error_message(exc), "error")
    return redirect(url_for("main.food_detail", food_id=food_id))


@main_bp.route("/requests")
def requests_page():
    try:
        ping_db()
        requests_list = list(
            donation_requests_col().find().sort("created_at", DESCENDING).limit(200)
        )
        for row in requests_list:
            row["allowed_next"] = allowed_request_next_statuses(row.get("status"))
        db_ready = True
    except PyMongoError:
        requests_list, db_ready = [], False

    return render_template(
        "requests.html",
        requests_list=requests_list,
        db_ready=db_ready,
        statuses=REQUEST_STATUSES,
    )


@main_bp.route("/requests/<request_id>/status", methods=["POST"])
def update_request_status(request_id):
    """Workflow: Process status transitions (Requested -> Accepted -> Collected / Cancelled)."""
    new_status = request.form.get("status", "").strip()
    actor_role = request.form.get("actor_role", "").strip() or None
    try:
        ping_db()
        updated_req, listing_status = transition_request_status(
            request_id, new_status, actor_role=actor_role
        )
        title = updated_req.get("listing_title", "food listing")
        if new_status == "Accepted":
            flash(
                f"Request for '{title}' accepted! Listing marked as Accepted and ready for pickup.",
                "success",
            )
        elif new_status == "Collected":
            flash(
                f"Donation for '{title}' marked as Collected. Permanent audit record saved in donation_records.",
                "success",
            )
        elif new_status == "Cancelled":
            flash(
                f"Request for '{title}' was cancelled. Food listing has been restored to Available.",
                "info",
            )
        else:
            flash(f"Request status successfully updated to {new_status}.", "success")
    except ValidationError as exc:
        flash(str(exc), "error")
    except PyMongoError as exc:
        flash(db_error_message(exc), "error")
    return redirect(url_for("main.requests_page"))


@main_bp.route("/reports")
def reports():
    """Impact reports dashboard powered entirely by MongoDB Aggregation Pipelines."""
    try:
        ping_db()
        report_data = get_full_dashboard_reports()
        db_ready = True
    except PyMongoError:
        report_data = {
            "overview": {
                "total_listings": 0,
                "total_quantity_listed": 0,
                "available_listings": 0,
                "expired_listings": 0,
                "requested_listings": 0,
                "accepted_listings": 0,
                "collected_listings": 0,
                "cancelled_listings": 0,
            },
            "unit_breakdown": [],
            "category_stats": [],
            "request_stats": [],
            "activity_timeline": [],
            "total_requests_count": 0,
            "completed_audits_count": 0,
            "total_rescued_quantity": 0,
            "registered_users_count": 0,
        }
        db_ready = False

    return render_template(
        "reports.html",
        report=report_data,
        db_ready=db_ready,
    )
