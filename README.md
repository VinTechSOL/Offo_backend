# OFFO Backend

OFFO (Order Food From Office) is a cafeteria food-ordering platform designed for offices, campuses, hospitals, and other workplace environments.

The OFFO Backend provides the APIs and business logic required by the User, Vendor, and Admin frontends.

It handles:

- Authentication
- OTP-based signup/login
- User context and locations
- Cafeterias and branches
- Menu management
- Cart management
- Order processing
- Scheduled orders
- Payments
- Refunds
- Notifications
- Vendor staff
- Roles and permissions
- Support tickets
- Feedback
- File and image uploads
- Background jobs
- Database migrations

---

# Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend programming language |
| FastAPI | REST API framework |
| SQLModel | Database models and ORM layer |
| PostgreSQL | Primary relational database |
| Alembic | Database migrations |
| Redis | OTP, rate limiting, and temporary/session data |
| APScheduler | Background scheduled jobs |
| AWS S3 | File and image storage |
| PhonePe | Payment processing |
| MSG91 | OTP/SMS delivery |
| Uvicorn | ASGI application server |
| Nginx | Reverse proxy / frontend web server |
| AWS EC2 | Production backend server |

---

# Architecture

The backend follows a **modular monolith / layered architecture**.

The application is maintained as one backend service while functionality is separated into logical modules.

The main flow is:

