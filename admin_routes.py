from flask import Blueprint, request, jsonify
from db import get_connection
from auth import hash_password
import random

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/login', methods=['POST'])
def admin_login():
    # validate and return session token
    pass

@admin_bp.route('/admin/register_customer', methods=['POST'])
def register_customer():
    data = request.json
    account_no = random.randint(10**9, 10**10-1)
    temp_password = str(random.randint(100000, 999999))
    hashed = hash_password(temp_password)
    
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO customer (full_name, address, mobile_no, email, account_type,
                              dob, id_proof, account_no, password_hash)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (data['full_name'], data['address'], data['mobile_no'], data['email'],
          data['account_type'], data['dob'], data['id_proof'],
          account_no, hashed))
    
    cursor.execute("INSERT INTO balance (account_no, balance) VALUES (%s, %s)", 
                   (account_no, data['initial_balance']))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"account_no": account_no, "temp_password": temp_password})
