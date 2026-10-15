"""MongoDB Aggregation Pipelines for Food Rescue Analytics and Reports.

This module provides server-side aggregation pipelines using:
- $match: filtering by status, date, or presence
- $group: grouping by category, status, date, and unit
- $project: formatting dates, calculating derived fields, reshaping output
- $sort: ordering by activity count, volume, or timeline
- $cond and $ifNull: defensive aggregations handling missing fields and empty collections
"""

from food_rescue.db import (
    donation_records_col,
    donation_requests_col,
    food_listings_col,
    users_col,
)


def get_listings_overview():
    """Aggregate high-level listing metrics using $group and $cond.

    Returns:
        dict: Counts of total, available, expired, requested, accepted, collected listings,
              and total food units listed.
    """
    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_listings": {"$sum": 1},
                "total_quantity_listed": {"$sum": {"$ifNull": ["$quantity", 0]}},
                "available_listings": {
                    "$sum": {"$cond": [{"$eq": ["$status", "Available"]}, 1, 0]}
                },
                "expired_listings": {
                    "$sum": {"$cond": [{"$eq": ["$status", "Expired"]}, 1, 0]}
                },
                "requested_listings": {
                    "$sum": {"$cond": [{"$eq": ["$status", "Requested"]}, 1, 0]}
                },
                "accepted_listings": {
                    "$sum": {"$cond": [{"$eq": ["$status", "Accepted"]}, 1, 0]}
                },
                "collected_listings": {
                    "$sum": {"$cond": [{"$eq": ["$status", "Collected"]}, 1, 0]}
                },
                "cancelled_listings": {
                    "$sum": {"$cond": [{"$eq": ["$status", "Cancelled"]}, 1, 0]}
                },
            }
        },
        {
            "$project": {
                "_id": 0,
                "total_listings": 1,
                "total_quantity_listed": 1,
                "available_listings": 1,
                "expired_listings": 1,
                "requested_listings": 1,
                "accepted_listings": 1,
                "collected_listings": 1,
                "cancelled_listings": 1,
            }
        },
    ]

    results = list(food_listings_col().aggregate(pipeline))
    if results:
        return results[0]
    return {
        "total_listings": 0,
        "total_quantity_listed": 0,
        "available_listings": 0,
        "expired_listings": 0,
        "requested_listings": 0,
        "accepted_listings": 0,
        "collected_listings": 0,
        "cancelled_listings": 0,
    }


def get_quantity_by_unit():
    """Aggregate listed vs rescued food volumes grouped strictly by consistent units.

    Ensures that different units (servings, packs, kg, boxes) are never summed together ambiguously.
    Returns:
        list[dict]: Consolidated unit metrics containing listed, rescued, and rescue rate.
    """
    listed_pipeline = [
        {
            "$group": {
                "_id": {"$ifNull": ["$unit", "servings"]},
                "listed_quantity": {"$sum": {"$ifNull": ["$quantity", 0]}},
                "listings_count": {"$sum": 1},
            }
        },
        {"$sort": {"listed_quantity": -1}},
    ]

    rescued_pipeline = [
        {
            "$group": {
                "_id": {"$ifNull": ["$unit", "servings"]},
                "rescued_quantity": {"$sum": {"$ifNull": ["$quantity_collected", 0]}},
                "records_count": {"$sum": 1},
            }
        },
        {"$sort": {"rescued_quantity": -1}},
    ]

    listed_rows = list(food_listings_col().aggregate(listed_pipeline))
    rescued_rows = list(donation_records_col().aggregate(rescued_pipeline))

    units_map = {}
    for row in listed_rows:
        unit = row["_id"]
        units_map[unit] = {
            "unit": unit,
            "listed_quantity": row.get("listed_quantity", 0),
            "listings_count": row.get("listings_count", 0),
            "rescued_quantity": 0,
            "records_count": 0,
            "rescue_rate": 0,
        }

    for row in rescued_rows:
        unit = row["_id"]
        if unit not in units_map:
            units_map[unit] = {
                "unit": unit,
                "listed_quantity": 0,
                "listings_count": 0,
                "rescued_quantity": 0,
                "records_count": 0,
                "rescue_rate": 0,
            }
        units_map[unit]["rescued_quantity"] = row.get("rescued_quantity", 0)
        units_map[unit]["records_count"] = row.get("records_count", 0)

    # Compute rescue percentage for each unit
    for entry in units_map.values():
        if entry["listed_quantity"] > 0:
            rate = round((entry["rescued_quantity"] / entry["listed_quantity"]) * 100, 1)
            entry["rescue_rate"] = min(rate, 100.0)
        else:
            entry["rescue_rate"] = 0

    return sorted(units_map.values(), key=lambda x: x["listed_quantity"], reverse=True)


