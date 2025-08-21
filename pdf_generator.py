from fpdf import FPDF
from db import get_connection

def generate_pdf(account_no):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT type, amount, timestamp FROM transactions
        WHERE account_no=%s
        ORDER BY timestamp DESC
        LIMIT 10
    """, (account_no,))
    records = cursor.fetchall()
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Mini Statement", ln=1, align='C')
    
    for txn in records:
        pdf.cell(200, 10, txt=f"{txn[0]} | Rs. {txn[1]} | {txn[2]}", ln=1)

    filename = f"mini_statement_{account_no}.pdf"
    pdf.output(filename)
    return filename
