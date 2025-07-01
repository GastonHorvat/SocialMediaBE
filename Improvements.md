# Suggested Improvements

This document outlines a series of suggested improvements for the backend application, with a focus on stabilizing the LinkedIn OAuth flow, enhancing security, and improving the overall architecture.

## 🔑 Authentication & Authorization (OAuth)

- [ ] **Replace `authlib` with a direct `httpx` implementation for LinkedIn OAuth.** The `connections_router.py` still uses `authlib` (`oauth.linkedin`), which contradicts the decision documented in the `CHANGELOG.md` to remove it. This is the most critical fix. You should create a manual, explicit `httpx` `POST` request to the token endpoint (`https://www.linkedin.com/oauth/v2/accessToken`) as planned.

- [ ] **Centralize and Encapsulate LinkedIn API Logic.** Create a dedicated `linkedin_service.py` to handle all interactions with the LinkedIn API (fetching tokens, getting user info, etc.). This will remove the direct dependency on `httpx` or `authlib` from the router, making the code cleaner and easier to maintain. The router should only call the service.

- [ ] **Enhance Security for Stored Tokens.** The changelog mentions encrypting tokens. Ensure the `token_data` is being encrypted with a strong algorithm (`Fernet` from the `cryptography` library is a good choice) within the `connections_service` before it's persisted to the database.

## 🏗️ Architecture & Code Quality

- [ ] **Consolidate Service Logic.** There is an opportunity to streamline services. For instance, the logic within `oauth_state_service.py` is tightly coupled to the connection flow and could potentially be absorbed into the `connections_service.py` to reduce the number of small, single-purpose service files.

- [ ] **Standardize Asynchronous Operations.** The use of `run_in_threadpool` is a good way to handle synchronous library calls in an async application. However, a full migration to async-native libraries (like `asyncpg` for PostgreSQL and `aiohttp` or `httpx` for HTTP requests) would provide better performance and cleaner code by allowing `await` to be used everywhere. Since `supabase-py` v2 introduced async support, it would be beneficial to review all database and storage calls to ensure they are using the async client correctly.

- [ ] **Refine Dependency Management.** The `requirements.txt` file could be improved by using a tool like `pip-tools` to manage dependencies. This creates a `requirements.in` file for high-level dependencies and a `requirements.txt` file that is compiled with all pinned sub-dependencies, ensuring reproducible builds and avoiding the "resolution-too-deep" errors mentioned in the changelog.

- [ ] **Improve Configuration Management.** Sensitive information like `client_id` and `client_secret` should be handled carefully. While `pydantic-settings` is great for loading from `.env` files, consider integrating a more robust secrets management solution for production environments (e.g., HashiCorp Vault, AWS Secrets Manager, or Doppler).

## 🧪 Testing

- [ ] **Introduce Unit and Integration Tests.** A testing suite is crucial for long-term stability, especially for critical flows like authentication. Start by adding unit tests for the helper functions and services (`connections_service`, `linkedin_service`). Then, create integration tests for the API endpoints to validate the entire flow, which will help catch regressions before they make it to production. 