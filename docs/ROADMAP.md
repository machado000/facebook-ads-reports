# Facebook Ads Reports - Roadmap & TODO

This document outlines planned improvements for the `facebook-ads-reports` package.

## Current Status

**Version**: 2.4.0  
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

## Near-term Goals (v2.4.x)

### API Reliability

- [x] **Make `@retry_on_api_error` actually cover API errors.** Done: non-200 responses
      now raise typed `APIError` / `AuthenticationError` with structured context, and the
      decorator retries throttling, transient, and 5xx failures. Previously only
      connection-level `RequestException` was retried, so a transient `code: 4` killed an
      extraction on the first attempt.
- [x] Honor `Retry-After`, and apply a 60s delay floor for rate-limit errors
- [ ] Read `x-fb-ads-insights-throttle` / `x-ad-account-usage` proactively to slow down
      *before* hitting the app-level limit, rather than reacting after
- [ ] Improve rate limit handling with adaptive backoff by error category
- [ ] Add richer API error context (request id, endpoint, report name)
- [ ] Add optional retry hooks/callbacks for observability

### Report Model Ergonomics

- [ ] Add report-model validation helper for required keys and field types
- [ ] Add typed model protocol/TypedDict definitions for stronger editor support
- [ ] Add alias deprecation guidance for long-term naming consistency

### Flattening Consistency

- [ ] **Normalize `targeting` field prefixes.** `_flatten_facebook_ads_response()` hoists
      the 26 `targeting` nested fields to top level *without* a prefix (`genders`,
      `age_min`, `countries`, `interests`, `cities`, ...), while `learning_stage_info`
      fields are correctly prefixed (`learning_stage_info_status`). The inconsistency
      makes ad set / ad output columns ambiguous about their origin, and any future
      top-level API field sharing one of those names would silently collide.
      Affects `adsets_report` and `ad_summary_report`. Fix is a `targeting_` prefix,
      which is a **breaking output change** — pair it with a major/minor bump and
      migration notes.
- [ ] **Preserve `action_video_type` detail.** With
      `action_breakdowns: ["action_type", "action_video_type"]`, the API returns several
      entries sharing one `action_type` but differing by `action_video_type`.
      `_flatten_action_list()` keys only on `action_type`, so all but the last entry are
      silently dropped. Either fold the secondary breakdown into the column name or
      aggregate explicitly.
- [ ] **Apply snake_case in the `flatten=False` path.** `get_report()` returns the
      pre-casing `response_data` when `flatten=False`, so raw-mode output keeps original
      API key casing while flattened output is snake_cased.
- [x] **Sanitize dotted action names into warehouse-safe identifiers.** Done in v2.4.0:
      `sanitize_column_name()` in `utils.py` folds every character outside `[0-9A-Za-z_]`
      to an underscore, so `offsite_conversion.fb_pixel_purchase` lands as
      `offsite_conversion_fb_pixel_purchase`. Exported publicly so loaders can reproduce it.
- [x] **Bound the insights column explosion.** Done in v2.4.0: models may declare an
      `action_types` allow-list, applied to every action-list family on the raw
      `action_type`. `ad_insights_report` ships one keeping the `omni_*` conversion scope,
      taking a live extract from 102 columns to 48.
- [ ] Filter action types server-side via the API `filtering` parameter, so the allow-list
      reduces payload and quota cost rather than only output columns

### Export and Data Handling

- [ ] Add optional JSON lines export helper
- [ ] Add optional duplicate-row guard helper by primary key set
- [ ] Add lightweight schema/profile summary utility for extracted datasets

---

## Mid-term Goals (v2.5.x)

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

**Last Updated**: 10 August 2026  
**Next Review**: September 2026

Feedback is welcome in the issue tracker: https://github.com/machado000/facebook-ads-reports/issues
