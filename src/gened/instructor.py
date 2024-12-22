# SPDX-FileCopyrightText: 2023 Mark Liffiton <liffiton@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-only

import datetime as dt
from sqlite3 import Row

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    render_template,
    request,
)
from werkzeug.wrappers.response import Response

from .auth import get_auth, instructor_required
from .csv import csv_response
from .db import get_db
from .redir import safe_redirect

bp = Blueprint('instructor', __name__, url_prefix="/instructor", template_folder='templates')

@bp.before_request
@instructor_required
def before_request() -> None:
    """ Apply decorator to protect all instructor blueprint endpoints. """


def get_queries(class_id: int, user: int | None = None) -> list[Row]:
    db = get_db()

    where_clause = "WHERE UNLIKELY(roles.class_id=?)"  # UNLIKELY() to help query planner in older sqlite versions
    params = [class_id]

    if user is not None:
        where_clause += " AND users.id=?"
        params += [user]

    queries = db.execute(f"""
        SELECT
            queries.id,
            users.display_name,
            users.email,
            queries.*
        FROM queries
        JOIN users
            ON queries.user_id=users.id
        JOIN roles
            ON queries.role_id=roles.id
        {where_clause}
        ORDER BY queries.id DESC
    """, params).fetchall()

    return queries


# def get_users(class_id: int, for_export: bool = False) -> list[Row]:
#     db = get_db()

#     users = db.execute(f"""
#         SELECT
#             {'roles.id AS role_id,' if not for_export else ''}
#             users.id,
#             users.display_name,
#             users.email,
#             auth_providers.name AS auth_provider,
#             users.auth_name,
#             COUNT(queries.id) AS num_queries,
#             SUM(CASE WHEN queries.query_time > date('now', '-7 days') THEN 1 ELSE 0 END) AS num_recent_queries,
#             roles.active,
#             roles.role = "instructor" AS instructor_role
#         FROM users
#         LEFT JOIN auth_providers ON users.auth_provider=auth_providers.id
#         JOIN roles ON roles.user_id=users.id
#         LEFT JOIN queries ON queries.role_id=roles.id
#         WHERE roles.class_id=?
#         GROUP BY users.id
#         ORDER BY display_name
#     """, [class_id]).fetchall()

#     return users

def get_users(class_id: int, for_export: bool = False) -> list[dict]:
    db = get_db()
    rows = db.execute(f"""
        SELECT
            {'roles.id AS role_id,' if not for_export else ''}
            users.id,
            users.display_name,
            users.email,
            users.queries_used,
            classes.max_queries,
            auth_providers.name AS auth_provider,
            users.auth_name,
            COUNT(queries.id) AS num_queries,
            SUM(CASE WHEN queries.query_time > date('now', '-7 days') THEN 1 ELSE 0 END) AS num_recent_queries,
            roles.active,
            roles.role,
            roles.role = 'instructor' AS instructor_role
        FROM users
        LEFT JOIN auth_providers ON users.auth_provider = auth_providers.id
        JOIN roles ON roles.user_id = users.id
        JOIN classes ON roles.class_id = classes.id
        LEFT JOIN queries ON queries.role_id = roles.id
        WHERE roles.class_id = ?
        GROUP BY users.id
        ORDER BY display_name
    """, [class_id]).fetchall()

    users = []
    for row in rows:
        user = dict(row)
        
        # Format queries info with color tag
        tag_class = 'is-danger' if user['queries_used'] >= user['max_queries'] else 'is-info'
        user['queries_info'] = f'<span class="tag {tag_class}">{user["queries_used"]}/{user["max_queries"]}</span>'
        
        # Add reset button if student with proper HTML structure
        if user['role'] == 'student':
            user['reset_button'] = (
                '<button class="button is-small is-warning" '
                f'onclick="resetStudentQueries(\'{user["id"]}\', \'{user["display_name"]}\')" '
                'title="Reset query count">'
                '<span class="icon"><i class="fas fa-redo"></i></span>'
                '<span>Reset</span>'
                '</button>'
            )
        else:
            user['reset_button'] = ''
            
        users.append(user)

    return users

@bp.route("/")
def main() -> str | Response:
    auth = get_auth()
    class_id = auth['class_id']
    assert class_id is not None

    users = get_users(class_id)

    sel_user_name = None
    sel_user_id = request.args.get('user', type=int)
    if sel_user_id is not None:
        sel_user_row = next(filter(lambda row: row['id'] == int(sel_user_id), users), None)
        if sel_user_row:
            sel_user_name = sel_user_row['display_name']

    queries = get_queries(class_id, sel_user_id)

    return render_template("instructor.html", users=users, queries=queries, user=sel_user_name)


@bp.route("/csv/<string:kind>")
def get_csv(kind: str) -> str | Response:
    if kind not in ('queries', 'users'):
        return abort(404)

    auth = get_auth()
    class_id = auth['class_id']
    class_name = auth['class_name']
    assert class_id is not None
    assert class_name is not None

    if kind == "queries":
        table = get_queries(class_id)
    elif kind == "users":
        table = get_users(class_id, for_export=True)

    return csv_response(class_name, kind, table)


