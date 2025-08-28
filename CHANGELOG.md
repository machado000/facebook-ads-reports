# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
