
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from sqlite3 import Row
from typing import ParamSpec, TypeVar
import jwt
from datetime import datetime, timezone
from flask import current_app, flash, render_template

from .auth import get_auth
from .db import get_db

class ClassDisabledError(Exception):
    pass

class NoKeyFoundError(Exception):
    pass

class NoTokensError(Exception):
    pass

class TokenExpiredError(Exception):
    pass

@dataclass
class LLMConfig:
    api_key: str
    model: str
    tokens_remaining: int | None = None
    _token: str | None = None

def _get_llm(*, use_system_key: bool, spend_token: bool) -> LLMConfig:
    db = get_db()
    
    def make_system_client(tokens_remaining: int | None = None) -> LLMConfig:
        system_model = current_app.config["DEFAULT_MODEL"]
        system_key = current_app.config["DARTMOUTH_API_KEY"]
        return LLMConfig(
            api_key=system_key,
            model=system_model,
            tokens_remaining=tokens_remaining
        )

    if use_system_key:
        return make_system_client()

    auth = get_auth()

    # Similar class/token logic as original but for Dartmouth API
    if auth['class_id']:
        # class_row = db.execute("""
        #     SELECT
        #         classes.enabled,
        #         COALESCE(consumers.dartmouth_key, classes_user.dartmouth_key) AS dartmouth_key,
        #         COALESCE(consumers.model_id, classes_user.model_id) AS _model_id,
        #         models.model
        #     FROM classes
        #     LEFT JOIN classes_lti ON classes.id = classes_lti.class_id
        #     LEFT JOIN consumers ON classes_lti.lti_consumer_id = consumers.id 
        #     LEFT JOIN classes_user ON classes.id = classes_user.class_id
        #     LEFT JOIN models ON models.id = _model_id
        #     WHERE classes.id = ?
        # """, [auth['class_id']]).fetchone()

        class_row = db.execute("""
            SELECT 
                classes.enabled,
                classes.max_queries,
                users.queries_used,
                COALESCE(consumers.dartmouth_key, classes_user.dartmouth_key) AS dartmouth_key,
                COALESCE(consumers.model_id, classes_user.model_id) AS _model_id,
                models.model,
                roles.role
            FROM classes
            LEFT JOIN classes_lti ON classes.id = classes_lti.class_id
            LEFT JOIN consumers ON classes_lti.lti_consumer_id = consumers.id 
            LEFT JOIN classes_user ON classes.id = classes_user.class_id
            LEFT JOIN models ON models.id = _model_id
            LEFT JOIN roles ON roles.class_id = classes.id AND roles.user_id = ?
            LEFT JOIN users ON users.id = ?
            WHERE classes.id = ?
        """, [auth['user_id'], auth['user_id'], auth['class_id']]).fetchone()


        if not class_row['enabled']:
            raise ClassDisabledError

        if not class_row['dartmouth_key']:
            raise NoKeyFoundError
        
        if class_row['role'] == 'student':
            if class_row['queries_used'] >= class_row['max_queries']:
                raise NoTokensError(
                    f"You have reached the maximum limit of {class_row['max_queries']} queries. "
                    "Please contact your instructor."
                )
            
            # Increment query count if spending a token
            if spend_token:
                db.execute(
                    "UPDATE users SET queries_used = queries_used + 1 WHERE id = ?",
                    [auth['user_id']]
                )
                db.commit()

        return LLMConfig(
            api_key=class_row['dartmouth_key'],
            model=class_row['model']
        )

    # Rest of token management same as original
    user_row = db.execute("""
        SELECT users.query_tokens, auth_providers.name AS auth_provider_name
        FROM users JOIN auth_providers ON users.auth_provider = auth_providers.id 
        WHERE users.id = ?
    """, [auth['user_id']]).fetchone()

    if user_row['auth_provider_name'] == "local":
        return make_system_client()

    tokens = user_row['query_tokens']
    if tokens == 0:
        raise NoTokensError

    if spend_token:
        db.execute("UPDATE users SET query_tokens=query_tokens-1 WHERE id=?", [auth['user_id']])
        db.commit()
        tokens -= 1

    return make_system_client(tokens_remaining=tokens)

P = ParamSpec('P')
R = TypeVar('R')

def with_llm(*, use_system_key: bool = False, spend_token: bool = False) -> Callable[[Callable[P, R]], Callable[P, str | R]]:
    def decorator(f: Callable[P, R]) -> Callable[P, str | R]:
        @wraps(f)
        def decorated_function(*args: P.args, **kwargs: P.kwargs) -> str | R:
            try:
                llm = _get_llm(use_system_key=use_system_key, spend_token=spend_token)
            except ClassDisabledError:
                flash("Error: The current class is archived or disabled.")
                return render_template("error.html")
            except NoKeyFoundError:
                flash("Error: No API key set. An API key must be set by the instructor.")
                return render_template("error.html")
            except NoTokensError:
                flash("You have used all of your free queries.")
                return render_template("error.html")
            
            kwargs['llm'] = llm
            return f(*args, **kwargs)
        return decorated_function
    return decorator

async def get_completion(llm: LLMConfig, prompt: str) -> tuple[dict[str, str], str]:
    from dartmouth.connectRawAPI import sendInstructions, generateInstructions, isTokenExpired
    
    try:
        # Get/refresh JWT token
        if not hasattr(llm, '_token') or not llm._token or isTokenExpired(llm._token, False):
            resp = sendInstructions("https://api.dartmouth.edu/api/jwt", llm.api_key, None, None, None)
            if resp.status_code != 200:
                return {'error': 'JWT token error'}, f"Error getting JWT token: {resp.text}"
            llm._token = resp.json()["jwt"]

        # Generate API request 
        prompt, parameters = generateInstructions(prompt, None)
        
        # Get response
        resp = sendInstructions(
            f"https://api.dartmouth.edu/api/ai/tgi/{llm.model}/generate",
            None,
            llm._token,
            prompt,
            parameters
        )
        
        if resp.status_code != 200:
            return {'error': resp.text}, f"Error: {resp.text}"
            
        return resp.json(), resp.json()["generated_text"].strip()

    except Exception as e:
        current_app.logger.error(f"Dartmouth API Error: {e}")
        return {'error': str(e)}, f"Error: {str(e)}"

def get_models() -> list[Row]:
    db = get_db()
    models = db.execute("SELECT * FROM models WHERE active ORDER BY id ASC").fetchall()
    return models