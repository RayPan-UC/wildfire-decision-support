from flask import request, jsonify
import jwt
import os
from functools import wraps

SECRET_KEY = os.getenv('SECRET_KEY', 'wildfire-secret-key-change-in-production')

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')

        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        elif request.args.get('token'):
            # Tile endpoints: Leaflet can't set headers, so accept ?token= param
            token = request.args.get('token')
        else:
            return jsonify({'message': 'Token missing.'}), 401

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            request.current_user   = payload  # accessible in route
            request._jwt_user_id   = payload.get('user_id')
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expired. Please log in again.'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token.'}), 401

        return f(*args, **kwargs)
    return decorated