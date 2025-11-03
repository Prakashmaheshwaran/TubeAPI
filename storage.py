import os
import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

# Configure logging (only if not already configured)
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
logger = logging.getLogger(__name__)


class StorageUploader(ABC):
    """Base class for storage uploaders."""
    
    @abstractmethod
    def upload_file(self, filepath: str, filename: str) -> str:
        """
        Upload a file to cloud storage.
        
        Args:
            filepath: Local path to the file
            filename: Name of the file
            
        Returns:
            Public URL of the uploaded file
            
        Raises:
            Exception: If upload fails
        """
        pass
    
    @abstractmethod
    def delete_file(self, storage_path: str) -> bool:
        """
        Delete a file from cloud storage.
        
        Args:
            storage_path: Path to file in storage (not full URL)
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def list_files(self) -> List[Dict[str, Any]]:
        """
        List all files in storage with metadata.
        
        Returns:
            List of dicts with keys: path, size, created_at (timestamp)
        """
        pass
    
    @staticmethod
    def get_date_path(filename: str) -> str:
        """
        Generate date-based storage path.
        
        Args:
            filename: Name of the file
            
        Returns:
            Storage path in format YYYY-MM-DD/filename
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        return f"{date_str}/{filename}"


class SupabaseUploader(StorageUploader):
    """Supabase storage uploader."""
    
    def __init__(self):
        """Initialize Supabase uploader with credentials from environment."""
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        self.bucket = os.getenv("SUPABASE_BUCKET")
        
        if not all([self.url, self.key, self.bucket]):
            logger.warning("Supabase credentials not fully configured. Some features may not work.")
            self.enabled = False
        else:
            self.enabled = True
            try:
                from supabase import create_client
                self.client = create_client(self.url, self.key)
                logger.info(f"Supabase uploader initialized with bucket: {self.bucket}")
            except ImportError:
                logger.error("supabase package not installed. Install with: pip install supabase")
                self.enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {str(e)}")
                self.enabled = False
    
    def upload_file(self, filepath: str, filename: str) -> str:
        """
        Upload a file to Supabase storage.
        
        Args:
            filepath: Local path to the file
            filename: Name of the file
            
        Returns:
            Public URL of the uploaded file
            
        Raises:
            Exception: If upload fails
        """
        if not self.enabled:
            raise Exception("Supabase uploader not properly configured. Check environment variables.")
        
        try:
            # Generate storage path with date structure
            storage_path = self.get_date_path(filename)
            
            # Read file content
            with open(filepath, 'rb') as f:
                file_data = f.read()
            
            # Try to upload to Supabase
            # If file exists, delete it first then upload (for overwrite behavior)
            try:
                # First, try to delete existing file if it exists (silent fail if not exists)
                try:
                    self.client.storage.from_(self.bucket).remove([storage_path])
                except:
                    pass  # File doesn't exist, which is fine
                
                # Upload the file
                response = self.client.storage.from_(self.bucket).upload(
                    path=storage_path,
                    file=file_data,
                    file_options={"content-type": self._get_content_type(filename)}
                )
            except Exception as upload_error:
                # If upload fails due to existing file, try to remove and retry
                error_str = str(upload_error).lower()
                if 'already exists' in error_str or 'duplicate' in error_str:
                    logger.info(f"File exists, removing and retrying upload: {storage_path}")
                    self.client.storage.from_(self.bucket).remove([storage_path])
                    response = self.client.storage.from_(self.bucket).upload(
                        path=storage_path,
                        file=file_data,
                        file_options={"content-type": self._get_content_type(filename)}
                    )
                else:
                    raise
            
            # Get public URL
            public_url = self.client.storage.from_(self.bucket).get_public_url(storage_path)
            
            logger.info(f"Successfully uploaded to Supabase: {storage_path} -> {public_url}")
            return public_url
            
        except Exception as e:
            logger.error(f"Failed to upload file to Supabase: {str(e)}")
            raise Exception(f"Supabase upload failed: {str(e)}")
    
    def delete_file(self, storage_path: str) -> bool:
        """
        Delete a file from Supabase storage.
        
        Args:
            storage_path: Path to file in storage (not full URL)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.warning("Supabase uploader not enabled, cannot delete file")
            return False
        
        try:
            # Remove leading slash if present
            storage_path = storage_path.lstrip('/')
            
            # Delete from Supabase
            self.client.storage.from_(self.bucket).remove([storage_path])
            
            logger.info(f"Successfully deleted from Supabase: {storage_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file from Supabase: {str(e)}")
            return False
    
    def list_files(self) -> List[Dict[str, Any]]:
        """
        List all files in Supabase storage with metadata.
        
        Returns:
            List of dicts with keys: path, size, created_at (timestamp)
        """
        if not self.enabled:
            logger.warning("Supabase uploader not enabled, cannot list files")
            return []
        
        try:
            files = []
            
            def _list_recursive(path: str = ""):
                """Recursively list files in subdirectories."""
                try:
                    items = self.client.storage.from_(self.bucket).list(path)
                    for item in items:
                        # Check if it's a file (has 'id' property) or folder
                        if item.get('id'):  # It's a file
                            # Try to get metadata if available
                            file_size = item.get('metadata', {}).get('size', 0) if isinstance(item.get('metadata'), dict) else 0
                            created_at = item.get('created_at') or item.get('updated_at') or ''
                            
                            file_path = f"{path}/{item['name']}" if path else item['name']
                            files.append({
                                'path': file_path.lstrip('/'),
                                'size': file_size or item.get('size', 0),
                                'created_at': created_at
                            })
                        elif item.get('name') and not item.get('id'):  # It's a folder, recurse
                            folder_path = f"{path}/{item['name']}" if path else item['name']
                            _list_recursive(folder_path)
                except Exception as e:
                    logger.warning(f"Error listing path {path}: {str(e)}")
            
            _list_recursive()
            
            logger.info(f"Listed {len(files)} files from Supabase")
            return files
            
        except Exception as e:
            logger.error(f"Failed to list files from Supabase: {str(e)}")
            return []
    
    @staticmethod
    def _get_content_type(filename: str) -> str:
        """Get content type based on file extension."""
        extension = Path(filename).suffix.lower()
        content_types = {
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
            '.mkv': 'video/x-matroska',
            '.flv': 'video/x-flv',
            '.avi': 'video/x-msvideo',
            '.mp3': 'audio/mpeg',
            '.m4a': 'audio/mp4',
            '.opus': 'audio/opus',
            '.ogg': 'audio/ogg',
            '.flac': 'audio/flac',
            '.wav': 'audio/wav',
        }
        return content_types.get(extension, 'application/octet-stream')


class S3Uploader(StorageUploader):
    """AWS S3 storage uploader."""
    
    def __init__(self):
        """Initialize S3 uploader with credentials from environment."""
        self.access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.bucket = os.getenv("AWS_S3_BUCKET")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        
        if not all([self.access_key, self.secret_key, self.bucket]):
            logger.warning("AWS S3 credentials not fully configured. Some features may not work.")
            self.enabled = False
        else:
            self.enabled = True
            try:
                import boto3
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    region_name=self.region
                )
                logger.info(f"S3 uploader initialized with bucket: {self.bucket} (region: {self.region})")
            except ImportError:
                logger.error("boto3 package not installed. Install with: pip install boto3")
                self.enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {str(e)}")
                self.enabled = False
    
    def upload_file(self, filepath: str, filename: str) -> str:
        """
        Upload a file to S3 storage.
        
        Args:
            filepath: Local path to the file
            filename: Name of the file
            
        Returns:
            Public URL of the uploaded file
            
        Raises:
            Exception: If upload fails
        """
        if not self.enabled:
            raise Exception("S3 uploader not properly configured. Check environment variables.")
        
        try:
            # Generate storage path with date structure
            storage_path = self.get_date_path(filename)
            
            # Upload to S3
            self.s3_client.upload_file(
                filepath,
                self.bucket,
                storage_path,
                ExtraArgs={'ContentType': self._get_content_type(filename)}
            )
            
            # Generate public URL
            # For public buckets, use standard URL format
            # For private buckets, users should configure bucket policy or use presigned URLs
            from urllib.parse import quote
            encoded_path = quote(storage_path, safe='/')
            # Standard S3 URL format: https://bucket-name.s3.region.amazonaws.com/key
            # Handle bucket names with dots (use s3-website format if needed)
            if '.' in self.bucket:
                # Buckets with dots must use path-style or virtual-hosted-style
                public_url = f"https://s3.{self.region}.amazonaws.com/{self.bucket}/{encoded_path}"
            else:
                public_url = f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{encoded_path}"
            
            logger.info(f"Successfully uploaded to S3: {storage_path} -> {public_url}")
            return public_url
            
        except Exception as e:
            logger.error(f"Failed to upload file to S3: {str(e)}")
            raise Exception(f"S3 upload failed: {str(e)}")
    
    def delete_file(self, storage_path: str) -> bool:
        """
        Delete a file from S3 storage.
        
        Args:
            storage_path: Path to file in storage (not full URL)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.warning("S3 uploader not enabled, cannot delete file")
            return False
        
        try:
            # Remove leading slash if present
            storage_path = storage_path.lstrip('/')
            
            # Delete from S3
            self.s3_client.delete_object(Bucket=self.bucket, Key=storage_path)
            
            logger.info(f"Successfully deleted from S3: {storage_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file from S3: {str(e)}")
            return False
    
    def list_files(self) -> List[Dict[str, Any]]:
        """
        List all files in S3 storage with metadata.
        
        Returns:
            List of dicts with keys: path, size, created_at (timestamp)
        """
        if not self.enabled:
            logger.warning("S3 uploader not enabled, cannot list files")
            return []
        
        try:
            files = []
            paginator = self.s3_client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=self.bucket):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        files.append({
                            'path': obj['Key'],
                            'size': obj['Size'],
                            'created_at': obj['LastModified'].isoformat()
                        })
            
            logger.info(f"Listed {len(files)} files from S3")
            return files
            
        except Exception as e:
            logger.error(f"Failed to list files from S3: {str(e)}")
            return []
    
    @staticmethod
    def _get_content_type(filename: str) -> str:
        """Get content type based on file extension."""
        extension = Path(filename).suffix.lower()
        content_types = {
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
            '.mkv': 'video/x-matroska',
            '.flv': 'video/x-flv',
            '.avi': 'video/x-msvideo',
            '.mp3': 'audio/mpeg',
            '.m4a': 'audio/mp4',
            '.opus': 'audio/opus',
            '.ogg': 'audio/ogg',
            '.flac': 'audio/flac',
            '.wav': 'audio/wav',
        }
        return content_types.get(extension, 'application/octet-stream')

