from flask import Blueprint, request, jsonify
from db import get_connection
from auth import hash_password, verify_password
from datetime import datetime

customer_bp = Blueprint('customer', __name__)

@customer_bp.route('/customer/setup_password', methods=['POST'])
def setup_password():
    data = request.json
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM customer WHERE account_no=%s", (data['account_no'],))
    row = cursor.fetchone()
    if row and verify_password(row[0], data['old_password']):
        cursor.execute("UPDATE customer SET password_hash=%s WHERE account_no=%s",
                       (hash_password(data['new_password']), data['account_no']))
        conn.commit()
        return jsonify({"message": "Password updated."})
    return jsonify({"error": "Invalid credentials"}), 401

@customer_bp.route('/customer/dashboard/<int:account_no>', methods=['GET'])
def dashboard(account_no):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM balance WHERE account_no=%s", (account_no,))
    balance = cursor.fetchone()
    return jsonify({"account_no": account_no, "balance": balance[0]})

@customer_bp.route('/customer/deposit', methods=['POST'])
def deposit():
    data = request.json
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE balance SET balance = balance + %s WHERE account_no = %s",
                   (data['amount'], data['account_no']))
    cursor.execute("INSERT INTO transactions (account_no, type, amount) VALUES (%s, 'Deposit', %s)",
                   (data['account_no'], data['amount']))
    conn.commit()
    return jsonify({"message": "Deposit successful"})

@customer_bp.route('/customer/withdraw', methods=['POST'])
def withdraw():
    data = request.json
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM balance WHERE account_no = %s", (data['account_no'],))
    bal = cursor.fetchone()[0]
    if bal >= data['amount']:
        cursor.execute("UPDATE balance SET balance = balance - %s WHERE account_no = %s",
                       (data['amount'], data['account_no']))
        cursor.execute("INSERT INTO transactions (account_no, type, amount) VALUES (%s, 'Withdraw', %s)",
                       (data['account_no'], data['amount']))
        conn.commit()
        return jsonify({"message": "Withdraw successful"})
    else:
        return jsonify({"error": "Insufficient balance"}), 400
