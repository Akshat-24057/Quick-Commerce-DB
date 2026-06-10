

"""
=============================================================================
Quick Commerce Demand & Supply — Main Streamlit Application
IIIT Delhi · Group 78 · Palak Maurya · Akshat Gupta · Anand Raj
=============================================================================
Run:  streamlit run app.py --server.port 8501
=============================================================================
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime

from database import (
    init_db, get_kpis,
    get_all_customers, get_warehouses, get_available_products,
    place_order, get_order_history, get_order_items, update_order_status,
    get_inventory_summary, get_batch_details, get_stock_alerts,
    resolve_alert, replenish_stock, get_stock_ledger,
    get_sales_summary, get_top_products, get_customer_analysis,
    get_warehouse_performance, get_delivery_partner_performance,
    get_expiring_soon, add_customer, add_delivery_partner,
    get_connection,
    get_transaction_demo_catalog, load_transaction_demo_sql,
    get_transaction_demo_snapshot, reset_transaction_demo,
    run_transaction_demo, run_conflicting_transaction_demo
)

# ─── Page Config ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="QuickCommerce DB System",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main background */
    .main {background-color: #f8fafc;}
    .stApp {background-color: #f8fafc;}

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e3a5f 0%, #0f2744 100%);
    }
    [data-testid="stSidebar"] .stMarkdown, 
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] p {color: #e2e8f0 !important;}
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {color: #f7c948 !important;}
    [data-testid="stSidebarNav"] a {color: #cbd5e1 !important;}

    /* KPI Cards */
    .kpi-card {
        background: white; border-radius: 12px;
        padding: 20px 16px; text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 4px solid #3b82f6;
        transition: transform .2s;
    }
    .kpi-card:hover {transform: translateY(-2px);}
    .kpi-title {font-size: 13px; color: #64748b; font-weight:600; text-transform:uppercase; letter-spacing:.5px;}
    .kpi-value {font-size: 36px; font-weight:800; color: #1e3a5f; margin-top:6px;}
    .kpi-sub   {font-size: 12px; color: #94a3b8; margin-top:4px;}

    /* Section headers */
    .section-header {
        background: linear-gradient(90deg, #1e3a5f, #3b82f6);
        color: white; padding: 12px 20px; border-radius: 8px;
        font-size:18px; font-weight:700; margin-bottom:16px;
    }

    /* Status badges */
    .badge-delivered   {background:#d1fae5; color:#065f46; padding:3px 10px; border-radius:20px; font-size:12px;}
    .badge-placed      {background:#dbeafe; color:#1e40af; padding:3px 10px; border-radius:20px; font-size:12px;}
    .badge-cancelled   {background:#fee2e2; color:#991b1b; padding:3px 10px; border-radius:20px; font-size:12px;}
    .badge-processing  {background:#fef3c7; color:#92400e; padding:3px 10px; border-radius:20px; font-size:12px;}
    .badge-low         {background:#fef3c7; color:#b45309; padding:3px 10px; border-radius:20px; font-size:12px;}
    .badge-critical    {background:#fee2e2; color:#b91c1c; padding:3px 10px; border-radius:20px; font-size:12px;}
    .badge-ok          {background:#d1fae5; color:#065f46; padding:3px 10px; border-radius:20px; font-size:12px;}

    /* Cart items */
    .cart-item {
        background: #eff6ff; border:1px solid #bfdbfe;
        border-radius:8px; padding:10px 14px; margin-bottom:6px;
    }

    /* Alert banner */
    .alert-critical {background:#fee2e2; border-left:4px solid #ef4444;
                     padding:10px 16px; border-radius:6px; margin:4px 0;}
    .alert-high     {background:#fef3c7; border-left:4px solid #f59e0b;
                     padding:10px 16px; border-radius:6px; margin:4px 0;}
    .alert-medium   {background:#eff6ff; border-left:4px solid #3b82f6;
                     padding:10px 16px; border-radius:6px; margin:4px 0;}

    /* Table tweaks */
    .dataframe {font-size:13px;}
    thead th {background:#1e3a5f !important; color:white !important;}

    /* Button tweaks */
    .stButton > button {border-radius:8px; font-weight:600;}
    .stButton > button:hover {transform:translateY(-1px);}
</style>
""", unsafe_allow_html=True)


# ─── Init DB once per session ──────────────────────────────────────────────
@st.cache_resource
def get_db():
    return init_db()

conn = get_db()


