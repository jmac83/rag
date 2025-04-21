import logging
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError

class BlobStorageService:
    def __init__(self, blob_service_client):
        self.blob_service_client = blob_service_client

    def list_blob_names(self, container_name, prefix=None):
        try:
            container_client = self.blob_service_client.get_container_client(container_name)
            blob_name_list = []
            blobs = container_client.list_blobs(name_starts_with=prefix)
            for blob in blobs:
                full_path = f"{container_name}/{blob.name}"
                blob_name_list.append({"name": full_path})
            return {"blobs": blob_name_list}
        except ResourceNotFoundError:
            logging.warning(f"Container not found: {container_name}")
            return {"blobs": []}
        except Exception as e:
            logging.error(f"Error listing blob names in {container_name}: {e}")
            raise

    def upload_blob(self, container_name, blob_name, file_content, overwrite=True):
        full_path = f"{container_name}/{blob_name}"
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name, blob=blob_name
            )
            blob_client.upload_blob(file_content, overwrite=overwrite)
            logging.info(f"Uploaded blob: {full_path}")
            return {"success": True, "path": full_path, "url": blob_client.url}
        except ResourceExistsError:
             logging.warning(f"Blob exists, overwrite=False: {full_path}")
             return {"success": False, "error": "Blob already exists", "path": full_path}
        except Exception as e:
            logging.error(f"Failed to upload blob {full_path}: {e}")
            return {"success": False, "error": str(e), "path": full_path}