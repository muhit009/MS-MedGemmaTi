"""
Supabase client service.
Provides a configured Supabase client instance.
"""

from functools import lru_cache
from supabase import create_client, Client

from app.core.config import settings


@lru_cache()
def get_supabase_client() -> Client:
    """
    Get a cached Supabase client instance.
    
    Returns:
        Configured Supabase client.
    
    Raises:
        ValueError: If Supabase credentials are not configured.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        raise ValueError(
            "Supabase credentials not configured. "
            "Please set SUPABASE_URL and SUPABASE_KEY in your .env file."
        )
    
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return client


def get_storage_client():
    """
    Get the Supabase storage client.
    
    Returns:
        Supabase storage client for file operations.
    """
    client = get_supabase_client()
    return client.storage


def create_signed_url(bucket: str, path: str, expires_in: int = 3600) -> str:
    """
    Create a signed URL for accessing a file in Supabase storage.
    
    Args:
        bucket: Storage bucket name.
        path: File path within the bucket.
        expires_in: URL expiration time in seconds (default: 1 hour).
    
    Returns:
        Signed URL string.
    """
    storage = get_storage_client()
    
    try:
        response = storage.from_(bucket).create_signed_url(path, expires_in)
        return response.get("signedURL", "")
    except Exception as e:
        print(f"Error creating signed URL: {e}")
        return ""


def upload_file(bucket: str, path: str, file_data: bytes, content_type: str = None) -> dict:
    """
    Upload a file to Supabase storage.
    
    Args:
        bucket: Storage bucket name.
        path: Destination path within the bucket.
        file_data: File content as bytes.
        content_type: MIME type of the file.
    
    Returns:
        Upload response dictionary.
    """
    storage = get_storage_client()
    
    options = {}
    if content_type:
        options["content-type"] = content_type
    
    try:
        response = storage.from_(bucket).upload(path, file_data, options)
        return {"success": True, "path": path, "response": response}
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_file(bucket: str, paths: list) -> dict:
    """
    Delete files from Supabase storage.
    
    Args:
        bucket: Storage bucket name.
        paths: List of file paths to delete.
    
    Returns:
        Deletion response dictionary.
    """
    storage = get_storage_client()
    
    try:
        response = storage.from_(bucket).remove(paths)
        return {"success": True, "response": response}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_files(bucket: str, path: str = "", limit: int = 100, offset: int = 0) -> list:
    """
    List files in a Supabase storage bucket.
    
    Args:
        bucket: Storage bucket name.
        path: Directory path within the bucket.
        limit: Maximum number of files to return.
        offset: Number of files to skip.
    
    Returns:
        List of file objects.
    """
    storage = get_storage_client()
    
    try:
        response = storage.from_(bucket).list(path, {"limit": limit, "offset": offset})
        return response
    except Exception as e:
        print(f"Error listing files: {e}")
        return []


class SupabaseService:
    """
    High-level Supabase service class.
    Provides convenient methods for common database operations.
    """
    
    def __init__(self):
        self.client = get_supabase_client()
    
    # =========================================================================
    # Generic CRUD Operations
    # =========================================================================
    
    def select(self, table: str, columns: str = "*", filters: dict = None, 
               order_by: str = None, desc: bool = False, limit: int = None) -> list:
        """
        Select records from a table.
        
        Args:
            table: Table name.
            columns: Columns to select (default: all).
            filters: Dictionary of column-value filters.
            order_by: Column to order by.
            desc: Order descending if True.
            limit: Maximum records to return.
        
        Returns:
            List of records.
        """
        query = self.client.table(table).select(columns)
        
        if filters:
            for column, value in filters.items():
                query = query.eq(column, value)
        
        if order_by:
            query = query.order(order_by, desc=desc)
        
        if limit:
            query = query.limit(limit)
        
        response = query.execute()
        return response.data
    
    def insert(self, table: str, data: dict) -> dict:
        """
        Insert a record into a table.
        
        Args:
            table: Table name.
            data: Record data.
        
        Returns:
            Inserted record.
        """
        response = self.client.table(table).insert(data).execute()
        return response.data[0] if response.data else None
    
    def update(self, table: str, data: dict, filters: dict) -> dict:
        """
        Update records in a table.
        
        Args:
            table: Table name.
            data: Updated data.
            filters: Dictionary of column-value filters.
        
        Returns:
            Updated record.
        """
        query = self.client.table(table).update(data)
        
        for column, value in filters.items():
            query = query.eq(column, value)
        
        response = query.execute()
        return response.data[0] if response.data else None
    
    def delete(self, table: str, filters: dict) -> bool:
        """
        Delete records from a table.
        
        Args:
            table: Table name.
            filters: Dictionary of column-value filters.
        
        Returns:
            True if successful.
        """
        query = self.client.table(table).delete()
        
        for column, value in filters.items():
            query = query.eq(column, value)
        
        query.execute()
        return True
    
    def upsert(self, table: str, data: dict) -> dict:
        """
        Insert or update a record.
        
        Args:
            table: Table name.
            data: Record data (must include primary key for update).
        
        Returns:
            Upserted record.
        """
        response = self.client.table(table).upsert(data).execute()
        return response.data[0] if response.data else None
    
    # =========================================================================
    # Search Operations
    # =========================================================================
    
    def search_ilike(self, table: str, column: str, pattern: str, 
                     select_columns: str = "*", limit: int = 20) -> list:
        """
        Search records using case-insensitive pattern matching.
        
        Args:
            table: Table name.
            column: Column to search.
            pattern: Search pattern (use % for wildcards).
            select_columns: Columns to return.
            limit: Maximum records to return.
        
        Returns:
            List of matching records.
        """
        response = self.client.table(table).select(select_columns).ilike(
            column, pattern
        ).limit(limit).execute()
        
        return response.data
    
    def search_full_text(self, table: str, column: str, query: str,
                         select_columns: str = "*", limit: int = 20) -> list:
        """
        Full-text search on a column.
        
        Args:
            table: Table name.
            column: Column to search.
            query: Search query.
            select_columns: Columns to return.
            limit: Maximum records to return.
        
        Returns:
            List of matching records.
        """
        response = self.client.table(table).select(select_columns).text_search(
            column, query
        ).limit(limit).execute()
        
        return response.data
    
    # =========================================================================
    # Pagination
    # =========================================================================
    
    def paginate(self, table: str, page: int = 1, per_page: int = 20,
                 columns: str = "*", filters: dict = None,
                 order_by: str = None, desc: bool = False) -> dict:
        """
        Get paginated records from a table.
        
        Args:
            table: Table name.
            page: Page number (1-indexed).
            per_page: Records per page.
            columns: Columns to select.
            filters: Dictionary of column-value filters.
            order_by: Column to order by.
            desc: Order descending if True.
        
        Returns:
            Dictionary with records and pagination info.
        """
        offset = (page - 1) * per_page
        
        query = self.client.table(table).select(columns, count="exact")
        
        if filters:
            for column, value in filters.items():
                query = query.eq(column, value)
        
        if order_by:
            query = query.order(order_by, desc=desc)
        
        response = query.range(offset, offset + per_page - 1).execute()
        
        total = response.count or 0
        total_pages = (total + per_page - 1) // per_page
        
        return {
            "data": response.data,
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }


# Singleton instance
_supabase_service = None


def get_supabase_service() -> SupabaseService:
    """
    Get the singleton SupabaseService instance.
    
    Returns:
        SupabaseService instance.
    """
    global _supabase_service
    if _supabase_service is None:
        _supabase_service = SupabaseService()
    return _supabase_service