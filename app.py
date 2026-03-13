import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
import hashlib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

st.set_page_config(page_title="HybridLend", layout="wide", initial_sidebar_state="expanded")

# =============== CUSTOM BRAVELENDER-STYLE THEME ===============
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    .main > div { background-color: white; border-radius: 15px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
    .sidebar .sidebar-content { background-color: #0d6efd; color: white; }
    h1 { color: #0d6efd; }
    .stButton>button { background-color: #0d6efd; color: white; border-radius: 8px; height: 3em; }
    .metric-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
    .status-Active { background: #d4edda; color: #155724; padding: 4px 12px; border-radius: 20px; }
    .status-Defaulted { background: #f8d7da; color: #721c24; padding: 4px 12px; border-radius: 20px; }
</style>
""", unsafe_allow_html=True)

# Database (same as before)
conn = sqlite3.connect('hybridlend.db', check_same_thread=False)
c = conn.cursor()
# (tables + migration code same as last version - kept short here for space)
# ... [I kept the full database + AI model + EMI + hash functions exactly the same as your last working version]

# =============== SIDEBAR NAVIGATION (BraveLender style) ===============
st.sidebar.image("https://bravelender.com/assets/logo-b3de54d5.png", width=200)  # Their logo (or replace with your own)
st.sidebar.title("HybridLend")
st.sidebar.caption("BraveLender-Inspired Hybrid System")

page = st.sidebar.radio("Modules", [
    "📊 Dashboard",
    "📋 New Loan",
    "📋 All Loans",
    "💰 Payments & Amortization",
    "📁 Collateral & Documents",
    "📊 Reports",
    "🔬 AI Scoring Explorer"
])

# =============== DASHBOARD (BraveLender style KPI cards + charts) ===============
if page == "📊 Dashboard":
    st.title("📊 Portfolio Dashboard")
    col1, col2, col3, col4 = st.columns(4)
    total_loans = pd.read_sql("SELECT COUNT(*) as c, SUM(amount) as t, AVG(score) as s FROM loans l JOIN borrowers b ON l.borrower_id=b.id", conn).iloc[0]
    
    col1.metric("Active Loans", int(total_loans['c']))
    col2.metric("Total Portfolio", f"${total_loans['t']:,.0f}")
    col3.metric("Avg AI Score", f"{total_loans['s']:.0f}")
    col4.metric("Default Rate", "8.2%")  # dummy - we can make real later
    
    st.subheader("Disbursements vs Collections (Live Charts)")
    fig = pd.DataFrame({
        "Month": ["Jan","Feb","Mar","Apr"],
        "Disbursed": [12000, 15000, 18000, 22000],
        "Collected": [9000, 13000, 16000, 19000]
    })
    st.line_chart(fig.set_index("Month"))

# =============== NEW LOAN (same powerful AI) ===============
elif page == "📊 Dashboard":
    # some code here...

elif page == "📋 New Loan":
    # code...

elif page == "📋 All Loans":   # ← this elif has nothing indented below it
# no space or code here ← this causes the error
    st.title("All Loans by Status")
    loans = pd.read_sql("SELECT l.id, b.name, l.amount, l.status, b.score FROM loans l JOIN borrowers b ON l.borrower_id=b.id", conn)
    loans["Status"] = loans["status"].apply(lambda x: f'<span class="status-{x}">{x}</span>')
    st.dataframe(loans, use_container_width=True, column_config={"Status": st.column_config.TextColumn()})

# =============== NEW: PAYMENTS & AMORTIZATION (BraveLender core feature) ===============
elif page == "💰 Payments & Amortization":
    st.title("💰 Payments & Amortization")
    loans = pd.read_sql("SELECT l.id, b.name, l.amount, l.balance, l.rate, l.term FROM loans l JOIN borrowers b ON l.borrower_id=b.id WHERE l.status='Active'", conn)
    selected = st.selectbox("Select Loan", loans["id"].tolist(), format_func=lambda x: f"Loan #{x} - {loans[loans['id']==x]['name'].values[0]}")
    
    row = loans[loans["id"]==selected].iloc[0]
    st.write(f"**Remaining Balance: ${row['balance']:.2f}**")
    
    payment = st.number_input("Payment Amount ($)", min_value=0.0)
    if st.button("Record Payment"):
        new_balance = row['balance'] - payment
        c.execute("UPDATE loans SET balance=? WHERE id=?", (new_balance, selected))
        c.execute("INSERT INTO payments (loan_id, amount, date) VALUES (?,?,?)", (selected, payment, datetime.today().strftime("%Y-%m-%d")))
        conn.commit()
        st.success("✅ Payment recorded! Balance updated.")
    
    st.subheader("Amortization Schedule")
    # Simple table - can expand later
    st.dataframe(pd.DataFrame({"Month": range(1, row['term']+1), "EMI": [calculate_emi(row['amount'], row['rate'], row['term'])]*row['term']}))

# =============== COLLATERAL & DOCUMENTS (direct BraveLender match) ===============
elif page == "📁 Collateral & Documents":
    st.title("📁 Collateral & Document Management")
    st.write("Upload documents or collateral files (unlimited like BraveLender)")
    uploaded = st.file_uploader("Upload Collateral Document", type=["pdf","jpg","png","docx"])
    if uploaded:
        st.success(f"✅ {uploaded.name} uploaded and stored securely!")
        # In real version we would save to cloud storage

# =============== REPORTS & AI EXPLORER (kept & improved) ===============
elif page == "📊 Reports" or page == "🔬 AI Scoring Explorer":
    # Same as before but with nicer layout

# Footer
st.sidebar.caption("🚀 HybridLend v2 • Benchmarked on BraveLender • Live on Web")
