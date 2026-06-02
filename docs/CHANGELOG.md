# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New utility function `get_week_date_pairs()` to break date ranges into weekly periods (Sunday-Saturday)
- Enhanced README features list to highlight date range utility functions

## [2.3.1] - 2026-06-02

### Fixed
- Included remaining v2.3.0 release updates for `client.py`, `models.py`, and `uv.lock`


## [2.3.0] - 2026-06-02

### Added
- Updated Facebook Marketing API support to v25 across the codebase
- Standardized `date_preset` to `last_3d` in all built-in report models


## [2.2.1] - 2026-04-12

### Fixed
- Bumped version to 2.2.1 after PyPI rejected re-upload of deleted 2.2.0 filenames

## [2.2.0] - 2026-04-12

### Added
- GitHub Actions CI workflow running `uv sync --all-groups`, `uv run pytest`, and `uv run mypy facebook_ads_reports` on push/PR to `main`
- GitHub Actions release workflow triggered by published GitHub Releases to automate version/changelog updates, package build, and PyPI publish

### Changed
- Bumped package version to 2.2.0 to include CI/CD release automation and docs pipeline migration under `docs/`
- Updated release documentation to use `docs/RELEASE_PIPELINE_SKILL.md` and `docs/CHANGELOG.md` as the canonical release docs

## [2.1.2] - 2026-04-10

### Added
- Exported `convert_keys_case` in package-level public API (`facebook_ads_reports.__init__`)

### Changed
- Renamed internal variable `response_data_cased` to `response_data_snake_case` in `MetaAdsReport.get_report()` for clearer intent
- Added reusable release/publish checklist skill document at project root

## [2.1.1] - 2026-04-10

### Changed
- Improved `MetaAdsReport._clean_text_encoding()` to preserve Unicode characters (including accents) while normalizing strings to NFC

### Fixed
- Replaced ASCII-stripping behavior in text cleanup that could remove valid non-ASCII characters from API responses
- Sanitized nested string values recursively while removing null bytes and unsafe control characters

## [2.1.0] - 2026-04-08

### Added
- Backward-compatible report model alias `MetaAdsReportModel.ad_performance_report` pointing to `ad_insights_report`
- Expanded report model registry so all pre-configured models are discoverable via `get_all_reports()` and `list_available_reports()`

### Changed
- Bumped package version to 2.1.0 for model and API compatibility improvements
- Updated README examples to use `get_report()` and current model set
- Fully refreshed project roadmap for Facebook Ads scope and current milestones
- Improved package and client docstrings for the current native Python (no pandas) architecture
- Added explanatory comments to `examples/basic_usage.py` around credentials and report/date behavior

### Fixed
- Fixed model definition syntax issues in `campaigns_report` and `adsets_report`
- Corrected pagination flow in `MetaAdsReport.get_report()` so next page URLs are followed consistently
- Prevented report model params from being mutated across repeated `get_report()` calls

### Technical
- Confirmed dependency declarations remain up-to-date for runtime and development workflows

## [2.0.1] - 2025-10-08

### Changed
- Updated Python version requirements to support Python 3.11-3.14

## [2.0.0] - 2025-08-29

### Added
- New utility functions `save_report_to_csv()` and `save_report_to_json()` for flexible data export
- Comprehensive type hints throughout the codebase with strict mypy compliance
- Enhanced error handling with properly typed exceptions

### Changed
- **BREAKING**: Removed pandas dependency for lighter, more flexible data handling
- **BREAKING**: `get_insights_report()` now returns `list[dict[str, Any]]` instead of pandas DataFrame
- **BREAKING**: Updated function signatures with complete type annotations
- Improved docstring consistency and parameter documentation
- Enhanced mypy strict mode compliance with proper type checking

### Removed
- **BREAKING**: Pandas dependency and all DataFrame-related functionality
- **BREAKING**: Database optimization features specific to pandas DataFrames

### Fixed
- All mypy type checking errors resolved
- Consistent parameter documentation in docstrings
- Proper type annotations for all function parameters and return values

### Technical
- Added `types-requests` development dependency for proper type checking
- Updated VS Code tasks configuration for correct mypy execution
- Improved code maintainability with strict typing

## [1.0.0] - 2025-08-28

### Added
- Environment variable support for credentials via `FACEBOOK_ADS_CONFIG_JSON`
- Comprehensive documentation for both file-based and environment variable credential setup
- Type annotations for better IDE support and static analysis

### Changed
- **BREAKING**: Updated Facebook Marketing API support from v22 to v23
- **BREAKING**: Constructor parameter changed from `credentials_json` to `credentials_dict`
- Updated development status from Beta to Production/Stable
- Improved error handling and credential loading logic
- Enhanced README with dual credential setup options
- Python support updated to 3.10-3.12 (removed 3.9 support)

### Fixed
- Fixed JSON structure in documentation (added missing `app_secret` field)
- Fixed mypy type checking errors in example code
- Updated dependencies format for proper parsing

### Documentation
- Added environment variable configuration examples
- Improved credential setup documentation with multiple options
- Updated API version references throughout documentation
- Fixed constructor usage examples in README

## [0.9.0] - 2025-08-09

### Added
- Initial release of Facebook Ads Reports ETL driver
- Facebook Marketing API v22 support
- Pre-configured report models: `ad_dimensions_report`, `ad_performance_report`
- Database-optimized DataFrame output
- Smart data type detection and conversion for metrics columns
- Configurable missing value handling by column type (numeric, datetime, object)
- Character encoding cleanup for database compatibility
- Robust zero impression filtering with multiple format support
- Custom report model creation
- Comprehensive error handling and retry logic
- Logging and configuration utilities
- Example usage in `examples/basic_usage.py`

### Technical
- Full type hint support
- Modular code structure for easy extension
- GPL License
