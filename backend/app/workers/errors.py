class NonRetryableWorkloadError(ValueError):
    """Safe validation failure that must not be retried by a worker."""
