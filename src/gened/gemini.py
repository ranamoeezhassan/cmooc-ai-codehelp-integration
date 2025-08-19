from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from sqlite3 import Row
from typing import ParamSpec, TypeVar
from flask import current_app, flash, render_template
from dotenv import find_dotenv, load_dotenv
import asyncio

from .auth import get_auth
from .db import get_db

try:
    from google import genai
except ImportError:
    genai = None

class ClassDisabledError(Exception):
    pass

class NoKeyFoundError(Exception):
    pass

class NoTokensError(Exception):
    pass

@dataclass
class LLMConfig:
    api_key: str
    model: str
    tokens_remaining: int | None = None

def _get_llm(*, use_system_key: bool = False, spend_token: bool = False) -> LLMConfig:
    db = get_db()
    auth = get_auth()

    def make_system_client(tokens_remaining: int | None = None) -> LLMConfig:
        system_model = current_app.config.get("SYSTEM_MODEL", "gemini-2.5-pro")
        system_key = current_app.config.get("GEMINI_API_KEY")
        if not system_key:
            raise NoKeyFoundError("No Gemini API key set in config.")
        return LLMConfig(
            api_key=system_key,
            model=system_model,
            tokens_remaining=tokens_remaining
        )

    if use_system_key:
        return make_system_client()

    # Get class data, if there is an active class
    if auth['class_id']:
        class_row = db.execute("""
            SELECT 
                classes.enabled,
                classes.max_queries,
                users.queries_used,
                COALESCE(consumers.dartmouth_key, classes_user.dartmouth_key, consumers.dartmouth_key, classes_user.dartmouth_key) AS gemini_key,
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

        if not class_row['gemini_key']:
            raise NoKeyFoundError
        
        if class_row['role'] == 'student':
            if class_row['queries_used'] >= class_row['max_queries']:
                raise NoTokensError(
                    f"You have reached the maximum limit of {class_row['max_queries']} queries. "
                    "Please contact your instructor."
                )
            if spend_token:
                db.execute(
                    "UPDATE users SET queries_used = queries_used + 1 WHERE id = ?",
                    [auth['user_id']]
                )
                db.commit()

        return LLMConfig(
            api_key=class_row['gemini_key'],
            model=class_row['model']
        )

    # Get user data for tokens, auth_provider
    user_row = db.execute("""
        SELECT
            users.query_tokens,
            auth_providers.name AS auth_provider_name
        FROM users
        JOIN auth_providers
          ON users.auth_provider = auth_providers.id
        WHERE users.id = ?
    """, [auth['user_id']]).fetchone()

    if user_row is None:
        raise ValueError("User not found")

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
                flash("Error: No Gemini API key set. An API key must be set by the instructor.")
                return render_template("error.html")
            except NoTokensError:
                flash("You have used all of your free queries.")
                return render_template("error.html")
            
            kwargs['llm'] = llm
            return f(*args, **kwargs)
        return decorated_function
    return decorator

async def get_completion(llm: LLMConfig, messages: list[dict] | None = None, prompt: str | None = None) -> tuple[dict[str, str], str]:
    if genai is None:
        current_app.logger.error("Google Generative AI SDK not installed")
        return {'error': 'Google Generative AI SDK not installed.'}, "Error: SDK missing"
    
    try:
        # The client gets the API key from the environment variable `GEMINI_API_KEY`.
        client = genai.Client(api_key=llm.api_key)

        # Prepare the content
        if messages:
            # Convert OpenAI-style messages to Gemini format
            # Gemini expects a simple string for single-turn or a list of content parts
            if len(messages) == 1:
                content = messages[0].get('content', '')
            else:
                # For multi-turn, you might need to format differently
                # For now, just concatenate
                content = "\n".join([msg.get('content', '') for msg in messages])
        elif prompt:
            content = prompt
        else:
            return {'error': 'No prompt or messages provided.'}, "Error: No input"
        
        # Use the client to generate content
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=llm.model,
            contents=content
        )
        
        # Extract the text from the response
        response_text = response.text if hasattr(response, 'text') else str(response)
        
        # Return in the same format as OpenAI
        return {'response': response_text}, response_text
        
    except Exception as e:
        current_app.logger.error(f"Gemini API Error: {e}")
        return {'error': str(e)}, f"Error: {str(e)}"

def get_models() -> list[Row]:
    db = get_db()
    models = db.execute("SELECT * FROM models WHERE active ORDER BY id ASC").fetchall()
    return models