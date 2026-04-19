"""
Firestore Client for Zenith AI
Provides async-compatible Firestore operations
"""
from datetime import datetime
from typing import Optional, Any, Callable, TypeVar, Awaitable
from functools import lru_cache

from google.cloud import firestore
from google.cloud.firestore_v1 import AsyncClient
import structlog
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from config import settings

logger = structlog.get_logger()

T = TypeVar("T")


def _is_transient_firestore_error(exc: BaseException) -> bool:
    try:
        from google.api_core import exceptions as gexc
    except ImportError:
        return False
    return isinstance(
        exc,
        (
            gexc.DeadlineExceeded,
            gexc.ServiceUnavailable,
            gexc.Aborted,
            gexc.InternalServerError,
            gexc.ResourceExhausted,
        ),
    )


async def _with_transient_retry(coro_factory: Callable[[], Awaitable[T]]) -> T:
    """Retry transient Firestore / gRPC failures with bounded backoff."""
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(4),
        wait=wait_exponential_jitter(initial=0.2, max=3.0),
        retry=retry_if_exception(_is_transient_firestore_error),
        reraise=True,
    ):
        with attempt:
            return await coro_factory()


class FirestoreClient:
    """
    Async-compatible Firestore client wrapper.
    Handles all database operations for Zenith AI.
    """
    
    def __init__(self):
        self._sync_client = firestore.Client(project=settings.gcp_project_id)
        self._async_client = AsyncClient(project=settings.gcp_project_id)
    
    @property
    def db(self) -> firestore.Client:
        """Get synchronous Firestore client."""
        return self._sync_client
    
    @property
    def async_db(self) -> AsyncClient:
        """Get async Firestore client."""
        return self._async_client
    
    # ==================== Generic Operations ====================
    
    async def get_document(
        self, 
        collection: str, 
        document_id: str
    ) -> Optional[dict]:
        """Get a single document by ID."""
        doc_ref = self._async_client.collection(collection).document(document_id)

        async def _read():
            return await doc_ref.get()

        doc = await _with_transient_retry(_read)

        if doc.exists:
            return {"id": doc.id, **doc.to_dict()}
        return None
    
    async def set_document(
        self,
        collection: str,
        document_id: str,
        data: dict,
        merge: bool = True
    ) -> None:
        """Set/update a document."""
        doc_ref = self._async_client.collection(collection).document(document_id)
        data["updated_at"] = datetime.utcnow().isoformat()

        async def _write():
            await doc_ref.set(data, merge=merge)

        await _with_transient_retry(_write)
        logger.debug("Document set", collection=collection, document_id=document_id)
    
    async def create_document(
        self,
        collection: str,
        data: dict,
        document_id: Optional[str] = None
    ) -> str:
        """Create a new document, optionally with specific ID."""
        data["created_at"] = datetime.utcnow().isoformat()
        data["updated_at"] = data["created_at"]
        
        if document_id:
            doc_ref = self._async_client.collection(collection).document(document_id)

            async def _write():
                await doc_ref.set(data)

            await _with_transient_retry(_write)
            return document_id
        else:

            async def _add():
                return await self._async_client.collection(collection).add(data)

            doc_ref = await _with_transient_retry(_add)
            return doc_ref[1].id
    
    async def delete_document(
        self,
        collection: str,
        document_id: str
    ) -> bool:
        """Delete a document."""
        try:
            doc_ref = self._async_client.collection(collection).document(document_id)

            async def _del():
                await doc_ref.delete()

            await _with_transient_retry(_del)
            logger.debug("Document deleted", collection=collection, document_id=document_id)
            return True
        except Exception as e:
            logger.error("Failed to delete document", collection=collection, document_id=document_id, error=str(e))
            return False
    
    async def query_documents(
        self,
        collection: str,
        filters: Optional[list[tuple]] = None,
        order_by: Optional[str] = None,
        order_direction: str = "ASCENDING",
        limit: Optional[int] = None
    ) -> list[dict]:
        """
        Query documents with filters.
        
        Args:
            collection: Collection name
            filters: List of (field, operator, value) tuples
            order_by: Field to order by
            order_direction: "ASCENDING" or "DESCENDING"
            limit: Maximum number of results
            
        Returns:
            List of documents
        """
        query = self._async_client.collection(collection)
        
        if filters:
            for field, operator, value in filters:
                query = query.where(field, operator, value)
        
        if order_by:
            direction = (
                firestore.Query.DESCENDING 
                if order_direction == "DESCENDING" 
                else firestore.Query.ASCENDING
            )
            query = query.order_by(order_by, direction=direction)
        
        if limit:
            query = query.limit(limit)

        async def _run_query():
            return await query.get()

        docs = await _with_transient_retry(_run_query)
        return [{"id": doc.id, **doc.to_dict()} for doc in docs]
    
    # ==================== User-Specific Operations ====================
    
    async def get_user_subcollection(
        self,
        user_id: str,
        subcollection: str,
        filters: Optional[list[tuple]] = None,
        limit: Optional[int] = None
    ) -> list[dict]:
        """Get documents from a user's subcollection."""
        query = (
            self._async_client
            .collection(settings.firestore_collection_users)
            .document(user_id)
            .collection(subcollection)
        )
        
        if filters:
            for field, operator, value in filters:
                query = query.where(field, operator, value)
        
        if limit:
            query = query.limit(limit)

        async def _run_sub_query():
            return await query.get()

        docs = await _with_transient_retry(_run_sub_query)
        return [{"id": doc.id, **doc.to_dict()} for doc in docs]
    
    async def add_to_user_subcollection(
        self,
        user_id: str,
        subcollection: str,
        data: dict,
        document_id: Optional[str] = None
    ) -> str:
        """Add a document to a user's subcollection."""
        data["created_at"] = datetime.utcnow().isoformat()
        data["updated_at"] = data["created_at"]
        
        collection_ref = (
            self._async_client
            .collection(settings.firestore_collection_users)
            .document(user_id)
            .collection(subcollection)
        )
        
        if document_id:
            doc_ref = collection_ref.document(document_id)

            async def _write():
                await doc_ref.set(data)

            await _with_transient_retry(_write)
            return document_id
        else:

            async def _add():
                return await collection_ref.add(data)

            doc_ref = await _with_transient_retry(_add)
            return doc_ref[1].id


@lru_cache()
def get_firestore_client() -> FirestoreClient:
    """Get cached Firestore client instance."""
    return FirestoreClient()
