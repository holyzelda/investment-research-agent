# Nacos Configuration Design

## Scope

Migrate the backend's incomplete Nacos bootstrap to the pattern used by the Ningxia backend without importing its business or authentication code. Preserve every existing settings consumer and all calculation behavior.

## Configuration Sources

`app.main` loads `ENV_FILE` before creating the application, and retains the standard `app.main:app` ASGI export. `.env.test` and `.env.prod` contain only `APP_*` and `NACOS_*` bootstrap values. `run.py` only creates the app and starts Uvicorn. `configs/application.yml` contains database, platform, Feishu, CORS, calculation, and spot-price configuration. Nacos uses the data ID `{app.name}-{nacos.profile}.yml` and supplies the same business sections as YAML.

Effective precedence is Nacos business YAML, then explicit existing business environment variables, then local `application.yml`, then model defaults. Nacos never overrides the app or Nacos bootstrap sections, so the process retains a stable Nacos endpoint, data ID, and service identity.

## Lifecycle

When enabled, startup creates the v2 Nacos configuration and naming clients, fetches and validates remote YAML, updates the settings cache, initializes the existing engine and scheduler, then registers the local instance with version and context metadata. Empty, invalid, unavailable, or disabled Nacos leaves settings on local YAML and environment values. Shutdown deregisters only a successfully registered instance and closes the client.

## Compatibility And Tests

`get_settings()` remains the public configuration API. Existing `IR_*` overrides remain valid as the local fallback tier for automated tests and deployment compatibility. Tests use a fake Nacos client to prove remote merge, local fallback, Nacos precedence, registration, and cleanup without a Nacos server.
