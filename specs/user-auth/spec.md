---
feature: user-auth
status: approved   # draft -> in-review -> approved
owner: pranay.gupta
created: 2026-09-22
# approved-by: <name>
# approved-date: <YYYY-MM-DD>
---

# Spec: User Authentication

> Do not mix "what the system must do" with "how it will be built." Tech stack and implementation choices belong in `plan.md`.

## Context

The Product CRUD API must be protected so that only authenticated callers can create, update, or delete products. This requires a minimal account and login mechanism that can issue a bearer token, independent of the product domain itself, so it can be reused by future e-commerce features.

## Technical requirements

- The system must store user accounts with a unique identifier, username/email, and a securely hashed password (never plaintext).
- The system must provide a registration endpoint to create a new user account.
- The system must provide a login endpoint that verifies credentials and issues a signed JWT access token on success.
- The API must reject registration of a duplicate username/email.
- The API must reject login with invalid credentials without revealing whether the username or the password was wrong.
- The system must sign JWTs using a secret/key sourced from an environment variable, never hardcoded.
- Issued JWTs must carry an expiration claim and must be rejected once expired.
- The API must expose a way for other services/features (e.g. Product CRUD) to validate a JWT and identify the calling user from it.
- Passwords must never be returned in any API response.

## Acceptance criteria

- [ ] **FR-001:** Register a new user
      Given no existing account uses the given username/email
      When a client POSTs valid registration data (username/email + password)
      Then the system creates a user record with a hashed password and returns 201 with the created user's public fields (no password)

- [ ] **FR-002:** Reject duplicate registration
      Given an account already exists with the given username/email
      When a client POSTs registration data reusing that username/email
      Then the system returns 409 Conflict and creates no new record

- [ ] **FR-003:** Reject invalid registration input
      Given a registration payload missing a required field or with an invalid email format or a password below the minimum length
      When a client POSTs that payload
      Then the system returns 422 with field-level validation errors and creates no record

- [ ] **FR-004:** Login with valid credentials
      Given a registered user account
      When a client POSTs the correct username/email and password to the login endpoint
      Then the system returns 200 with a signed JWT access token and its expiration

- [ ] **FR-005:** Reject login with invalid credentials
      Given a registered user account
      When a client POSTs an incorrect password, or a username/email that does not exist
      Then the system returns 401 with a generic "invalid credentials" error that does not indicate which field was wrong

- [ ] **FR-006:** Reject expired or malformed tokens
      Given a request carries a JWT that is expired, has an invalid signature, or is malformed
      When that request is validated by the token-checking mechanism
      Then the system rejects it with 401 before any protected logic runs

- [ ] **FR-007:** Identify the calling user from a valid token
      Given a request carries a valid, unexpired JWT
      When the token is validated
      Then the system can resolve the user identity (e.g. user ID) encoded in the token for use by protected endpoints

## Out of scope

- Password reset / forgot-password flow.
- Email verification.
- Role-based access control / permission levels (all authenticated users are treated equally for now).
- Token refresh endpoint (short-lived access tokens only for v1; re-login is required after expiry).
- OAuth / social login / SSO.
- Account update or deletion endpoints.
- Rate limiting / brute-force login protection.

## Open questions

- None — resolved with stakeholder: single unified user model with self-service registration (no admin-only account creation), access-token-only (no refresh token) for v1.
