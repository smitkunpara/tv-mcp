# Plan: TradingView MCP Rebuild with `tv_scrapper`, `new_vercel`, and `new_test`

**Created:** 2026-02-16  
**Status:** Ready for Atlas Execution

## Summary

This plan rebuilds the MCP + HTTP server architecture around a new internal package (`tv_scrapper`) while keeping all current code paths in place as reference and compatibility shims. The migration aligns server internals with `tv_scraper` v1 API conventions (standardized response envelope, renamed classes/methods, split `exchange` + `symbol`, and native options APIs). The rollout is incremental and test-driven: preserve existing behavior first, then modularize and standardize, then switch default entrypoints after parity is proven. The old modules under `src/tradingview_mcp`, `vercel/`, and `tests/` remain intact until explicit removal is requested.

## Context & Analysis

**Relevant Files:**
- `src/tradingview_mcp/main.py`: current MCP server and tool wrappers; contains transport-level coercion, validation, and TOON formatting.
- `src/tradingview_mcp/tradingview_tools.py`: monolithic core service implementation; includes data/news/social/options logic and token/cookie handling.
- `src/tradingview_mcp/validators.py`: validation constants and functions used by both MCP and HTTP layers.
- `src/tradingview_mcp/config.py`: settings singleton with runtime cookie update path.
- `src/tradingview_mcp/auth.py`: JWT extraction and decode utilities.
- `src/tradingview_mcp/utils.py`: output transforms, timestamp conversion, and content cleanup.
- `vercel/index.py`: monolithic FastAPI app with all routes and auth dependencies.
- `vercel/models.py`: HTTP Pydantic schemas.
- `tests/http/*` and `tests/stdio/*`: parity-oriented integration suites that currently verify behavior.
- `pyproject.toml`: dependency and script entrypoints; currently pins `tradingview-scraper` Git source.

**Key Functions/Classes:**
- MCP tool entry points in `src/tradingview_mcp/main.py`:
  - `get_historical_data`, `get_news_headlines`, `get_news_content`, `get_all_indicators`, `get_ideas`, `get_minds`, `get_option_chain_greeks`.
- Core domain functions in `src/tradingview_mcp/tradingview_tools.py`:
  - `fetch_historical_data`, `fetch_news_headlines`, `fetch_news_content`, `fetch_all_indicators`, `fetch_ideas`, `fetch_minds`, `process_option_chain_with_analysis`, `fetch_option_chain_data`, `get_current_spot_price`.
- HTTP auth/endpoint surface in `vercel/index.py`:
  - `verify_client`, `verify_admin`, and all route handlers including `/update-cookies`.
- Schema classes in `vercel/models.py`:
  - `HistoricalDataRequest`, `NewsHeadlinesRequest`, `NewsContentRequest`, `AllIndicatorsRequest`, `IdeasRequest`, `MindsRequest`, `OptionChainGreeksRequest`.

**Dependencies:**
- `fastmcp`: MCP stdio transport.
- `fastapi`, `uvicorn`: HTTP API.
- `python-toon`: payload encoding in MCP and HTTP wrappers.
- `tradingview-scraper` (current): existing integration library that will be aligned to `tv_scraper` v1 API patterns.
- `python-dotenv`, `requests`, `pydantic`, `pytest`.

**Patterns & Conventions:**
- Thin transport wrappers around shared domain logic (MCP and HTTP both consume shared functions).
- TOON encoding as wire format for response payloads.
- Validation split between wrappers and core functions (currently duplicated).
- Runtime cookie update flow for extension/Vercel admin endpoint.
- Existing test suite emphasizes integration behavior and endpoint parity.

## Implementation Phases

### Phase 1: Baseline Guardrails and New Folder Scaffolding

**Objective:** Introduce `tv_scrapper`, `new_vercel`, and `new_test` directories without breaking existing behavior.

