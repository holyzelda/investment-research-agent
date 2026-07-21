# Nacos Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Load backend business configuration from Nacos with local YAML fallback and register the running service instance.

**Architecture:** Environment files bootstrap only application and Nacos connection settings. Settings give remote business YAML highest priority, followed by existing explicit business environment variables and local YAML. A focused Nacos client owns v2 SDK creation, config retrieval, registration, deregistration, and close operations.

**Tech Stack:** FastAPI, Pydantic, PyYAML, python-dotenv, nacos-sdk-python v2, pytest.

---

### Task 1: Specify Settings Precedence

**Files:**
- Modify: `agent-backend/tests/integration/infrastructure/test_nacos_fallback.py`
- Modify: `agent-backend/app/core/config/settings.py`

- [ ] Write tests proving Nacos business configuration overrides local YAML and existing environment variables.
- [ ] Run `./.venv/bin/python -m pytest tests/integration/infrastructure/test_nacos_fallback.py -q` and observe the remote-configuration assertion fail.
- [ ] Add validated remote-overlay storage and merge it before existing environment variable reads.
- [ ] Re-run the focused test and verify it passes.

### Task 2: Implement Nacos Lifecycle

**Files:**
- Modify: `agent-backend/tests/integration/infrastructure/test_nacos_fallback.py`
- Modify: `agent-backend/app/infrastructure/nacos/client.py`

- [ ] Write tests with a fake client for config retrieval, registration metadata, deregistration, and local fallback.
- [ ] Run the focused test and observe the lifecycle assertions fail.
- [ ] Implement the minimal v2 SDK client wrapper and startup/shutdown sequence.
- [ ] Re-run the focused test and verify it passes.

### Task 3: Classify Bootstrap Files

**Files:**
- Create: `agent-backend/.env.test`
- Create: `agent-backend/.env.prod`
- Create: `agent-backend/run.py`
- Modify: `agent-backend/configs/application.yml`
- Modify: `agent-backend/app/core/config/settings.py`
- Modify: `agent-backend/requirements.txt`
- Modify: `agent-backend/README.md`

- [ ] Write a test proving an explicit `ENV_FILE` supplies app and Nacos bootstrap values without replacing business YAML.
- [ ] Run the focused test and observe it fail before dotenv bootstrap exists.
- [ ] Add a `run.py` environment bootstrap before importing `app.main`, environment templates, and documentation; remove only app/Nacos sections from local YAML.
- [ ] Run focused tests and the backend settings suite.

### Task 4: Verify Regression Safety

**Files:**
- Test: `agent-backend/tests/integration/infrastructure/test_nacos_fallback.py`
- Test: `agent-backend/tests/unit/test_settings.py`
- Test: `agent-backend/tests/e2e/test_app_boot.py`

- [ ] Run focused Nacos and settings tests.
- [ ] Run the complete backend pytest suite.
- [ ] Inspect the final diff to verify no calculation, identity, response, or Feishu interface behavior changed.
