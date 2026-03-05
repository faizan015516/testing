import logging
from azure.storage.blob import BlobServiceClient, ContentSettings
from config import Config

logger = logging.getLogger(__name__)


def get_blob_service_client():
    """
    Returns a BlobServiceClient.
    Uses connection string now; swap for DefaultAzureCredential for Managed Identity:

        from azure.identity import DefaultAzureCredential
        account_url = f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
        return BlobServiceClient(account_url=account_url, credential=DefaultAzureCredential())
    """
    return BlobServiceClient.from_connection_string(Config.AZURE_STORAGE_CONNECTION_STRING)


def ensure_container_exists():
    """Create the blob container if it doesn't exist."""
    client = get_blob_service_client()
    container_client = client.get_container_client(Config.AZURE_STORAGE_CONTAINER_NAME)
    try:
        container_client.create_container()
        logger.info(f"Created container: {Config.AZURE_STORAGE_CONTAINER_NAME}")
    except Exception as e:
        if "ContainerAlreadyExists" in str(e):
            logger.info(f"Container already exists: {Config.AZURE_STORAGE_CONTAINER_NAME}")
        else:
            raise


def upload_file_to_blob(file_stream, filename: str, content_type: str) -> str:
    """
    Upload a file stream to Azure Blob Storage.
    Returns the blob URL.
    """
    client = get_blob_service_client()
    blob_client = client.get_blob_client(
        container=Config.AZURE_STORAGE_CONTAINER_NAME,
        blob=filename
    )

    blob_client.upload_blob(
        file_stream,
        overwrite=True,
        content_settings=ContentSettings(content_type=content_type)
    )

    blob_url = blob_client.url
    logger.info(f"Uploaded blob: {filename} -> {blob_url}")
    return blob_url


def delete_blob(filename: str):
    """Delete a blob by filename."""
    client = get_blob_service_client()
    blob_client = client.get_blob_client(
        container=Config.AZURE_STORAGE_CONTAINER_NAME,
        blob=filename
    )
    blob_client.delete_blob()
    logger.info(f"Deleted blob: {filename}")


def list_blobs() -> list:
    """List all blobs in the container."""
    client = get_blob_service_client()
    container_client = client.get_container_client(Config.AZURE_STORAGE_CONTAINER_NAME)
    return [blob.name for blob in container_client.list_blobs()]
