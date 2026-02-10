# Security

This document outlines the security measures implemented in the Taggarr Web UI.

## Authentication

- [x] Password hashing with PBKDF2-SHA256 (600,000 iterations)
- [x] Secure session tokens (secrets.token_urlsafe)
- [x] HTTP-only session cookies
- [x] API keys stored as SHA256 hashes
- [x] Session expiration (configurable, default 7 days)
- [x] Automatic session cleanup

## API Security

- [x] All endpoints require authentication (except /health, /auth/status)
- [x] Input validation via Pydantic models
- [x] CORS configured (permissive for development)
- [ ] Rate limiting (recommended for production)

## Database

- [x] Parameterized queries via SQLAlchemy ORM (prevents SQL injection)
- [x] Unique constraints on sensitive fields (username, API key names)
- [x] Sensitive data (passwords, API keys) never stored in plaintext

## Session Management

- [x] Cryptographically secure session tokens
- [x] Session tokens tied to user accounts
- [x] Session invalidation on logout
- [x] Expired session cleanup

## Recommendations for Production

### HTTPS

Enable HTTPS and configure secure cookies:

```python
# In production, set secure=True on session cookies
response.set_cookie(
    key="session_id",
    value=token,
    httponly=True,
    secure=True,  # Enable in production
    samesite="strict"
)
```

### CORS Configuration

Restrict CORS to specific origins in production:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### Rate Limiting

Add rate limiting to authentication endpoints to prevent brute force attacks:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, ...):
    ...
```

### CSRF Protection

For browser-based clients, consider adding CSRF protection:

```python
from fastapi_csrf_protect import CsrfProtect

@app.post("/auth/login")
async def login(request: Request, csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    ...
```

### Security Headers

Add security headers via middleware:

```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

### Regular Updates

- Keep dependencies updated for security patches
- Monitor security advisories for FastAPI, SQLAlchemy, and other dependencies
- Run `uv audit` or similar tools to check for known vulnerabilities

## Reporting Security Issues

If you discover a security vulnerability, please report it responsibly by:

1. Opening a private security advisory on GitHub
2. Emailing the maintainers directly
3. Not disclosing the issue publicly until a fix is available
