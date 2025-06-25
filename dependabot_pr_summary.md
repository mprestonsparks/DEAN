# Dependabot PR Summary

## Overview
15 Dependabot pull requests pending review as of 2025-06-24.

## PR Breakdown

### GitHub Actions Updates (5 PRs)
- PR #1: actions/upload-artifact from 3 to 4
- PR #2: azure/setup-helm from 3 to 4
- PR #3: actions/download-artifact from 3 to 4
- PR #12: github/codeql-action from 2 to 3
- PR #13: softprops/action-gh-release from 1 to 2

### Python Dependencies (10 PRs)
- PR #4: rich from 13.7.0 to 14.0.0
- PR #5: pre-commit from 3.5.0 to 4.2.0
- PR #6: scipy from 1.11.4 to 1.15.3
- PR #7: development-dependencies group (9 updates)
- PR #8: alembic from 1.13.0 to 1.16.2
- PR #9: tenacity from 8.2.3 to 9.1.2
- PR #10: apache-airflow-client from 2.7.0 to 3.0.2
- PR #11: pydantic from 2.5.0 to 2.11.7
- PR #14: asyncpg from 0.29.0 to 0.30.0
- PR #15: redis from 5.0.1 to 6.2.0

## Recommendations
1. **Priority 1**: Security-related updates (check release notes)
2. **Priority 2**: GitHub Actions updates (generally safe)
3. **Priority 3**: Core dependencies (pydantic, redis, asyncpg)
4. **Priority 4**: Development dependencies

## Review Strategy
Use `./review_dependabot_prs.sh` to interactively review and merge PRs.