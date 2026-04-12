# Facebook Ads Reports - Roadmap & TODO

This document outlines planned improvements for the `facebook-ads-reports` package.

## Current Status

**Version**: 2.1.0  
**Status**: Production-ready and published  
**Core Features**: Complete and maintained

- Modular architecture (`client`, `models`, `utils`, `exceptions`)
- Retry-aware API client and custom exception hierarchy
- Multiple pre-configured report models
- Dynamic report extraction via `get_report()` model configuration
- Native Python outputs (`list[dict[str, Any]]`) with no pandas dependency
- CSV and JSON export utilities
- Type hints and mypy support

---

## Near-term Goals (v2.2.x)

### API Reliability

- [ ] Improve rate limit handling with adaptive backoff by error category
- [ ] Add richer API error context (request id, endpoint, report name)
- [ ] Add optional retry hooks/callbacks for observability

### Report Model Ergonomics

- [ ] Add report-model validation helper for required keys and field types
- [ ] Add typed model protocol/TypedDict definitions for stronger editor support
- [ ] Add alias deprecation guidance for long-term naming consistency

### Export and Data Handling

- [ ] Add optional JSON lines export helper
- [ ] Add optional duplicate-row guard helper by primary key set
- [ ] Add lightweight schema/profile summary utility for extracted datasets

---

## Mid-term Goals (v2.3.x - v2.4.x)

### Testing and QA

- [ ] Expand unit tests for each built-in report model
- [ ] Add pagination regression tests for multi-page API responses
- [ ] Add integration tests for happy-path extraction with mocked API payloads
- [ ] Add CI matrix for Python 3.11-3.14

### Documentation

- [ ] Add cookbook-style examples for common extraction workflows
- [ ] Add troubleshooting section for token, permissions, and rate-limit issues
- [ ] Add migration notes for legacy method names and aliases

---

## Technical Debt and Maintenance

### Code Quality

- [ ] Strengthen internal type annotations in response flattening helpers
- [ ] Review private helper behavior for edge-case nested payloads
- [ ] Improve logging consistency between INFO and DEBUG levels

### Release Management

- [ ] Document a single release checklist (`uv sync`, tests, mypy, build, publish)
- [ ] Add automated changelog validation in CI
- [ ] Add signed tag/release notes workflow for published versions

---

## Contributing

Contributions are welcome. Open an issue to discuss a roadmap item before implementation.

---

**Last Updated**: April 2026  
**Next Review**: July 2026

Feedback is welcome in the issue tracker: https://github.com/machado000/facebook-ads-reports/issues
