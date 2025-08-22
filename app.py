from flask import Flask, render_template, request, redirect, session, url_for, flash, send_file
from db import get_connection
from auth import hash_password, verify_password
from pdf_generate_customer import generate_customer_pdf
from pdf_generator import generate_pdf

app = Flask(__name__)
app.secret_key = "your_secret_key"  # needed for session & flash

# ========== LANDING PAGE ==========
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM admin WHERE username = %s", (username,))
        user = cursor.fetchone()

        # ✅ Password check using werkzeug.security
        if user and verify_password(user[0], password):
            session["admin_logged_in"] = True
            session["admin_username"] = username
            return redirect(url_for("admin_dashboard"))  # ✅ Ends the request here

        # If no user or password mismatch
        flash("Invalid username or password")
    
    # Render the login page if GET or after failed POST
    return render_template("admin_login.html")



@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    return render_template("admin_dashboard.html", 
                           admin_username=session["admin_username"])




import random
import string

def generate_temp_password(length=8):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k=length))


@app.route("/admin/register_customer", methods=["GET", "POST"])
def register_customer():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        full_name = request.form["full_name"]
        address = request.form["address"]
        mobile_no = request.form["mobile_no"]
        email = request.form["email"]
        account_type = request.form["account_type"]
        initial_balance = float(request.form["initial_balance"])
        dob = request.form["dob"]
        id_proof = request.form["id_proof"]

        if initial_balance < 1000:
            flash("Initial balance must be at least ₹1000.")
            return render_template("register_customer.html")

        account_no = random.randint(1000000000, 9999999999)
        temp_password = generate_temp_password()
        hashed_password = hash_password(temp_password)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO customer (
                full_name, address, mobile_no, email, account_type,
                dob, id_proof, account_no, password_hash, is_active, balance, temp_password
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s)
        """, (
            full_name, address, mobile_no, email, account_type,
            dob, id_proof, account_no, hashed_password,
            initial_balance, temp_password
        ))


        conn.commit()
        cursor.execute("""
            INSERT INTO balance (account_no, balance)
            VALUES (%s, %s)
        """, (account_no, initial_balance))
        conn.commit()
        # ✅ Pass data to success template directly
        return render_template("register_success.html",
                               full_name=full_name,
                               account_no=account_no,
                               temp_password=temp_password)

    return render_template("register_customer.html")

@app.route("/download_customer_pdf/<account_no>")
def download_customer_pdf(account_no):
    filename = generate_customer_pdf(account_no)
    return send_file(filename, as_attachment=True)

@app.route("/admin/view_customers")
def view_customers():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT account_no, full_name, mobile_no, email, balance, is_active FROM customer")
    customers = cursor.fetchall()
    conn.close()

    return render_template("view_customers.html", customers=customers)




@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    session.pop("admin_username", None)
    flash("Logged out successfully.")
    return redirect(url_for("admin_login"))

@app.route("/customer/login", methods=["GET", "POST"])
def customer_login():
    if request.method == "POST":
        acc_no = request.form["account_no"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash, full_name FROM customer WHERE account_no=%s AND is_active=1", (acc_no,))
        row = cursor.fetchone()
        if row and verify_password(row[0], password):
            session["customer"] = {"account_no": acc_no, "full_name": row[1]}
            return redirect(url_for("customer_dashboard"))
        flash("Invalid login")
    return render_template("customer_login.html")

@app.route("/customer/setup_password", methods=["GET", "POST"])
def setup_password():
    acc_no = request.args.get("account_no", "")
    if request.method == "POST":
        acc_no = request.form["account_no"]
        old_pw = request.form["old_password"]
        new_pw = request.form["new_password"]

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM customer WHERE account_no=%s", (acc_no,))
        row = cursor.fetchone()

        if row and verify_password(row[0], old_pw):
            cursor.execute("UPDATE customer SET password_hash=%s WHERE account_no=%s",
                           (hash_password(new_pw), acc_no))
            conn.commit()
            flash("✅ Password updated successfully. You can now log in.")
        else:
            flash("❌ Invalid temporary password")

    return render_template("setup_password.html", account_no=acc_no)




@app.route("/customer/dashboard")
def customer_dashboard():
    if "customer" not in session:
        return redirect(url_for("customer_login"))

    account_no = session["customer"]["account_no"]

    conn = get_connection()
    cursor = conn.cursor()

    
    cursor.execute("SELECT balance FROM balance WHERE account_no=%s", (account_no,))
    row = cursor.fetchone()
    balance = row[0] if row else 0   

    conn.close()

    return render_template("customer_dashboard.html", customer=session["customer"], balance=balance)


@app.route("/customer/deposit", methods=["POST"])
def deposit():
    if "customer" not in session: return redirect(url_for("customer_login"))
    acc_no = request.form["account_no"]
    amount = float(request.form["amount"])

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE balance SET balance = balance + %s WHERE account_no = %s", (amount, acc_no))
    cursor.execute("INSERT INTO transactions (account_no, type, amount) VALUES (%s, 'Deposit', %s)", (acc_no, amount))
    conn.commit()
    return redirect(url_for("customer_dashboard"))

@app.route("/customer/withdraw", methods=["POST"])
def withdraw():
    if "customer" not in session: return redirect(url_for("customer_login"))
    acc_no = request.form["account_no"]
    amount = float(request.form["amount"])

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM balance WHERE account_no=%s", (acc_no,))
    balance = cursor.fetchone()[0]

    if balance >= amount:
        cursor.execute("UPDATE balance SET balance = balance - %s WHERE account_no = %s", (amount, acc_no))
        cursor.execute("INSERT INTO transactions (account_no, type, amount) VALUES (%s, 'Withdraw', %s)", (acc_no, amount))
        conn.commit()
        return redirect(url_for("customer_dashboard"))
    else:
        flash("Insufficient balance.")
        return redirect(url_for("customer_dashboard"))

@app.route("/customer/transactions/<int:account_no>")
def view_transactions(account_no):
    if "customer" not in session or session["customer"]["account_no"] != str(account_no):
        return redirect(url_for("customer_login"))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT type, amount, timestamp FROM transactions WHERE account_no=%s ORDER BY timestamp DESC LIMIT 10", (account_no,))
    txns = cursor.fetchall()

    return render_template("transactions.html", transactions=txns)

@app.route("/customer/download_pdf/<int:account_no>")
def download_pdf(account_no):
    if "customer" not in session or session["customer"]["account_no"] != str(account_no):
        return redirect(url_for("customer_login"))

    filename = generate_pdf(account_no)
    return send_file(filename, as_attachment=True)

@app.route("/customer/close/<int:account_no>")
def close_account(account_no):
    if "customer" not in session or int(session["customer"]["account_no"]) != account_no:
        flash("Unauthorized access.")
        return redirect(url_for("customer_login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT balance FROM balance WHERE account_no = %s", (account_no,))
    result = cursor.fetchone()

    if not result:
        flash("Account not found or balance missing.")
        return redirect(url_for("customer_dashboard"))

    bal = result[0]

    if bal > 0:
        flash("Withdraw all money before closing the account.")
        return redirect(url_for("customer_dashboard"))

    cursor.execute("UPDATE customer SET is_active = 0 WHERE account_no = %s", (account_no,))
    conn.commit()
    conn.close()

    session.pop("customer", None)
    flash("Account closed successfully.")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
