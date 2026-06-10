-- ============================================================================
-- QUICK COMMERCE DEMAND & SUPPLY DATABASE SYSTEM (ENHANCED VERSION)
-- Database Schema with Comprehensive Improvements
-- Created for: IIIT Delhi DBMS Project - Group 78
-- Enhanced Version: Addresses gaps in original ER diagram while maintaining core structure
-- ============================================================================

DROP DATABASE IF EXISTS quick_commerce;
CREATE DATABASE quick_commerce;
USE quick_commerce;

-- ============================================================================
-- TABLE CREATION (Enhanced with additional fields and constraints)
-- ============================================================================

-- 1. CATEGORY TABLE
-- Hierarchical structure for product classification
CREATE TABLE Category (
    category_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    parent_category_id INT DEFAULT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_category_id) REFERENCES Category(category_id) ON DELETE SET NULL,
    INDEX idx_parent_category (parent_category_id),
    INDEX idx_active (is_active)
);

-- 2. SUPPLIER TABLE
-- Vendors who supply products to warehouses
CREATE TABLE Supplier (
    supplier_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(15) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    address TEXT NOT NULL,
    contact_person VARCHAR(100),
    gstin VARCHAR(15) UNIQUE, -- GST Identification Number for tax compliance
    rating DECIMAL(3, 2) DEFAULT 0.00 CHECK (rating >= 0 AND rating <= 5),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_active (is_active),
    INDEX idx_rating (rating)
);

-- 3. PRODUCT TABLE
-- Global product catalog
CREATE TABLE Product (
    product_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    brand VARCHAR(100),
    price DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
    weight DECIMAL(8, 2) NOT NULL CHECK (weight > 0), -- in grams or kg
    category_id INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    sku VARCHAR(50) UNIQUE, -- Stock Keeping Unit for inventory tracking
    barcode VARCHAR(50) UNIQUE, -- EAN/UPC barcode
    min_order_quantity INT DEFAULT 1 CHECK (min_order_quantity > 0),
    max_order_quantity INT DEFAULT 100,
    tax_rate DECIMAL(5, 2) DEFAULT 0.00 CHECK (tax_rate >= 0), -- Tax percentage
    image_url VARCHAR(500),
    shelf_life_days INT, -- Expected shelf life in days
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES Category(category_id) ON DELETE RESTRICT,
    CONSTRAINT chk_max_order_qty CHECK (max_order_quantity >= min_order_quantity),
    INDEX idx_category (category_id),
    INDEX idx_active (is_active),
    INDEX idx_sku (sku),
    INDEX idx_brand (brand)
);

-- 4. WAREHOUSE TABLE
-- Dark stores / micro-warehouses with geolocation
CREATE TABLE Warehouse (
    warehouse_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(200) NOT NULL,
    address TEXT NOT NULL,
    capacity INT NOT NULL CHECK (capacity > 0), -- maximum storage units
    latitude DECIMAL(10, 8), -- For distance calculations
    longitude DECIMAL(11, 8), -- For distance calculations
    serviceable_radius_km DECIMAL(5, 2) DEFAULT 5.00, -- Service area radius
    is_operational BOOLEAN DEFAULT TRUE,
    operating_hours_start TIME DEFAULT '06:00:00',
    operating_hours_end TIME DEFAULT '23:59:59',
    contact_phone VARCHAR(15),
    manager_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_operational (is_operational),
    INDEX idx_location (latitude, longitude)
);

-- 5. BATCH_INVENTORY TABLE
-- Tracks product batches by expiry date at each warehouse with enhanced fields
CREATE TABLE Batch_Inventory (
    batch_id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    warehouse_id INT NOT NULL,
    supplier_id INT NOT NULL,
    batch_number VARCHAR(50) UNIQUE, -- Supplier batch identification
    manufacture_date DATE NOT NULL,
    expiry_date DATE NOT NULL,
    initial_quantity INT NOT NULL CHECK (initial_quantity >= 0),
    current_quantity INT NOT NULL CHECK (current_quantity >= 0),
    reserved_quantity INT DEFAULT 0 CHECK (reserved_quantity >= 0), -- Items in pending orders
    reorder_level INT DEFAULT 10, -- Alert threshold for replenishment
    shelf_location VARCHAR(50), -- Physical location in warehouse (e.g., A-12-03)
    cost_price DECIMAL(10, 2), -- Procurement cost per unit
    is_damaged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES Product(product_id) ON DELETE RESTRICT,
    FOREIGN KEY (warehouse_id) REFERENCES Warehouse(warehouse_id) ON DELETE RESTRICT,
    FOREIGN KEY (supplier_id) REFERENCES Supplier(supplier_id) ON DELETE RESTRICT,
    CONSTRAINT chk_expiry_after_manufacture CHECK (expiry_date > manufacture_date),
    CONSTRAINT chk_current_lte_initial CHECK (current_quantity <= initial_quantity),
    CONSTRAINT chk_reserved_lte_current CHECK (reserved_quantity <= current_quantity),
    INDEX idx_warehouse (warehouse_id),
    INDEX idx_product (product_id),
    INDEX idx_expiry (expiry_date),
    INDEX idx_batch_number (batch_number),
    INDEX idx_reorder (current_quantity, reorder_level)
);