**Files to Modify/Create:**
- `src/tv_scrapper/__init__.py`: package root and compatibility exports.
- `src/tv_scrapper/README.md`: internal architecture and migration notes.
- `new_vercel/__init__.py`: new HTTP package namespace.
- `new_test/__init__.py`: new test namespace marker.
- `new_test/http/` and `new_test/stdio/`: mirrored test directory skeleton.
- `README.md`: migration note documenting temporary dual-structure and non-removal policy.

**Tests to Write:**
- `new_test/http/test_scaffold_imports.py`: verifies new_vercel importability.
- `new_test/stdio/test_scaffold_imports.py`: verifies tv_scrapper importability.
- `new_test/test_legacy_paths_unchanged.py`: verifies legacy import paths still resolve.

**Steps:**
1. Write scaffold tests for import stability (red).
2. Create new directories and minimal `__init__.py`/README stubs (green).
3. Add compatibility assertions that old package imports remain unchanged (green).
4. Ensure no existing `tests/http` or `tests/stdio` files are edited yet.
5. Document migration constraints in README and plan notes.

**Acceptance Criteria:**
- [ ] `tv_scrapper`, `new_vercel`, and `new_test` directories exist.
- [ ] Legacy paths remain functional and untouched for reference.
- [ ] New scaffold tests pass.
- [ ] Existing tests remain runnable with no import break.

---

### Phase 2: `tv_scrapper` Core Foundation (Config, Validation, Auth, Transforms)

**Objective:** Extract foundational concerns from monolith into modular `tv_scrapper` core modules.

**Files to Modify/Create:**
- `src/tv_scrapper/core/settings.py`: settings lifecycle and cookie update support.
- `src/tv_scrapper/core/validators.py`: centralized validation wrappers and constants.
- `src/tv_scrapper/core/auth.py`: JWT retrieval/cache helpers.
- `src/tv_scrapper/core/contracts.py`: normalized internal response dataclasses/types.
- `src/tv_scrapper/transforms/time.py`, `src/tv_scrapper/transforms/news.py`, `src/tv_scrapper/transforms/ohlc.py`.
- Legacy shim updates:
  - `src/tradingview_mcp/config.py`
  - `src/tradingview_mcp/validators.py`
  - `src/tradingview_mcp/auth.py`
  - `src/tradingview_mcp/utils.py`

**Tests to Write:**
- `new_test/stdio/test_core_validators.py`: equivalent validation behavior for exchange/timeframe/provider/area.
- `new_test/stdio/test_core_auth_cache.py`: token cache refresh/expiry behavior.
- `new_test/stdio/test_core_transforms.py`: time/news/ohlc transform parity.

**Steps:**
1. Write parity tests comparing old vs new validator/auth utility outcomes (red).
2. Implement new `tv_scrapper.core` and `tv_scrapper.transforms` modules (green).
3. Convert legacy modules to thin re-export shims (green).
4. Keep legacy symbol/function names unchanged.
5. Refactor duplicated helper logic into shared utilities only if parity tests stay green.

**Acceptance Criteria:**
- [ ] Core concerns are moved into `tv_scrapper` modules.
- [ ] Legacy modules remain as compatibility shims with same exports.
- [ ] No behavior regressions in validation/auth/transform outputs.
- [ ] All phase tests pass.

---

### Phase 3: Domain Services in `tv_scrapper` with Standardized Internal Contracts

**Objective:** Split monolithic `tradingview_tools.py` into domain services and align internal I/O to `tv_scraper` conventions.

**Files to Modify/Create:**
- `src/tv_scrapper/services/historical.py`
- `src/tv_scrapper/services/technicals.py`
- `src/tv_scrapper/services/news.py`
- `src/tv_scrapper/services/ideas.py`
- `src/tv_scrapper/services/minds.py`
- `src/tv_scrapper/services/options.py`
- `src/tv_scrapper/services/__init__.py`
- `src/tv_scrapper/adapters/legacy_response_adapter.py`: maps `tv_scraper` envelope ↔ existing MCP/HTTP expected structure.
- `src/tradingview_mcp/tradingview_tools.py`: replaced by shim delegating to new services while preserving function signatures.

