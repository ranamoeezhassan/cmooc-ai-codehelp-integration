# Dartmouth API AI Integration for CodeHelp

This document details all the changes that we at Dartmouth have made to the open source CodeHelp application to use it with the Dartmouth API instead of the OpenAI service.

## Implementation Details

### 1. Switching from OpenAI to Dartmouth AI

Wrote a new module called `dartmouth.py` located in `src/gened` meant to replace the `openai.py` module. Below are specific details that can be used as a guideline to extend the module or switch the API to another service.

#### \_get_llm()

- Internal function that manages LLM configuration and authentication
- Handles both system and user-specific API keys
- Manages token usage and class-based access restrictions
- Returns LLMConfig with api_key, model, and tokens data

#### with_llm()

- Decorator function for LLM operations
- Manages error handling for:
  - Disabled classes
  - Missing API keys
  - Exhausted tokens
- Injects LLM configuration into decorated functions

#### get_completion()

- Handles API communication for text completions
- Manages JWT token acquisition and refresh
- Sends prompts to Dartmouth API endpoints
- Returns tuple of response data and generated text

#### Supporting Functions

- `getBaseURL()`: Retrieves base API URL from environment
- `getJWTURL()`: Retrieves JWT endpoint URL from environment
- `isTokenExpired()`: Checks JWT token expiration
- `generateInstructions()`: Formats prompts for API submission
- `sendInstructions()`: Handles API request transmission

#### Error Classes

- ClassDisabledError
- NoKeyFoundError
- NoTokensError
- TokenExpiredError

### 2. New Model Configuration

- All models that you plan on using need to be added in the database schema. The only way I figured out how to do that was use the database migrations in order to remove/add api models and write new URLs.
- Added new Dartmouth models in schema migrations:
  - CodeLlama 13B: General code and instruction following
  - CodeLlama 13B Python: Specialized for Python code assistance
  - Llama 3-1 8B: Smaller alternative model for general queries
  - LLama 3 8B: Another alternative model for general queries
  - The default queries are sent to the model configured in the .env file whereas once a user joins a class, the instructor has to set a default model where all the student queries are directed to.
  - If you wanted to add additional models down the line, you would have to write a new migration file (likely a SQL file) that would add the model to the `models` table.

### 3. Query Management

- Modified the database to add `queries_used` column in the `users` table that is responsible for making sure that a student does not exceed the allocated query limit to them. The `max_queries` column in the
- Added per-user query tracking and limits
- Query counts visible in instructor and admin interfaces
- Query reset functionality available to instructors

### 4. API Integration

#### Authentication System

- JWT-based authentication with 1-hour token expiration
- Tokens signed using `SECRET_KEY` environment variable
- Token validation through Authorization header decorator
- Automatic user_id extraction into Flask context

#### Core API Endpoints

##### Authentication

Authentication is handled through JWT tokens. Users must obtain a valid token to access protected endpoints.

- `POST /api/login`
  - Validates username/password credentials
  - Returns JWT access token upon success

##### Query Management

- `POST /api/query` (Protected)
  - Handles code assistance requests
  - Supports optional context parameter
  - Returns query_id and AI responses
  - Requires valid JWT token

##### Context Management

- `GET /api/contexts` - Lists available contexts
- `GET /api/context/<name>` - Retrieves specific context
- `POST /api/context` - Creates new context (instructor only)
- `DELETE /api/context/<name>` - Removes context (instructor only)

#### Client Library (api_requests.py)

- Authentication helper for JWT token acquisition
- Query submission and retrieval functions
- Context management CRUD operations
- All requests include JWT authentication headers
- `api_requests.ipynb` serves as an example of how I envision the API service being used.

#### Error Handling

- 403 errors for invalid/missing tokens
- Authentication failures return appropriate status codes
- Context management restricted to instructor roles

The API follows RESTful principles with JWT authentication securing all protected endpoints. Context management is primarily handled by instructors through the provided CRUD operations.

## Setup Requirements

These instructions are specific to the dartmouth api changes that I have made. These build on the "Set Up CodeHelp Application" instructions in the `README.md` so please make sure you follow those instructions before you proceed with these.

1. Environment Configuration:

```
DARTMOUTH_API_KEY=<your_api_key>
BASE_URL=https://api.dartmouth.edu
JWT_URL=https://api.dartmouth.edu/api/jwt
SYSTEM_MODEL=/api/ai/tgi/codellama-13b-instruct-hf/generate
```

2. Database Migration:
   Run custom dartmouth models related migrations.

```sh
flask --app codehelp dartmouth-migrations
```

## Limitations

- API requests require valid Dartmouth API key
- Query limits enforced per user. However, if a user is in two different classes, then the query limit might be buggy the way the database changes are implemented.
- Models may have different capabilities than OpenAI equivalents

## Base URL Configuration for Testing

Base URL for the API endpoints can be configured in the environment settings. Default development URL is `http://localhost:5000/`
