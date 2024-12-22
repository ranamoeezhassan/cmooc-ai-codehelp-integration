import json
from flask import Blueprint, jsonify, request, g
from functools import wraps
from werkzeug.security import check_password_hash
import jwt
import os
import datetime
from werkzeug.wrappers.response import Response

from gened.db import get_db
from .helper import run_query, get_query
from .context import get_context_by_name
from gened.auth import login_required, class_enabled_required, get_auth, set_session_auth_user, set_session_auth_class, get_last_class
from gened.dartmouth import LLMConfig, with_llm
from .context import get_context_by_name, ContextConfig, get_available_contexts

bp = Blueprint('api', __name__)
SECRET_KEY = os.environ.get("SECRET_KEY")

def generate_token(user_id):
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

@bp.route("/api/login", methods=['POST'])
def api_login() -> Response:
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    db = get_db()
    auth_row = db.execute("SELECT * FROM auth_local JOIN users ON auth_local.user_id=users.id WHERE username=?", [username]).fetchone()

    if not auth_row or not check_password_hash(auth_row['password'], password):
        return jsonify({"error": "Invalid username or password"}), 401

    # Set session auth user and class
    set_session_auth_user(auth_row['id'])
    last_class_id = get_last_class(auth_row['id'])
    set_session_auth_class(last_class_id)

    token = generate_token(auth_row['id'])
    return jsonify({"access_token": token})

def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Token is missing!"}), 403

        try:
            token = token.split(" ")[1]  # Remove "Bearer" prefix
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            g.auth = get_auth()
            g.auth['user_id'] = data['user_id']  # Ensure user_id is set
        except Exception as e:
            return jsonify({"error": str(e)}), 403

        return f(*args, **kwargs)
    return decorated_function

@bp.route("/api/query", methods=["POST"])
@token_required
@class_enabled_required
@with_llm(spend_token=True)
def submit_query(llm: LLMConfig):
    data = request.get_json()
    
    # Get context if provided
    context = None
    if 'context' in data:
        context = get_context_by_name(data['context'])
        if context is None:
            return jsonify({"error": f"Context not found: {data['context']}"}), 400

    # Extract query data    
    code = data.get("code", "")
    error = data.get("error", "")
    issue = data.get("issue", "")

    # Run query and get response
    query_id = run_query(llm, context, code, error, issue)
    query_row, responses = get_query(query_id)

    return jsonify({
        "query_id": query_id,
        "responses": responses,
        "context": context.name if context else None
    })

@bp.route("/api/query/<int:query_id>", methods=["GET"]) 
@token_required
def get_query_response(query_id):
    query_row, responses = get_query(query_id)
    if query_row is None:
        return jsonify({"error": "Query not found"}), 404

    return jsonify({
        "query": {
            "id": query_row['id'],
            "code": query_row['code'],
            "error": query_row['error'], 
            "issue": query_row['issue'],
            "context": query_row['context_name']
        },
        "responses": responses
    })

@bp.route("/api/contexts", methods=["GET"])
@token_required
def get_contexts():
    """Get all available contexts."""
    contexts = get_available_contexts()
    return jsonify({
        "contexts": [
            {
                "name": ctx.name,
                "description": ctx.description if hasattr(ctx, 'description') else None,
                "tools": ctx.tools if hasattr(ctx, 'tools') else None,
                "config": ctx.config if hasattr(ctx, 'config') else None
            } for ctx in contexts
        ]
    })

@bp.route("/api/context/<name>", methods=["GET"])
@token_required 
def get_context(name):
    """Get a specific context by name."""
    context = get_context_by_name(name)
    if context is None:
        return jsonify({"error": "Context not found"}), 404
    
    return jsonify({
        "name": context.name,
        "description": context.description if hasattr(context, 'description') else None,
        "tools": context.tools if hasattr(context, 'tools') else None,
        "config": context.config if hasattr(context, 'config') else None
    })

@bp.route("/api/context", methods=["POST"])
@token_required
def create_context():
    """Create a new context (instructor only)."""
    if not g.auth.get('is_admin') and g.auth.get('role') != 'instructor':
        return jsonify({"error": "Unauthorized. Requires instructor role."}), 403
    
    data = request.get_json()
    name = data.get('name')
    config = data.get('config', {})
    context_str = data.get('context_str', '')
    
    if not name or not context_str:
        return jsonify({"error": "Name and context_str are required"}), 400

    db = get_db()
    try:
        # First insert context string and get its ID
        db.execute(
            "INSERT INTO context_strings (ctx_str) VALUES (?) ON CONFLICT DO UPDATE SET id=id RETURNING id",
            [context_str]
        )

        # Then insert into contexts table (without context_string_id)
        db.execute("""
            INSERT INTO contexts (
                name, class_id, class_order, available, config
            ) VALUES (?, ?, 
                (SELECT COALESCE(MAX(class_order) + 1, 0) 
                 FROM contexts 
                 WHERE class_id = ?), 
                ?, ?)
        """, [name, g.auth['class_id'], g.auth['class_id'], 
              '0001-01-01', json.dumps(config)])
        
        db.commit()
        return jsonify({"message": "Context created successfully"}), 201
    except db.IntegrityError:
        db.rollback()
        return jsonify({"error": "Context already exists"}), 409
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    
@bp.route("/api/context/<name>", methods=["DELETE"])
@token_required
def delete_context(name):
    """Delete a context by name (instructor only)."""
    if not g.auth.get('is_admin') and g.auth.get('role') != 'instructor':
        return jsonify({"error": "Unauthorized. Requires instructor role."}), 403

    db = get_db()
    try:
        # Delete from contexts table
        result = db.execute("DELETE FROM contexts WHERE name = ?", [name])
        if result.rowcount == 0:
            return jsonify({"error": "Context not found"}), 404
            
        db.commit()
        return jsonify({"message": f"Context '{name}' deleted successfully"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500