# ─── Sidebar Navigation ────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚡ QuickCommerce")
    st.markdown("**DB System · Group 78**")
    st.markdown("---")
    page = st.radio(
        "Navigate",
        ["🏠 Dashboard",
         "🛒 Place Order",
         "📦 Order History & Tracking",
         "🏪 Inventory Management",
         "📊 Analytics & Reports",
         "🔄 Transactions",
         "👥 Admin Panel"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.markdown("**IIIT Delhi · CSE · DBMS**")
    st.markdown("Palak Maurya · Akshat Gupta · Anand Raj")
    st.markdown("*Tutorial 6 · Group 78*")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 1 – DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════
if page == "🏠 Dashboard":
    st.markdown('<div class="section-header">⚡ Quick Commerce — Live Dashboard</div>',
                unsafe_allow_html=True)

    kpis = get_kpis(conn)

    # KPI Row 1
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    kpi_data = [
        (col1, "📦 Orders Today",    kpis['orders_today'],     "new orders"),
        (col2, "💰 Revenue Today",   f"₹{kpis['revenue_today']:.0f}", "INR"),
        (col3, "🔄 Active Orders",   kpis['active_orders'],    "in pipeline"),
        (col4, "⚠️ Open Alerts",    kpis['open_alerts'],      "need attention"),
        (col5, "👤 Customers",       kpis['total_customers'],  "registered"),
        (col6, "🚴 Partners Free",   kpis['available_partners'], "available now"),
    ]
    for col, title, val, sub in kpi_data:
        with col:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">{title}</div>
                <div class="kpi-value">{val}</div>
                <div class="kpi-sub">{sub}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    col_left, col_right = st.columns([3, 2])

    # Recent Orders
    with col_left:
        st.markdown("### 📋 Recent Orders")
        orders = get_order_history(conn)[:10]
        if orders:
            df = pd.DataFrame([dict(r) for r in orders])
            status_color = {
                'Delivered':'🟢','Placed':'🔵','Confirmed':'🟡',
                'Processing':'🟠','Out for Delivery':'🟣',
                'Cancelled':'🔴','Returned':'⚪'
            }
            df['Status'] = df['order_status'].map(
                lambda s: f"{status_color.get(s,'⚪')} {s}"
            )
            df['Amount'] = df['total_amount'].fillna(0).map(lambda x: f"₹{x:.2f}")
            df['Placed'] = pd.to_datetime(df['placed_at']).dt.strftime('%d %b %H:%M')
            st.dataframe(
                df[['order_number','customer_name','warehouse_name',
                    'Status','Amount','Placed']],
                use_container_width=True, hide_index=True
            )
        else:
            st.info("No orders yet.")

    # Active Alerts
    with col_right:
        st.markdown("### 🚨 Inventory Alerts")
        alerts = [a for a in get_stock_alerts(conn) if not a['is_resolved']]
        if alerts:
            for a in alerts[:8]:
                sev = a['severity']
                cls = 'alert-critical' if sev=='Critical' else \
                      'alert-high'     if sev=='High'     else 'alert-medium'
                icon = '🔴' if sev=='Critical' else '🟡' if sev=='High' else '🔵'
                st.markdown(f"""
                <div class="{cls}">
                    {icon} <b>{a['alert_type']}</b> · {a['warehouse']}<br>
                    <small>{a['alert_message'][:80]}</small>
                </div>""", unsafe_allow_html=True)
        else:
            st.success("✅ No active alerts!")

    st.markdown("---")

    # Charts Row
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("### 📈 Product Sales (Quantity)")
        top_p = get_top_products(conn)
        if top_p:
            df_tp = pd.DataFrame([dict(r) for r in top_p])
            fig = px.bar(df_tp, x='product_name', y='total_qty',
                         color='total_revenue',
                         labels={'product_name':'Product','total_qty':'Units Sold'},
                         color_continuous_scale='Blues',
                         height=300)
            fig.update_layout(showlegend=False, margin=dict(t=10,b=0,l=0,r=0))
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("### 🏪 Warehouse Revenue")
        wh_perf = get_warehouse_performance(conn)
        if wh_perf:
            df_wh = pd.DataFrame([dict(r) for r in wh_perf])
            fig = px.pie(df_wh, names='warehouse', values='total_revenue',
                         color_discrete_sequence=px.colors.sequential.Blues_r,
                         height=300)
            fig.update_layout(margin=dict(t=10,b=0,l=0,r=0))
            st.plotly_chart(fig, use_container_width=True)

    # Expiring Soon Banner
    exp = get_expiring_soon(conn, 7)
    if exp:
        st.warning(f"⏰ **{len(exp)} batch(es) expiring within 7 days!** "
                   "Go to Inventory Management to view details.")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 2 – PLACE ORDER
# ═══════════════════════════════════════════════════════════════════════════
elif page == "🛒 Place Order":
    st.markdown('<div class="section-header">🛒 Place New Order</div>',
                unsafe_allow_html=True)

    # Session state cart
    if 'cart' not in st.session_state:
        st.session_state.cart = []
    if 'order_placed' not in st.session_state:
        st.session_state.order_placed = None

    # ── Step 1: Select Customer & Warehouse ─────────────────────
    with st.expander("📍 Step 1 — Select Customer & Warehouse", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            customers = get_all_customers(conn)
            cust_map = {f"{r['name']} ({r['phone']})": r['customer_id']
                        for r in customers}
            cust_label = st.selectbox("👤 Select Customer", list(cust_map.keys()))
            customer_id = cust_map[cust_label]

        with col2:
            warehouses = get_warehouses(conn)
            wh_map = {f"{r['name']} — {r['location']}": r['warehouse_id']
                      for r in warehouses}
            wh_label = st.selectbox("🏪 Select Warehouse (Dark Store)", list(wh_map.keys()))
            warehouse_id = wh_map[wh_label]

        payment_method = st.selectbox(
            "💳 Payment Method",
            ['UPI','Credit Card','Debit Card','Cash on Delivery','Net Banking','Wallet']
        )

    # ── Step 2: Browse & Add Products ────────────────────────────
    with st.expander("🛍️ Step 2 — Browse Products & Add to Cart", expanded=True):
        products = get_available_products(conn, warehouse_id)
        if not products:
            st.warning("No products available at this warehouse right now.")
        else:
            # Group by category
            cat_map = {}
            for p in products:
                cat_map.setdefault(p['category'], []).append(p)

            selected_cat = st.selectbox("Filter by Category",
                                        ['All'] + sorted(cat_map.keys()))
            display_prods = products if selected_cat == 'All' \
                            else cat_map.get(selected_cat, [])

            cols = st.columns(3)
            for idx, prod in enumerate(display_prods):
                with cols[idx % 3]:
                    expiry_str = prod['nearest_expiry'] or 'N/A'
                    in_cart = next((i for i in st.session_state.cart
                                    if i['batch_id']==prod['batch_id']), None)
                    qty_label = f"  ✅ (×{in_cart['quantity']} in cart)" if in_cart else ""

                    with st.container(border=True):
                        st.markdown(f"**{prod['product_name']}**{qty_label}")
                        st.caption(f"🏷️ {prod['brand']}  |  📂 {prod['category']}")
                        st.markdown(f"**₹{prod['price']:.2f}** "
                                    f"+ {prod['tax_rate']:.0f}% tax")
                        st.caption(f"📦 Available: {prod['available_qty']}  |  "
                                   f"🗓️ Exp: {expiry_str}")

                        qty = st.number_input(
                            "Qty", min_value=1,
                            max_value=int(prod['available_qty']),
                            value=1, key=f"qty_{prod['batch_id']}"
                        )
                        if st.button("➕ Add to Cart", key=f"add_{prod['batch_id']}"):
                            existing = next(
                                (i for i in st.session_state.cart
                                 if i['batch_id']==prod['batch_id']), None
                            )
                            if existing:
                                existing['quantity'] += qty
                            else:
                                st.session_state.cart.append({
                                    'product_id': prod['product_id'],
                                    'batch_id':   prod['batch_id'],
                                    'product_name': prod['product_name'],
                                    'quantity':   qty,
                                    'price':      prod['price'],
                                    'tax_rate':   prod['tax_rate'],
                                })
                            st.success(f"Added {qty}× {prod['product_name']} to cart!")
                            st.rerun()

    # ── Step 3: Review Cart & Place Order ────────────────────────
    with st.expander("🧾 Step 3 — Review Cart & Confirm Order", expanded=True):
        if not st.session_state.cart:
            st.info("Your cart is empty. Add products above.")
        else:
            total_sub = sum(i['quantity']*i['price'] for i in st.session_state.cart)
            total_tax = sum(i['quantity']*i['price']*(i['tax_rate']/100)
                            for i in st.session_state.cart)
            total_amt = total_sub + total_tax

            for idx, item in enumerate(st.session_state.cart):
                col1, col2, col3 = st.columns([4,2,1])
                with col1:
                    st.markdown(f"""<div class="cart-item">
                        <b>{item['product_name']}</b><br>
                        ₹{item['price']:.2f} × {item['quantity']} = 
                        <b>₹{item['quantity']*item['price']:.2f}</b>
                        + tax ₹{item['quantity']*item['price']*(item['tax_rate']/100):.2f}
                    </div>""", unsafe_allow_html=True)
                with col2:
                    new_qty = st.number_input("Qty", value=item['quantity'],
                                              min_value=1, key=f"cart_qty_{idx}")
                    if new_qty != item['quantity']:
                        st.session_state.cart[idx]['quantity'] = new_qty
                        st.rerun()
                with col3:
                    if st.button("🗑️", key=f"rm_{idx}"):
                        st.session_state.cart.pop(idx)
                        st.rerun()

            st.markdown("---")
            col_s, col_t, col_g = st.columns(3)
            col_s.metric("Subtotal",    f"₹{total_sub:.2f}")
            col_t.metric("Tax",         f"₹{total_tax:.2f}")
            col_g.metric("Grand Total", f"₹{total_amt:.2f}")

            col_place, col_clear = st.columns([3,1])
            with col_place:
                if st.button("🚀 Place Order Now", type="primary",
                              use_container_width=True):
                    try:
                        oid = place_order(conn, customer_id, warehouse_id,
                                          st.session_state.cart, payment_method)
                        st.session_state.order_placed = oid
                        st.session_state.cart = []
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Order failed: {e}")
            with col_clear:
                if st.button("🗑️ Clear Cart", use_container_width=True):
                    st.session_state.cart = []
                    st.rerun()

    # ── Order Success Banner ──────────────────────────────────────
    if st.session_state.order_placed:
        oid = st.session_state.order_placed
        items = get_order_items(conn, oid)
        orders = get_order_history(conn)
        order = next((o for o in orders if o['order_id']==oid), None)
        if order:
            st.success(f"""
            ✅ **Order #{order['order_number']} placed successfully!**
            🚚 Estimated delivery: ~20 minutes  |  
            💳 Payment: {order['payment_method']} — {order['payment_status']}  |  
            🚴 Partner: {order['partner_name'] or 'Assigning...'}
            """)
            st.markdown("**Trigger Fired:** `trg_after_order_item_insert` — "
                        "inventory auto-deducted & Stock_Ledger entries created for each item.")
        if st.button("Place Another Order"):
            st.session_state.order_placed = None
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 3 – ORDER HISTORY & TRACKING
# ═══════════════════════════════════════════════════════════════════════════
elif page == "📦 Order History & Tracking":
    st.markdown('<div class="section-header">📦 Order History & Tracking</div>',
                unsafe_allow_html=True)

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        customers = get_all_customers(conn)
        cust_opts = ['All Customers'] + \
                    [f"{r['name']} ({r['phone']})" for r in customers]
        cust_sel = st.selectbox("Filter by Customer", cust_opts)
    with col2:
        status_filter = st.selectbox("Filter by Status",
            ['All','Placed','Confirmed','Processing','Packed',
             'Out for Delivery','Delivered','Cancelled','Returned'])
    with col3:
        st.markdown("")
        search_id = st.text_input("Search Order Number", placeholder="ORD-2026-00001")

    # Fetch orders
    if cust_sel == 'All Customers':
        orders = get_order_history(conn)
    else:
        cid = next(r['customer_id'] for r in customers
                   if f"{r['name']} ({r['phone']})" == cust_sel)
        orders = get_order_history(conn, cid)

    if status_filter != 'All':
        orders = [o for o in orders if o['order_status'] == status_filter]
    if search_id:
        orders = [o for o in orders if search_id.upper() in o['order_number'].upper()]

    st.markdown(f"**{len(orders)} orders found**")

    if orders:
        for order in orders:
            with st.expander(
                f"🔖 {order['order_number']}  |  {order['customer_name']}  |  "
                f"₹{order['total_amount']:.2f}  |  {order['order_status']}", 
                expanded=False
            ):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total",   f"₹{order['total_amount']:.2f}")
                c2.metric("Status",  order['order_status'])
                c3.metric("Payment", order['payment_status'])
                c4.metric("Warehouse", order['warehouse_name'])

                col_det, col_upd = st.columns([3,1])
                with col_det:
                    items = get_order_items(conn, order['order_id'])
                    if items:
                        df = pd.DataFrame([dict(i) for i in items])
                        df['Line Total'] = (df['quantity'] * df['price_at_time'].fillna(0)).fillna(0).map(
                            lambda x: f"₹{x:.2f}")
                        df['Price'] = df['price_at_time'].fillna(0).map(lambda x: f"₹{x:.2f}")
                        st.dataframe(
                            df[['product_name','brand','quantity','Price',
                                'Line Total','expiry_date','batch_number']],
                            use_container_width=True, hide_index=True
                        )
                    st.caption(
                        f"🕐 Placed: {order['placed_at']}  |  "
                        f"📍 ETA: {order['expected_delivery_time'] or 'N/A'}  |  "
                        f"🚴 Partner: {order['partner_name'] or 'N/A'}"
                    )

                with col_upd:
                    if order['order_status'] not in ('Delivered','Cancelled','Returned'):
                        allowed = {
                            'Placed':          ['Confirmed','Cancelled'],
                            'Confirmed':       ['Processing','Cancelled'],
                            'Processing':      ['Packed','Cancelled'],
                            'Packed':          ['Out for Delivery'],
                            'Out for Delivery':['Delivered'],
                        }
                        opts = allowed.get(order['order_status'], [])
                        if opts:
                            new_s = st.selectbox("Update Status", opts,
                                                  key=f"upd_{order['order_id']}")
                            if st.button("✅ Update",
                                         key=f"btn_{order['order_id']}"):
                                update_order_status(conn, order['order_id'], new_s)
                                st.success(f"Status → {new_s}")
                                st.rerun()
    else:
        st.info("No orders found for the selected filters.")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 4 – INVENTORY MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════
elif page == "🏪 Inventory Management":
    st.markdown('<div class="section-header">🏪 Inventory Management</div>',
                unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Stock Overview",
        "📦 Batch Details",
        "🚨 Alerts",
        "🔄 Stock Ledger",
        "➕ Replenish Stock"
    ])

    warehouses = get_warehouses(conn)
    wh_opts = ['All Warehouses'] + [r['name'] for r in warehouses]
    wh_id_map = {r['name']: r['warehouse_id'] for r in warehouses}

    # ── Tab 1: Stock Overview ──────────────────────────────────────
    with tab1:
        sel_wh = st.selectbox("Warehouse", wh_opts, key="inv_wh")
        wid = wh_id_map.get(sel_wh) if sel_wh != 'All Warehouses' else None
        inv = get_inventory_summary(conn, wid)
        if inv:
            df = pd.DataFrame([dict(r) for r in inv])
            df['Stock Status'] = df['stock_status'].map(
                lambda s: f"🔴 {s}" if 'Out' in s else
                          f"🟡 {s}" if 'Low' in s else f"🟢 {s}"
            )
            df['Available'] = df['available_qty'].astype(str)

            # Summary counts
            c1, c2, c3 = st.columns(3)
            c1.metric("🟢 In Stock",     len(df[df['stock_status']=='In Stock']))
            c2.metric("🟡 Low Stock",    len(df[df['stock_status']=='Low Stock']))
            c3.metric("🔴 Out of Stock", len(df[df['stock_status']=='Out of Stock']))

            # Chart
            if wid:
                fig = px.bar(df, x='product_name', y='available_qty',
                             color='stock_status',
                             color_discrete_map={
                                 'In Stock':'#22c55e',
                                 'Low Stock':'#f59e0b',
                                 'Out of Stock':'#ef4444'
                             },
                             labels={'product_name':'Product','available_qty':'Qty'},
                             height=300)
                fig.update_layout(margin=dict(t=0,b=0), showlegend=True)
                st.plotly_chart(fig, use_container_width=True)

            st.dataframe(
                df[['warehouse_name','product_name','brand','category',
                    'total_quantity','reserved_quantity','Available',
                    'reorder_threshold','Stock Status']],
                use_container_width=True, hide_index=True
            )
        else:
            st.info("No inventory data.")

    # ── Tab 2: Batch Details ───────────────────────────────────────
    with tab2:
        sel_wh2 = st.selectbox("Warehouse", wh_opts, key="batch_wh")
        wid2 = wh_id_map.get(sel_wh2) if sel_wh2 != 'All Warehouses' else None
        batches = get_batch_details(conn, wid2)
        if batches:
            df = pd.DataFrame([dict(r) for r in batches])
            df['Status'] = df['batch_status'].map(
                lambda s: f"⛔ {s}" if s in ('Expired','Out of Stock') else
                          f"⚠️ {s}" if s in ('Expiring Soon','Low Stock') else f"✅ {s}"
            )

            # Expiry timeline chart
            df_chart = df[df['batch_status'] != 'Expired'].copy()
            if not df_chart.empty:
                fig = px.scatter(
                    df_chart, x='expiry_date', y='product',
                    size='current_quantity',
                    color='batch_status',
                    color_discrete_map={
                        'OK':'#22c55e','Low Stock':'#f59e0b',
                        'Expiring Soon':'#f97316','Out of Stock':'#ef4444'
                    },
                    hover_data=['warehouse','supplier','current_quantity'],
                    title="Batch Expiry Timeline",
                    height=350
                )
                fig.update_layout(margin=dict(t=30,b=0))
                st.plotly_chart(fig, use_container_width=True)

            st.dataframe(
                df[['batch_id','batch_number','warehouse','product','supplier',
                    'manufacture_date','expiry_date','initial_quantity',
                    'current_quantity','reorder_level','shelf_location',
                    'cost_price','Status']],
                use_container_width=True, hide_index=True
            )
        else:
            st.info("No batch data.")

    # ── Tab 3: Alerts ─────────────────────────────────────────────
    with tab3:
        st.markdown("#### 🚨 Inventory Alerts")
        show_resolved = st.checkbox("Show Resolved Alerts")
        alerts = get_stock_alerts(conn)
        if not show_resolved:
            alerts = [a for a in alerts if not a['is_resolved']]

        if alerts:
            for a in alerts:
                col1, col2 = st.columns([5,1])
                with col1:
                    sev = a['severity']
                    cls = ('alert-critical' if sev=='Critical' else
                           'alert-high'     if sev=='High' else 'alert-medium')
                    icon = ('🔴' if sev=='Critical' else
                            '🟡' if sev=='High'     else '🔵')
                    resolved_tag = " ✅ (Resolved)" if a['is_resolved'] else ""
                    st.markdown(f"""
                    <div class="{cls}">
                        {icon} <b>[{sev}] {a['alert_type']}</b>{resolved_tag}<br>
                        📍 {a['warehouse']}  |  
                        📦 {a['product'] or 'N/A'}<br>
                        <small>{a['alert_message']}</small><br>
                        <small>🕐 {a['created_at']}</small>
                    </div>""", unsafe_allow_html=True)
                with col2:
                    if not a['is_resolved']:
                        if st.button("✅ Resolve", key=f"res_{a['alert_id']}"):
                            resolve_alert(conn, a['alert_id'])
                            st.success("Resolved!")
                            st.rerun()

        else:
            st.success("✅ No active alerts!")

        st.markdown("---")
        st.markdown("**Trigger 2 Demo:** `trg_low_stock_alert`")
        st.info(
            "This trigger fires automatically **AFTER UPDATE** on `Batch_Inventory`. "
            "When `current_quantity` drops ≤ `reorder_level`, a **High** alert is "
            "auto-inserted. When it hits 0, a **Critical** alert is created. "
            "All alerts above are auto-generated by this database trigger."
        )

    # ── Tab 4: Stock Ledger ────────────────────────────────────────
    with tab4:
        st.markdown("#### 📜 Stock Movement Audit Trail")
        st.caption("All inventory changes are automatically logged here. "
                   "Sale entries are created by **Trigger 1** (`trg_after_order_item_insert`).")
        ledger = get_stock_ledger(conn, limit=50)
        if ledger:
            df = pd.DataFrame([dict(r) for r in ledger])
            df['Change'] = df['quantity_change'].map(
                lambda x: f"+{x}" if x > 0 else str(x)
            )
            type_colors = {
                'Sale':'🔴','Stock In':'🟢','Damage':'🟠',
                'Return':'🔵','Adjustment':'🟡','Expiry':'⛔'
            }
            df['Type'] = df['transaction_type'].map(
                lambda t: f"{type_colors.get(t,'⚪')} {t}"
            )
            st.dataframe(
                df[['ledger_id','Type','product_name','warehouse_name',
                    'Change','previous_quantity','new_quantity',
                    'reference_type','performed_by','transaction_date']],
                use_container_width=True, hide_index=True
            )
        else:
            st.info("No ledger entries yet.")

    # ── Tab 5: Replenish ───────────────────────────────────────────
    with tab5:
        st.markdown("#### ➕ Replenish Batch Stock")
        batches_all = get_batch_details(conn)
        if batches_all:
            batch_opts = {
                f"Batch {b['batch_id']} | {b['product']} @ {b['warehouse']} "
                f"(Current: {b['current_quantity']})": b['batch_id']
                for b in batches_all
            }
            sel_batch = st.selectbox("Select Batch", list(batch_opts.keys()))
            bid = batch_opts[sel_batch]
            qty_add = st.number_input("Quantity to Add", min_value=1, value=50)
            performer = st.text_input("Performed By", value="Warehouse Staff")
            if st.button("✅ Replenish Stock", type="primary"):
                try:
                    replenish_stock(conn, bid, qty_add, performer)
                    st.success(f"✅ Added {qty_add} units to batch {bid}!")
                    st.info("Trigger check: `trg_low_stock_alert` will auto-resolve "
                            "if stock now exceeds reorder level.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 5 – ANALYTICS & REPORTS
# ═══════════════════════════════════════════════════════════════════════════
elif page == "📊 Analytics & Reports":
    st.markdown('<div class="section-header">📊 Analytics & Reports</div>',
                unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Sales Analysis",
        "👤 Customer Analysis",
        "🏪 Warehouse Performance",
        "🚴 Delivery Performance"
    ])

    # ── Tab 1: Sales ──────────────────────────────────────────────
    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 🏆 Top Selling Products")
            top_p = get_top_products(conn)
            if top_p:
                df = pd.DataFrame([dict(r) for r in top_p])
                fig = px.bar(df, x='total_revenue', y='product_name',
                             orientation='h',
                             color='total_qty',
                             color_continuous_scale='Viridis',
                             labels={'total_revenue':'Revenue (₹)',
                                     'product_name':'Product',
                                     'total_qty':'Units Sold'},
                             height=400)
                fig.update_layout(yaxis={'categoryorder':'total ascending'},
                                  margin=dict(t=0,b=0))
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(df[['product_name','brand','total_qty',
                                  'order_count','total_revenue']],
                             use_container_width=True, hide_index=True)

        with col2:
            st.markdown("#### 📉 Revenue by Product")
            if top_p:
                fig = px.treemap(df, path=['product_name'], values='total_revenue',
                                 color='total_qty',
                                 color_continuous_scale='Blues',
                                 height=400)
                fig.update_layout(margin=dict(t=0,b=0))
                st.plotly_chart(fig, use_container_width=True)

        # Expiring items risk table
        st.markdown("#### ⏰ Items Expiring Soon (Next 7 Days)")
        exp = get_expiring_soon(conn, 7)
        if exp:
            df_exp = pd.DataFrame([dict(r) for r in exp])
            df_exp['days_left'] = df_exp['days_left'].fillna(0).map(lambda x: f"{x:.1f} days")
            st.dataframe(df_exp[['product','warehouse','expiry_date',
                                  'current_quantity','days_left']],
                         use_container_width=True, hide_index=True)
        else:
            st.success("No items expiring in the next 7 days!")

    # ── Tab 2: Customer Analysis ──────────────────────────────────
    with tab2:
        st.markdown("#### 👤 Customer Segmentation & Spending")
        custs = get_customer_analysis(conn)
        if custs:
            df = pd.DataFrame([dict(r) for r in custs])

            # Segment chart
            seg_counts = df['customer_segment'].value_counts()
            fig_pie = px.pie(values=seg_counts.values,
                             names=seg_counts.index,
                             color_discrete_sequence=px.colors.qualitative.Set3,
                             title="Customer Segments",
                             height=300)
            fig_pie.update_layout(margin=dict(t=30,b=0))

            # Spending chart
            fig_bar = px.bar(df.head(8), x='name', y='total_spent',
                             color='customer_segment',
                             labels={'name':'Customer','total_spent':'Total Spent (₹)'},
                             title="Top Customer Spending",
                             height=300)
            fig_bar.update_layout(margin=dict(t=30,b=0), showlegend=False)

            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(fig_pie, use_container_width=True)
            with col2:
                st.plotly_chart(fig_bar, use_container_width=True)

            # Table
            df['Total Spent'] = df['total_spent'].fillna(0).map(lambda x: f"₹{x:.2f}")
            st.dataframe(
                df[['customer_id','name','phone','email','total_orders',
                    'Total Spent','customer_segment','preferred_warehouse']],
                use_container_width=True, hide_index=True
            )
        else:
            st.info("No customer data yet.")

    # ── Tab 3: Warehouse Performance ──────────────────────────────
    with tab3:
        st.markdown("#### 🏪 Warehouse Performance Comparison")
        wh_perf = get_warehouse_performance(conn)
        if wh_perf:
            df = pd.DataFrame([dict(r) for r in wh_perf])

            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(df, x='warehouse', y=['delivered','cancelled'],
                             barmode='group',
                             color_discrete_map={
                                 'delivered':'#22c55e','cancelled':'#ef4444'
                             },
                             labels={'warehouse':'Warehouse'},
                             title="Orders: Delivered vs Cancelled",
                             height=300)
                fig.update_layout(margin=dict(t=30,b=0))
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                fig2 = px.bar(df, x='warehouse', y='total_revenue',
                              color='total_revenue',
                              color_continuous_scale='Greens',
                              labels={'warehouse':'Warehouse',
                                      'total_revenue':'Revenue (₹)'},
                              title="Total Revenue by Warehouse",
                              height=300)
                fig2.update_layout(margin=dict(t=30,b=0), showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)

            df['Revenue'] = df['total_revenue'].fillna(0).map(lambda x: f"₹{x:.2f}")
            df['Avg Delivery (mins)'] = df['avg_delivery_mins'].fillna(0).map(
                lambda x: f"{x:.1f} min")
            st.dataframe(
                df[['warehouse','total_orders','delivered','cancelled',
                    'Avg Delivery (mins)','Revenue']],
                use_container_width=True, hide_index=True
            )

    # ── Tab 4: Delivery Performance ───────────────────────────────
    with tab4:
        st.markdown("#### 🚴 Delivery Partner Performance")
        dp_perf = get_delivery_partner_performance(conn)
        if dp_perf:
            df = pd.DataFrame([dict(r) for r in dp_perf])

            fig = go.Figure()
            fig.add_trace(go.Bar(
                name='Total Deliveries',
                x=df['name'], y=df['total_deliveries'],
                marker_color='#3b82f6'
            ))
            fig.add_trace(go.Bar(
                name='Successful',
                x=df['name'], y=df['successful_deliveries'],
                marker_color='#22c55e'
            ))
            fig.add_trace(go.Scatter(
                name='Rating (×10)',
                x=df['name'], y=df['rating'].fillna(0)*10,
                mode='lines+markers',
                yaxis='y2',
                line=dict(color='#f59e0b', width=3)
            ))
            fig.update_layout(
                barmode='group',
                yaxis2=dict(overlaying='y', side='right', title='Rating ×10'),
                height=350,
                margin=dict(t=10,b=0)
            )
            st.plotly_chart(fig, use_container_width=True)

            status_map = {
                'Available':'🟢 Available',
                'Busy':'🟠 Busy',
                'Offline':'⚫ Offline',
                'On Break':'🟡 On Break'
            }
            df['Status'] = df['availability_status'].map(
                lambda s: status_map.get(s, s))
            df['Rating ⭐'] = df['rating'].fillna(0).map(lambda r: f"⭐ {r:.1f}")
            st.dataframe(
                df[['name','vehicle_type','warehouse','Rating ⭐',
                    'total_deliveries','successful_deliveries','Status']],
                use_container_width=True, hide_index=True
            )



# ═══════════════════════════════════════════════════════════════════════════
# PAGE 6 – TRANSACTIONS
# ═══════════════════════════════════════════════════════════════════════════
elif page == "🔄 Transactions":
    st.markdown('<div class="section-header">🔄 Transaction & Concurrency Demo</div>',
                unsafe_allow_html=True)
    st.caption("Each demo resets the dedicated transaction demo tables first, so the results stay predictable for classroom demonstrations.")

    if "transaction_demo_runs" not in st.session_state:
        st.session_state.transaction_demo_runs = {}

    demo_catalog = get_transaction_demo_catalog()

    top_col1, top_col2 = st.columns([4, 1])
    with top_col1:
        st.info("These transaction demos now use SQL embedded directly inside database.py, so the app is self-contained and no external transaction_examples folder is required.")
    with top_col2:
        if st.button("🔁 Reset Demo Data", use_container_width=True):
            reset_transaction_demo()
            st.session_state.transaction_demo_runs = {}
            st.success("Demo tables reset to their baseline values.")

    baseline = get_transaction_demo_snapshot()
    base_cols = st.columns([3, 2])
    with base_cols[0]:
        st.markdown("#### Current Demo Inventory")
        if baseline["inventory"]:
            st.dataframe(pd.DataFrame(baseline["inventory"]), use_container_width=True, hide_index=True)
        else:
            st.info("Demo inventory is empty.")
    with base_cols[1]:
        st.markdown("#### Latest Demo Logs")
        if baseline["logs"]:
            st.dataframe(pd.DataFrame(baseline["logs"]), use_container_width=True, hide_index=True)
        else:
            st.info("No demo logs available yet.")

    def render_snapshot_pair(result_key: str):
        result = st.session_state.transaction_demo_runs.get(result_key)
        if not result:
            return

        if result.get("ok"):
            st.success(result.get("message", "Transaction executed successfully."))
        else:
            st.error(result.get("message", "Transaction execution failed."))

        if result.get("timeline"):
            st.markdown("**Execution timeline**")
            for step in result["timeline"]:
                st.markdown(f"- **{step['session']}** — {step['message']}")

        before_col, after_col = st.columns(2)
        with before_col:
            st.markdown("##### Before execution")
            st.dataframe(pd.DataFrame(result.get("before", {}).get("inventory", [])), use_container_width=True, hide_index=True)
        with after_col:
            st.markdown("##### After execution")
            st.dataframe(pd.DataFrame(result.get("after", {}).get("inventory", [])), use_container_width=True, hide_index=True)

        st.markdown("##### Persistent audit trail after execution")
        logs_df = pd.DataFrame(result.get("after", {}).get("logs", []))
        if not logs_df.empty:
            st.dataframe(logs_df, use_container_width=True, hide_index=True)
        else:
            st.info("No audit rows were written for this run.")

    tab_commit, tab_rollback, tab_conflict = st.tabs([
        "✅ Committed Transactions",
        "↩️ Rollback Transaction",
        "⚠️ Conflicting Transactions"
    ])

    with tab_commit:
        sale_meta = demo_catalog["committed_sale"]
        restock_meta = demo_catalog["committed_restock"]
        commit_col1, commit_col2 = st.columns(2)

        with commit_col1:
            st.markdown(f"### {sale_meta['title']}")
            st.write(sale_meta["description"])
            st.markdown(f"**Impact on database:** {sale_meta['impact']}")
            st.caption(sale_meta['script_label'])
            with st.expander("View SQL used in this example"):
                st.code(load_transaction_demo_sql("committed_sale"), language="sql")
            if st.button("Run committed sale example", key="run_committed_sale", use_container_width=True):
                with st.spinner("Running committed sale example..."):
                    st.session_state.transaction_demo_runs["committed_sale"] = run_transaction_demo("committed_sale")
            render_snapshot_pair("committed_sale")

        with commit_col2:
            st.markdown(f"### {restock_meta['title']}")
            st.write(restock_meta["description"])
            st.markdown(f"**Impact on database:** {restock_meta['impact']}")
            st.caption(restock_meta['script_label'])
            with st.expander("View SQL used in this example"):
                st.code(load_transaction_demo_sql("committed_restock"), language="sql")
            if st.button("Run committed restock example", key="run_committed_restock", use_container_width=True):
                with st.spinner("Running committed restock example..."):
                    st.session_state.transaction_demo_runs["committed_restock"] = run_transaction_demo("committed_restock")
            render_snapshot_pair("committed_restock")

    with tab_rollback:
        rollback_meta = demo_catalog["rollback_sale"]
        st.markdown(f"### {rollback_meta['title']}")
        st.write(rollback_meta["description"])
        st.markdown(f"**Impact on database:** {rollback_meta['impact']}")
        st.caption(rollback_meta['script_label'])
        with st.expander("View SQL used in this example"):
            st.code(load_transaction_demo_sql("rollback_sale"), language="sql")
        if st.button("Run rollback example", key="run_rollback_sale", use_container_width=True):
            with st.spinner("Running rollback example..."):
                st.session_state.transaction_demo_runs["rollback_sale"] = run_transaction_demo("rollback_sale")
        render_snapshot_pair("rollback_sale")

    with tab_conflict:
        conflict_meta = demo_catalog["conflict_pair"]
        st.markdown(f"### {conflict_meta['title']}")
        st.write(conflict_meta["description"])
        st.markdown(f"**Impact on database:** {conflict_meta['impact']}")
        st.caption(f"Embedded SQL blocks: {', '.join(conflict_meta['script_labels'])}")

        sql_col1, sql_col2 = st.columns(2)
        with sql_col1:
            with st.expander("Session A SQL"):
                st.code(load_transaction_demo_sql("conflict_session_a"), language="sql")
        with sql_col2:
            with st.expander("Session B SQL"):
                st.code(load_transaction_demo_sql("conflict_session_b"), language="sql")

        if st.button("Run conflicting transaction demo", key="run_conflict_demo", use_container_width=True):
            with st.spinner("Running concurrent sessions and waiting for the conflict outcome..."):
                st.session_state.transaction_demo_runs["conflict_pair"] = run_conflicting_transaction_demo()
        render_snapshot_pair("conflict_pair")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 7 – ADMIN PANEL
# ═══════════════════════════════════════════════════════════════════════════
elif page == "👥 Admin Panel":
    st.markdown('<div class="section-header">⚙️ Admin Panel</div>',
                unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs([
        "👤 Customers",
        "🚴 Delivery Partners",
        "🏷️ Trigger Demo",
        "📖 About"
    ])

    # ── Tab 1: Customers ──────────────────────────────────────────
    with tab1:
        st.markdown("#### 👥 All Customers")
        custs = get_all_customers(conn)
        if custs:
            df = pd.DataFrame([dict(c) for c in custs])
            df['Spent'] = df['total_spent'].fillna(0).map(lambda x: f"₹{x:.2f}")
            st.dataframe(
                df[['customer_id','name','phone','email','total_orders',
                    'Spent','preferred_warehouse_id']],
                use_container_width=True, hide_index=True
            )

        st.markdown("---")
        st.markdown("#### ➕ Add New Customer")
        with st.form("add_cust"):
            c1, c2 = st.columns(2)
            c_name  = c1.text_input("Full Name")
            c_phone = c2.text_input("Phone")
            c_email = c1.text_input("Email")
            c_pin   = c2.text_input("Pincode")
            c_addr  = st.text_area("Address", height=80)
            warehouses = get_warehouses(conn)
            wh_m = {r['name']: r['warehouse_id'] for r in warehouses}
            c_wh = st.selectbox("Preferred Warehouse", list(wh_m.keys()))
            submitted = st.form_submit_button("Add Customer")
            if submitted and c_name and c_phone and c_email:
                try:
                    add_customer(conn, c_name, c_phone, c_email,
                                 c_addr, c_pin, wh_m[c_wh])
                    st.success(f"✅ Customer '{c_name}' added!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # ── Tab 2: Delivery Partners ───────────────────────────────────
    with tab2:
        st.markdown("#### 🚴 Delivery Partners")
        dp = get_delivery_partner_performance(conn)
        if dp:
            df = pd.DataFrame([dict(d) for d in dp])
            st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("#### ➕ Add Delivery Partner")
        with st.form("add_dp"):
            c1, c2 = st.columns(2)
            dp_name    = c1.text_input("Full Name")
            dp_phone   = c2.text_input("Phone")
            dp_email   = c1.text_input("Email")
            dp_vehicle = c2.selectbox("Vehicle Type",
                                       ['Bike','Scooter','Bicycle','Car'])
            dp_vnum    = c1.text_input("Vehicle Number")
            dp_addr    = st.text_area("Address", height=60)
            warehouses = get_warehouses(conn)
            wh_m = {r['name']: r['warehouse_id'] for r in warehouses}
            dp_wh = st.selectbox("Assigned Warehouse", list(wh_m.keys()))
            submitted = st.form_submit_button("Add Delivery Partner")
            if submitted and dp_name and dp_phone:
                try:
                    add_delivery_partner(conn, dp_name, dp_phone, dp_email,
                                         dp_vehicle, dp_vnum, dp_addr,
                                         wh_m[dp_wh])
                    st.success(f"✅ Partner '{dp_name}' added!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # ── Tab 3: Trigger Demo ────────────────────────────────────────
    with tab3:
        st.markdown("## 🔥 Database Trigger Documentation & Live Demo")

        st.markdown("""
        ### Trigger 1 — `trg_after_order_item_insert`
        **Type:** AFTER INSERT on `Order_Item`  
        **Purpose:** Implements the FEFO stock deduction pipeline.

        **Actions Taken Automatically:**
        1. 📉 Deducts `quantity` from `Batch_Inventory.current_quantity`
        2. 📉 Deducts `quantity` from aggregated `Inventory.total_quantity`
        3. 📝 Inserts a **Sale** record into `Stock_Ledger` with before/after quantities

        **Business Rule Enforced:** Every sale is atomically recorded with a full audit trail — 
        no manual coding needed in the application layer.
        """)

        with st.expander("📋 View Trigger 1 SQL"):
            st.code("""
CREATE TRIGGER trg_after_order_item_insert
AFTER INSERT ON Order_Item
FOR EACH ROW
BEGIN
    -- Step 1: Deduct from Batch_Inventory
    UPDATE Batch_Inventory
    SET current_quantity = current_quantity - NEW.quantity
    WHERE batch_id = NEW.batch_id;

    -- Step 2: Deduct from aggregated Inventory
    UPDATE Inventory
    SET total_quantity = total_quantity - NEW.quantity
    WHERE product_id = NEW.product_id
      AND warehouse_id = (
          SELECT warehouse_id FROM Batch_Inventory WHERE batch_id = NEW.batch_id
      );

    -- Step 3: Insert Sale audit record into Stock_Ledger
    INSERT INTO Stock_Ledger (
        batch_id, transaction_type, quantity_change,
        transaction_date, reference_type, reference_id,
        performed_by, notes, previous_quantity, new_quantity
    )
    SELECT
        NEW.batch_id, 'Sale', -NEW.quantity, datetime('now'),
        'Order', NEW.order_id,
        'TRIGGER:trg_after_order_item_insert',
        'Auto-deducted on order item insert',
        current_quantity + NEW.quantity, current_quantity
    FROM Batch_Inventory WHERE batch_id = NEW.batch_id;
END;
            """, language='sql')

        st.markdown("""
        ---
        ### Trigger 2 — `trg_low_stock_alert`
        **Type:** AFTER UPDATE OF `current_quantity` on `Batch_Inventory`  
        **Purpose:** Real-time inventory monitoring & automated alerting.

        **Actions Taken Automatically:**
        - 🟡 If `current_quantity` drops to ≤ `reorder_level` → inserts **High** alert
        - 🔴 If `current_quantity` reaches `0` → inserts **Critical "Out of Stock"** alert
        - Duplicate prevention: checks for existing unresolved alerts before inserting

        **Business Rule Enforced:** Operations team is always notified immediately when 
        stock is critically low — with zero application-layer polling needed.
        """)

        with st.expander("📋 View Trigger 2 SQL"):
            st.code("""
CREATE TRIGGER trg_low_stock_alert
AFTER UPDATE OF current_quantity ON Batch_Inventory
FOR EACH ROW
WHEN NEW.current_quantity != OLD.current_quantity
BEGIN
    -- Case A: Stock hits zero → Critical alert
    INSERT INTO Warehouse_Inventory_Alert (
        warehouse_id, product_id, batch_id,
        alert_type, alert_message, severity, is_resolved
    )
    SELECT
        NEW.warehouse_id, NEW.product_id, NEW.batch_id,
        'Out of Stock',
        'CRITICAL: Batch ' || NEW.batch_id || ' is completely out of stock.',
        'Critical', 0
    WHERE NEW.current_quantity = 0
      AND OLD.current_quantity > 0
      AND NOT EXISTS (
          SELECT 1 FROM Warehouse_Inventory_Alert
          WHERE batch_id = NEW.batch_id
            AND alert_type = 'Out of Stock'
            AND is_resolved = 0
      );

    -- Case B: Stock below reorder level → High alert
    INSERT INTO Warehouse_Inventory_Alert (
        warehouse_id, product_id, batch_id,
        alert_type, alert_message, severity, is_resolved
    )
    SELECT
        NEW.warehouse_id, NEW.product_id, NEW.batch_id,
        'Low Stock',
        'LOW STOCK: Batch ' || NEW.batch_id ||
            ' — Current: ' || NEW.current_quantity ||
            ', Reorder Level: ' || NEW.reorder_level,
        'High', 0
    WHERE NEW.current_quantity > 0
      AND NEW.current_quantity <= NEW.reorder_level
      AND OLD.current_quantity > NEW.reorder_level
      AND NOT EXISTS (
          SELECT 1 FROM Warehouse_Inventory_Alert
          WHERE batch_id = NEW.batch_id
            AND alert_type = 'Low Stock'
            AND is_resolved = 0
      );
END;
            """, language='sql')

        st.markdown("---")
        st.markdown("### 🧪 Live Trigger Test")
        st.info("Place an order on the 🛒 Place Order page to see Trigger 1 fire "
                "and watch the Stock Ledger populate in real time. "
                "Or use the Replenish tab to push stock below reorder level "
                "by manually adjusting a batch quantity.")

        # Show recent Stock_Ledger (trigger 1 output)
        st.markdown("#### Stock Ledger — Last 10 auto-trigger entries")
        ledger = get_stock_ledger(conn, limit=10)
        if ledger:
            df = pd.DataFrame([dict(r) for r in ledger])
            df['Δ Qty'] = df['quantity_change'].map(
                lambda x: f"+{x}" if x > 0 else str(x))
            st.dataframe(
                df[['ledger_id','transaction_type','product_name',
                    'warehouse_name','Δ Qty','previous_quantity',
                    'new_quantity','performed_by','transaction_date']],
                use_container_width=True, hide_index=True
            )

    # ── Tab 4: About ───────────────────────────────────────────────
    with tab4:
        st.markdown("""
        ## ⚡ Quick Commerce Demand & Supply Database System

        | Field | Details |
        |-------|---------|
        | **Institute** | Indraprastha Institute of Information Technology, Delhi |
        | **Course** | Fundamentals of Database Management Systems |
        | **Project** | Quick Commerce Demand & Supply DB System |
        | **Group** | 78 — Tutorial Section 6 |
        | **Members** | Palak Maurya (2024400), Akshat Gupta (2024057), Anand Raj (2024068) |
        | **TAs** | Nidhi Jha, Mann Khatri |
        | **Date** | January 2026 |

        ---

        ## 🗄️ Database Schema (18 Tables)

        | # | Table | Purpose |
        |---|-------|---------|
        | 1 | `Category` | Hierarchical product categories |
        | 2 | `Supplier` | Vendor / supplier management |
        | 3 | `Product` | Global product catalog |
        | 4 | `Warehouse` | Dark store locations |
        | 5 | `Batch_Inventory` | Batch-level stock (FEFO) |
        | 6 | `Inventory` | Aggregated stock per warehouse |
        | 7 | `Customer` | Customer profiles |
        | 8 | `Customer_Address` | Multiple delivery addresses |
        | 9 | `Delivery_Partner` | Rider management |
        | 10 | `Orders` | Order lifecycle |
        | 11 | `Order_Item` | Line items per order |
        | 12 | `Payment` | Payment records |
        | 13 | `Stock_Ledger` | Full inventory audit trail |
        | 14 | `Warehouse_Inventory_Alert` | Auto-generated alerts |
        | 15 | `Coupon` | Discounts & promotions |
        | 16 | `Product_Review` | Customer reviews |
        | 17 | `Delivery_Rating` | Rider ratings |
        | 18 | *(Schema normalized to 3NF)* | |

        ---

        ## 🔥 Two Database Triggers

        ### Trigger 1: `trg_after_order_item_insert`
        - **When:** AFTER INSERT on `Order_Item`
        - **Effect:** Auto-deducts stock from `Batch_Inventory` + `Inventory`, 
          inserts Sale record in `Stock_Ledger`

        ### Trigger 2: `trg_low_stock_alert`  
        - **When:** AFTER UPDATE OF `current_quantity` on `Batch_Inventory`
        - **Effect:** Auto-creates `Warehouse_Inventory_Alert` for Low Stock / Out of Stock

        ---

        ## 💡 Application Use Cases

        ### Use Case 1: Order Placement
        - Customer selection → Warehouse selection → Product catalog browsing
        - Cart management → Atomic order placement with embedded SQL
        - Payment processing → Delivery partner auto-assignment
        - Order status tracking with real-time updates

        ### Use Case 2: Inventory & Customer Analysis
        - Stock overview across all dark stores
        - Batch-level FEFO management with expiry tracking
        - Customer segmentation (New / Occasional / Regular / Premium)
        - Warehouse & delivery performance analytics
        - Real-time alert management

        ---

        ## 🛠️ Tech Stack
        - **Database:** SQLite (with MySQL-compatible schema)
        - **Backend:** Python 3 with `sqlite3` (Embedded SQL)
        - **UI:** Streamlit + Plotly
        - **Design Pattern:** Embedded SQL — all queries written inline 
          using `cursor.execute()` with parameterized queries
        """)
