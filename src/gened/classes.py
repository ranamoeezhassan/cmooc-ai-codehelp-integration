# SPDX-FileCopyrightText: 2023 Mark Liffiton <liffiton@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-only

import datetime as dt
import secrets

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.wrappers.response import Response

from .auth import _invalidate_g_auth, get_auth, login_required, set_session_auth_class
from .db import get_db
from .redir import safe_redirect_next
from .tz import date_is_past

bp = Blueprint('classes', __name__, url_prefix="/classes", template_folder='templates')

@bp.before_request
@login_required
def before_request() -> None:
    """ Apply decorator to protect all blueprint endpoints. """


def get_or_create_lti_class(lti_consumer_id: int, lti_context_id: str, class_name: str) -> int:
    """
    Get a class (by id) for a given LTI connection, creating the class
    if it does not already exist.

    Parameters
    ----------
    lti_consumer_id : int
      row ID for an LTI consumer (in table lti_consumers)
    lti_context_id : str
      class identifier from the LMS
    class_name : str
      class name from the LMS

    Returns
    -------
    int: class ID (row primary key) for the new or existing class.
    """
    db = get_db()

    class_row = db.execute("""
        SELECT classes.id, classes.name
        FROM classes
        JOIN classes_lti
          ON classes.id=classes_lti.class_id
        WHERE classes_lti.lti_consumer_id=?
          AND classes_lti.lti_context_id=?
    """, [lti_consumer_id, lti_context_id]).fetchone()

    if class_row:
        # update class name if it has changed on the remote
        if class_row['name'] != class_name:
            db.execute("UPDATE classes SET name=? WHERE id=?", [class_name, class_row['id']])
            db.commit()

        assert isinstance(class_row['id'], int)
        return class_row['id']

    else:
        cur = db.execute("INSERT INTO classes (name) VALUES (?)", [class_name])
        class_id = cur.lastrowid
        assert class_id is not None
        db.execute(
            "INSERT INTO classes_lti (class_id, lti_consumer_id, lti_context_id) VALUES (?, ?, ?)",
            [class_id, lti_consumer_id, lti_context_id]
        )
        db.commit()

        current_app.logger.info(f"New class (LTI): {class_name} ({class_id})")

        assert class_id is not None
        return class_id


def create_user_class(user_id: int, class_name: str, dartmouth_key: str) -> int:
    """
    Create a user class.  Assign the given user an 'instructor' role in it.

    Parameters
    ----------
    user_id : int
      id of the user creating the course -- will be given the instructor role
    class_name : str
      class name from the user
    dartmouth_key : str
      dartmouth key from the user.  This is not strictly required, as a class can
      exist with no key assigned, but it is clearer for the user if we require
      an dartmouth key up front.

    Returns
    -------
    int: class ID (row primary key) for the new class.
    """
    db = get_db()

    # generate a new, unique, unguessable link identifier
    is_unique = False
    while not is_unique:
        link_ident = secrets.token_urlsafe(6)  # 8 characters
        match_row = db.execute("SELECT 1 FROM classes_user WHERE link_ident=?", [link_ident]).fetchone()
        is_unique = not match_row

    cur = db.execute("INSERT INTO classes (name) VALUES (?)", [class_name])
    class_id = cur.lastrowid
    assert class_id is not None

    # Get default model ID - we validated at startup that this exists
    model_id_row = db.execute(
        "SELECT id FROM models WHERE active AND shortname = ?",
        [current_app.config['DEFAULT_CLASS_MODEL_SHORTNAME']]
    ).fetchone()

    if model_id_row is None:
        raise ValueError(f"Default model shortname '{current_app.config['DEFAULT_CLASS_MODEL_SHORTNAME']}' not found in active models.")

    model_id = model_id_row['id']

    db.execute(
        "INSERT INTO classes_user (class_id, creator_user_id, link_ident, dartmouth_key, link_reg_expires, model_id) VALUES (?, ?, ?, ?, ?, ?)",
        [class_id, user_id, link_ident, dartmouth_key, dt.date.min, model_id]
    )
    db.execute(
        "INSERT INTO roles (user_id, class_id, role) VALUES (?, ?, ?)",
        [user_id, class_id, 'instructor']
    )
    db.commit()

    current_app.logger.info(f"New class (user): {class_name} ({class_id})")

    return class_id


