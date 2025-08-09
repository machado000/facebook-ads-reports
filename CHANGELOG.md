# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2025-07-22

### Added
- Configurable column naming conventions: snake_case (default) or camelCase
- New `column_naming` parameter in `get_gads_report()` method
- `_transform_column_names()` private method for flexible column transformation
- Input validation for column naming parameter
- Enhanced documentation with column naming examples

### Enhanced
- Updated method docstrings with new parameter descriptions
- Added column naming examples to README.md
- Improved class documentation to reflect new capabilities

### Technical
- Added comprehensive error handling for invalid column naming options
- Maintains backward compatibility (snake_case remains default)
- Graceful fallback to snake_case for invalid naming conventions

## [1.1.0] - 2025-07-21

### Added
- Database optimization features for DataFrames
- Smart data type detection and conversion for metrics columns
- Configurable missing value handling by column type (numeric, datetime, object)
- Character encoding cleanup for database compatibility
- Robust zero impression filtering with multiple format support
- Enhanced type hints with Optional support
- Comprehensive docstring updates with detailed parameter descriptions

### Enhanced
- Zero impression filtering now handles: 0, "0", 0.0, "0.0", None, NaN
- Dynamic metrics conversion from object to appropriate numeric types
- Database-compatible column naming (snake_case, no dots)
- Preserved NaN/NaT values for proper database NULL mapping
- Text columns automatically sanitized (ASCII-safe, length-limited)
- Updated README.md with new features and database optimization examples

### Technical
- Added Optional type hints for better type checking
- Improved method signatures and parameter documentation
- Enhanced class docstring with comprehensive method overview
- Fixed trailing whitespace and lint issues
- Updated dependencies and version information

### Backward Compatibility
- All existing method signatures preserved
- No breaking changes to public API
- Maintains compatibility with existing integrations

## [1.0.0] - Previous Release
- Initial release with Google Ads API v20 support
- Basic data extraction and DataFrame conversion
- Pre-configured report models
- Custom report creation capabilities
- Comprehensive error handling and retry logic
