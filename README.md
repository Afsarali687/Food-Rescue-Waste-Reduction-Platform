# Food Rescue & Waste Reduction Platform Using MongoDB

[![Coursework CA2](https://img.shields.io/badge/Coursework-College%20CA2%20Project-success.svg)](#)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Framework](https://img.shields.io/badge/Framework-Flask%203.x-lightgrey.svg)](https://flask.palletsprojects.com/)
[![Database](https://img.shields.io/badge/Database-MongoDB%20%28NoSQL%29-green.svg)](https://www.mongodb.com/)
[![UN SDG](https://img.shields.io/badge/UN%20SDG-2%3A%20Zero%20Hunger-emerald.svg)](https://sdgs.un.org/goals/goal2)

A full-stack web application designed for a college CA2 evaluation project. The platform connects surplus food providers (campus canteens, restaurants, hostel mess facilities, bakeries) with authorized recipient NGOs, food banks, and certified community volunteers to minimize food waste and support families in need.

---

## 📖 Table of Contents
1. [Problem Statement & Objectives](#-problem-statement--objectives)
2. [Key Features](#-key-features)
3. [Architecture & Folder Structure](#-architecture--folder-structure)
4. [MongoDB Database & Collection Design](#-mongodb-database--collection-design)
5. [Concurrency, Transaction Safety & Standalone MongoDB](#-concurrency-transaction-safety--standalone-mongodb)
6. [MongoDB Aggregation Pipelines (Reports & Analytics)](#-mongodb-aggregation-pipelines-reports--analytics)
7. [Security Architecture](#-security-architecture)
8. [Prerequisites & Installation](#-prerequisites--installation)
9. [Windows Setup & Execution Commands](#-windows-setup--execution-commands)
10. [Environment Variable Configuration](#-environment-variable-configuration)
11. [Running Diagnostics & Automated Tests](#-running-diagnostics--automated-tests)
12. [End-to-End Workflow Walkthrough](#-end-to-end-workflow-walkthrough)
13. [Known Limitations & Future Enhancements](#-known-limitations--future-enhancements)
14. [GitHub Submission Checklist](#-github-submission-checklist)

---

## 🎯 Problem Statement & Objectives

### Problem Statement
Massive volumes of edible cooked meals, bakery products, and fresh groceries from institutional canteens, hostel dining halls, and banquet facilities are discarded daily due to inaccurate demand forecasting and tight shelf lives. Meanwhile, local shelters, orphanages, and community charity networks face chronic food shortages. The primary barrier is the absence of an immediate, real-time coordination bridge capable of tracking perishable food availability, pickup deadlines, and verified hand-offs.

### Project Objectives
1. **Reduce Edible Waste:** Allow food providers to rapidly list surplus portions before expiration.
2. **Real-time Recipient Matching:** Enable NGOs and community volunteers to search, filter, and claim portions.
3. **Structured Request Lifecycle:** Enforce clear status transitions (`Requested` &rarr; `Accepted` &rarr; `Collected` / `Cancelled`) with automated listing synchronization.
4. **Permanent Audit Trail:** Maintain immutable historical records of completed distributions in a dedicated `donation_records` collection.
5. **Data-Driven Analytics:** Leverage server-side MongoDB Aggregation Pipelines to measure food rescued, unit efficiency, category distributions, and daily activity trends.

---

## ✨ Key Features

* **Responsive Design System:** Clean, modern food-rescue aesthetic with a forest/emerald palette, Plus Jakarta Sans typography, and mobile-friendly Bootstrap 5 cards.
* **Surplus Food Directory:** Real-time search across title, provider, and description with category, location, and status filters.
* **Structured Donation Form:** 3-section listing creation with server-side validation enforcing positive whole numbers, accepted food categories, and pickup deadlines.
* **Safe Concurrency Claiming:** Prevents double-claiming, overselling, or claiming expired items using atomic optimistic locking (`find_one_and_update`).
* **Manage Requests Center:** Dedicated provider workflow control panel with contextual action buttons (`Accept`, `Mark Collected`, `Cancel`) and modal confirmations.
* **Aggregated Impact Dashboard:** Real-time reports computing total food rescued, volume listed vs. rescued by consistent units, category distribution, and daily timelines via MongoDB pipelines.
* **Defensive Application Security:** Native CSRF protection, secure cookies (`HttpOnly`, `SameSite=Lax`), HTTP defensive security headers, strict Jinja2 XSS escaping, and safe regex escaping.

---

## 📂 Architecture & Folder Structure

The application follows the **Application Factory** architectural pattern with modular Flask Blueprints:

```
Food-Rescue-Waste-Reduction-Platform/
│
├── app.py                            # Application entry point with host & debug configuration
├── seed_data.py                      # Database seeder (inserts sample users & listings if empty)
├── requirements.txt                  # Python runtime dependencies
├── .env                              # Local environment variables (IGNORED BY GIT)
├── .env.example                      # Safe template containing placeholder values
├── .gitignore                        # Git ignore rules (.env, venvs, __pycache__, etc.)
├── DATABASE.md                       # Comprehensive schema and data model documentation
├── README.md                         # Complete project documentation and viva defense guide
├── START_HERE.txt                    # Quick-start cheat sheet
│
├── food_rescue/                      # Core application package
│   ├── __init__.py                   # create_app() factory, security headers, CSRF registration
│   ├── config.py                     # Environment variable loader & cookie security options
│   ├── constants.py                  # Domain constants (roles, categories, units, statuses, transitions)
│   ├── csrf.py                       # Lightweight, dependency-free anti-CSRF token verification
│   ├── db.py                         # PyMongo connection lifecycle, index creation, ping helpers
│   ├── health.py                     # /health diagnostic API endpoint
│   ├── routes.py                     # Main Flask routes (/, /listings, /food/*, /requests, /reports)
│   ├── workflow.py                   # State machine, atomic optimistic locking, and audit recording
│   ├── aggregations.py               # Server-side MongoDB aggregation pipelines for reports
│   └── validation.py                 # Server-side validation rules & role checks
│
├── static/                           # Static assets
│   ├── css/
│   │   └── style.css                 # Custom design tokens, responsive cards, and badge components
│   └── js/
│       └── script.js                 # Submit spinners, double-click prevention, active nav tracking
│
├── templates/                        # Reusable Jinja2 templates extending base.html
│   ├── base.html                     # Unified header, live DB indicator, flash banners, footer
│   ├── index.html                    # Homepage: mission hero, search, summary cards, recent listings
│   ├── listings.html                 # Food directory with multi-filter bar and dynamic card grid
│   ├── food_form.html                # 3-section surplus food publishing form
│   ├── food_detail.html              # Item overview, donor contact, and claim form
│   ├── requests.html                 # Request tracking table and authorized workflow action buttons
│   └── reports.html                  # Impact dashboard backed by MongoDB aggregation pipelines
│
├── tests/                            # Automated test suite (43 test cases)
│   ├── __init__.py
│   ├── test_app_factory.py           # HTTP view rendering and health endpoint tests
│   ├── test_db.py                    # DB connection, index creation, and collection access tests
│   ├── test_validation.py            # Unit tests for input validation, numbers, and allowed roles
│   ├── test_workflow.py              # Lifecycle state transitions, quantity limits, duplicate checks
│   ├── test_aggregations.py          # MongoDB aggregation pipeline correctness tests
│   └── test_security_and_edge_cases.py# CSRF, security headers, XSS escaping, malformed ObjectIds
│
└── scripts/
    └── check_foundation.py           # Automated diagnostic script checking AST syntax & MongoDB health
```

---

## 🗄️ MongoDB Database & Collection Design

Database name: `food_rescue_db` (configured via `MONGO_DB` in `.env`).

```
                    ┌──────────────┐
                    │    users     │
                    └──────┬───────┘
                           │ (optional reference)
                           ▼
┌──────────────────┐  1:N   ┌───────────────────┐  1:1   ┌──────────────────┐
│  food_listings   │◄───────┤ donation_requests ├───────►│ donation_records │
└──────────────────┘        └───────────────────┘        └──────────────────┘
```

### 1. `users` Collection
Directory of participants (campus providers, recipient NGOs, student volunteers).
```javascript
{
  "_id": ObjectId("6ad105ebb3cd3162c4800312"),
  "name": "Campus Canteen Desk",
  "role": "provider", // "provider", "recipient", or "volunteer"
  "organization": "Green Campus Canteen",
  "contact": "canteen@example.org",
  "location": "Campus Main Gate",
  "created_at": ISODate("2026-10-15T16:57:15.090Z")
}
```
* **Indexes:** `role: 1`, `organization: 1`.

### 2. `food_listings` Collection
Surplus food published by providers for redistribution.
```javascript
{
  "_id": ObjectId("6ad105ebb3cd3162c4800315"),
  "title": "Fresh vegetarian lunch boxes",
  "provider_name": "Green Campus Canteen",
  "category": "Cooked Meals",
  "quantity": 25,
  "unit": "servings", // "servings", "packs", "kg", "boxes"
  "location": "Campus Main Gate",
  "expiry_time": "Today, 6:00 PM",
  "pickup_deadline": "Today, 5:30 PM",
  "description": "Nutritious sealed vegetarian thali boxes prepared fresh today.",
  "contact": "canteen@example.org",
  "status": "Available", // "Available", "Requested", "Accepted", "Collected", "Cancelled", "Expired"
  "created_at": ISODate("2026-10-15T16:45:00.000Z"),
  "updated_at": ISODate("2026-10-15T16:45:00.000Z")
}
```
* **Indexes:** `[('status', 1), ('created_at', -1)]`, `category: 1`, `provider_name: 1`, `location: 1`.

### 3. `donation_requests` Collection
Claims placed by recipient organizations for a food listing.
```javascript
{
  "_id": ObjectId("6ad10605dd4e9194c365bae3"),
  "listing_id": ObjectId("6ad105ebb3cd3162c4800315"),
  "listing_title": "Fresh vegetarian lunch boxes",
  "recipient_name": "Sarah Jenkins",
  "organization": "City Food Bank",
  "contact": "sarah@shelter.org",
  "quantity_requested": 10,
  "status": "Requested", // "Requested", "Accepted", "Collected", "Cancelled"
  "created_at": ISODate("2026-10-15T17:00:00.000Z"),
  "updated_at": ISODate("2026-10-15T17:00:00.000Z")
}
```
* **Indexes:** `listing_id: 1`, `[('status', 1), ('created_at', -1)]`.

### 4. `donation_records` Collection
Permanent historical snapshot written only when a donation reaches `Collected`.
```javascript
{
  "_id": ObjectId("6ad10605dd4e9194c365baeb"),
  "listing_id": ObjectId("6ad105ebb3cd3162c4800315"),
  "request_id": ObjectId("6ad10605dd4e9194c365bae3"),
  "listing_title": "Fresh vegetarian lunch boxes",
  "provider_name": "Green Campus Canteen",
  "recipient_name": "Sarah Jenkins",
  "organization": "City Food Bank",
  "category": "Cooked Meals",
  "quantity_collected": 10,
  "unit": "servings",
  "collected_at": ISODate("2026-10-15T17:30:00.000Z")
}
```
* **Indexes:** `listing_id: 1`, `request_id: 1` (**unique: true** &mdash; guarantees idempotency).

---

## 🔒 Concurrency, Transaction Safety & Standalone MongoDB

### The Standalone MongoDB Limitation
MongoDB multi-document transactions (`session.start_transaction()`) require a replica set or sharded cluster. In default local student development, MongoDB Community Server runs as a **single-node standalone process** (`isMaster.setName = None`). Attempting transactions on a standalone instance raises:
`OperationFailure: Transaction numbers are only allowed on a replica set member or mongos`.

### Safe Alternative Implemented
1. **Single-Document Atomic Optimistic Locking:**
   When a claim is submitted, [food_rescue/workflow.py](file:///c:/Users/hp/Downloads/Food-Rescue-Waste-Reduction-Platform/food_rescue/workflow.py) calls PyMongo's atomic `find_one_and_update`:
   ```python
   reserved = food_listings_col().find_one_and_update(
       {
           "_id": listing_oid,
           "status": "Available",
           "quantity": {"$gte": requested_qty},
       },
       {"$set": {"status": "Requested", "updated_at": _now()}},
       return_document=ReturnDocument.AFTER,
   )
   ```
   MongoDB's WiredTiger storage engine serializes this check atomically. If another claimant clicks concurrently or the listing is no longer available, the query matches 0 documents and returns `None`, cleanly aborting the claim without data races.
2. **Compensating Action (Saga Pattern):**
   If inserting the subsequent `donation_requests` document throws any database exception, an exception handler immediately executes a compensating rollback:
   ```python
   food_listings_col().update_one(
       {"_id": listing_oid, "status": "Requested"},
       {"$set": {"status": "Available", "updated_at": _now()}},
   )
   ```
3. **Idempotent Audit Recording:**
   `donation_records` enforces a unique index on `request_id`. Even under duplicate network submissions, a completed rescue can never produce redundant audit entries.

---

## 📊 MongoDB Aggregation Pipelines (Reports & Analytics)

All analytics on `/reports` are computed live by MongoDB without in-memory Python calculations:

### 1. Listings Status & Volume Overview
Aggregates total, available, expired, and listed volumes in a single aggregation pass using conditional sums:
```javascript
db.food_listings.aggregate([
  {
    $group: {
      _id: null,
      total_listings: { $sum: 1 },
      total_quantity_listed: { $sum: { $ifNull: ["$quantity", 0] } },
      available_listings: { $sum: { $cond: [{ $eq: ["$status", "Available"] }, 1, 0] } },
      expired_listings: { $sum: { $cond: [{ $eq: ["$status", "Expired"] }, 1, 0] } },
      collected_listings: { $sum: { $cond: [{ $eq: ["$status", "Collected"] }, 1, 0] } }
    }
  },
  {
    $project: {
      _id: 0,
      total_listings: 1,
      total_quantity_listed: 1,
      available_listings: 1,
      expired_listings: 1,
      collected_listings: 1
    }
  }
])
```

### 2. Grouping by Consistent Units
Ensures volumes in different units (`servings`, `packs`, `kg`, `boxes`) are never added together:
```javascript
// Listed by unit from food_listings
db.food_listings.aggregate([
  { $group: { _id: { $ifNull: ["$unit", "servings"] }, listed_quantity: { $sum: { $ifNull: ["$quantity", 0] } }, count: { $sum: 1 } } },
  { $sort: { listed_quantity: -1 } }
])

// Rescued by unit from donation_records
db.donation_records.aggregate([
  { $group: { _id: { $ifNull: ["$unit", "servings"] }, rescued_quantity: { $sum: { $ifNull: ["$quantity_collected", 0] } }, count: { $sum: 1 } } },
  { $sort: { rescued_quantity: -1 } }
])
```

### 3. Daily Donation Timeline via `$dateToString`
Formats timestamps into UTC date strings and groups daily volume:
```javascript
db.donation_records.aggregate([
  { $match: { collected_at: { $ne: null } } },
  {
    $project: {
      date: { $dateToString: { format: "%Y-%m-%d", date: "$collected_at" } },
      quantity_collected: { $ifNull: ["$quantity_collected", 0] }
    }
  },
  {
    $group: {
      _id: "$date",
      rescues_count: { $sum: 1 },
      total_quantity_collected: { $sum: "$quantity_collected" }
    }
  },
  { $sort: { _id: -1 } },
  { $limit: 14 }
])
```

---

## 🛡️ Security Architecture

| Security Domain | Defense Mechanism | Implementation Details |
| :--- | :--- | :--- |
| **Cross-Site Request Forgery (CSRF)** | Session-backed Anti-CSRF Token | Implemented in [food_rescue/csrf.py](file:///c:/Users/hp/Downloads/Food-Rescue-Waste-Reduction-Platform/food_rescue/csrf.py) using `secrets.token_hex(32)` and constant-time string comparison (`secrets.compare_digest`). Injected into every POST form. |
| **Cross-Site Scripting (XSS)** | Jinja2 Contextual Auto-escaping | All user inputs are strictly escaped; zero unescaped `\| safe` filters are used in templates. |
| **NoSQL / Regex Injection** | Regex Escaping & BSON Typing | User search terms are escaped via `re.escape(query[:100])`. ObjectIds are strictly parsed with BSON `ObjectId(hex_string)`. |
| **State Tampering via GET** | HTTP Method Restrictions | State changes strictly reject GET requests with `405 Method Not Allowed`. |
| **Clickjacking & Sniffing** | Defensive HTTP Headers | `@app.after_request` injects `X-Frame-Options: SAMEORIGIN`, `X-Content-Type-Options: nosniff`, `X-XSS-Protection: 1; mode=block`. |
| **Session Cookie Hijacking** | Cookie Security Flags | Configured in [food_rescue/config.py](file:///c:/Users/hp/Downloads/Food-Rescue-Waste-Reduction-Platform/food_rescue/config.py) with `SESSION_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_SAMESITE = "Lax"`. |
| **Secret & Credential Exposure** | Strict Environment Separation | `.env` is ignored by `.gitignore`. `.env.example` contains only safe placeholder values. `/health` API exposes no connection strings. |
| **Production Debug Mode** | Environment-driven Flags | `app.py` controls debug mode via `FLASK_DEBUG` rather than hardcoded `debug=True`. |

---

## 💻 Prerequisites & Installation

* **Operating System:** Windows 10/11, macOS, or Linux.
* **Python:** Python 3.10, 3.11, 3.12, or 3.13.
* **MongoDB:** MongoDB Community Server (v6.0 or v7.0) running locally at `mongodb://127.0.0.1:27017/` **OR** a MongoDB Atlas cloud cluster.

---

## 🪟 Windows Setup & Execution Commands

Follow these exact commands in Windows PowerShell:

### 1. Open Project Directory
```powershell
cd c:\Users\hp\Downloads\Food-Rescue-Waste-Reduction-Platform
```

### 2. Create and Activate Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
*(If PowerShell restricts script execution, run in Command Prompt: `.venv\Scripts\activate.bat` or run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy the template to create `.env`:
```powershell
Copy-Item .env.example .env
```

### 5. Verify Local MongoDB is Running
Make sure MongoDB Community Server is started:
```powershell
Get-Service -Name MongoDB
```
*(If stopped, start it via `Start-Service MongoDB` or by running `mongod`)*

### 6. Seed Sample Demonstration Data
```powershell
python seed_data.py
```

### 7. Run Automated Diagnostics & Unit Tests
```powershell
# Run the foundation verification script
python scripts/check_foundation.py

# Run all 43 automated unit, integration, and security tests
python -m unittest discover tests -v
```

### 8. Start the Development Server
```powershell
python app.py
```
Open your browser at:
* **Web Application:** `http://127.0.0.1:5000`
* **Browse Food Directory:** `http://127.0.0.1:5000/listings`
* **Donation Requests Workflow:** `http://127.0.0.1:5000/requests`
* **Impact Reports Dashboard:** `http://127.0.0.1:5000/reports`
* **API Health Diagnostic:** `http://127.0.0.1:5000/health`

---

## ⚙️ Environment Variable Configuration

Create `.env` based on `.env.example`:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `MONGO_URI` | `mongodb://127.0.0.1:27017/` | Connection URI for local MongoDB or MongoDB Atlas cluster. |
| `MONGO_DB` | `food_rescue_db` | Target database name. |
| `MONGO_TIMEOUT_MS` | `2500` | Server selection timeout in milliseconds. |
| `SECRET_KEY` | *(auto-generated random)* | Secret key for signed session cookies and flash messages. |
| `FLASK_DEBUG` | `True` | Set to `False` in production deployments. |

---

## 🧪 Running Diagnostics & Automated Tests

The platform includes a test suite with **43 automated tests**:

```powershell
python -m unittest discover tests -v
```

### Test Suite Organization:
1. [tests/test_workflow.py](file:///c:/Users/hp/Downloads/Food-Rescue-Waste-Reduction-Platform/tests/test_workflow.py) (9 tests):
   - Claim submission, quantity validation (cannot exceed available), duplicate active request blocking, expired food rejection, role authorization, lifecycle transitions (`Requested` &rarr; `Accepted` &rarr; `Collected`), cancellations, and expiration marking.
2. [tests/test_security_and_edge_cases.py](file:///c:/Users/hp/Downloads/Food-Rescue-Waste-Reduction-Platform/tests/test_security_and_edge_cases.py) (8 tests):
   - HTTP security response headers (`X-Frame-Options`, `X-Content-Type-Options`), session cookie flags, anti-CSRF token verification, XSS template escaping, regex metacharacter resilience, and rejection of state modifications via HTTP GET.
3. [tests/test_aggregations.py](file:///c:/Users/hp/Downloads/Food-Rescue-Waste-Reduction-Platform/tests/test_aggregations.py) (6 tests):
   - MongoDB aggregation pipelines, consistent unit volume analysis, category breakdown, request statuses, and daily activity timeline.
4. [tests/test_validation.py](file:///c:/Users/hp/Downloads/Food-Rescue-Waste-Reduction-Platform/tests/test_validation.py) (7 tests):
   - Server-side validators, positive integer bounds, food categories, pickup deadlines.
5. [tests/test_db.py](file:///c:/Users/hp/Downloads/Food-Rescue-Waste-Reduction-Platform/tests/test_db.py) (5 tests):
   - MongoDB configuration, collection accessors, index creation, live ping, and offline fallback.
6. [tests/test_app_factory.py](file:///c:/Users/hp/Downloads/Food-Rescue-Waste-Reduction-Platform/tests/test_app_factory.py) (8 tests):
   - Application factory initialization, HTTP 200 view rendering, and `/health` endpoint response.

---

## 🔄 End-to-End Workflow Walkthrough

1. **Publish Surplus Food:**
   - Provider navigates to **Donate Food** (`/food/new`).
   - Fills in Food Title, Category, Quantity (e.g., 20 servings), Location, Expiry Time, and Pickup Deadline.
   - Listing appears immediately in the directory with status `Available`.
2. **Claim Donation:**
   - NGO coordinator navigates to **Browse Food** (`/listings`) or views an individual item (`/food/<id>`).
   - Selects their registered NGO from the dropdown or inputs their representative details.
   - Enters quantity to claim (e.g., 10 servings).
   - Atomic optimistic locking transitions the listing to `Requested`.
3. **Approve & Coordinate:**
   - Food provider visits **Manage Requests** (`/requests`).
   - Clicks **Accept Request**. Both request and listing move to `Accepted`.
4. **Collect Food & Log Audit Record:**
   - Upon physical pickup, the provider clicks **Mark Collected**.
   - Request and listing transition to terminal state `Collected`.
   - Immutable audit snapshot is written to `donation_records`.
5. **View Real-Time Impact:**
   - Visit **Impact Reports** (`/reports`).
   - Server-side aggregation pipelines reflect the newly rescued meals in the total volume, unit diversion efficiency bar, and daily activity timeline.

---

## 📌 Known Limitations & Future Enhancements

* **Directory vs. Full Authentication:** This academic prototype uses directory-style user profiles without password logins or session-based JWT authentication.
  * *Future Enhancement:* Add OAuth 2.0 or Flask-Login with bcrypt password hashing and email verification.
* **Partial Listing Claims:** When an item is claimed, the current workflow reserves the listing for that recipient.
  * *Future Enhancement:* Split remaining unrequested quantities into child listings automatically upon partial claim acceptance.
* **Geographic Proximity Matching:** Locations are currently searched using text regex.
  * *Future Enhancement:* Add GeoJSON `Point` coordinates and MongoDB `$near` geospatial indexing for distance-based sorting.
* **Automated Expiry Scheduler:** Expiration is checked upon request submission and can be manually marked by providers.
  * *Future Enhancement:* Implement a Celery / APScheduler background cron job to automatically mark listings as `Expired` once pickup deadlines pass.

---

## 📋 GitHub Submission Checklist

Before submitting or pushing code to your repository:

- [x] **No Hardcoded Credentials:** Confirmed `.env` is listed in `.gitignore` and `.env.example` contains only safe placeholder values.
- [x] **Database Safety:** Code uses environment variables (`MONGO_URI`, `MONGO_DB`) without hardcoded passwords.
- [x] **All 43 Automated Tests Pass:** Executed `python -m unittest discover tests -v` with 0 failures or errors.
- [x] **AST Syntax Check Passes:** Executed `python scripts/check_foundation.py` with all 19 Python files parsed cleanly.
- [x] **CSRF Protection Active:** Anti-CSRF token verification enabled across all POST forms.
- [x] **Defensive Security Headers:** `X-Frame-Options`, `X-Content-Type-Options`, and `X-XSS-Protection` injected.
- [x] **No Raw XSS Vulnerabilities:** Zero unescaped `| safe` template filters.
- [x] **No Unsafe State Changes via GET:** Mutation routes enforce `POST` only.
- [x] **Clean Repository State:** No temporary scratch files, test dumps, or `__pycache__` committed.
