def ensure_container_exists(container_name):
    from azure.core.exceptions import ResourceNotFoundError, AzureError
    import logging

    logger = logging.getLogger(__name__)
    try:
        # Your existing code to check if container exists
        pass  # Replace with actual implementation
    except ResourceNotFoundError:
        logger.error(f"Resource not found: {container_name}")
        # Handle specific case for ResourceNotFoundError
    except AzureError as e:
        logger.error(f"Azure storage error occurred: {str(e)}")
        # Handle other Azure specific exceptions
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