**Tests to Write:**
- `new_test/stdio/test_service_historical_parity.py`
- `new_test/stdio/test_service_news_parity.py`
- `new_test/stdio/test_service_social_parity.py`
- `new_test/stdio/test_service_options_parity.py`

**Steps:**
1. Write tests that assert old function signatures and key response fields remain available (red).
2. Implement domain service modules and route old function calls through adapter layer (green).
3. Use a single internal contract (`status`, `data`, `metadata`, `error`) for service internals.
4. Preserve legacy wrapper outputs (including TOON payload expectations) via adapter mapping.
5. Reduce duplicated validation/coercion by centralizing in service boundary.

**Acceptance Criteria:**
- [ ] `tradingview_tools` behavior remains backward compatible.
- [ ] Domain logic exists in modular service files.
- [ ] Internal standardized envelope is in place.
- [ ] All phase tests pass.

---

### Phase 4: Native Option Chain Integration Using `tv_scraper` Options APIs

**Objective:** Replace custom direct request option-chain fetch paths with native `tv_scraper` options methods while preserving analytics output.

**Files to Modify/Create:**
- `src/tv_scrapper/services/options.py`: use `Options.get_chain_by_expiry` and `Options.get_chain_by_strike` adapters.
- `src/tv_scrapper/services/options_analytics.py`: retain/customize ITM/OTM filtering and Greeks analytics shape.
- `src/tv_scrapper/adapters/options_contract_adapter.py`: map native options envelope to legacy option-chain-greeks response contract.
- `src/tradingview_mcp/tradingview_tools.py`: keep `process_option_chain_with_analysis` signature stable via delegation.

**Tests to Write:**
- `new_test/stdio/test_options_native_fetch.py`: verifies native options fetch by expiry/strike.
- `new_test/stdio/test_options_analytics_contract.py`: verifies returned keys (`spot_price`, `analytics`, `available_expiries`, etc.) remain present.
- `new_test/http/test_option_chain_endpoint_contract.py`: verifies endpoint transport still wraps TOON correctly.

**Steps:**
1. Add failing tests for native options behavior and legacy contract compatibility (red).
2. Integrate `tv_scraper` `Options` methods in options service (green).
3. Move analytics computations into dedicated module and keep output schema stable (green).
4. Preserve current filtering semantics (`nearest`, `all`, explicit date; ITM/OTM bounds).
5. Validate error mapping from native failed envelopes to existing transport behavior.

**Acceptance Criteria:**
- [ ] Option chain fetching is native through `tv_scraper` options APIs.
- [ ] Legacy analytics response contract remains compatible.
- [ ] Transport-level endpoint/tool behaviors remain stable.
- [ ] All phase tests pass.

---

### Phase 5: MCP Server Rebuild as Modular Adapter over `tv_scrapper`

**Objective:** Rebuild MCP transport layer with cleaner structure while preserving existing tool names and behavior.

**Files to Modify/Create:**
- `src/tv_scrapper/mcp/server.py`: FastMCP app factory and tool registration.
- `src/tv_scrapper/mcp/tools/`:
  - `historical.py`, `news.py`, `technicals.py`, `social.py`, `options.py`
- `src/tv_scrapper/mcp/serializers.py`: TOON encoder/decoder helper and error serializer.
- `src/tradingview_mcp/main.py`: compatibility shim delegating to `tv_scrapper.mcp.server` while preserving module execution entrypoint.

**Tests to Write:**
- `new_test/stdio/test_mcp_tool_registration.py`: tool names and descriptions are preserved.
- `new_test/stdio/test_mcp_tool_contracts.py`: tool parameter coercion and TOON response parity.
- `new_test/stdio/test_mcp_error_serialization.py`: consistent error envelope handling.

**Steps:**
1. Add tests asserting current MCP tool names and return contract (red).
2. Implement modular MCP server and tool handlers in `tv_scrapper` (green).
3. Keep legacy `src/tradingview_mcp/main.py` as shim to avoid breaking scripts/imports.
4. Centralize shared coercion/error mapping in MCP adapter utilities.
5. Validate compatibility with existing `tradingview-mcp` script entrypoint.