```text
Frontend
   |
   | HTTPS / REST API
   v
Nginx / API Endpoint
   |
   v
FastAPI
   |
   +-------------------+
   |                   |
   v                   v
Services            API Routes
   |
   +--------+---------+----------+
   |        |         |          |
   v        v         v          v
PostgreSQL Redis     S3       External APIs
                         |
                         +--> PhonePe
                         |
                         +--> MSG91

The backend remains the source of truth for:

Authentication
Authorization
Orders
Payments
Refunds
Database state
Vendor permissions
File validation
Business rules
Repository Structure


Keep the actual repository structure as the source of truth if a module or directory differs.

Core Backend Modules

The backend currently contains functionality for:

Authentication
Users
Locations
Cafeteria / Vendor
Menu
Cart
Orders
Payments
Notifications
Staff
Permissions
Support
Feedback
Database

OFFO uses PostgreSQL as the primary database.

The database is divided into logical schemas.

Examples include:

core
locations
catalog
orders
payments
support

This keeps different areas of the application logically organized while still operating within the same PostgreSQL database.

Database Tables

The main database tables include:

core.signup_sessions
core.refresh_sessions

core.users
core.user_addresses
core.user_context

locations.cities
locations.campuses
locations.buildings

core.cafeteria
core.cafe_branch
core.branch_documents

catalog.item_types
catalog.menu_categories
catalog.menu_items
catalog.branch_menu_items

orders.cart
orders.cart_items

orders.orders
orders.order_items
orders.order_status_logs

payments.payment_intents
payments.payment_intent_orders
payments.payment_attempts

orders.payment_events

core.notifications

core.permissions
core.role_permissions
core.staff
core.staff_refresh_tokens
core.staff_roles

support.tickets
support.ticket_messages

support.vendor_tickets
support.vendor_ticket_messages

support.feedback
Authentication

OFFO uses mobile-number based authentication with OTP verification.

Signup Flow
User
 |
 | Name + Mobile Number
 v
Signup API
 |
 v
SignupSession
 |
 | OTP
 v
MSG91
 |
 v
User enters OTP
 |
 v
OTP Verification
 |
 v
User Account

A SignupSession represents a temporary signup state.

A signup session should not be treated as a registered user until OTP verification has been successfully completed.

Signup Sessions

Signup sessions store temporary information required to complete registration.

They are separate from:

core.users

This distinction is important.

For example:

Signup started
      |
      v
SignupSession created
      |
      +---- OTP fails/never verified
      |
      v
User does not become registered

The backend should use expiration/validation rules to prevent stale signup sessions from remaining usable indefinitely.

Refresh Sessions

OFFO maintains refresh-session information for authenticated users.

The refresh flow is:

Access Token
     |
     | expired
     v
Refresh Token / Session
     |
     v
Refresh API
     |
     v
New Access Token

Refresh sessions are associated with users.

Users

The user system contains:

User
UserAddress
UserContext

A user contains basic account information such as:

User ID
First name
Last name
Mobile number
OTP verification state
Created timestamp
Updated timestamp
User Context

The user context represents the user's selected workplace location.

The hierarchy is:

City
  ↓
Campus
  ↓
Building

This context is used to identify cafeterias and branches relevant to the user.

Locations

The location system contains:

City
Campus
Building

Relationships:

City
 └── Campus
      └── Building

Cafeteria branches can be associated with the relevant location hierarchy.

Cafeterias

A cafeteria represents a vendor/cafeteria entity.

A cafeteria can have multiple branches.

Cafeteria
   |
   +---- Branch
   |
   +---- Branch
   |
   +---- Branch

Cafeteria information includes basic business/contact information and active status.

Cafe Branch

A branch represents a physical cafeteria location.

Branch information can include:

Branch name
City
Campus
Building
Address
Opening time
Closing time
Latitude
Longitude
Branch image
Business type
FSSAI information
GST information
Bank information
Owner information
Active status

Branch documents are stored separately.

Branch Documents

Branch documents contain information associated with a cafeteria branch.

Examples can include:

Business documents
Registration documents
Food-related documents
Other required vendor documents

The actual file is stored in AWS S3 while the URL/reference is stored in PostgreSQL.

Menu

The menu system consists of:

ItemType
MenuCategory
MenuItem
BranchMenuItem

The general relationship is:

Item Type
    |
    v
Menu Item
    |
    v
Branch Menu Item
    |
    v
Cafe Branch
Menu Categories

Menu categories organize food items.

Examples:

Breakfast
Lunch
Snacks
Beverages
Desserts

The actual categories depend on vendor configuration.

Menu Items

Menu items contain information such as:

Name
Price
Item type
Food information
Image
Availability

The menu item represents the reusable food item.

Branch Menu Items

A branch menu item connects a menu item to a specific branch.

This allows the same menu item to exist at multiple branches while each branch can have its own configuration.

The branch/item relationship is protected by a uniqueness constraint.

Cart

The cart system contains:

Cart
CartItem

A cart belongs to the user and contains the items selected for ordering.

The cart stores the required branch/menu item information and quantity.

Cart Flow
User
 ↓
Select Cafeteria
 ↓
Select Menu Item
 ↓
Add to Cart
 ↓
Update Quantity
 ↓
Remove Item
 ↓
Checkout

Cart operations are handled through backend APIs.

Orders

The order system contains:

Order
OrderItem
OrderStatusLog

The order represents the customer's purchase.

Order items preserve the relevant item and price information at the time the order was created.

This is important because menu prices may change later.

Order Status

Supported order statuses:

CREATED
PREPARING
READY
PICKED_UP
COMPLETED
REJECTED
CANCELLED

The backend controls valid state transitions.

Order Status History

Every important order status transition can be recorded in:

orders.order_status_logs

This provides a historical record of order state changes.

Example:

CREATED
   ↓
PREPARING
   ↓
READY
   ↓
PICKED_UP
   ↓
COMPLETED
Instant Orders

Instant orders are intended for food required during the current operating period.

The backend applies expiration logic to prevent stale active orders from remaining open indefinitely.

The automatic cancellation scheduler checks instant orders periodically.

Scheduled Orders

Users can place orders for a future time.

Scheduled orders contain the required scheduling information and are handled separately from instant orders.

The scheduler performs reminder and expiration-related operations.

Order Expiration

The backend contains automatic order cancellation logic.

The scheduler checks orders periodically.

Current behavior includes:

Instant orders
→ expire after the configured active window

Scheduled orders
→ expire after the configured post-scheduled window

Rows are locked while processing to reduce the possibility of concurrent cancellation.

If a paid order is automatically cancelled, the payment can be moved into the refund workflow.

Order Priority

The backend calculates operational urgency for the vendor UI.

Priority is based on how close the order is to its relevant preparation/pickup time.

The priority levels are:

HIGH
NORMAL
LOW

Priority is primarily a UI/operational urgency concept and does not replace the actual order status.

Order Bill Calculation

The order service calculates the order subtotal from order items.

Conceptually:

Item Price × Quantity
        ↓
Items Subtotal

The backend also supports:

Platform Fee
GST
Convenience Fee

The current order calculation uses the configured fee values.

The checkout convenience fee is associated with the payment intent's anchor order where applicable.

Payments

OFFO uses a payment-intent based payment architecture.

The payment system contains:

PaymentIntent
PaymentIntentOrder
PaymentAttempt
PaymentEvent
Payment Intent

A PaymentIntent represents the overall payment operation.

One payment intent can contain multiple orders.

For example:

PaymentIntent
 |
 +---- Order A
 |
 +---- Order B
 |
 +---- Order C

This allows multiple related orders to be represented under one payment operation.

Payment Intent Orders

PaymentIntentOrder links individual orders to a payment intent.

This creates the relationship between:

PaymentIntent
       |
       +---- Orders
Payment Attempts

A payment intent can have multiple attempts.

Payment attempts track gateway-related information such as:

Merchant order ID
PhonePe order ID
Gateway transaction ID
Merchant refund ID
Gateway refund ID
Attempt state

The payment system uses unique identifiers to reduce duplicate processing.

Payment Status

Supported payment states include:

PENDING
PAID
FAILED
REFUNDED
REFUND_PENDING

The backend payment service is authoritative for payment state.

Payment Events

Payment events provide a record of important payment operations.

Examples include:

PAYMENT_PENDING
PAYMENT_SUCCESS
PAYMENT_FAILED
REFUND_REQUESTED
REFUND_SUCCESS
REFUND_FAILED

Events are recorded to provide payment history and support idempotent processing.

PhonePe Integration

PhonePe is used for payment processing.

The backend communicates with PhonePe rather than allowing the frontend to directly determine payment success.

The general flow is:

Frontend
   ↓
Backend
   ↓
Payment Intent
   ↓
PhonePe
   ↓
Payment Result
   ↓
Backend Verification
   ↓
Database
   ↓
Frontend
Payment Synchronization

Payment status synchronization is handled by the backend payment service.

The backend:

Checks the payment state.
Records payment events.
Updates the payment attempt.
Updates the payment intent.
Updates the related order payment state.

The system prevents certain invalid payment-state rollbacks.

For example, an already-refunded payment should not simply be changed back to paid because of an outdated gateway response.

Refunds

Refunds are handled through a dedicated backend flow.

The refund lifecycle can include:

PAID
 ↓
REFUND_PENDING
 ↓
Refund Attempt
 ↓
PhonePe Refund
 ↓
REFUNDED
Automatic Refund Processing

The backend includes a scheduled refund processor.

It checks orders/payment intents requiring refund processing.

The processor:

Finds pending refunds.
Locks the relevant payment records.
Identifies the successful original payment attempt.
Creates a refund attempt.
Calls the payment provider.
Stores refund information.
Synchronizes the final refund state.
Refund Idempotency

Refund processing is designed to avoid duplicate refunds.

A refund attempt is persisted before the external gateway operation where required.

If an external request times out, the system retains the appropriate initiated state so the retry processor can query/reconcile the same refund operation instead of blindly creating another refund.

Redis

Redis is used for temporary/high-speed backend data.

Current uses include:

OTP storage
Rate limiting
Session-related temporary data

Redis should not be treated as the primary source of persistent business data.

PostgreSQL remains the source of truth for persistent application data.

OTP

OTP data is stored temporarily in Redis.

The general flow is:

User
 ↓
Request OTP
 ↓
Backend
 ↓
Generate OTP
 ↓
Redis
 ↓
MSG91
 ↓
User receives OTP
 ↓
Verify OTP
 ↓
Authentication

OTP values should expire automatically.

Rate Limiting

Redis can be used for rate-limiting sensitive operations such as OTP requests.

The goal is to prevent excessive requests and abuse while maintaining a simple implementation appropriate for the MVP.

MSG91

MSG91 is used for OTP/SMS delivery.

The backend communicates with MSG91.

Sensitive MSG91 credentials must remain server-side.

They must never be exposed to the frontend.

Notifications

The backend contains:

Notification
NotificationRecipient

Notifications are primarily used for in-app communication.

Examples include:

Order updates
Scheduled order reminders
Operational notifications
Other user/vendor notifications
Scheduled Notifications

The backend scheduler creates reminder notifications for scheduled orders.

The reminder process checks scheduled orders and sends the appropriate in-app notification before the scheduled time.

The notification process is designed to avoid repeatedly sending the same reminder.

APScheduler

APScheduler is used for recurring background jobs.

The scheduler currently handles jobs such as:

Auto-cancel orders
Scheduled-order reminders
Pending refunds

The scheduler runs with:

max_instances = 1
coalesce = True

This helps prevent overlapping executions of the same scheduled job.

Background Job Flow
APScheduler
    |
    +---- Auto Cancel
    |
    +---- Scheduled Reminder
    |
    +---- Pending Refund Processor

Jobs operate against PostgreSQL data and use transaction/locking logic where required.

Staff

Vendor/admin staff are represented separately from normal customer users.

Staff-related tables include:

core.staff
core.staff_roles
core.staff_refresh_tokens

This keeps staff authentication and authorization separate from customer accounts.

Roles

Staff roles are represented by:

StaffRole

Roles determine which permissions a staff member can access.

Permissions

Permissions are represented by:

Permission
RolePermission

The relationship is:

Staff
  ↓
Staff Role
  ↓
Role Permissions
  ↓
Permissions

Backend authorization is responsible for enforcing these permissions.

Support

The backend contains a customer support system.

Customer support includes:

Ticket
TicketMessage

A customer ticket can be associated with:

User
Order
Order item
Issue type
Description
Screenshot
Status
Vendor Support

Vendor support is intentionally separate.

Vendor support contains:

VendorTicket
VendorTicketMessage

This allows vendor operational support to be handled independently from customer support.

Feedback

Customer feedback is stored through:

support.feedback

Feedback can contain:

User
Order
Food rating
App rating
Comments
Creation timestamp

Feedback is associated with the order so that the platform can understand the context in which the feedback was submitted.

AWS S3

OFFO uses AWS S3 for centralized file and image storage.

S3 is used for areas such as:

Menu Item Images
Branch Images
Branch Documents
Support Ticket Screenshots
S3 Storage Design

Uploaded files are organized into module-specific folders.

The backend generates unique filenames using UUIDs.

Conceptually:

S3 Bucket
│
├── menu/
│   └── ...
│
├── branches/
│   └── ...
│
├── documents/
│   └── ...
│
└── support/
    └── ...

The exact folder names should follow the current backend implementation.

File Validation

The backend validates uploaded files before sending them to S3.

Current supported image types include:

JPEG
PNG
WEBP

Supported document types include:

PDF
JPEG
PNG
WEBP

Maximum sizes:

Images    → 400 KB
Documents → 1 MB
S3 URLs

After a successful upload:

File
 ↓
S3
 ↓
Unique S3 URL
 ↓
Database

The URL/reference is stored with the appropriate database entity.

This allows the frontend to retrieve the file without storing the actual file in PostgreSQL.

S3 Credentials

The backend supports different credential mechanisms depending on the environment.

Local Development

Local credentials can be configured using AWS environment variables where required.

Example:

AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=...
S3_BUCKET=...
AWS Production

The production EC2 environment can use the AWS IAM role instead of hardcoded access keys.

This avoids storing long-lived AWS credentials on the production server.

Database Migrations

Alembic is used for database schema migrations.

Migration files should be committed to source control.

After pulling a backend release:

alembic upgrade head

should be run before restarting the application when migrations are included.

Creating a Migration

After making an intentional model/schema change:

alembic revision --autogenerate -m "describe change"

Review the generated migration before applying it.

Do not blindly trust autogenerated migrations for complex schema changes.

Applying Migrations

Run:

alembic upgrade head

This upgrades the database to the latest migration.

Rolling Back a Migration

Alembic supports migration downgrade operations.

Example:

alembic downgrade -1

Only use downgrades when the migration and data implications are understood.

Environment Configuration

The backend uses environment-based configuration.

Sensitive values must not be committed to Git.

Typical configuration categories include:

Database
Redis
JWT/Auth
AWS
S3
PhonePe
MSG91
Application settings
Example Environment

The exact variable names must match the current settings implementation.

Conceptually:

DATABASE_URL=postgresql://...
REDIS_URL=redis://...

AWS_REGION=...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET=...

PHONEPE_...
MSG91_...

Never commit real production values.

Local Development
Requirements

Install:

Python
PostgreSQL
Redis

External services such as PhonePe, MSG91, and AWS S3 should be configured according to the development environment.

Python Environment

Create a virtual environment:

python3 -m venv venv

Activate it:

source venv/bin/activate

On Windows:

venv\Scripts\activate
Install Dependencies
pip install -r requirements.txt
Run Database Migrations
alembic upgrade head
Run Backend

Run the FastAPI application using Uvicorn according to the project's application entry point.

For example:

uvicorn app.main:app --reload

Use the actual module path configured by the repository if it differs.

API Documentation

FastAPI provides interactive API documentation.

When running locally, the documentation is normally available through:

/docs

and the OpenAPI schema through:

/openapi.json

These should be used during development to inspect available API contracts.

API Design

The backend exposes REST APIs grouped by functionality.

Typical areas include:

/auth
/users
/locations
/cafes
/menu
/cart
/orders
/payments
/notifications
/support
/staff
/admin

The exact endpoint paths should follow the current route definitions.

Transaction Handling

Operations that modify multiple related database records should use appropriate database transactions.

Examples include:

Creating an order
Updating order status
Payment state changes
Refund state changes
Cart operations where multiple records are affected

Transactions help prevent partially completed business operations.

Concurrency

Concurrency is particularly important for:

Orders
Payment state
Refunds
Automatic cancellation
Scheduled jobs

The backend uses database locking/transactional behavior where required to reduce conflicting updates.

For example, the auto-cancellation job locks the relevant rows before changing their state.

Idempotency

Payment operations must be designed so that repeated requests do not create duplicate financial effects.

This is particularly important for:

Payment callbacks
Payment synchronization
Refunds
Retry processing

The payment system stores gateway identifiers and attempt information to support safe reconciliation.

Error Handling

The backend should return appropriate HTTP status codes and structured error responses.

Common categories include:

400 - Invalid request
401 - Authentication required
403 - Permission denied
404 - Resource not found
409 - Conflict
422 - Validation error
500 - Internal server error

The exact response structure follows the FastAPI/Pydantic implementation.

Logging

The backend should log information necessary for diagnosing application errors.

Important areas include:

Authentication failures
Payment failures
Refund failures
Order-processing failures
Scheduled-job failures
S3 upload failures
External-service failures

Sensitive credentials, OTP values, tokens, and payment secrets must not be written to logs.

Monitoring

The current production approach focuses primarily on error monitoring, rather than introducing a large performance-monitoring stack.

Important production errors to monitor include:

Backend exceptions
Payment failures
Refund failures
Scheduler failures
Database errors
External API failures
S3 failures
Production Deployment

The OFFO backend is deployed on AWS EC2.

The current deployment does not use Docker or CI/CD.

The backend runs as a systemd service:

offo-backend.service
Production Backend Location

The repository is deployed under:

~/offo-backend

The backend application is located under:

~/offo-backend/backend
First-Time Backend Deployment

Connect to the EC2 server using MobaXterm/SSH.

Then:

cd ~

Clone the repository:

git clone <repository-url>

Enter the repository:

cd offo-backend

Verify the Git remote:

git remote -v

Fetch the repository:

git fetch origin

Checkout the production branch:

git checkout -B main origin/main

Pull the latest code:

git pull origin main

Enter the backend directory:

cd backend

Create the Python virtual environment:

python3 -m venv venv

Activate it:

source venv/bin/activate

Install dependencies:

pip install -r requirements.txt

Configure the production environment.

Run migrations:

alembic upgrade head

Configure the systemd service:

offo-backend.service

Restart the backend:

sudo systemctl restart offo-backend.service

Check the service:

sudo systemctl status offo-backend.service
Updating the Production Backend

For subsequent deployments:

cd ~/offo-backend

Pull the latest code:

git pull origin main

Enter the backend:

cd backend

Activate the virtual environment:

source venv/bin/activate

If dependencies changed:

pip install -r requirements.txt

Run migrations:

alembic upgrade head

Restart the backend:

sudo systemctl restart offo-backend.service

Check status:

sudo systemctl status offo-backend.service
Production API

The configured production API endpoint is:

https://api.offo.co.in

The frontend applications use this backend endpoint for production API communication.

Systemd Service

The backend runs as:

offo-backend.service

Useful commands:

sudo systemctl start offo-backend.service
sudo systemctl stop offo-backend.service
sudo systemctl restart offo-backend.service
sudo systemctl status offo-backend.service
Deployment Flow

The normal production update process is:

Developer
   |
   v
GitHub
   |
   v
AWS EC2
   |
   v
git pull
   |
   v
Install dependencies if required
   |
   v
Alembic migration
   |
   v
Restart systemd service
   |
   v
FastAPI
   |
   v
Production API
Security Guidelines

Never commit:

.env
Production database passwords
AWS secret keys
PhonePe credentials
MSG91 credentials
JWT secrets
Private keys

Use environment variables or the appropriate AWS/IAM mechanism.

Important Backend Rules
Database Is the Source of Truth

Do not rely on frontend state for:

Payment status
Order status
User authorization
Vendor permissions
Refund state
Payment State Is Backend Controlled

Never mark an order as paid merely because the frontend receives a successful UI response.

Payment state must be confirmed through the backend payment flow.

Refunds Must Be Safe to Retry

Refund processing must remain idempotent.

A retry should reconcile an existing refund attempt instead of blindly creating a second refund.

Order State Must Be Controlled

Order status transitions must follow backend business rules.

The frontend should not be able to arbitrarily change an order into any status.

Staff Permissions Must Be Backend Enforced

Frontend permission checks improve the user experience but are not a security boundary.

Every protected administrative/vendor operation must be authorized by the backend.

External Services

OFFO Backend integrates with:

PostgreSQL

Primary persistent database.

Redis

Temporary and high-speed data:

OTP
Rate limiting
Session-related data
AWS S3

File and image storage.

PhonePe

Payment processing and refunds.

MSG91

OTP/SMS delivery.

Backend Data Flow

A typical food-order flow is:

User Frontend
      |
      v
FastAPI
      |
      +---- User Context
      |
      +---- Cafeteria
      |
      +---- Menu
      |
      +---- Cart
      |
      +---- Order
      |
      +---- Payment Intent
      |
      v
PhonePe
      |
      v
Payment Result
      |
      v
FastAPI
      |
      v
PostgreSQL
      |
      v
Order Status
      |
      v
User / Vendor Frontend
Scheduled Processing

The scheduler operates independently of frontend activity.

For example:

Scheduled Order
      |
      v
APScheduler
      |
      +---- Reminder
      |
      +---- Expiration

Refund processing can similarly occur in the background:

REFUND_PENDING
      |
      v
Refund Processor
      |
      v
PhonePe
      |
      v
REFUNDED
Database Relationship Overview

The high-level relationship between major modules is:

User
 |
 +---- User Context
 |
 +---- Addresses
 |
 +---- Cart
 |
 +---- Orders
        |
        +---- Order Items
        |
        +---- Status Logs
        |
        +---- Payment Events
        |
        +---- Support Tickets
        |
        +---- Feedback

Cafeteria
 |
 +---- Branch
        |
        +---- Menu
        |
        +---- Documents
        |
        +---- Orders

Staff
 |
 +---- Staff Role
        |
        +---- Permissions
