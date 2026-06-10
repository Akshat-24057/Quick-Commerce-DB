# Quick Commerce Demand & Supply Database System

This repository contains a DBMS project for a **quick commerce platform** (similar to Blinkit, Zepto, or Instamart) focused on **real-time inventory accuracy, order fulfillment, warehouse operations, and analytics**.

The archive includes:
- A **Streamlit application** for interacting with the system
- A **MySQL-backed database module** with schema creation, triggers, seed data, and transaction demos
- A full **SQL schema file**
- Supporting project documents in PDF format, including business requirements and ER / relational models

## Project Goals

The system is designed to support:
- Ultra-fast delivery workflows (roughly **10–20 minutes**)
- Distributed **dark store / warehouse** inventory management
- Batch-level stock tracking with **expiry awareness**
- Order placement, tracking, and fulfillment
- Delivery partner assignment and performance reporting
- Inventory alerts, replenishment, and stock ledger audit trails
- Transaction and concurrency demonstrations for DBMS learning

## Main Features

### 1. Dashboard
- Orders today
- Revenue today
- Active orders
- Open inventory alerts
- Customer count
- Available delivery partners
- Recent orders and warehouse revenue visualizations

### 2. Order Management
- Browse products by warehouse
- Add items to cart
- Place orders with payment method selection
- Auto-generate order numbers
- Record payments
- Assign an available delivery partner

### 3. Order History & Tracking
- Filter by customer
- Filter by status
- Search by order number
- View item-level order details

### 4. Inventory Management
- Stock overview by warehouse
- Batch-level details
- Inventory alerts
- Stock ledger tracking
- Stock replenishment workflows
- Expiry monitoring

### 5. Analytics & Reports
- Top-selling products
- Revenue analysis
- Customer analysis
- Warehouse performance
- Delivery partner performance
- Expiring inventory insights

### 6. Transactions / Concurrency Demo
- Embedded transaction demos inside the database module
- Commit and rollback scenarios
- Conflict / locking demonstrations for teaching database isolation concepts

### 7. Admin Panel
- View and add customers
- View and add delivery partners
- Trigger / demo utilities
- About section

## Repository Structure

```text
quick_commerce/
├── Business Requirements.pdf
├── Database_ER_and_Relational_Models.pdf
├── ER-DIAGRAM.pdf
├── quick_commerce_database.sql
└── app/
    ├── app.py
    └── database.py
```

## Important Technical Notes

### Application stack
- **Frontend:** Streamlit
- **Backend language:** Python
- **Database:** MySQL
- **Visualizations:** Plotly + Pandas

### Python dependencies
Install at least these packages:

```bash
pip install streamlit pandas plotly mysql-connector-python
```

### Database initialization behavior
The Streamlit app uses `app/database.py`, which:
- connects to MySQL
- creates the database if needed
- creates tables programmatically
- creates triggers
- seeds sample data
- prepares transaction demo objects

This means the app is designed to be **self-initializing** when MySQL is available.

### Database name mismatch to be aware of
There is an important naming inconsistency in the archive:
- `quick_commerce_database.sql` creates and uses database: `quick_commerce`
- `app/database.py` defaults to database: `quick_commerce_new`

To avoid confusion, use **one** of these approaches:
1. **Preferred for running the app:** set `MYSQL_DATABASE=quick_commerce_new` and let `database.py` initialize everything itself.
2. **If you want to use the provided SQL file directly:** either change the app configuration to `quick_commerce`, or edit the SQL / environment so both use the same database name.

## Configuration

You can configure MySQL in either of these ways.

### Option A: Streamlit secrets
Create `.streamlit/secrets.toml`:

```toml
[mysql]
host = "localhost"
port = 3306
user = "root"
password = "YOUR_PASSWORD_HERE"
database = "quick_commerce_new"
```

### Option B: Environment variables

```bash
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=root
export MYSQL_PASSWORD=YOUR_PASSWORD_HERE
export MYSQL_DATABASE=quick_commerce_new
```

## How to Run

1. Make sure **MySQL** is running.
2. Install the required Python packages.
3. Open the project directory.
4. Go to the app folder:

```bash
cd app
```

5. Start the Streamlit app:

```bash
streamlit run app.py --server.port 8501
```

6. Open the local Streamlit URL shown in the terminal.

## Core Data Model

From the included SQL schema, the system defines **18 tables** and **3 views**.

### Key tables
- `Category`
- `Supplier`
- `Product`
- `Warehouse`
- `Batch_Inventory`
- `Inventory`
- `Customer`
- `Delivery_Partner`
- `Orders`
- `Order_Item`
- `Payment`
- `Stock_Ledger`
- `Coupon`
- `Order_Coupon`
- `Product_Review`
- `Delivery_Rating`
- `Warehouse_Inventory_Alert`
- `Customer_Address`

### Views
- `Available_Inventory`
- `Order_Summary`
- `Product_Performance`

## Trigger / Audit Logic

The project includes database trigger logic for behaviors such as:
- auto-deducting stock when order items are inserted
- recording stock movements in the ledger
- generating low-stock / out-of-stock alerts

This supports the project’s focus on:
- **inventory correctness**
- **auditability**
- **transaction safety**

## Educational Value

This project is especially useful for:
- DBMS coursework
- ER-to-relational mapping practice
- trigger and transaction demonstrations
- inventory and order management system design
- analytics dashboards backed by relational data