**Acceptance Criteria:**
- [ ] MCP server is modularized under `tv_scrapper/mcp`.
- [ ] Existing tool names and usage remain unchanged.
- [ ] `python -m src.tradingview_mcp.main` compatibility is preserved.
- [ ] All phase tests pass.

---

### Phase 6: `new_vercel` Modularization with Backward-Compatible Entrypoint

**Objective:** Split monolithic Vercel API into modular routers/services while preserving route/auth behavior and deployment entrypoint compatibility.

**Files to Modify/Create:**
- `new_vercel/app.py`: FastAPI app factory.
- `new_vercel/auth.py`: `verify_client`, `verify_admin`, APIKeyHeader setup.
- `new_vercel/schemas.py`: request schema definitions (or re-exports).
- `new_vercel/routers/public.py`: `/`, `/health`, `/privacy-policy`.
- `new_vercel/routers/client.py`: business POST routes.
- `new_vercel/routers/admin.py`: `/update-cookies`.
- `new_vercel/services/`:
  - `historical_service.py`, `news_service.py`, `technicals_service.py`, `social_service.py`, `options_service.py`, `cookies_service.py`.
- `vercel/index.py`: compatibility shim importing app from `new_vercel.app`.
- `vercel/models.py`: shim/re-export to `new_vercel.schemas` if moved.

**Tests to Write:**
- `new_test/http/test_auth_dependencies.py`: header validation parity.
- `new_test/http/test_public_routes.py`: `/`, `/health`, `/privacy-policy`.
- `new_test/http/test_client_routes_contract.py`: TOON envelope and status code parity.
- `new_test/http/test_admin_update_cookies_contract.py`: cookie update behavior parity.

**Steps:**
1. Write tests for route+auth behavior exactness (red).
2. Build `new_vercel` modular app and route handlers (green).
3. Keep `vercel/index.py` stable as deployment and import shim (green).
4. Ensure status codes/detail messages remain unchanged.
5. Verify extension compatibility for `/update-cookies` request/response contract.

**Acceptance Criteria:**
- [ ] `new_vercel` contains modular API implementation.
- [ ] Existing `vercel/index.py` entrypoint still works without caller changes.
- [ ] Route/auth/response contracts match legacy behavior.
- [ ] All phase tests pass.

---

### Phase 7: `new_test` Suite Build-Out and Dual-Run Strategy

**Objective:** Introduce `new_test` as the new canonical test suite while keeping old tests active as reference until removal.

**Files to Modify/Create:**
- `new_test/http/*`: mirrored and improved HTTP tests.
- `new_test/stdio/*`: mirrored and improved stdio/service tests.
- `new_test/conftest.py`: shared fixtures/utilities for TOON decode and env setup.
- Optional CI/test config updates in `pyproject.toml` for phased suite selection.

**Tests to Write:**
- Mirror all current feature coverage from old tests.
- Add missing smoke tests for currently untested routes (`/health`, `/privacy-policy`, `/`).
- Add explicit parity tests ensuring legacy and new adapters return equivalent normalized contracts.

**Steps:**
1. Copy baseline tests into `new_test` with minimal path changes (red/green parity).
2. Add missing smoke/contract tests for uncovered endpoints.
3. Introduce deterministic unit-level tests for validators/adapters.
4. Run both old and new suites in parallel during transition.
5. Mark old suite as reference-only (still runnable) until explicit cleanup approval.

**Acceptance Criteria:**
- [ ] `new_test` has full parity coverage with legacy test suites.
- [ ] Old tests remain available and passing.
- [ ] New tests validate both backward compatibility and modular architecture.
- [ ] All phase tests pass.

---

### Phase 8: Documentation, Dependency Alignment, and Controlled Cutover

**Objective:** Finalize documentation and packaging so maintainers can switch to the new architecture safely while retaining rollback paths.

