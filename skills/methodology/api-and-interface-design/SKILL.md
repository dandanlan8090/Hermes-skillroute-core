---
name: api-and-interface-design
description: >
  API and interface design: RESTful, GraphQL, and internal API patterns. Use when designing new API endpoints, defining data contracts, creating SDK interfaces, or standardizing internal service communication.
  Not for trivial data passthrough or internal-only refactors.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms:
- linux
- macos
- windows
metadata:
  hermes:
    tags:
      trigger:
      - API设计
      - REST API
      - GraphQL
      - 接口设计
      - endpoint
      - 数据契约
      - API contract
      - OpenAPI
      - Swagger
      - 接口规范
      - 数据模型
      - request/response
      disable:
      - 内部数据透传
      - 仅供内部使用且无消费者
      - 一次性脚本接口
    skill_type: methodology
    priority: normal
    related_skills:
    - source-driven-development
    - spec-driven-development
prerequisites:
  commands:
  - terminal
  - read_file
  - write_file
---
# API and Interface Design

## Overview

Well-designed APIs are consistent, predictable, and self-documenting. This skill covers REST and GraphQL patterns for internal and external APIs — focusing on naming, error handling, pagination, versioning, and documentation.

Core principles: consistency over cleverness, explicitness over implicitness, and forward compatibility.

## When to Use

- Designing new API endpoints
- Defining data contracts between services
- Creating SDK or client library interfaces
- Standardizing internal service communication
- Reviewing existing API design

**When NOT to use:** Trivial internal data passthrough, internal-only refactors with no consumer contract.

## REST API Design

### URL Structure

```
GET    /resources              # List
POST   /resources              # Create
GET    /resources/:id          # Read
PATCH  /resources/:id          # Partial update
DELETE /resources/:id          # Delete
```

### Naming Conventions

- **Plural nouns** for resources: `/users`, `/orders`
- **Kebab-case** for multi-word: `/order-items`
- **No verbs** in URLs — use HTTP methods: `POST /payments` (not `POST /make-payment`)
- **Nested for sub-resources:** `/users/:id/orders`
- **Query params for filtering:** `?status=active&limit=20`

### Error Responses

Consistent error shape:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Title is required",
    "details": [
      { "field": "title", "code": "required" }
    ]
  }
}
```

HTTP status codes: 200 OK, 201 Created, 204 No Content, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 409 Conflict, 422 Unprocessable, 429 Too Many Requests, 500 Internal Server Error.

### Pagination

Cursor-based pagination preferred for lists:

```json
{
  "data": [...],
  "pagination": {
    "cursor": "abc123",
    "has_more": true
  }
}
```

### Versioning

- URL versioning: `/v1/users`, `/v2/users`
- Never remove fields from a version — add new fields, deprecate old ones
- Minimum 6-month deprecation window

## GraphQL Design

- Clear, consistent naming: `users`, `user(id:)`, `createUser(input:)`
- Use enums for constrained values
- Avoid overlapping types
- Document @deprecated with migration path

## Verification Checklist

- [ ] Naming consistent with conventions
- [ ] Error responses return consistent shape
- [ ] Pagination implemented for list endpoints
- [ ] Deprecation strategy defined
- [ ] Documentation generated (OpenAPI / SDL)
- [ ] Auth and rate limiting specified

---

**Reference:** https://github.com/addyosmani/agent-skills
