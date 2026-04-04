"""
Gmail Tools for Zenith AI
Provides email management capabilities: search, read, send, summarize
"""
from datetime import datetime, timedelta
from typing import Optional
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import structlog

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from auth.google_oauth import GoogleOAuthManager, get_oauth_manager

logger = structlog.get_logger()


class GmailTools:
    """
    Gmail API integration.
    Handles all email operations for Zenith AI.
    """
    
    def __init__(self, oauth_manager: Optional[GoogleOAuthManager] = None):
        self.oauth = oauth_manager or get_oauth_manager()
    
    def _get_service(self, credentials_dict: dict):
        """Get Gmail API service."""
        return self.oauth.build_service("gmail", "v1", credentials_dict)
    
    async def search_messages(
        self,
        credentials: dict,
        query: Optional[str] = None,
        max_results: int = 10,
        label_ids: Optional[list[str]] = None,
        include_spam_trash: bool = False
    ) -> list[dict]:
        """
        Search Gmail messages.
        
        Args:
            credentials: User's OAuth credentials
            query: Gmail search query (same syntax as Gmail search)
                   Examples: "from:john@example.com", "subject:meeting", "is:unread"
            max_results: Maximum number of messages to return
            label_ids: Filter by label IDs (e.g., ["INBOX", "UNREAD"])
            include_spam_trash: Include spam and trash in results
            
        Returns:
            List of message summaries
        """
        service = self._get_service(credentials)
        
        try:
            request_params = {
                "userId": "me",
                "maxResults": max_results,
                "includeSpamTrash": include_spam_trash
            }
            
            if query:
                request_params["q"] = query
            
            if label_ids:
                request_params["labelIds"] = label_ids
            
            results = service.users().messages().list(**request_params).execute()
            messages = results.get("messages", [])
            
            # Fetch details for each message
            detailed_messages = []
            for msg in messages:
                message_detail = service.users().messages().get(
                    userId="me",
                    id=msg["id"],
                    format="metadata",
                    metadataHeaders=["From", "To", "Subject", "Date"]
                ).execute()
                detailed_messages.append(self._format_message_summary(message_detail))
            
            logger.info("Searched messages", count=len(detailed_messages), query=query)
            return detailed_messages
            
        except HttpError as e:
            logger.error("Failed to search messages", error=str(e))
            raise
    
    async def get_message(
        self,
        credentials: dict,
        message_id: str,
        format: str = "full"
    ) -> dict:
        """
        Get a specific message by ID.
        
        Args:
            credentials: User's OAuth credentials
            message_id: Message ID
            format: "full", "metadata", "minimal", or "raw"
            
        Returns:
            Full message details including body
        """
        service = self._get_service(credentials)
        
        try:
            message = service.users().messages().get(
                userId="me",
                id=message_id,
                format=format
            ).execute()
            
            return self._format_full_message(message)
            
        except HttpError as e:
            logger.error("Failed to get message", error=str(e), message_id=message_id)
            raise
    
    async def get_thread(
        self,
        credentials: dict,
        thread_id: str,
        format: str = "full"
    ) -> dict:
        """
        Get an email thread (conversation).
        
        Args:
            credentials: User's OAuth credentials
            thread_id: Thread ID
            format: Message format
            
        Returns:
            Thread with all messages
        """
        service = self._get_service(credentials)
        
        try:
            thread = service.users().threads().get(
                userId="me",
                id=thread_id,
                format=format
            ).execute()
            
            messages = [
                self._format_full_message(msg) 
                for msg in thread.get("messages", [])
            ]
            
            return {
                "id": thread.get("id"),
                "snippet": thread.get("snippet"),
                "messages": messages,
                "message_count": len(messages)
            }
            
        except HttpError as e:
            logger.error("Failed to get thread", error=str(e), thread_id=thread_id)
            raise
    
    async def summarize_inbox(
        self,
        credentials: dict,
        hours: int = 24,
        max_messages: int = 20
    ) -> dict:
        """
        Get a summary of recent inbox activity.
        
        Args:
            credentials: User's OAuth credentials
            hours: Look back period in hours
            max_messages: Maximum messages to analyze
            
        Returns:
            Inbox summary with categorized messages
        """
        service = self._get_service(credentials)
        
        # Calculate time filter
        after_date = datetime.utcnow() - timedelta(hours=hours)
        after_timestamp = int(after_date.timestamp())
        
        try:
            # Get recent inbox messages
            query = f"in:inbox after:{after_timestamp}"
            results = service.users().messages().list(
                userId="me",
                q=query,
                maxResults=max_messages
            ).execute()
            
            messages = results.get("messages", [])
            
            # Fetch and categorize messages
            summary = {
                "total_count": len(messages),
                "unread_count": 0,
                "important_count": 0,
                "messages": [],
                "senders": {},
                "time_range": {
                    "from": after_date.isoformat(),
                    "to": datetime.utcnow().isoformat()
                }
            }
            
            for msg in messages:
                message_detail = service.users().messages().get(
                    userId="me",
                    id=msg["id"],
                    format="metadata",
                    metadataHeaders=["From", "To", "Subject", "Date"]
                ).execute()
                
                formatted = self._format_message_summary(message_detail)
                summary["messages"].append(formatted)
                
                # Count unread
                if formatted.get("is_unread"):
                    summary["unread_count"] += 1
                
                # Count important
                if formatted.get("is_important"):
                    summary["important_count"] += 1
                
                # Track senders
                sender = formatted.get("from", "Unknown")
                if sender not in summary["senders"]:
                    summary["senders"][sender] = 0
                summary["senders"][sender] += 1
            
            logger.info("Summarized inbox", 
                       total=summary["total_count"],
                       unread=summary["unread_count"])
            
            return summary
            
        except HttpError as e:
            logger.error("Failed to summarize inbox", error=str(e))
            raise
    
    async def send_email(
        self,
        credentials: dict,
        to: str | list[str],
        subject: str,
        body: str,
        cc: Optional[str | list[str]] = None,
        bcc: Optional[str | list[str]] = None,
        html_body: Optional[str] = None,
        reply_to_message_id: Optional[str] = None,
        thread_id: Optional[str] = None
    ) -> dict:
        """
        Send an email.
        
        Args:
            credentials: User's OAuth credentials
            to: Recipient email(s)
            subject: Email subject
            body: Plain text body
            cc: CC recipient(s)
            bcc: BCC recipient(s)
            html_body: Optional HTML body
            reply_to_message_id: Message ID to reply to
            thread_id: Thread ID for threading
            
        Returns:
            Sent message details
        """
        service = self._get_service(credentials)
        
        # Normalize recipients to lists
        to_list = [to] if isinstance(to, str) else to
        cc_list = [cc] if isinstance(cc, str) else (cc or [])
        bcc_list = [bcc] if isinstance(bcc, str) else (bcc or [])
        
        # Create message
        if html_body:
            message = MIMEMultipart("alternative")
            message.attach(MIMEText(body, "plain"))
            message.attach(MIMEText(html_body, "html"))
        else:
            message = MIMEText(body)
        
        message["To"] = ", ".join(to_list)
        message["Subject"] = subject
        
        if cc_list:
            message["Cc"] = ", ".join(cc_list)
        if bcc_list:
            message["Bcc"] = ", ".join(bcc_list)
        
        # Handle reply headers
        if reply_to_message_id:
            # Fetch original message for headers
            original = service.users().messages().get(
                userId="me",
                id=reply_to_message_id,
                format="metadata",
                metadataHeaders=["Message-ID", "References"]
            ).execute()
            
            headers = {h["name"]: h["value"] for h in original.get("payload", {}).get("headers", [])}
            
            if "Message-ID" in headers:
                message["In-Reply-To"] = headers["Message-ID"]
                refs = headers.get("References", "")
                message["References"] = f"{refs} {headers['Message-ID']}".strip()
        
        # Encode message
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        try:
            body = {"raw": raw}
            if thread_id:
                body["threadId"] = thread_id
            
            sent_message = service.users().messages().send(
                userId="me",
                body=body
            ).execute()
            
            logger.info("Sent email", 
                       message_id=sent_message.get("id"),
                       to=to_list,
                       subject=subject)
            
            return {
                "id": sent_message.get("id"),
                "thread_id": sent_message.get("threadId"),
                "label_ids": sent_message.get("labelIds"),
                "status": "sent"
            }
            
        except HttpError as e:
            logger.error("Failed to send email", error=str(e))
            raise
    
    async def modify_labels(
        self,
        credentials: dict,
        message_id: str,
        add_labels: Optional[list[str]] = None,
        remove_labels: Optional[list[str]] = None
    ) -> dict:
        """
        Modify labels on a message (mark read/unread, archive, etc.)
        
        Common labels: INBOX, UNREAD, STARRED, IMPORTANT, SPAM, TRASH
        """
        service = self._get_service(credentials)
        
        try:
            body = {}
            if add_labels:
                body["addLabelIds"] = add_labels
            if remove_labels:
                body["removeLabelIds"] = remove_labels
            
            result = service.users().messages().modify(
                userId="me",
                id=message_id,
                body=body
            ).execute()
            
            logger.info("Modified labels", 
                       message_id=message_id,
                       added=add_labels,
                       removed=remove_labels)
            
            return {"id": result.get("id"), "label_ids": result.get("labelIds")}
            
        except HttpError as e:
            logger.error("Failed to modify labels", error=str(e))
            raise
    
    async def mark_as_read(self, credentials: dict, message_id: str) -> dict:
        """Mark a message as read."""
        return await self.modify_labels(credentials, message_id, remove_labels=["UNREAD"])
    
    async def mark_as_unread(self, credentials: dict, message_id: str) -> dict:
        """Mark a message as unread."""
        return await self.modify_labels(credentials, message_id, add_labels=["UNREAD"])
    
    async def archive_message(self, credentials: dict, message_id: str) -> dict:
        """Archive a message (remove from inbox)."""
        return await self.modify_labels(credentials, message_id, remove_labels=["INBOX"])
    
    async def get_labels(self, credentials: dict) -> list[dict]:
        """Get all labels in the user's mailbox."""
        service = self._get_service(credentials)
        
        try:
            results = service.users().labels().list(userId="me").execute()
            labels = results.get("labels", [])
            
            return [
                {
                    "id": label.get("id"),
                    "name": label.get("name"),
                    "type": label.get("type"),
                    "message_list_visibility": label.get("messageListVisibility"),
                    "label_list_visibility": label.get("labelListVisibility")
                }
                for label in labels
            ]
            
        except HttpError as e:
            logger.error("Failed to get labels", error=str(e))
            raise
    
    def _format_message_summary(self, message: dict) -> dict:
        """Format a message into a summary structure."""
        headers = {
            h["name"]: h["value"] 
            for h in message.get("payload", {}).get("headers", [])
        }
        
        label_ids = message.get("labelIds", [])
        
        return {
            "id": message.get("id"),
            "thread_id": message.get("threadId"),
            "snippet": message.get("snippet"),
            "from": headers.get("From"),
            "to": headers.get("To"),
            "subject": headers.get("Subject"),
            "date": headers.get("Date"),
            "is_unread": "UNREAD" in label_ids,
            "is_important": "IMPORTANT" in label_ids,
            "is_starred": "STARRED" in label_ids,
            "labels": label_ids
        }
    
    def _format_full_message(self, message: dict) -> dict:
        """Format a full message with body."""
        summary = self._format_message_summary(message)
        
        # Extract body
        body_text = ""
        body_html = ""
        
        payload = message.get("payload", {})
        
        # Handle different MIME structures
        if "parts" in payload:
            for part in payload["parts"]:
                mime_type = part.get("mimeType", "")
                data = part.get("body", {}).get("data", "")
                
                if data:
                    decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                    if mime_type == "text/plain":
                        body_text = decoded
                    elif mime_type == "text/html":
                        body_html = decoded
        else:
            # Simple message without parts
            data = payload.get("body", {}).get("data", "")
            if data:
                body_text = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        
        summary["body_text"] = body_text
        summary["body_html"] = body_html
        summary["size_estimate"] = message.get("sizeEstimate")
        summary["internal_date"] = message.get("internalDate")
        
        return summary
