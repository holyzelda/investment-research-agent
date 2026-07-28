# Policy Ask SDK Startup Optimization Design

**Date:** 2026-07-28

## Goal

Reduce backend startup latency caused by the `lark_oapi` SDK while preserving the policy-question API behavior. Remove an unused duplicate FastAPI application construction in `run.py`.

## Current Cause

`app.main` imports the policy-market router. That router imports `PolicyAskExecutorAdapter`, whose module-level import of `tools.policy_ask` imports `lark_oapi`. The SDK initializes a broad API surface at import time, making cold imports expensive.

`run.py` also constructs an application with `create_app()`, but starts Uvicorn with the separate module-level application at `app.main:app`. The `run.py` application is unused.

## Design

### Policy script loading

Introduce a small policy-question loader module that owns exactly one process-wide background warm-up task and its result.

- The FastAPI lifespan creates the task after startup begins.
- The task imports `tools.policy_ask` through `asyncio.to_thread()` so its synchronous import does not block the event loop.
- The loader stores the imported module or the import exception.
- The lifespan cancels and awaits an unfinished task during shutdown.

### Policy-question execution

`PolicyAskExecutorAdapter` must not import `tools.policy_ask` at module scope.

When the adapter receives a question, it obtains the module from the loader:

- If warm-up completed successfully, it returns the module immediately.
- If warm-up is running, it awaits the same task, then returns the module.
- If warm-up failed, it propagates the stored exception through the existing consultation failure handling.

This uses the selected background-warm-up plus request-wait strategy. The service can begin listening without waiting for the SDK, while a request that arrives unusually early waits rather than receiving a new readiness response. Only SDK import behavior changes; the existing synchronous `policy_ask.ask()` execution model is out of scope.

### Entrypoint cleanup

Remove the `create_app` import and unused `app = create_app()` from `run.py`. Continue invoking Uvicorn with `app.main:app`, which is the sole application instance.

## Error Handling

Warm-up import errors are retained by the loader. A consultation request awaiting the task receives the same failure, which follows the established `ConsultationExecutionError` path and the existing `{code, msg, data}` response behavior. No new HTTP readiness status or frontend behavior is introduced.

## Tests

- Verify loading a policy-question module is deferred and the warm-up task is shared.
- Verify a request during warm-up waits and invokes the returned module afterward.
- Verify warm-up failures propagate to callers.
- Verify the adapter module has no eager dependency on `tools.policy_ask`.
- Verify `run.py` does not call `create_app()`.

## Scope Limits

- Do not change the policy knowledge-base retrieval or LLM behavior.
- Do not add service-discovery changes, Nacos retries, health-check behavior, or frontend changes.
- Do not modify the overall synchronous policy-question execution model.
