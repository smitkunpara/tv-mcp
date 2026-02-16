## Phase 1 Complete: Scaffold & Guardrails

Created new directory structure (`tv_scrapper`, `new_vercel`, `new_test`) with __init__.py stubs and scaffold import smoke tests. Legacy import paths verified stable.

**Files created/changed:**
- src/tv_scrapper/__init__.py
- src/tv_scrapper/core/__init__.py
- src/tv_scrapper/transforms/__init__.py
- src/tv_scrapper/services/__init__.py
- src/tv_scrapper/adapters/__init__.py
- src/tv_scrapper/mcp/__init__.py
- src/tv_scrapper/mcp/tools/__init__.py
- new_vercel/__init__.py
- new_vercel/routers/__init__.py
- new_vercel/services/__init__.py
- new_test/__init__.py
- new_test/conftest.py
- new_test/http/__init__.py
- new_test/stdio/__init__.py

**Functions created/changed:**
- None (init stubs only)

**Tests created/changed:**
- new_test/stdio/test_scaffold_imports.py (7 tests)
- new_test/http/test_scaffold_imports.py (3 tests)
- new_test/test_legacy_paths_unchanged.py (8 tests)

**Review Status:** APPROVED

**Git Commit Message:**
feat: scaffold tv_scrapper, new_vercel, new_test directories
