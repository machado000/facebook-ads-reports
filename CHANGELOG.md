# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-08-09

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