@bp.route("/user_class/set", methods=["POST"])
def set_user_class_setting() -> Response:
    db = get_db()
    auth = get_auth()

    # only trust class_id from auth, not from user
    class_id = auth['class_id']

    if 'clear_dartmouth_key' in request.form:  # Changed from clear_openai_key
        db.execute("UPDATE classes_user SET dartmouth_key='' WHERE class_id=?", [class_id])  # Changed from openai_key
        db.commit()
        flash("Class API key cleared.", "success")

    elif 'save_access_form' in request.form:
        if 'link_reg_active_present' in request.form:
            # only present for user classes, not LTI
            link_reg_active = request.form['link_reg_active']
            if link_reg_active == "disabled":
                new_date = str(dt.date.min)
            elif link_reg_active == "enabled":
                new_date = str(dt.date.max)
            else:
                new_date = request.form['link_reg_expires']
            db.execute("UPDATE classes_user SET link_reg_expires=? WHERE class_id=?", [new_date, class_id])
        class_enabled = 1 if 'class_enabled' in request.form else 0
        db.execute("UPDATE classes SET enabled=? WHERE id=?", [class_enabled, class_id])
        db.commit()
        flash("Class access configuration updated.", "success")

    elif 'save_llm_form' in request.form:
        if 'dartmouth_key' in request.form:  # Changed from openai_key
            db.execute(
                "UPDATE classes_user SET dartmouth_key=? WHERE class_id=?",  # Changed from openai_key
                [request.form['dartmouth_key'], class_id]  # Changed from openai_key
            )
        db.execute("UPDATE classes_user SET model_id=? WHERE class_id=?", [request.form['model_id'], class_id])
        db.commit()
        flash("Class language model configuration updated.",  "success")
    
    elif 'save_query_limits' in request.form:
        try:
            max_queries = int(request.form['max_queries'])
            if max_queries < 1:
                raise ValueError("Query limit must be positive")
            
            db.execute(
                "UPDATE classes SET max_queries=? WHERE id=?",
                [max_queries, class_id]
            )
            db.commit()
            flash("Query limits updated successfully", "success")
        except ValueError as e:
            flash(f"Invalid query limit: {str(e)}", "error")
            
    # Add reset functionality
    elif 'reset_query_counts' in request.form:
        db.execute("""
            UPDATE users 
            SET queries_used = 0 
            WHERE id IN (
                SELECT user_id 
                FROM roles 
                WHERE class_id = ? AND role = 'student'
            )
        """, [class_id])
        db.commit()
        flash("Query counts reset for all students", "success")

    return safe_redirect(request.referrer, default_endpoint="profile.main")


@bp.route("/role/set_active", methods=["POST"])  # just for url_for in the Javascript code
@bp.route("/role/set_active/<int:role_id>/<int(min=0, max=1):bool_active>", methods=["POST"])
def set_role_active(role_id: int, bool_active: int) -> str:
    db = get_db()
    auth = get_auth()

    # prevent instructors from mistakenly making themselves not active and locking themselves out
    if role_id == auth['role_id']:
        return "You cannot make yourself inactive."

    # class_id should be redundant w/ role_id, but without it, an instructor
    # could potentially deactivate a role in someone else's class.
    # only trust class_id from auth, not from user
    class_id = auth['class_id']

    db.execute("UPDATE roles SET active=? WHERE id=? AND class_id=?", [bool_active, role_id, class_id])
    db.commit()

    return "okay"


@bp.route("/role/set_instructor", methods=["POST"])  # just for url_for in the Javascript code
@bp.route("/role/set_instructor/<int:role_id>/<int(min=0, max=1):bool_instructor>", methods=["POST"])
def set_role_instructor(role_id: int, bool_instructor: int) -> str:
    db = get_db()
    auth = get_auth()

    # prevent instructors from mistakenly making themselves not instructors and locking themselves out
    if role_id == auth['role_id']:
        return "You cannot change your own role."

    # class_id should be redundant w/ role_id, but without it, an instructor
    # could potentially deactivate a role in someone else's class.
    # only trust class_id from auth, not from user
    class_id = auth['class_id']

    new_role = 'instructor' if bool_instructor else 'student'

    db.execute("UPDATE roles SET role=? WHERE id=? AND class_id=?", [new_role, role_id, class_id])
    db.commit()

    return "okay"


@bp.route("/reset_student_queries/<int:student_id>", methods=["POST"])
@instructor_required  # This ensures only instructors can access this route
def reset_student_queries(student_id: int) -> Response:
    db = get_db()
    auth = get_auth()
    class_id = auth['class_id']

    # Verify the student exists in this instructor's class
    student = db.execute("""
        SELECT users.id, users.display_name 
        FROM users
        JOIN roles ON users.id = roles.user_id
        WHERE roles.class_id = ? 
        AND roles.role = 'student'
        AND users.id = ?
    """, [class_id, student_id]).fetchone()

    if not student:
        flash("Student not found in this class", "error")
        return jsonify({"error": "Student not found"}), 404

    # Reset the student's query count
    db.execute("UPDATE users SET queries_used = 0 WHERE id = ?", [student_id])
    db.commit()

    flash(f"Query count reset for {student['display_name']}", "success")
    return jsonify({"status": "success"})