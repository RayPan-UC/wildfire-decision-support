from flask import request, jsonify
import jwt
import os
from functools import wraps

SECRET_KEY = os.getenv('SECRET_KEY', 'wildfire-secret-key-change-in-production')

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            return jsonify({'message': 'Token missing.'}), 401

        token = auth_header.split(' ')[1]

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            request.current_user = payload  # accessible in route
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expired. Please log in again.'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token.'}), 401

        return f(*args, **kwargs)
    return decorated