**Files to Modify/Create:**
- `README.md`: add architecture section for `tv_scrapper`, `new_vercel`, `new_test`, and migration status.
- `pyproject.toml`: ensure dependency and script entrypoints align with intended runtime package usage.
- `plans/` execution log/checklist updates.
- Optional compatibility docs:
  - `docs/migration-internal.md` (if docs dir exists)
  - `src/tradingview_mcp/DEPRECATION.md`

**Tests to Write:**
- `new_test/test_entrypoint_compatibility.py`: validates script/module entrypoint integrity.
- `new_test/test_import_compatibility_matrix.py`: legacy + new import paths matrix.

**Steps:**
1. Write documentation/tests to confirm both old and new paths are discoverable (red).
2. Update readme and package metadata to describe dual-structure strategy (green).
3. Final compatibility pass on MCP + HTTP + options and cookie-update workflows.
4. Produce a removal-ready checklist for old modules (but do not delete).
5. Tag migration as complete only when parity and docs criteria pass.

**Acceptance Criteria:**
- [ ] Docs clearly explain current dual-structure and future cleanup process.
- [ ] Entry points and imports are validated by tests.
- [ ] No deletion of legacy code occurs in this cycle.
- [ ] All tests pass and migration is release-ready.

## Open Questions

1. Folder naming target for new internal package?
   - **Option A:** Use `tv_scrapper` exactly (matches requested folder name).
   - **Option B:** Use `tv_scraper` for naming consistency with upstream package; keep `tv_scrapper` as alias package.
   - **Recommendation:** Option A for now (explicit user request), plus alias support if needed later.

2. How strict should backward output compatibility be during transition?
   - **Option A:** Preserve all current response quirks exactly (including sentinel strings and error text).
   - **Option B:** Normalize to strict `tv_scraper` envelope at transport boundaries now.
   - **Recommendation:** Option A during rebuild; introduce normalization behind feature flag after parity.

3. What to do with existing validation duplication in wrappers?
   - **Option A:** Keep duplicate checks for low-risk compatibility.
   - **Option B:** Centralize in service layer and keep wrappers minimal.
   - **Recommendation:** Option B, but phase it with strict parity tests to avoid regressions.

4. Dependency source for scraper library?
   - **Option A:** Keep Git direct reference in `pyproject.toml`.
   - **Option B:** Switch to stable package release pin once available and tested.
   - **Recommendation:** Start with current Git ref for parity; move to version pin in a follow-up stabilization phase.

## Risks & Mitigation

- **Risk:** Behavior regressions due to large refactor.
  - **Mitigation:** Strangler pattern with shim modules and dual-test execution.

- **Risk:** Live network instability causes flaky tests.
  - **Mitigation:** Separate deterministic unit/contract tests from live integration tests; run integration in controlled stage.

- **Risk:** Option chain response differences after native API adoption.
  - **Mitigation:** Add adapter contract tests and keep output mapping stable.

- **Risk:** Vercel auth/cookie endpoint breaks extension flow.
  - **Mitigation:** Preserve exact route/header/status contracts and add dedicated admin endpoint tests.

- **Risk:** Team confusion during dual-structure period.
  - **Mitigation:** Clear README migration section and deprecation notes in legacy modules.

## Success Criteria

- [ ] New directories exist and are actively used: `src/tv_scrapper`, `new_vercel`, `new_test`.
- [ ] Legacy code remains available as reference and compatibility layer (not removed).
- [ ] MCP tools and HTTP endpoints maintain functional parity with existing behavior.
- [ ] Native option chain fetching is integrated through `tv_scraper` options APIs.
- [ ] Internal service architecture follows standardized input/output contracts.
- [ ] Vercel code is modularized without changing deployment entrypoint expectations.
- [ ] Old and new test suites pass in transition mode.
- [ ] Documentation updated for migration workflow and future cleanup.

## Notes for Atlas

- Use a strict phased implementation order; do not attempt big-bang replacement.
- Preserve old files and import paths until the user explicitly requests deletion.
- Favor compatibility shims over wide import rewrites to minimize churn.
- Keep external API behavior stable first; apply contract cleanup only after parity and explicit approval.
- Prioritize option-chain native integration and response-adapter correctness as critical path.
