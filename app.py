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

# DATABASE SETUP + MIGRATION
conn = sqlite3.connect('hybridlend.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS borrowers 
             (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, age INTEGER, employment TEXT, 
              prev_loans INTEGER, credit_history_good INTEGER, collateral_value REAL,
              score INTEGER, income REAL, risk TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS loans 
             (id INTEGER PRIMARY KEY, borrower_id INTEGER, amount REAL, rate REAL, 
              term INTEGER, status TEXT, start_date TEXT, balance REAL, 
              immutable_hash TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS payments 
             (id INTEGER PRIMARY KEY, loan_id INTEGER, amount REAL, date TEXT)''')

# Auto-migrate (safe)
new_cols = [
    ("age", "INTEGER"), ("employment", "TEXT"), ("prev_loans", "INTEGER"),
    ("credit_history_good", "INTEGER"), ("collateral_value", "REAL")
]
for col, typ in new_cols:
    try:
        c.execute(f"ALTER TABLE borrowers ADD COLUMN {col} {typ}")
        conn.commit()
    except:
        pass

# EXPANDED AI CREDIT SCORING
def calculate_credit_score(income, age, employment, prev_loans, credit_history_good, collateral_value):
    np.random.seed(42)
    n = 500
    incomes = np.random.randint(200, 10000, n)
    ages = np.random.randint(18, 70, n)
    employments = np.random.choice(['Employed', 'Self-employed', 'Unemployed'], n)
    prev_list = np.random.randint(0, 5, n)
    credit_good = np.random.choice([0, 1], n, p=[0.4, 0.6])
    coll = np.random.randint(0, 5000, n)

    good = (
        (incomes > 1500) &
        (ages >= 25) & (ages <= 55) &
        np.isin(employments, ['Employed', 'Self-employed']) &
        (prev_list < 3) &
        (credit_good == 1) &
        (coll > 1000)
    )
    target = good.astype(int)
    target = np.clip(target + np.random.choice([-1, 0, 1], n, p=[0.1, 0.8, 0.1]), 0, 1)

    emp_map = {'Employed': 2, 'Self-employed': 1, 'Unemployed': 0}
    df = pd.DataFrame({
        'income': incomes, 'age': ages, 'employment': employments,
        'prev_loans': prev_list, 'credit_history_good': credit_good,
        'collateral_value': coll, 'good_borrower': target
    })
    df['emp_score'] = df['employment'].map(emp_map)

    X = df[['income', 'age', 'emp_score', 'prev_loans', 'credit_history_good', 'collateral_value']]
    y = df['good_borrower']

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)

    input_df = pd.DataFrame([{
        'income': income, 'age': age,
        'emp_score': emp_map.get(employment, 0),
        'prev_loans': prev_loans,
        'credit_history_good': 1 if credit_history_good else 0,
        'collateral_value': collateral_value
    }])
    prob_good = model.predict_proba(input_df)[0][1]
    score = int(300 + prob_good * 550)
    score = max(300, min(850, score))

    importances = model.feature_importances_
    feature_names = ['Income', 'Age', 'Employment', 'Prev Loans', 'Credit History', 'Collateral']
    expl = dict(zip(feature_names, importances.round(3)))
    top_factor = max(expl, key=expl.get)

    return score, prob_good, expl, top_factor

# LOAN EMI
def calculate_emi(principal, rate, months):
    r = rate / (12 * 100)
    if r == 0: return round(principal / months, 2)
    emi = (principal * r * (1 + r)**months) / ((1 + r)**months - 1)
    return round(emi, 2)

# IMMUTABLE HASH
def create_immutable_hash(loan_data):
    data_str = str(loan_data) + datetime.now().isoformat()
    return hashlib.sha256(data_str.encode()).hexdigest()

# STREAMLIT APP
st.set_page_config(page_title="HybridLend MVP", layout="wide")
st.title("🚀 HybridLend – BraveLender Hybrid Prototype")
st.caption("Expanded AI Credit Scoring • Random Forest • Explainable")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 New Loan", "👥 Borrowers", "💰 Dashboard", "📊 Reports", "🔬 AI Explorer"])

with tab1:
    st.subheader("Create New Loan + Advanced AI Scoring")
    name = st.text_input("Borrower Name")
    phone = st.text_input("Phone")
    age = st.number_input("Age", 18, 70, 30)
    employment = st.selectbox("Employment Status", ["Employed", "Self-employed", "Unemployed"])
    income = st.number_input("Monthly Income ($)", min_value=0.0, value=2500.0)
    prev_loans = st.number_input("Previous Loans", 0, 10, 1)
    credit_history = st.checkbox("Has Good Credit History", value=True)
    collateral_value = st.number_input("Collateral Value ($)", min_value=0.0, value=1500.0)
    
    amount = st.number_input("Loan Amount ($)", min_value=100.0, value=5000.0)
    rate = st.slider("Interest Rate (%)", 5.0, 36.0, 18.0)
    term = st.slider("Term (months)", 3, 36, 12)

    if st.button("Create Loan & Run AI Scoring"):
        score, prob_good, expl, top_factor = calculate_credit_score(income, age, employment, prev_loans, credit_history, collateral_value)
        risk = "Low" if score > 700 else "Medium" if score > 550 else "High"
        
        c.execute("""INSERT INTO borrowers 
                     (name, phone, age, employment, prev_loans, credit_history_good, collateral_value, score, income, risk) 
                     VALUES (?,?,?,?,?,?,?,?,?,?)""",
                  (name, phone, age, employment, prev_loans, 1 if credit_history else 0, collateral_value, score, income, risk))
        borrower_id = c.lastrowid
        
        emi = calculate_emi(amount, rate, term)
        start_date = datetime.today().strftime("%Y-%m-%d")
        balance = amount
        loan_data = (borrower_id, amount, rate, term, "Active", start_date, balance)
        immutable_hash = create_immutable_hash(loan_data)
        
        c.execute("INSERT INTO loans (borrower_id, amount, rate, term, status, start_date, balance, immutable_hash) VALUES (?,?,?,?,?,?,?,?)",
                  (*loan_data, immutable_hash))
        conn.commit()
        
        st.success(f"✅ Loan created! AI Credit Score: **{score}** ({risk} Risk)")
        st.metric("Default Probability", f"{(1-prob_good)*100:.1f}%")
        st.info(f"Monthly EMI: **${emi}** | Top Factor: **{top_factor}** | Immutable Hash: {immutable_hash[:16]}...")
        
        st.subheader("Score Breakdown")
        chart_data = pd.Series(expl).sort_values(ascending=False)
        st.bar_chart(chart_data)

with tab2:
    st.subheader("All Borrowers & Loans")
    borrowers = pd.read_sql("SELECT * FROM borrowers", conn)
    loans = pd.read_sql("SELECT l.*, b.name, b.score FROM loans l JOIN borrowers b ON l.borrower_id = b.id", conn)
    st.dataframe(loans, use_container_width=True)

with tab3:
    st.subheader("Portfolio Dashboard")
    total = pd.read_sql("SELECT COUNT(*) as count, SUM(amount) as total, AVG(score) as avg_score FROM loans l JOIN borrowers b ON l.borrower_id = b.id", conn).iloc[0]
    st.metric("Active Loans", int(total['count']))
    st.metric("Total Portfolio", f"${total['total']:,.2f}")
    st.metric("Avg AI Credit Score", f"{total['avg_score']:.0f}" if not pd.isna(total['avg_score']) else "N/A")

with tab4:
    st.subheader("Export Reports")
    if st.button("Generate PDF Portfolio Report"):
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        p.drawString(100, 750, "HybridLend Portfolio Report – " + datetime.now().strftime("%d %b %Y"))
        p.drawString(100, 700, f"Total Portfolio: ${total['total']:,.2f} | Avg Score: {total['avg_score']:.0f}")
        p.save()
        buffer.seek(0)
        st.download_button("Download PDF", buffer, "HybridLend_Report.pdf", "application/pdf")

with tab5:
    st.subheader("🔬 AI Model Explorer")
    test_age = st.number_input("Test Age", 18, 70, 35)
    test_emp = st.selectbox("Test Employment", ["Employed", "Self-employed", "Unemployed"], key="test_emp")
    test_income = st.number_input("Test Income ($)", value=3000.0, key="test_inc")
    test_prev = st.number_input("Test Previous Loans", 0, 10, 0, key="test_prev")
    test_credit = st.checkbox("Test Good Credit History", value=True, key="test_credit")
    test_coll = st.number_input("Test Collateral Value ($)", value=2500.0, key="test_coll")
    
    if st.button("Run AI Simulation"):
        s, p, e, t = calculate_credit_score(test_income, test_age, test_emp, test_prev, test_credit, test_coll)
        st.metric("Simulated Credit Score", s)
        st.metric("Default Probability", f"{(1-p)*100:.1f}%")
        st.info(f"Top Factor: **{t}**")
        st.bar_chart(pd.Series(e).sort_values(ascending=False))
