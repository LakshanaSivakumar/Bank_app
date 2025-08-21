from fpdf import FPDF
from db import get_connection

def generate_customer_pdf(account_no):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM customer WHERE account_no=%s", (account_no,))
    customer = cursor.fetchone()
    conn.close()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Customer Registration Details", ln=1, align='C')
    pdf.ln(10)

    pdf.cell(200, 10, txt=f"Account No: {customer['account_no']}", ln=1)
    pdf.cell(200, 10, txt=f"Full Name: {customer['full_name']}", ln=1)
    pdf.cell(200, 10, txt=f"Email: {customer['email']}", ln=1)
    pdf.cell(200, 10, txt=f"Mobile: {customer['mobile_no']}", ln=1)
    pdf.cell(200, 10, txt=f"Temporary password: {customer['temp_password']}", ln=1)
    pdf.cell(200, 10, txt=f"Balance: Rs. {customer['balance']}", ln=1)
    pdf.cell(200, 10, txt=f"Status: {'Active' if customer['is_active'] else 'Closed'}", ln=1)

    filename = f"customer_{account_no}.pdf"
    pdf.output(filename)
    return filename