-- 6. INVENTORY TABLE
-- Aggregated view of total product quantity per warehouse
CREATE TABLE Inventory (
    inventory_id INT PRIMARY KEY AUTO_INCREMENT,
    warehouse_id INT NOT NULL,
    product_id INT NOT NULL,
    total_quantity INT NOT NULL DEFAULT 0 CHECK (total_quantity >= 0),
    reserved_quantity INT NOT NULL DEFAULT 0 CHECK (reserved_quantity >= 0),
    available_quantity INT GENERATED ALWAYS AS (total_quantity - reserved_quantity) STORED,
    last_restocked_at TIMESTAMP NULL,
    reorder_threshold INT DEFAULT 20,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (warehouse_id) REFERENCES Warehouse(warehouse_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES Product(product_id) ON DELETE CASCADE,
    UNIQUE KEY (warehouse_id, product_id),
    INDEX idx_warehouse (warehouse_id),
    INDEX idx_product (product_id),
    INDEX idx_available (available_quantity)
);

-- 7. CUSTOMER TABLE
-- End users of the platform with geolocation
CREATE TABLE Customer (
    customer_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(15) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    address TEXT NOT NULL,
    latitude DECIMAL(10, 8), -- For nearest warehouse matching
    longitude DECIMAL(11, 8), -- For nearest warehouse matching
    pincode VARCHAR(10),
    is_active BOOLEAN DEFAULT TRUE,
    preferred_warehouse_id INT, -- Customer's usual warehouse
    total_orders INT DEFAULT 0,
    total_spent DECIMAL(12, 2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (preferred_warehouse_id) REFERENCES Warehouse(warehouse_id) ON DELETE SET NULL,
    INDEX idx_phone (phone),
    INDEX idx_email (email),
    INDEX idx_active (is_active),
    INDEX idx_location (latitude, longitude)
);

-- 8. DELIVERY_PARTNER TABLE
-- Logistics personnel delivering orders with availability tracking
CREATE TABLE Delivery_Partner (
    partner_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(15) NOT NULL UNIQUE,
    email VARCHAR(100) UNIQUE,
    vehicle_type ENUM('Bike', 'Scooter', 'Bicycle', 'Car') NOT NULL,
    vehicle_number VARCHAR(20),
    license_number VARCHAR(30),
    address TEXT NOT NULL,
    assigned_warehouse_id INT, -- Primary warehouse assignment
    current_latitude DECIMAL(10, 8), -- Real-time location tracking
    current_longitude DECIMAL(11, 8), -- Real-time location tracking
    availability_status ENUM('Available', 'Busy', 'Offline', 'On Break') DEFAULT 'Available',
    rating DECIMAL(3, 2) DEFAULT 0.00 CHECK (rating >= 0 AND rating <= 5),
    total_deliveries INT DEFAULT 0,
    successful_deliveries INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (assigned_warehouse_id) REFERENCES Warehouse(warehouse_id) ON DELETE SET NULL,
    INDEX idx_warehouse (assigned_warehouse_id),
    INDEX idx_availability (availability_status),
    INDEX idx_active (is_active),
    INDEX idx_rating (rating)
);

-- 9. ORDERS TABLE
-- Customer orders fulfilled by warehouses with comprehensive tracking
CREATE TABLE Orders (
    order_id INT PRIMARY KEY AUTO_INCREMENT,
    order_number VARCHAR(50) UNIQUE, -- Human-readable order number (e.g., ORD-2026-00001)
    customer_id INT NOT NULL,
    warehouse_id INT NOT NULL,
    delivery_partner_id INT DEFAULT NULL,
    order_status ENUM('Placed', 'Confirmed', 'Processing', 'Packed', 'Out for Delivery', 'Delivered', 'Cancelled', 'Returned') NOT NULL DEFAULT 'Placed',
    payment_status ENUM('Pending', 'Paid', 'Failed', 'Refunded') DEFAULT 'Pending',
    placed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMP NULL,
    packed_at TIMESTAMP NULL,
    dispatched_at TIMESTAMP NULL,
    delivered_at TIMESTAMP NULL,
    cancelled_at TIMESTAMP NULL,
    expected_delivery_time TIMESTAMP, -- Promised delivery time (typically 10-20 mins)
    actual_delivery_time_minutes INT, -- Actual time taken for delivery
    subtotal DECIMAL(10, 2) NOT NULL DEFAULT 0.00 CHECK (subtotal >= 0),
    tax_amount DECIMAL(10, 2) DEFAULT 0.00 CHECK (tax_amount >= 0),
    delivery_fee DECIMAL(10, 2) DEFAULT 0.00 CHECK (delivery_fee >= 0),
    discount_amount DECIMAL(10, 2) DEFAULT 0.00 CHECK (discount_amount >= 0),
    total_amount DECIMAL(10, 2) NOT NULL CHECK (total_amount >= 0),
    cancellation_reason TEXT,
    delivery_instructions TEXT,
    distance_km DECIMAL(5, 2), -- Distance between customer and warehouse
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES Customer(customer_id) ON DELETE RESTRICT,
    FOREIGN KEY (warehouse_id) REFERENCES Warehouse(warehouse_id) ON DELETE RESTRICT,
    FOREIGN KEY (delivery_partner_id) REFERENCES Delivery_Partner(partner_id) ON DELETE SET NULL,
    INDEX idx_customer (customer_id),
    INDEX idx_warehouse (warehouse_id),
    INDEX idx_partner (delivery_partner_id),
    INDEX idx_status (order_status),
    INDEX idx_payment_status (payment_status),
    INDEX idx_placed_at (placed_at),
    INDEX idx_order_number (order_number)
);

-- 10. ORDER_ITEM TABLE
-- Line items in an order (products + quantities)
CREATE TABLE Order_Item (
    order_item_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    batch_id INT NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0),
    price_at_time DECIMAL(10, 2) NOT NULL CHECK (price_at_time >= 0),
    tax_at_time DECIMAL(5, 2) DEFAULT 0.00,
    discount_at_time DECIMAL(10, 2) DEFAULT 0.00,
    subtotal DECIMAL(10, 2) GENERATED ALWAYS AS (quantity * price_at_time) STORED,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES Orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES Product(product_id) ON DELETE RESTRICT,
    FOREIGN KEY (batch_id) REFERENCES Batch_Inventory(batch_id) ON DELETE RESTRICT,
    INDEX idx_order (order_id),
    INDEX idx_product (product_id),
    INDEX idx_batch (batch_id)
);

-- 11. PAYMENT TABLE
-- Payment records for orders with transaction tracking
CREATE TABLE Payment (
    payment_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL UNIQUE,
    transaction_id VARCHAR(100) UNIQUE, -- Payment gateway transaction reference
    amount DECIMAL(10, 2) NOT NULL CHECK (amount >= 0),
    payment_method ENUM('UPI', 'Credit Card', 'Debit Card', 'Cash on Delivery', 'Net Banking', 'Wallet') NOT NULL,
    payment_status ENUM('Pending', 'Completed', 'Failed', 'Refunded', 'Partially Refunded') NOT NULL DEFAULT 'Pending',
    payment_gateway VARCHAR(50), -- Razorpay, Paytm, PhonePe, etc.
    paid_at TIMESTAMP NULL DEFAULT NULL,
    refund_amount DECIMAL(10, 2) DEFAULT 0.00,
    refund_date TIMESTAMP NULL,
    refund_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES Orders(order_id) ON DELETE CASCADE,
    INDEX idx_status (payment_status),
    INDEX idx_transaction (transaction_id),
    INDEX idx_paid_at (paid_at)
);

-- 12. STOCK_LEDGER TABLE
-- Comprehensive audit log for all inventory movements
CREATE TABLE Stock_Ledger (
    ledger_id INT PRIMARY KEY AUTO_INCREMENT,
    batch_id INT NOT NULL,
    transaction_type ENUM('Stock In', 'Sale', 'Damage', 'Expiry', 'Return', 'Adjustment', 'Transfer', 'Reserved', 'Unreserved') NOT NULL,
    quantity_change INT NOT NULL, -- Positive for additions, negative for deductions
    transaction_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reference_type ENUM('Order', 'Supplier', 'Manual', 'System', 'Transfer') NOT NULL,
    reference_id INT DEFAULT NULL, -- FK to Order_ID, Supplier_ID, or Transfer_ID
    performed_by VARCHAR(100), -- Staff member or system identifier
    notes TEXT, -- Additional context for the transaction
    previous_quantity INT, -- Quantity before transaction
    new_quantity INT, -- Quantity after transaction
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES Batch_Inventory(batch_id) ON DELETE RESTRICT,
    INDEX idx_batch (batch_id),
    INDEX idx_date (transaction_date),
    INDEX idx_type (transaction_type),
    INDEX idx_reference (reference_type, reference_id)
);

-- ============================================================================
-- NEW TABLES FOR ENHANCED FUNCTIONALITY
-- ============================================================================

-- 13. COUPON TABLE
-- Discount coupons and promotional offers
CREATE TABLE Coupon (
    coupon_id INT PRIMARY KEY AUTO_INCREMENT,
    coupon_code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    discount_type ENUM('Percentage', 'Fixed Amount', 'Free Delivery') NOT NULL,
    discount_value DECIMAL(10, 2) NOT NULL CHECK (discount_value >= 0),
    min_order_value DECIMAL(10, 2) DEFAULT 0.00,
    max_discount_amount DECIMAL(10, 2), -- Cap for percentage discounts
    valid_from TIMESTAMP NOT NULL,
    valid_until TIMESTAMP NOT NULL,
    usage_limit INT, -- Total times coupon can be used
    usage_count INT DEFAULT 0,
    per_user_limit INT DEFAULT 1, -- Times each user can use
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_coupon_valid_dates CHECK (valid_until > valid_from),
    INDEX idx_code (coupon_code),
    INDEX idx_active (is_active),
    INDEX idx_validity (valid_from, valid_until)
);

-- 14. ORDER_COUPON TABLE
-- Junction table for applied coupons
CREATE TABLE Order_Coupon (
    order_coupon_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    coupon_id INT NOT NULL,
    discount_applied DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES Orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (coupon_id) REFERENCES Coupon(coupon_id) ON DELETE RESTRICT,
    UNIQUE KEY (order_id, coupon_id)
);

-- 15. PRODUCT_REVIEW TABLE
-- Customer reviews and ratings for products
CREATE TABLE Product_Review (
    review_id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    customer_id INT NOT NULL,
    order_id INT NOT NULL, -- Only verified purchases can review
    rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    review_title VARCHAR(200),
    review_text TEXT,
    is_verified_purchase BOOLEAN DEFAULT TRUE,
    is_approved BOOLEAN DEFAULT FALSE, -- Moderation flag
    helpful_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES Product(product_id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES Customer(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (order_id) REFERENCES Orders(order_id) ON DELETE CASCADE,
    INDEX idx_product (product_id),
    INDEX idx_customer (customer_id),
    INDEX idx_rating (rating),
    INDEX idx_approved (is_approved)
);

-- 16. DELIVERY_RATING TABLE
-- Customer ratings for delivery experience
CREATE TABLE Delivery_Rating (
    rating_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL UNIQUE,
    delivery_partner_id INT NOT NULL,
    rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES Orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (delivery_partner_id) REFERENCES Delivery_Partner(partner_id) ON DELETE CASCADE,
    INDEX idx_partner (delivery_partner_id),
    INDEX idx_rating (rating)
);

-- 17. WAREHOUSE_INVENTORY_ALERT TABLE
-- Automated alerts for low stock and expiring items
CREATE TABLE Warehouse_Inventory_Alert (
    alert_id INT PRIMARY KEY AUTO_INCREMENT,
    warehouse_id INT NOT NULL,
    product_id INT,
    batch_id INT,
    alert_type ENUM('Low Stock', 'Out of Stock', 'Expiring Soon', 'Expired', 'Overstock') NOT NULL,
    alert_message TEXT NOT NULL,
    severity ENUM('Low', 'Medium', 'High', 'Critical') DEFAULT 'Medium',
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (warehouse_id) REFERENCES Warehouse(warehouse_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES Product(product_id) ON DELETE CASCADE,
    FOREIGN KEY (batch_id) REFERENCES Batch_Inventory(batch_id) ON DELETE CASCADE,
    INDEX idx_warehouse (warehouse_id),
    INDEX idx_type (alert_type),
    INDEX idx_severity (severity),
    INDEX idx_resolved (is_resolved)
);

-- 18. CUSTOMER_ADDRESS TABLE
-- Multiple delivery addresses per customer
CREATE TABLE Customer_Address (
    address_id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    address_type ENUM('Home', 'Work', 'Other') DEFAULT 'Home',
    address_line1 VARCHAR(255) NOT NULL,
    address_line2 VARCHAR(255),
    landmark VARCHAR(100),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    pincode VARCHAR(10) NOT NULL,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES Customer(customer_id) ON DELETE CASCADE,
    INDEX idx_customer (customer_id),
    INDEX idx_default (is_default)
);

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- View: Available inventory excluding expired batches
CREATE VIEW Available_Inventory AS
SELECT 
    i.warehouse_id,
    w.name AS warehouse_name,
    i.product_id,
    p.name AS product_name,
    p.brand,
    p.price,
    i.available_quantity,
    MIN(bi.expiry_date) AS nearest_expiry,
    COUNT(DISTINCT bi.batch_id) AS batch_count
FROM Inventory i
JOIN Warehouse w ON i.warehouse_id = w.warehouse_id
JOIN Product p ON i.product_id = p.product_id
LEFT JOIN Batch_Inventory bi ON i.product_id = bi.product_id 
    AND i.warehouse_id = bi.warehouse_id 
    AND bi.expiry_date > CURDATE()
    AND bi.current_quantity > 0
WHERE i.available_quantity > 0 
    AND p.is_active = TRUE 
    AND w.is_operational = TRUE
GROUP BY i.warehouse_id, w.name, i.product_id, p.name, p.brand, p.price, i.available_quantity;

-- View: Order Summary with customer and delivery details
CREATE VIEW Order_Summary AS
SELECT 
    o.order_id,
    o.order_number,
    c.name AS customer_name,
    c.phone AS customer_phone,
    w.name AS warehouse_name,
    dp.name AS delivery_partner_name,
    dp.phone AS delivery_partner_phone,
    o.order_status,
    o.payment_status,
    o.total_amount,
    o.placed_at,
    o.expected_delivery_time,
    o.delivered_at,
    TIMESTAMPDIFF(MINUTE, o.placed_at, o.delivered_at) AS delivery_time_minutes
FROM Orders o
JOIN Customer c ON o.customer_id = c.customer_id
JOIN Warehouse w ON o.warehouse_id = w.warehouse_id
LEFT JOIN Delivery_Partner dp ON o.delivery_partner_id = dp.partner_id;

-- View: Product performance metrics
CREATE VIEW Product_Performance AS
SELECT 
    p.product_id,
    p.name AS product_name,
    p.brand,
    p.category_id,
    c.name AS category_name,
    p.price,
    COUNT(DISTINCT oi.order_id) AS total_orders,
    SUM(oi.quantity) AS total_quantity_sold,
    SUM(oi.subtotal) AS total_revenue,
    AVG(pr.rating) AS average_rating,
    COUNT(pr.review_id) AS review_count
FROM Product p
JOIN Category c ON p.category_id = c.category_id
LEFT JOIN Order_Item oi ON p.product_id = oi.product_id
LEFT JOIN Product_Review pr ON p.product_id = pr.product_id AND pr.is_approved = TRUE
WHERE p.is_active = TRUE
GROUP BY p.product_id, p.name, p.brand, p.category_id, c.name, p.price;

-- ============================================================================
-- TRIGGERS FOR AUTOMATED INVENTORY MANAGEMENT
-- ============================================================================

-- Trigger: Update inventory after order item insertion
DELIMITER //
CREATE TRIGGER trg_after_order_item_insert
AFTER INSERT ON Order_Item
FOR EACH ROW
BEGIN
    -- Decrease batch quantity
    UPDATE Batch_Inventory
    SET current_quantity = current_quantity - NEW.quantity,
        updated_at = CURRENT_TIMESTAMP
    WHERE batch_id = NEW.batch_id;
    
    -- Update aggregated inventory
    UPDATE Inventory
    SET total_quantity = total_quantity - NEW.quantity,
        updated_at = CURRENT_TIMESTAMP
    WHERE product_id = NEW.product_id
        AND warehouse_id = (SELECT warehouse_id FROM Batch_Inventory WHERE batch_id = NEW.batch_id);
    
    -- Insert stock ledger entry
    INSERT INTO Stock_Ledger (
        batch_id, 
        transaction_type, 
        quantity_change, 
        reference_type, 
        reference_id,
        previous_quantity,
        new_quantity
    )
    SELECT 
        NEW.batch_id,
        'Sale',
        -NEW.quantity,
        'Order',
        NEW.order_id,
        current_quantity + NEW.quantity,
        current_quantity
    FROM Batch_Inventory
    WHERE batch_id = NEW.batch_id;
END//

-- Trigger: Check for low stock alerts after inventory update
CREATE TRIGGER trg_check_low_stock_alert
AFTER UPDATE ON Batch_Inventory
FOR EACH ROW
BEGIN
    -- Alert if current quantity falls below reorder level
    IF NEW.current_quantity <= NEW.reorder_level AND OLD.current_quantity > NEW.reorder_level THEN
        INSERT INTO Warehouse_Inventory_Alert (
            warehouse_id,
            product_id,
            batch_id,
            alert_type,
            alert_message,
            severity
        ) VALUES (
            NEW.warehouse_id,
            NEW.product_id,
            NEW.batch_id,
            'Low Stock',
            CONCAT('Product batch ', NEW.batch_id, ' is below reorder level. Current: ', NEW.current_quantity, ', Reorder Level: ', NEW.reorder_level),
            'High'
        );
    END IF;
    
    -- Alert if stock is completely out
    IF NEW.current_quantity = 0 AND OLD.current_quantity > 0 THEN
        INSERT INTO Warehouse_Inventory_Alert (
            warehouse_id,
            product_id,
            batch_id,
            alert_type,
            alert_message,
            severity
        ) VALUES (
            NEW.warehouse_id,
            NEW.product_id,
            NEW.batch_id,
            'Out of Stock',
            CONCAT('Product batch ', NEW.batch_id, ' is out of stock'),
            'Critical'
        );
    END IF;
END//

-- Trigger: Check for expiring items
CREATE TRIGGER trg_check_expiry_alert
AFTER INSERT ON Batch_Inventory
FOR EACH ROW
BEGIN
    -- Alert if expiry is within 3 days
    IF DATEDIFF(NEW.expiry_date, CURDATE()) <= 3 AND DATEDIFF(NEW.expiry_date, CURDATE()) > 0 THEN
        INSERT INTO Warehouse_Inventory_Alert (
            warehouse_id,
            product_id,
            batch_id,
            alert_type,
            alert_message,
            severity
        ) VALUES (
            NEW.warehouse_id,
            NEW.product_id,
            NEW.batch_id,
            'Expiring Soon',
            CONCAT('Batch ', NEW.batch_id, ' expires on ', NEW.expiry_date, ' (', DATEDIFF(NEW.expiry_date, CURDATE()), ' days remaining)'),
            'High'
        );
    END IF;
END//

-- Trigger: Update customer statistics after order completion
CREATE TRIGGER trg_update_customer_stats
AFTER UPDATE ON Orders
FOR EACH ROW
BEGIN
    IF NEW.order_status = 'Delivered' AND OLD.order_status != 'Delivered' THEN
        UPDATE Customer
        SET total_orders = total_orders + 1,
            total_spent = total_spent + NEW.total_amount,
            updated_at = CURRENT_TIMESTAMP
        WHERE customer_id = NEW.customer_id;
    END IF;
END//

-- Trigger: Update delivery partner statistics
CREATE TRIGGER trg_update_partner_stats
AFTER UPDATE ON Orders
FOR EACH ROW
BEGIN
    IF NEW.order_status = 'Delivered' AND OLD.order_status != 'Delivered' AND NEW.delivery_partner_id IS NOT NULL THEN
        UPDATE Delivery_Partner
        SET total_deliveries = total_deliveries + 1,
            successful_deliveries = successful_deliveries + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE partner_id = NEW.delivery_partner_id;
    END IF;
END//

-- Trigger: Update delivery partner rating after review
CREATE TRIGGER trg_update_partner_rating
AFTER INSERT ON Delivery_Rating
FOR EACH ROW
BEGIN
    UPDATE Delivery_Partner dp
    SET rating = (
        SELECT AVG(rating)
        FROM Delivery_Rating
        WHERE delivery_partner_id = NEW.delivery_partner_id
    ),
    updated_at = CURRENT_TIMESTAMP
    WHERE partner_id = NEW.delivery_partner_id;
END//

DELIMITER ;

-- ============================================================================
-- INDEXES FOR PERFORMANCE OPTIMIZATION (Additional)
-- ============================================================================

CREATE INDEX idx_batch_supplier ON Batch_Inventory(supplier_id);
CREATE INDEX idx_order_dates ON Orders(placed_at, delivered_at);
CREATE INDEX idx_customer_stats ON Customer(total_orders, total_spent);
CREATE INDEX idx_product_price ON Product(price);
CREATE INDEX idx_warehouse_operational ON Warehouse(is_operational);

-- ============================================================================
-- STORED PROCEDURES FOR COMMON OPERATIONS
-- ============================================================================

DELIMITER //

-- Procedure: Get available warehouses for a customer location
CREATE PROCEDURE sp_get_serviceable_warehouses(
    IN cust_lat DECIMAL(10,8),
    IN cust_lng DECIMAL(11,8)
)
BEGIN
    SELECT 
        w.warehouse_id,
        w.name,
        w.address,
        w.serviceable_radius_km,
        (6371 * ACOS(
            COS(RADIANS(cust_lat)) * COS(RADIANS(w.latitude)) *
            COS(RADIANS(w.longitude) - RADIANS(cust_lng)) +
            SIN(RADIANS(cust_lat)) * SIN(RADIANS(w.latitude))
        )) AS distance_km
    FROM Warehouse w
    WHERE w.is_operational = TRUE
        AND w.latitude IS NOT NULL
        AND w.longitude IS NOT NULL
    HAVING distance_km <= w.serviceable_radius_km
    ORDER BY distance_km ASC;
END//

-- Procedure: Check product availability at warehouse
CREATE PROCEDURE sp_check_product_availability(
    IN p_product_id INT,
    IN p_warehouse_id INT,
    IN p_quantity INT
)
BEGIN
    SELECT 
        p.product_id,
        p.name,
        p.price,
        i.available_quantity,
        CASE 
            WHEN i.available_quantity >= p_quantity THEN 'Available'
            WHEN i.available_quantity > 0 THEN 'Partially Available'
            ELSE 'Out of Stock'
        END AS stock_status,
        bi.batch_id,
        bi.expiry_date,
        bi.current_quantity AS batch_quantity
    FROM Product p
    LEFT JOIN Inventory i ON p.product_id = i.product_id AND i.warehouse_id = p_warehouse_id
    LEFT JOIN Batch_Inventory bi ON p.product_id = bi.product_id 
        AND bi.warehouse_id = p_warehouse_id
        AND bi.expiry_date > CURDATE()
        AND bi.current_quantity > 0
    WHERE p.product_id = p_product_id
        AND p.is_active = TRUE
    ORDER BY bi.expiry_date ASC
    LIMIT 1;
END//

-- Procedure: Get order details with items
CREATE PROCEDURE sp_get_order_details(
    IN p_order_id INT
)
BEGIN
    -- Order header
    SELECT 
        o.*,
        c.name AS customer_name,
        c.phone AS customer_phone,
        c.address AS customer_address,
        w.name AS warehouse_name,
        dp.name AS delivery_partner_name,
        dp.phone AS delivery_partner_phone,
        dp.vehicle_type,
        p.payment_method,
        p.payment_status,
        p.transaction_id
    FROM Orders o
    JOIN Customer c ON o.customer_id = c.customer_id
    JOIN Warehouse w ON o.warehouse_id = w.warehouse_id
    LEFT JOIN Delivery_Partner dp ON o.delivery_partner_id = dp.partner_id
    LEFT JOIN Payment p ON o.order_id = p.order_id
    WHERE o.order_id = p_order_id;
    
    -- Order items
    SELECT 
        oi.*,
        pr.name AS product_name,
        pr.brand,
        bi.batch_number,
        bi.expiry_date
    FROM Order_Item oi
    JOIN Product pr ON oi.product_id = pr.product_id
    LEFT JOIN Batch_Inventory bi ON oi.batch_id = bi.batch_id
    WHERE oi.order_id = p_order_id;
END//

-- Procedure: Allocate delivery partner to order
CREATE PROCEDURE sp_allocate_delivery_partner(
    IN p_order_id INT
)
BEGIN
    DECLARE v_warehouse_id INT;
    DECLARE v_partner_id INT;
    
    -- Get warehouse for the order
    SELECT warehouse_id INTO v_warehouse_id
    FROM Orders
    WHERE order_id = p_order_id;
    
    -- Find available delivery partner at that warehouse
    SELECT partner_id INTO v_partner_id
    FROM Delivery_Partner
    WHERE assigned_warehouse_id = v_warehouse_id
        AND availability_status = 'Available'
        AND is_active = TRUE
    ORDER BY rating DESC, total_deliveries ASC
    LIMIT 1;
    
    -- Update order with delivery partner
    IF v_partner_id IS NOT NULL THEN
        UPDATE Orders
        SET delivery_partner_id = v_partner_id,
            order_status = 'Processing',
            confirmed_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE order_id = p_order_id;
        
        -- Update partner status
        UPDATE Delivery_Partner
        SET availability_status = 'Busy',
            updated_at = CURRENT_TIMESTAMP
        WHERE partner_id = v_partner_id;
        
        SELECT 'Partner Allocated' AS status, v_partner_id AS partner_id;
    ELSE
        SELECT 'No Available Partner' AS status, NULL AS partner_id;
    END IF;
END//

DELIMITER ;

-- ============================================================================
-- SAMPLE DATA INSERTION (Enhanced with new fields)
-- ============================================================================

-- Insert Categories (Hierarchical Structure)
INSERT INTO Category (name, parent_category_id, description) VALUES
('Groceries', NULL, 'Essential grocery items'),
('Electronics', NULL, 'Electronic devices and accessories'),
('Personal Care', NULL, 'Health and hygiene products'),
('Beverages', NULL, 'Drinks and refreshments'),
('Snacks', NULL, 'Quick bites and munchies'),
('Fruits & Vegetables', 1, 'Fresh produce'),
('Dairy Products', 1, 'Milk, cheese, yogurt and more'),
('Cooking Essentials', 1, 'Spices, oils, and staples'),
('Mobile Accessories', 2, 'Chargers, cases, and more'),
('Health & Hygiene', 3, 'Sanitizers, soaps, and wellness products');

-- Insert Suppliers
INSERT INTO Supplier (name, phone, email, address, contact_person, gstin, rating) VALUES
('Fresh Farms Pvt Ltd', '9876543210', 'contact@freshfarms.com', '12, Agriculture Market, Delhi', 'Ramesh Kumar', '07AABCU9603R1ZX', 4.5),
('Dairy Best Co.', '9876543211', 'sales@dairybest.com', '45, Milk Colony, Gurgaon', 'Suresh Sharma', '06AABCU9603R1ZY', 4.7),
('Tech Suppliers Inc.', '9876543212', 'info@techsuppliers.com', '78, Electronics Hub, Noida', 'Amit Verma', '09AABCU9603R1ZZ', 4.3),
('Snack Masters', '9876543213', 'orders@snackmasters.com', '23, Food Street, Delhi', 'Priya Singh', '07AABCU9603R1ZA', 4.6),
('Beverage Distributors', '9876543214', 'contact@bevdist.com', '56, Drink Avenue, Faridabad', 'Vikram Malhotra', '06AABCU9603R1ZB', 4.4);

-- Insert Products
INSERT INTO Product (name, description, brand, price, weight, category_id, sku, barcode, tax_rate, shelf_life_days) VALUES
('Organic Bananas', 'Fresh organic bananas - 6 pieces', 'FreshFarms', 60.00, 600, 6, 'FF-BAN-001', '8901234567890', 0.00, 7),
('Full Cream Milk 1L', 'Fresh full cream milk', 'Amul', 65.00, 1000, 7, 'AML-MLK-001', '8901234567891', 0.00, 5),
('Whole Wheat Bread', 'Freshly baked whole wheat bread', 'Britannia', 45.00, 400, 1, 'BRT-BRD-001', '8901234567892', 5.00, 4),
('Potato Chips - Classic', 'Crispy salted potato chips', 'Lays', 20.00, 50, 5, 'LAY-CHP-001', '8901234567893', 12.00, 180),
('Coca Cola 600ml', 'Chilled soft drink', 'Coca-Cola', 40.00, 600, 4, 'COC-COL-001', '8901234567894', 12.00, 365),
('Tomatoes 500g', 'Fresh red tomatoes', 'FreshFarms', 30.00, 500, 6, 'FF-TOM-001', '8901234567895', 0.00, 5),
('Basmati Rice 5kg', 'Premium aged basmati rice', 'India Gate', 450.00, 5000, 8, 'IND-RIC-001', '8901234567896', 5.00, 730),
('Mobile Phone Charger', 'Fast charging USB-C cable', 'Mi', 299.00, 50, 9, 'MI-CHR-001', '8901234567897', 18.00, 1825),
('Hand Sanitizer 250ml', 'Antibacterial hand sanitizer', 'Dettol', 80.00, 250, 10, 'DET-SAN-001', '8901234567898', 18.00, 730),
('Greek Yogurt 200g', 'High protein Greek yogurt', 'Epigamia', 75.00, 200, 7, 'EPI-YOG-001', '8901234567899', 5.00, 15);

-- Insert Warehouses with geolocation
INSERT INTO Warehouse (name, location, address, capacity, latitude, longitude, serviceable_radius_km, contact_phone, manager_name) VALUES
('DarkStore Dwarka', 'Dwarka Sector 10', 'Plot 45, Dwarka Sector 10, Delhi - 110075', 5000, 28.5921, 77.0460, 5.00, '9811111111', 'Rajesh Kumar'),
('DarkStore Rohini', 'Rohini Sector 15', 'Shop 12, Rohini Sector 15, Delhi - 110085', 4500, 28.7485, 77.1072, 4.50, '9822222222', 'Priya Sharma'),
('DarkStore Noida', 'Sector 62 Noida', 'Building A, Sector 62, Noida - 201301', 6000, 28.6273, 77.3714, 6.00, '9833333333', 'Amit Verma'),
('DarkStore Gurgaon', 'DLF Phase 3', 'Tower B, DLF Phase 3, Gurgaon - 122002', 5500, 28.4931, 77.0935, 5.50, '9844444444', 'Sneha Gupta');

-- Insert Batch Inventory with enhanced fields
INSERT INTO Batch_Inventory (product_id, warehouse_id, supplier_id, batch_number, manufacture_date, expiry_date, initial_quantity, current_quantity, reorder_level, shelf_location, cost_price) VALUES
-- Warehouse 1 (Dwarka)
(1, 1, 1, 'FF-BAN-2026-001', '2026-01-30', '2026-02-10', 100, 85, 20, 'A-01-15', 50.00),
(2, 1, 2, 'AML-MLK-2026-001', '2026-02-01', '2026-02-08', 80, 60, 15, 'B-02-08', 55.00),
(3, 1, 1, 'BRT-BRD-2026-001', '2026-02-02', '2026-02-12', 50, 40, 10, 'C-01-22', 38.00),
(4, 1, 4, 'LAY-CHP-2026-001', '2026-01-15', '2026-05-15', 200, 180, 30, 'D-05-11', 15.00),
(5, 1, 5, 'COC-COL-2025-012', '2025-12-01', '2026-06-01', 150, 120, 25, 'E-03-06', 32.00),
-- Warehouse 2 (Rohini)
(1, 2, 1, 'FF-BAN-2026-002', '2026-02-01', '2026-02-12', 90, 75, 20, 'A-02-10', 50.00),
(2, 2, 2, 'AML-MLK-2026-002', '2026-02-02', '2026-02-09', 70, 55, 15, 'B-01-12', 55.00),
(6, 2, 1, 'FF-TOM-2026-001', '2026-02-03', '2026-02-08', 60, 50, 15, 'A-03-05', 24.00),
(7, 2, 1, 'IND-RIC-2025-011', '2025-11-01', '2027-11-01', 30, 25, 5, 'F-01-20', 380.00),
(10, 2, 2, 'EPI-YOG-2026-001', '2026-02-01', '2026-02-15', 100, 90, 20, 'B-05-08', 65.00),
-- Warehouse 3 (Noida)
(3, 3, 1, 'BRT-BRD-2026-002', '2026-02-01', '2026-02-11', 60, 50, 10, 'C-02-18', 38.00),
(4, 3, 4, 'LAY-CHP-2026-002', '2026-01-20', '2026-05-20', 250, 230, 40, 'D-03-15', 15.00),
(5, 3, 5, 'COC-COL-2025-013', '2025-12-15', '2026-06-15', 180, 160, 30, 'E-02-09', 32.00),
(8, 3, 3, 'MI-CHR-2026-001', '2026-01-01', '2028-01-01', 50, 45, 10, 'G-01-12', 250.00),
(9, 3, 3, 'DET-SAN-2025-012', '2025-12-01', '2027-12-01', 120, 110, 20, 'H-02-06', 65.00),
-- Warehouse 4 (Gurgaon)
(1, 4, 1, 'FF-BAN-2026-003', '2026-02-02', '2026-02-13', 110, 95, 20, 'A-04-08', 50.00),
(6, 4, 1, 'FF-TOM-2026-002', '2026-02-03', '2026-02-09', 70, 60, 15, 'A-05-12', 24.00),
(7, 4, 1, 'IND-RIC-2025-010', '2025-10-01', '2027-10-01', 40, 35, 8, 'F-02-15', 380.00),
(9, 4, 3, 'DET-SAN-2026-001', '2026-01-01', '2027-01-01', 100, 85, 20, 'H-01-10', 65.00),
(10, 4, 2, 'EPI-YOG-2026-002', '2026-02-02', '2026-02-16', 80, 70, 15, 'B-03-20', 65.00);

-- Insert Inventory (Aggregated quantities)
INSERT INTO Inventory (warehouse_id, product_id, total_quantity, reserved_quantity, last_restocked_at, reorder_threshold) VALUES
-- Warehouse 1
(1, 1, 85, 0, '2026-02-01 08:00:00', 20),
(1, 2, 60, 0, '2026-02-01 08:30:00', 15),
(1, 3, 40, 0, '2026-02-02 09:00:00', 10),
(1, 4, 180, 0, '2026-01-20 10:00:00', 30),
(1, 5, 120, 0, '2025-12-15 11:00:00', 25),
-- Warehouse 2
(2, 1, 75, 0, '2026-02-01 09:00:00', 20),
(2, 2, 55, 0, '2026-02-02 08:00:00', 15),
(2, 6, 50, 0, '2026-02-03 07:00:00', 15),
(2, 7, 25, 0, '2025-11-01 10:00:00', 5),
(2, 10, 90, 0, '2026-02-01 09:30:00', 20),
-- Warehouse 3
(3, 3, 50, 0, '2026-02-01 08:30:00', 10),
(3, 4, 230, 0, '2026-01-20 11:00:00', 40),
(3, 5, 160, 0, '2025-12-15 10:30:00', 30),
(3, 8, 45, 0, '2026-01-01 12:00:00', 10),
(3, 9, 110, 0, '2025-12-01 11:30:00', 20),
-- Warehouse 4
(4, 1, 95, 0, '2026-02-02 08:00:00', 20),
(4, 6, 60, 0, '2026-02-03 07:30:00', 15),
(4, 7, 35, 0, '2025-10-01 10:00:00', 8),
(4, 9, 85, 0, '2026-01-01 11:00:00', 20),
(4, 10, 70, 0, '2026-02-02 09:00:00', 15);

-- Insert Customers with geolocation
INSERT INTO Customer (name, phone, email, address, latitude, longitude, pincode, preferred_warehouse_id) VALUES
('Rahul Sharma', '9811111111', 'rahul.sharma@email.com', 'A-101, Dwarka Sector 12, Delhi', 28.5882, 77.0460, '110075', 1),
('Priya Verma', '9822222222', 'priya.verma@email.com', 'B-205, Rohini Sector 18, Delhi', 28.7520, 77.1072, '110085', 2),
('Amit Kumar', '9833333333', 'amit.kumar@email.com', 'C-302, Sector 63, Noida', 28.6289, 77.3728, '201301', 3),
('Sneha Gupta', '9844444444', 'sneha.gupta@email.com', 'D-401, DLF Phase 2, Gurgaon', 28.4942, 77.0948, '122002', 4),
('Vikram Singh', '9855555555', 'vikram.singh@email.com', 'E-501, Dwarka Sector 8, Delhi', 28.5891, 77.0520, '110075', 1),
('Anjali Mehta', '9866666666', 'anjali.mehta@email.com', 'F-102, Sector 62, Noida', 28.6260, 77.3700, '201301', 3),
('Rohan Joshi', '9877777777', 'rohan.joshi@email.com', 'G-203, Rohini Sector 20, Delhi', 28.7530, 77.1100, '110085', 2),
('Pooja Nair', '9888888888', 'pooja.nair@email.com', 'H-304, DLF Phase 4, Gurgaon', 28.4920, 77.0920, '122002', 4);

-- Insert Customer Addresses
INSERT INTO Customer_Address (customer_id, address_type, address_line1, address_line2, landmark, city, state, pincode, latitude, longitude, is_default) VALUES
(1, 'Home', 'A-101, Dwarka Sector 12', 'Near Metro Station', 'Dwarka Sector 12 Metro', 'Delhi', 'Delhi', '110075', 28.5882, 77.0460, TRUE),
(1, 'Work', 'Office 405, Cyber City', 'DLF Building 10', 'Cyber Hub', 'Gurgaon', 'Haryana', '122002', 28.4950, 77.0890, FALSE),
(2, 'Home', 'B-205, Rohini Sector 18', 'Opposite Park', 'Rohini West Metro', 'Delhi', 'Delhi', '110085', 28.7520, 77.1072, TRUE);

-- Insert Delivery Partners
INSERT INTO Delivery_Partner (name, phone, email, vehicle_type, vehicle_number, license_number, address, assigned_warehouse_id, rating) VALUES
('Rajesh Kumar', '9711111111', 'rajesh.delivery@email.com', 'Bike', 'DL-01-AB-1234', 'DL-1234567890', 'Dwarka, Delhi', 1, 4.8),
('Suresh Yadav', '9722222222', 'suresh.delivery@email.com', 'Scooter', 'DL-02-CD-5678', 'DL-9876543210', 'Rohini, Delhi', 2, 4.6),
('Manoj Tiwari', '9733333333', 'manoj.delivery@email.com', 'Bike', 'UP-16-EF-9012', 'UP-1122334455', 'Noida', 3, 4.7),
('Deepak Verma', '9744444444', 'deepak.delivery@email.com', 'Bicycle', 'HR-26-GH-3456', 'HR-5566778899', 'Gurgaon', 4, 4.5),
('Sanjay Rawat', '9755555555', 'sanjay.delivery@email.com', 'Bike', 'DL-03-IJ-7890', 'DL-6677889900', 'Dwarka, Delhi', 1, 4.9),
('Anil Sharma', '9766666666', 'anil.delivery@email.com', 'Scooter', 'UP-17-KL-2345', 'UP-7788990011', 'Noida', 3, 4.4);

-- Insert Orders with enhanced tracking
INSERT INTO Orders (order_number, customer_id, warehouse_id, delivery_partner_id, order_status, payment_status, placed_at, confirmed_at, delivered_at, expected_delivery_time, subtotal, tax_amount, delivery_fee, total_amount, distance_km) VALUES
('ORD-2026-00001', 1, 1, 1, 'Delivered', 'Paid', '2026-02-03 10:30:00', '2026-02-03 10:32:00', '2026-02-03 10:48:00', '2026-02-03 10:50:00', 175.00, 10.00, 0.00, 185.00, 2.5),
('ORD-2026-00002', 2, 2, 2, 'Delivered', 'Paid', '2026-02-03 11:45:00', '2026-02-03 11:47:00', '2026-02-03 12:03:00', '2026-02-03 12:05:00', 156.25, 8.75, 0.00, 165.00, 1.8),
('ORD-2026-00003', 3, 3, 3, 'Out for Delivery', 'Paid', '2026-02-04 09:15:00', '2026-02-04 09:17:00', NULL, '2026-02-04 09:35:00', 307.14, 31.86, 0.00, 339.00, 3.2),
('ORD-2026-00004', 4, 4, 4, 'Processing', 'Paid', '2026-02-04 10:00:00', '2026-02-04 10:02:00', NULL, '2026-02-04 10:20:00', 230.95, 14.05, 0.00, 245.00, 2.1),
('ORD-2026-00005', 5, 1, 5, 'Delivered', 'Paid', '2026-02-03 14:20:00', '2026-02-03 14:22:00', '2026-02-03 14:35:00', '2026-02-03 14:40:00', 100.00, 5.00, 0.00, 105.00, 1.5),
('ORD-2026-00006', 6, 3, 3, 'Out for Delivery', 'Paid', '2026-02-04 11:30:00', '2026-02-04 11:32:00', NULL, '2026-02-04 11:50:00', 383.93, 40.07, 0.00, 424.00, 2.8),
('ORD-2026-00007', 7, 2, 2, 'Processing', 'Pending', '2026-02-04 12:00:00', '2026-02-04 12:02:00', NULL, '2026-02-04 12:20:00', 133.33, 6.67, 0.00, 140.00, 1.9),
('ORD-2026-00008', 8, 4, 4, 'Placed', 'Pending', '2026-02-04 13:45:00', NULL, NULL, '2026-02-04 14:05:00', 192.00, 18.00, 0.00, 210.00, 2.3);

-- Calculate actual delivery time for delivered orders
UPDATE Orders 
SET actual_delivery_time_minutes = TIMESTAMPDIFF(MINUTE, placed_at, delivered_at)
WHERE order_status = 'Delivered' AND delivered_at IS NOT NULL;

-- Insert Order Items
INSERT INTO Order_Item (order_id, product_id, batch_id, quantity, price_at_time, tax_at_time) VALUES
-- Order 1
(1, 1, 1, 2, 60.00, 0.00),
(1, 2, 2, 1, 65.00, 0.00),
-- Order 2
(2, 1, 6, 1, 60.00, 0.00),
(2, 2, 7, 1, 65.00, 0.00),
(2, 10, 10, 1, 75.00, 5.00),
-- Order 3
(3, 4, 12, 3, 20.00, 12.00),
(3, 5, 13, 2, 40.00, 12.00),
(3, 8, 14, 1, 299.00, 18.00),
-- Order 4
(4, 1, 16, 2, 60.00, 0.00),
(4, 9, 19, 1, 80.00, 18.00),
(4, 10, 20, 1, 75.00, 5.00),
-- Order 5
(5, 3, 3, 1, 45.00, 5.00),
(5, 1, 1, 1, 60.00, 0.00),
-- Order 6
(6, 3, 11, 2, 45.00, 5.00),
(6, 4, 12, 4, 20.00, 12.00),
(6, 9, 15, 2, 80.00, 18.00),
-- Order 7
(7, 6, 8, 2, 30.00, 0.00),
(7, 2, 7, 1, 65.00, 0.00),
-- Order 8
(8, 6, 17, 3, 30.00, 0.00),
(8, 7, 18, 1, 450.00, 5.00);

-- Insert Payments
INSERT INTO Payment (order_id, transaction_id, amount, payment_method, payment_status, payment_gateway, paid_at) VALUES
(1, 'TXN-UPI-202602031031001', 185.00, 'UPI', 'Completed', 'Razorpay', '2026-02-03 10:31:00'),
(2, 'TXN-CC-202602031146001', 165.00, 'Credit Card', 'Completed', 'Razorpay', '2026-02-03 11:46:00'),
(3, 'TXN-DC-202602040916001', 339.00, 'Debit Card', 'Completed', 'Paytm', '2026-02-04 09:16:00'),
(4, 'TXN-UPI-202602041001001', 245.00, 'UPI', 'Completed', 'PhonePe', '2026-02-04 10:01:00'),
(5, 'TXN-COD-202602031435001', 105.00, 'Cash on Delivery', 'Completed', NULL, '2026-02-03 14:50:00'),
(6, 'TXN-NB-202602041131001', 424.00, 'Net Banking', 'Completed', 'Razorpay', '2026-02-04 11:31:00'),
(7, NULL, 140.00, 'UPI', 'Pending', 'PhonePe', NULL),
(8, NULL, 210.00, 'Credit Card', 'Pending', 'Razorpay', NULL);

-- Insert Coupons
INSERT INTO Coupon (coupon_code, description, discount_type, discount_value, min_order_value, max_discount_amount, valid_from, valid_until, usage_limit, per_user_limit) VALUES
('FIRST50', 'First order discount - 50% off', 'Percentage', 50.00, 100.00, 100.00, '2026-01-01 00:00:00', '2026-12-31 23:59:59', 1000, 1),
('SAVE100', 'Get Rs. 100 off on orders above Rs. 500', 'Fixed Amount', 100.00, 500.00, NULL, '2026-02-01 00:00:00', '2026-02-28 23:59:59', NULL, 3),
('FREEDEL', 'Free delivery on all orders', 'Free Delivery', 0.00, 200.00, NULL, '2026-02-01 00:00:00', '2026-02-15 23:59:59', 5000, 5);

-- Insert Product Reviews
INSERT INTO Product_Review (product_id, customer_id, order_id, rating, review_title, review_text, is_approved) VALUES
(1, 1, 1, 5, 'Fresh and good quality', 'The bananas were fresh and ripened perfectly. Great quality!', TRUE),
(2, 1, 1, 4, 'Good milk', 'Fresh milk, good packaging', TRUE),
(10, 2, 2, 5, 'Excellent yogurt', 'Best Greek yogurt I have tried. High protein and tastes great!', TRUE),
(4, 3, 3, 3, 'Average taste', 'Chips were okay, but I expected better crunch', TRUE);

-- Insert Delivery Ratings
INSERT INTO Delivery_Rating (order_id, delivery_partner_id, rating, feedback) VALUES
(1, 1, 5, 'Very prompt delivery. Polite and professional.'),
(2, 2, 4, 'Good service, delivered on time.'),
(5, 5, 5, 'Excellent! Super fast delivery and friendly delivery partner.');

-- Insert Stock Ledger (Audit Trail) - Initial Stock In
INSERT INTO Stock_Ledger (batch_id, transaction_type, quantity_change, transaction_date, reference_type, reference_id, performed_by, previous_quantity, new_quantity) VALUES
(1, 'Stock In', 100, '2026-02-01 08:00:00', 'Supplier', 1, 'System', 0, 100),
(2, 'Stock In', 80, '2026-02-01 08:30:00', 'Supplier', 2, 'System', 0, 80),
(3, 'Stock In', 50, '2026-02-02 09:00:00', 'Supplier', 1, 'System', 0, 50),
(4, 'Stock In', 200, '2026-01-20 10:00:00', 'Supplier', 4, 'System', 0, 200),
(5, 'Stock In', 150, '2025-12-15 11:00:00', 'Supplier', 5, 'System', 0, 150);

-- Note: Sale entries will be automatically created by the trigger when orders are placed

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check table creation
SELECT 'Enhanced Database setup completed successfully!' AS Status;

-- Show table counts
SELECT 
    'Categories' AS TableName, COUNT(*) AS RecordCount FROM Category
UNION ALL SELECT 'Suppliers', COUNT(*) FROM Supplier
UNION ALL SELECT 'Products', COUNT(*) FROM Product
UNION ALL SELECT 'Warehouses', COUNT(*) FROM Warehouse
UNION ALL SELECT 'Batch_Inventory', COUNT(*) FROM Batch_Inventory
UNION ALL SELECT 'Inventory', COUNT(*) FROM Inventory
UNION ALL SELECT 'Customers', COUNT(*) FROM Customer
UNION ALL SELECT 'Customer_Address', COUNT(*) FROM Customer_Address
UNION ALL SELECT 'Delivery_Partners', COUNT(*) FROM Delivery_Partner
UNION ALL SELECT 'Orders', COUNT(*) FROM Orders
UNION ALL SELECT 'Order_Items', COUNT(*) FROM Order_Item
UNION ALL SELECT 'Payments', COUNT(*) FROM Payment
UNION ALL SELECT 'Stock_Ledger', COUNT(*) FROM Stock_Ledger
UNION ALL SELECT 'Coupons', COUNT(*) FROM Coupon
UNION ALL SELECT 'Product_Reviews', COUNT(*) FROM Product_Review
UNION ALL SELECT 'Delivery_Ratings', COUNT(*) FROM Delivery_Rating
UNION ALL SELECT 'Warehouse_Alerts', COUNT(*) FROM Warehouse_Inventory_Alert;

-- ============================================================================
-- SAMPLE ANALYTICS QUERIES
-- ============================================================================

-- Top selling products
SELECT 
    p.product_id,
    p.name AS product_name,
    p.brand,
    COUNT(DISTINCT oi.order_id) AS total_orders,
    SUM(oi.quantity) AS total_quantity_sold,
    SUM(oi.subtotal) AS total_revenue
FROM Product p
LEFT JOIN Order_Item oi ON p.product_id = oi.product_id
GROUP BY p.product_id, p.name, p.brand
ORDER BY total_revenue DESC
LIMIT 5;

-- Warehouse performance
SELECT 
    w.warehouse_id,
    w.name AS warehouse_name,
    COUNT(DISTINCT o.order_id) AS total_orders,
    AVG(o.actual_delivery_time_minutes) AS avg_delivery_time,
    SUM(o.total_amount) AS total_revenue
FROM Warehouse w
LEFT JOIN Orders o ON w.warehouse_id = o.warehouse_id
WHERE o.order_status = 'Delivered'
GROUP BY w.warehouse_id, w.name
ORDER BY total_revenue DESC;

-- Delivery partner performance
SELECT 
    dp.partner_id,
    dp.name AS partner_name,
    dp.total_deliveries,
    dp.successful_deliveries,
    dp.rating,
    AVG(o.actual_delivery_time_minutes) AS avg_delivery_time
FROM Delivery_Partner dp
LEFT JOIN Orders o ON dp.partner_id = o.delivery_partner_id AND o.order_status = 'Delivered'
WHERE dp.is_active = TRUE
GROUP BY dp.partner_id, dp.name, dp.total_deliveries, dp.successful_deliveries, dp.rating
ORDER BY dp.rating DESC;

-- ============================================================================
-- END OF ENHANCED SCRIPT
-- ============================================================================