def switch_class(class_id: int | None) -> bool:
    '''Switch the current user to their role in the given class.
       Or switch them to no class / no role if class_id is None.

       Admin users can switch to any class.

    Returns bool: True if user has an active role in that class and switch succeeds.
                  False otherwise.
    '''
    auth = get_auth()
    user_id = auth['user_id']
    db = get_db()

    # admins can access any class, but we don't bother setting last_class_id for them
    if auth['is_admin']:
       # Get complete class and role information for admin
        class_row = db.execute("""
            SELECT
                classes.id AS class_id,
                classes.name AS class_name,
                roles.id AS role_id,
                roles.role
            FROM classes
            LEFT JOIN roles ON roles.class_id = classes.id AND roles.user_id = ?
            WHERE classes.id = ?
        """, [user_id, class_id]).fetchone()
        
        if class_row:
            # Update session first
            set_session_auth_class(class_id)
            
            # Update g.auth with complete information
            if hasattr(g, 'auth'):
                g.auth.update({
                    'class_id': class_row['class_id'],
                    'class_name': class_row['class_name'],
                    'role_id': class_row['role_id'],  # Preserve role_id if exists
                    'role': 'instructor'  # Admin always gets instructor role
                })

            # Update last_class_id in database
            db.execute("UPDATE users SET last_class_id = ? WHERE id = ?", [class_id, user_id])
            db.commit()
            
            current_app.logger.info(f"Admin switched to class: {class_id}")
            return True
            
        return False  # Class not found
    
    if class_id:
        # check for a valid role in the new class
        row = db.execute("""
            SELECT
                roles.id AS role_id,
                roles.role,
                classes.id AS class_id,
                classes.name AS class_name
            FROM roles
            LEFT JOIN classes ON roles.class_id=classes.id
            WHERE roles.user_id=? AND roles.active=1 AND classes.id=?
        """, [user_id, class_id]).fetchone()

        if not row:
            # no valid row found; change nothing and return failure
            current_app.logger.info(f"Failed to switch to class: {class_id} for user: {user_id}")
            return False

        # otherwise, we can continue with this class_id
        set_session_auth_class(class_id)

        # Update g.auth for token-based authentication
        if hasattr(g, 'auth'):
            g.auth.update({
                'class_id': row['class_id'],
                'class_name': row['class_name'],
                'role_id': row['role_id'],
                'role': row['role']
            })
        
        # record as user's latest active class
        db.execute("UPDATE users SET last_class_id=? WHERE users.id=?", [class_id, user_id])
        db.commit()

        # _invalidate_g_auth()
        current_app.logger.info(f"Switched to class: {class_id} for user: {user_id}")
        return True

    # If class_id is None, clear the session and update the user's last_class_id to None
    set_session_auth_class(None)
    db.execute("UPDATE users SET last_class_id=NULL WHERE users.id=?", [user_id])
    db.commit()

    # Clear g.auth for token-based authentication
    if hasattr(g, 'auth'):
        g.auth.update({
            'class_id': None,
            'class_name': None,
            'role_id': None,
            'role': None
        })

    _invalidate_g_auth()
    current_app.logger.info(f"Cleared current class for user: {user_id}")
    return True


@bp.route("/switch/<int:class_id>")
def switch_class_handler(class_id: int) -> Response:
    success = switch_class(class_id)
    if not success:
        flash("Failed to switch class.", "error")
    else:
        flash(f"Switched to class {class_id}.", "success")
    return safe_redirect_next(default_endpoint="profile.main")


@bp.route("/leave/")
def leave_class_handler() -> Response:
    success = switch_class(None)
    if not success:
        flash("Failed to leave the class.", "error")
    else:
        flash("You have left the class.", "success")
    return redirect(url_for("profile.main"))


@bp.route("/create/", methods=['POST'])
def create_class() -> Response:
    auth = get_auth()
    user_id = auth['user_id']
    assert user_id is not None

    class_name = request.form['class_name']
    dartmouth_key = request.form['dartmouth_key']

    class_id = create_user_class(user_id, class_name, dartmouth_key)
    success = switch_class(class_id)
    assert success

    return redirect(url_for("class_config.config_form"))


@bp.route("/access/<string:class_ident>")
def access_class(class_ident: str) -> str | Response:
    '''Join a class or just login/access it.

    If the user already has a role in the class, just access it.
    Otherwise, check if the link and class are both enabled, and if so,
    add this user to the class.
    '''
    db = get_db()

    auth = get_auth()
    user_id = auth['user_id']

    # Get the class info
    class_row = db.execute("""
        SELECT classes.id, classes_user.link_reg_expires
        FROM classes
        JOIN classes_user
          ON classes.id = classes_user.class_id
        WHERE classes_user.link_ident = ?
    """, [class_ident]).fetchone()

    if not class_row:
        return abort(404)

    class_id = class_row['id']

    role_row = db.execute("SELECT * FROM roles WHERE class_id=? AND user_id=?", [class_id, user_id]).fetchone()

    if role_row:
        # user already has a role, but it may not be active
        success = switch_class(class_id)
        if not success:
            return abort(403)
        else:
            return redirect(url_for("landing"))

    # user does not have a role
    if date_is_past(class_row['link_reg_expires']):
        # but registration is not currently active
        flash("Registration is not active for this class.  Please contact the instructor for assistance.", "warning")
        return render_template("error.html")

    # user does not have a role and registration is currently active for this class
    # register them and switch to that role
    db.execute(
        "INSERT INTO roles (user_id, class_id, role) VALUES (?, ?, ?)",
        [user_id, class_id, 'student']
    )
    db.commit()
    success = switch_class(class_id)
    assert success
    return redirect(url_for("landing"))
