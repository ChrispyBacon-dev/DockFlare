from functools import wraps
from flask import request, jsonify
from app.core.jwt_auth import verify_jwt

def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid token'}), 401
        
        token = auth_header.split(' ')[1]
        decoded = verify_jwt(token)
        if not decoded:
            return jsonify({'error': 'Invalid token'}), 401
            
        request.user = decoded
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    @jwt_required
    def decorated(*args, **kwargs):
        if request.user.get('role') != 'admin':
            return jsonify({'error': 'Admin required'}), 403
        return f(*args, **kwargs)
    return decorated
