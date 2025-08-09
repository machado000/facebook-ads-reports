"""
Custom exceptions for the Facebook Ads driver module.
"""


class MetaAdsReportError(Exception):
    """Base exception for all Facebook Marketing API errors."""

    def __init__(self, message: str, original_error=None, **context):
        self.message = message
        self.original_error = original_error
        self.context = context

        if original_error:
            super().__init__(f"{message} (caused by: {str(original_error)})")
        else:
            super().__init__(message)


class AuthenticationError(MetaAdsReportError):
    """Raised when authentication with Facebook Marketing API fails."""
    pass


class ValidationError(MetaAdsReportError):
    """Raised when input validation fails."""
    pass


class APIError(MetaAdsReportError):
    """Raised when Facebook Marketing API returns an error."""
    pass


class DataProcessingError(MetaAdsReportError):
    """Raised when data processing/transformation fails."""
    pass


class ConfigurationError(MetaAdsReportError):
    """Raised when configuration is invalid."""
    pass
