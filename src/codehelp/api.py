import json
from flask import Blueprint, current_app, jsonify, request, g
from functools import wraps
from werkzeug.security import check_password_hash
import jwt
import os
import datetime
from werkzeug.wrappers.response import Response
from flask_cors import cross_origin

from gened.db import get_db
from .helper import run_query, get_query
from .context import get_context_by_name, record_context_string
from gened.auth import login_required, class_enabled_required, get_auth, set_session_auth_user, set_session_auth_class, get_last_class
from gened.dartmouth import LLMConfig, with_llm
from gened.classes import switch_class
from .context import get_context_by_name, ContextConfig, TaskInstructions, get_available_contexts

bp = Blueprint('api', __name__)
SECRET_KEY = os.environ.get("SECRET_KEY")

def generate_token(user_id):
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

# @bp.route("/api/login", methods=['POST'])
# def api_login() -> Response:
#     data = request.get_json()
#     username = data.get('username')
#     password = data.get('password')
#     db = get_db()
#     # auth_row = get_auth()
#     auth_row = db.execute("SELECT * FROM auth_local JOIN users ON auth_local.user_id=users.id WHERE username=?", [username]).fetchone()

#     if not auth_row or not check_password_hash(auth_row['password'], password):
#         return jsonify({"error": "Invalid username or password"}), 401

#     # Set session auth user and class
#     set_session_auth_user(auth_row['id'])
#     last_class_id = get_last_class(auth_row['id'])
#     set_session_auth_class(last_class_id)

#     token = generate_token(auth_row['id'])
#     return jsonify({"access_token": token})

@bp.route("/api/login", methods=['POST'])
@cross_origin()
def api_login() -> Response:
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    db = get_db()

    # Get user data with all necessary information including admin status
    auth_row = db.execute("""
        SELECT 
            users.id,
            users.is_admin,
            auth_local.password,
            users.display_name,
            roles.role as role_name
        FROM users
        JOIN auth_local ON auth_local.user_id = users.id
        LEFT JOIN roles ON users.id = roles.user_id
        WHERE users.auth_name = ?
    """, [username]).fetchone()

    if not auth_row or not check_password_hash(auth_row['password'], password):
        return jsonify({"error": "Invalid username or password"}), 401

    # Set up auth session
    set_session_auth_user(auth_row['id'])
    last_class_id = get_last_class(auth_row['id'])
    set_session_auth_class(last_class_id)

    # Generate token with additional claims
    payload = {
        "user_id": auth_row['id'],
        "is_admin": bool(auth_row['is_admin']),
        "role": auth_row['role_name'] if auth_row['role_name'] else None,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    return jsonify({
        "access_token": token,
        "user_info": {
            "is_admin": bool(auth_row['is_admin']),
            "role": auth_row['role_name']
        }
    })

def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Token is missing!"}), 403

        try:
            token = token.split(" ")[1]
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            
            db = get_db()
            
            # Fetch user's current role and class
            current_role = db.execute("""
                SELECT
                    users.id,
                    users.is_admin,
                    users.display_name,
                    users.last_class_id,
                    roles.id AS role_id,
                    roles.role AS role_name,
                    classes.id AS class_id,
                    classes.name AS class_name
                FROM users
                LEFT JOIN roles ON roles.user_id = users.id
                LEFT JOIN classes ON classes.id = users.last_class_id
                WHERE users.id = ? AND roles.class_id = users.last_class_id
            """, [data['user_id']]).fetchone()

            # Fetch all other available classes for the user
            other_classes = db.execute("""
                SELECT 
                    classes.id AS class_id,
                    classes.name AS class_name,
                    roles.id AS role_id,
                    roles.role AS role_name
                FROM roles
                JOIN classes ON classes.id = roles.class_id
                WHERE roles.user_id = ? AND roles.active = 1
                ORDER BY classes.id
            """, [data['user_id']]).fetchall()

            # Initialize g.auth with comprehensive data
            g.auth = {
                'user_id': data['user_id'],
                'is_admin': current_role['is_admin'] if current_role else data.get('is_admin', False),
                'display_name': current_role['display_name'] if current_role else None,
                'role': current_role['role_name'] if current_role else None,
                'role_id': current_role['role_id'] if current_role else None,
                'class_id': current_role['class_id'] if current_role else None,
                'class_name': current_role['class_name'] if current_role else None,
                'class_experiments': [],
                'other_classes': [{
                    'class_id': row['class_id'],
                    'class_name': row['class_name'],
                    'role_id': row['role_id'],
                    'role': row['role_name']
                } for row in other_classes]
            }

        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        return f(*args, **kwargs)
    return decorated_function


@bp.route("/api/query", methods=["POST"])
@cross_origin()
@token_required
@class_enabled_required
@with_llm(spend_token=True)
def submit_query(llm: LLMConfig):
    """Submit a query and return the response."""
    try:
        data = request.get_json()
        current_app.logger.debug("Received query request")
        current_app.logger.debug(f"Request data: {data}")
        current_app.logger.debug(f"Auth: {g.auth}")

        # Get either context or task_instructions
        context = None
        if 'context' in data:
            context = get_context_by_name(data['context'])
            if not context:
                return jsonify({"error": f"Context not found: {data['context']}"}), 404
        elif 'task_instructions' in data:
            try:
                task_data = data['task_instructions']
                context = TaskInstructions(
                    tools=task_data.get('tools'),
                    details=task_data.get('details'),
                    avoid=task_data.get('avoid'),
                    name=task_data.get('name')
                )
            except Exception as e:
                current_app.logger.error(f"Invalid task instructions: {e}")
                return jsonify({"error": f"Invalid task instructions format: {str(e)}"}), 400

        # Extract query data
        code = data.get("code", "")
        error = data.get("error", "")
        issue = data.get("issue", "")
        if code is None or error is None or issue is None:
            return jsonify({"error": "Code, Error, or Issue parameters cannot be None"}), 400

        # Run query using the formatted context
        query_id = run_query(llm, context, code, error, issue)
        query_row, responses = get_query(query_id)

        return jsonify({
            "query_id": query_id,
            "responses": responses,
            "context": context.name if hasattr(context, 'name') else None
        })

    except Exception as e:
        current_app.logger.error(f"Error processing query: {e}")
        return jsonify({"error": str(e)}), 500

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
    # Add debugging for role verification
    print("Auth info:", g.auth)
    print("Is admin:", g.auth.get('is_admin'))
    print("Role:", g.auth.get('role'))

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
    

@bp.route("/api/classes/switch/<int:class_id>", methods=["POST"])
@token_required
def switch_active_class(class_id):
    """Switch active class for the user."""
    # print("Auth before switch state: ", g.auth)
    success = switch_class(class_id)

    if not success:
        print(f"Failed to switch class {class_id} for user {g.auth['user_id']}")
        current_app.logger.error(f"Failed to switch class {class_id} for user {g.auth['user_id']}")
        return jsonify({"error": f"Failed to switch class {class_id}. User may not have access."}), 403

    # print("Auth after switch state: ", g.auth)

    return jsonify({
        "message": f"Switched to class: {g.auth['class_name']}",
        "class_id": g.auth['class_id'],
        "role": g.auth['role'],
        "role_id": g.auth['role_id'],
        "other_classes": g.auth['other_classes']
    })