def get_category_breakdown():
    """Aggregate listings and quantities grouped by food category.

    Pipeline stages:
    - $group: groups by category, counting listings and sum of quantities
    - $sort: sorts by listings count descending
    """
    pipeline = [
        {
            "$group": {
                "_id": {"$ifNull": ["$category", "Other"]},
                "listings_count": {"$sum": 1},
                "total_quantity": {"$sum": {"$ifNull": ["$quantity", 0]}},
                "available_count": {
                    "$sum": {"$cond": [{"$eq": ["$status", "Available"]}, 1, 0]}
                },
                "collected_count": {
                    "$sum": {"$cond": [{"$eq": ["$status", "Collected"]}, 1, 0]}
                },
            }
        },
        {"$sort": {"listings_count": -1, "total_quantity": -1}},
    ]
    return list(food_listings_col().aggregate(pipeline))


def get_request_status_breakdown():
    """Aggregate donation requests grouped by workflow status."""
    pipeline = [
        {
            "$group": {
                "_id": {"$ifNull": ["$status", "Unknown"]},
                "requests_count": {"$sum": 1},
                "total_quantity_requested": {
                    "$sum": {"$ifNull": ["$quantity_requested", 0]}
                },
            }
        },
        {"$sort": {"requests_count": -1}},
    ]
    return list(donation_requests_col().aggregate(pipeline))


def get_donation_activity_by_date():
    """Aggregate completed rescues grouped by collection date using $dateToString.

    Pipeline stages:
    - $match: filters documents with valid collected_at timestamps
    - $project: extracts formatted YYYY-MM-DD date string
    - $group: groups by date with counts and volume sum
    - $sort: orders chronologically descending
    - $limit: caps at recent 14 days of activity
    """
    pipeline = [
        {"$match": {"collected_at": {"$ne": None}}},
        {
            "$project": {
                "date": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$collected_at"}
                },
                "quantity_collected": {"$ifNull": ["$quantity_collected", 0]},
                "unit": {"$ifNull": ["$unit", "units"]},
                "category": {"$ifNull": ["$category", "Other"]},
            }
        },
        {
            "$group": {
                "_id": "$date",
                "rescues_count": {"$sum": 1},
                "total_quantity_collected": {"$sum": "$quantity_collected"},
            }
        },
        {"$sort": {"_id": -1}},
        {"$limit": 14},
    ]
    return list(donation_records_col().aggregate(pipeline))


def get_full_dashboard_reports():
    """Compile comprehensive metrics for the impact reports dashboard."""
    overview = get_listings_overview()
    unit_breakdown = get_quantity_by_unit()
    category_stats = get_category_breakdown()
    request_stats = get_request_status_breakdown()
    activity_timeline = get_donation_activity_by_date()

    total_requests_count = donation_requests_col().count_documents({})
    completed_audits_count = donation_records_col().count_documents({})
    registered_users_count = users_col().count_documents({})

    # Aggregate total rescued quantity across all completed donation records
    total_rescued_pipeline = [
        {"$group": {"_id": None, "total": {"$sum": "$quantity_collected"}}}
    ]
    rescued_agg = list(donation_records_col().aggregate(total_rescued_pipeline))
    total_rescued_quantity = rescued_agg[0]["total"] if rescued_agg else 0

    return {
        "overview": overview,
        "unit_breakdown": unit_breakdown,
        "category_stats": category_stats,
        "request_stats": request_stats,
        "activity_timeline": activity_timeline,
        "total_requests_count": total_requests_count,
        "completed_audits_count": completed_audits_count,
        "total_rescued_quantity": total_rescued_quantity,
        "registered_users_count": registered_users_count,
    }
