# Database design (MongoDB / NoSQL)

Database name comes from `MONGO_DB` (default: `food_rescue_db`).

This is a document database. Relationships use ObjectId references, not SQL foreign keys.
A short denormalized copy (for example listing title on a request) is kept only where a page needs to display it without an extra lookup.

This project stores **directory-style user records**. It does **not** implement login, passwords, or access control.

## Collections

### 1. `users`

People or organizations that take part in food rescue.

| Field | Type | Notes |
| --- | --- | --- |
| `_id` | ObjectId | MongoDB primary key |
| `name` | string | Required |
| `role` | string | `provider`, `recipient`, or `volunteer` |
| `organization` | string | Required |
| `contact` | string | Organization contact for the demo |
| `location` | string | Optional |
| `created_at` | datetime | UTC |

**Relationships:** optional. A listing may later store `provider_user_id`; a request may store `recipient_user_id`. The current pages still work with names on the listing/request documents so existing features stay simple.

**Indexes:** `role`, `organization`.

### 2. `food_listings`

Surplus food that a provider publishes.

| Field | Type | Notes |
| --- | --- | --- |
| `_id` | ObjectId | Primary key |
| `title` | string | Required |
| `provider_name` | string | Display name (avoids joining users on every card) |
| `provider_user_id` | ObjectId | Optional link to `users` |
| `category` | string | One of the allowed food categories |
| `quantity` | int | Must be ≥ 1 |
| `unit` | string | `servings`, `packs`, `kg`, or `boxes` |
| `location` | string | Pickup place |
| `expiry_time` | string | Pickup-by time (as entered by the student demo) |
| `description` | string | Optional |
| `contact` | string | Optional organization contact |
| `status` | string | See listing statuses below |
| `created_at` | datetime | UTC |
| `updated_at` | datetime | Set when status changes |

**Indexes:** `(status, created_at desc)`, `category`, `provider_name`.

### 3. `donation_requests`

A recipient asking for a listing. One active workflow per listing in the current UI: requesting an Available listing moves that listing to `Requested`.

| Field | Type | Notes |
| --- | --- | --- |
| `_id` | ObjectId | Primary key |
| `listing_id` | ObjectId | Reference to `food_listings._id` |
| `listing_title` | string | Copy of title for the requests table |
| `recipient_user_id` | ObjectId | Optional link to `users` |
| `recipient_name` | string | Required |
| `organization` | string | Required |
| `contact` | string | Required |
| `quantity_requested` | int | ≥ 1 and ≤ listing quantity |
| `status` | string | See request statuses below |
| `created_at` | datetime | UTC |
| `updated_at` | datetime | Set when status changes |

**Indexes:** `listing_id`, `(status, created_at desc)`.

### 4. `donation_records`

Completed pickups. Created only when a request becomes `Collected`. One record per request (`request_id` is unique).

| Field | Type | Notes |
| --- | --- | --- |
| `_id` | ObjectId | Primary key |
| `listing_id` | ObjectId | Reference to `food_listings` |
| `request_id` | ObjectId | Unique reference to `donation_requests` |
| `listing_title` | string | Snapshot |
| `provider_name` | string | Snapshot |
| `recipient_name` | string | Snapshot |
| `organization` | string | Snapshot |
| `category` | string | Snapshot |
| `quantity_collected` | int | Taken from the request |
| `unit` | string | Taken from the listing |
| `collected_at` | datetime | UTC |

Snapshots mean reports still make sense if a listing is edited later. We do **not** copy the full listing document.

**Indexes:** `listing_id`, unique `request_id`.

## Status values and transitions

### Listing (`food_listings.status`)

`Available` → `Requested`, `Cancelled`, or `Expired`  
`Requested` → `Accepted`, `Available` (if the request is cancelled), or `Cancelled`  
`Accepted` → `Collected` or `Cancelled`  
`Collected`, `Cancelled`, and `Expired` are final.


### Request (`donation_requests.status`)

`Requested` → `Accepted` or `Cancelled`  
`Accepted` → `Collected` or `Cancelled`  
`Collected` and `Cancelled` are final.

When a request status changes, the linked listing is updated:

| Request becomes | Listing becomes |
| --- | --- |
| Requested | Requested |
| Accepted | Accepted |
| Collected | Collected |
| Cancelled | Available |

You cannot jump from `Requested` straight to `Collected`. Accept first, then mark collected.

## Why four collections (viva answer)

- **users** — who participates (provider / recipient / volunteer), separate from food.
- **food_listings** — what food is offered, searched, and filtered.
- **donation_requests** — who asked for which listing, and the workflow state.
- **donation_records** — what was actually collected, for impact reporting, without overwriting history on the listing.
