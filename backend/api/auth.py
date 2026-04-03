from flask import Blueprint, request, jsonify
import psycopg2
import bcrypt
import jwt
import os
from datetime import datetime, timedelta
from db.connection import get_db

auth_bp = Blueprint('auth', __name__)

SECRET_KEY = os.getenv('SECRET_KEY', 'wildfire-secret-key-change-in-production')


#REGISTER 
@auth_bp.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()

    username = data.get('username', '').strip()
    password = data.get('password', '')

    # Basic validation
    if not username or not password:
        return jsonify({'message': 'Username and password are required.'}), 400

    if len(username) < 3:
        return jsonify({'message': 'Username must be at least 3 characters.'}), 400

    if len(password) < 6:
        return jsonify({'message': 'Password must be at least 6 characters.'}), 400

    # Hash the password
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    try:
        conn = get_db()
        cur  = conn.cursor()

        cur.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (username, hashed.decode('utf-8'))
        )
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({'message': 'Account created successfully.'}), 201

    except psycopg2.errors.UniqueViolation:
        return jsonify({'message': 'Username already exists.'}), 409

    except Exception as e:
        return jsonify({'message': 'Server error.', 'error': str(e)}), 500


#LOGIN 
@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'message': 'Username and password are required.'}), 400

    try:
        conn = get_db()
        cur  = conn.cursor()

        cur.execute(
            "SELECT id, username, password FROM users WHERE username = %s",
            (username,)
        )
        user = cur.fetchone()
        cur.close()
        conn.close()

        # User not found
        if not user:
            return jsonify({'message': 'Invalid username or password.'}), 401

        user_id, user_name, stored_hash = user

        # Check password
        if not bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
            return jsonify({'message': 'Invalid username or password.'}), 401

        # Generate JWT token : expires in 24 hours
        token = jwt.encode({
            'user_id':  user_id,
            'username': user_name,
            'exp':      datetime.utcnow() + timedelta(hours=24)
        }, SECRET_KEY, algorithm='HS256')

        return jsonify({
            'token':    token,
            'username': user_name,
            'message':  'Login successful.'
        }), 200

    except Exception as e:
        return jsonify({'message': 'Server error.', 'error': str(e)}), 500


# VERIFY TOKEN 
@auth_bp.route('/api/auth/verify', methods=['GET'])
def verify():
    auth_header = request.headers.get('Authorization', '')

    if not auth_header.startswith('Bearer '):
        return jsonify({'message': 'No token provided.'}), 401

    token = auth_header.split(' ')[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return jsonify({'valid': True, 'username': payload['username']}), 200
    except jwt.ExpiredSignatureError:
        return jsonify({'message': 'Token expired.'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'message': 'Invalid token.'}), 401