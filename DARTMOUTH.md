# Dartmouth API AI Integration for CodeHelp

## Overview
This document details the integration of Dartmouth College's AI API service with CodeHelp, providing an alternative to OpenAI models for code assistance.

## Implementation Details

### 1. New Model Configuration
- Added new Dartmouth models in schema migrations:
    - CodeLlama 13B Python (`codellama-13b-py`)
    - Other Dartmouth models configurable via environment variables 

### 2. API Integration
- Base URL and JWT token endpoint configurable via environment variables:
    - `BASE_URL`: Base URL for API requests
    - `JWT_URL`: JWT token generation endpoint
    - `DARTMOUTH_API_KEY`: API key for authentication
    - `SYSTEM_MODEL`: Default model endpoint path

### 3. Query Management
- Added per-user query tracking and limits
- Query counts visible in instructor and admin interfaces
- Query reset functionality available to instructors
- Default model configured via `DEFAULT_CLASS_MODEL_SHORTNAME`

## Setup Requirements

1. Environment Configuration:
```
DARTMOUTH_API_KEY=<your_api_key>
BASE_URL=https://api.dartmouth.edu
JWT_URL=/api/jwt
SYSTEM_MODEL=/api/ai/tgi/codellama-13b-instruct-hf/generate
```

2. Database Migration:
```sh
flask --app codehelp migrate
```

## Available Models

- `codellama-13b-python-hf`: Specialized for Python code assistance
- `codellama-13b-instruct-hf`: General code and instruction following
- `llama-3-1-8b-instruct`: Smaller alternative model

## Limitations

- API requests require valid Dartmouth API key
- Query limits enforced per user
- Models may have different capabilities than OpenAI equivalents

The integration enables using Dartmouth's AI models while maintaining CodeHelp's core functionality for programming assistance.

### Base URL Configuration
Base URL for the API endpoints can be configured in the environment settings. Default development URL is `http://localhost:5000/api/v1`


## CodeHelp API Integration

### API Overview
The CodeHelp API provides functionality for managing code help requests and responses through a RESTful interface. The API is built using Python Flask and interacts with a MongoDB database.

### Authentication
Authentication is handled through JWT tokens. Users must obtain a valid token to access protected endpoints.

### Core Components

#### api.py
- Main API router and endpoint handler
- Implements Flask RESTful architecture
- Handles the following endpoints:
    - POST `/auth/login`: User authentication and JWT token generation
    - POST `/help/request`: Create new code help request
    - GET `/help/requests`: Retrieve all help requests
    - GET `/help/request/{id}`: Get specific help request
    - PUT `/help/request/{id}`: Update help request status
    - DELETE `/help/request/{id}`: Remove help request

#### api_requests.py
- HTTP request handler for API operations
- Manages API request lifecycle
- Implements the following functionality:
    - Token management and refresh
    - Request validation
    - Error handling and response formatting
    - Rate limiting implementation
    - Request retries with exponential backoff

### Request/Response Format
All API requests and responses use JSON format: