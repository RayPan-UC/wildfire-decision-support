from flask import Blueprint, request, jsonify
import bcrypt
import jwt
import os
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from db.connection import db
from db.models import User

auth_bp = Blueprint('auth', __name__)

SECRET_KEY = os.getenv('SECRET_KEY', 'wildfire-secret-key-change-in-production')


#REGISTER
@auth_bp.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'message': 'Username and password are required.'}), 400

    if len(username) < 3:
        return jsonify({'message': 'Username must be at least 3 characters.'}), 400

    if len(password) < 6:
        return jsonify({'message': 'Password must be at least 6 characters.'}), 400

    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    try:
        new_user = User(username=username, password=hashed.decode('utf-8'))
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'message': 'Account created successfully.'}), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify({'message': 'Username already exists.'}), 409

    except Exception as e:
        db.session.rollback()
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
        user = User.query.filter_by(username=username).first()

        if not user:
            return jsonify({'message': 'Invalid username or password.'}), 401

        if not bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            return jsonify({'message': 'Invalid username or password.'}), 401

        token = jwt.encode({
            'user_id':  user.id,
            'username': user.username,
            'exp':      datetime.utcnow() + timedelta(hours=24)
        }, SECRET_KEY, algorithm='HS256')

        return jsonify({
            'token':    token,
            'username': user.username,
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
