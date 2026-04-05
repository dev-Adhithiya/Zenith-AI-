"""
Google Tasks Tools for Zenith AI
Provides task management capabilities: add, list, update, complete tasks
"""
from datetime import datetime, timedelta
from typing import Optional
import structlog

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from auth.google_oauth import GoogleOAuthManager, get_oauth_manager

logger = structlog.get_logger()


class TasksTools:
    """
    Google Tasks API integration.
    Handles all task operations for Zenith AI.
    """
    
    def __init__(self, oauth_manager: Optional[GoogleOAuthManager] = None):
        self.oauth = oauth_manager or get_oauth_manager()
    
    def _get_service(self, credentials_dict: dict):
        """Get Tasks API service."""
        return self.oauth.build_service("tasks", "v1", credentials_dict)
    
    async def list_task_lists(self, credentials: dict) -> list[dict]:
        """
        List all task lists.
        
        Returns:
            List of task lists with their IDs and titles
        """
        service = self._get_service(credentials)
        
        try:
            results = service.tasklists().list(maxResults=100).execute()
            task_lists = results.get("items", [])
            
            return [
                {
                    "id": tl.get("id"),
                    "title": tl.get("title"),
                    "updated": tl.get("updated"),
                    "self_link": tl.get("selfLink")
                }
                for tl in task_lists
            ]
            
        except HttpError as e:
            logger.error("Failed to list task lists", error=str(e))
            raise
    
    async def get_default_task_list(self, credentials: dict) -> str:
        """Get the default task list ID (@default)."""
        service = self._get_service(credentials)
        
        try:
            # The @default tasklist is the user's primary task list
            task_list = service.tasklists().get(tasklist="@default").execute()
            return task_list.get("id")
            
        except HttpError as e:
            logger.error("Failed to get default task list", error=str(e))
            raise
    
    async def list_tasks(
        self,
        credentials: dict,
        task_list_id: str = "@default",
        show_completed: bool = False,
        show_hidden: bool = False,
        due_min: Optional[datetime] = None,
        due_max: Optional[datetime] = None,
        max_results: int = 100
    ) -> list[dict]:
        """
        List tasks from a task list.
        
        Args:
            credentials: User's OAuth credentials
            task_list_id: Task list ID (default: @default)
            show_completed: Include completed tasks
            show_hidden: Include hidden tasks
            due_min: Minimum due date filter
            due_max: Maximum due date filter
            max_results: Maximum number of tasks
            
        Returns:
            List of tasks
        """
        service = self._get_service(credentials)
        
        try:
            request_params = {
                "tasklist": task_list_id,
                "maxResults": max_results,
                "showCompleted": show_completed,
                "showHidden": show_hidden
            }
            
            if due_min:
                request_params["dueMin"] = due_min.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            if due_max:
                request_params["dueMax"] = due_max.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            
            results = service.tasks().list(**request_params).execute()
            tasks = results.get("items", [])
            
            logger.info("Listed tasks", count=len(tasks), task_list_id=task_list_id)
            
            return [self._format_task(task) for task in tasks]
            
        except HttpError as e:
            logger.error("Failed to list tasks", error=str(e))
            raise
    
    async def get_task(
        self,
        credentials: dict,
        task_id: str,
        task_list_id: str = "@default"
    ) -> Optional[dict]:
        """Get a specific task by ID."""
        service = self._get_service(credentials)
        
        try:
            task = service.tasks().get(
                tasklist=task_list_id,
                task=task_id
            ).execute()
            
            return self._format_task(task)
            
        except HttpError as e:
            if e.resp.status == 404:
                return None
            logger.error("Failed to get task", error=str(e), task_id=task_id)
            raise
    
    async def add_task(
        self,
        credentials: dict,
        title: str,
        notes: Optional[str] = None,
        due_date: Optional[datetime] = None,
        task_list_id: str = "@default",
        parent_task_id: Optional[str] = None
    ) -> dict:
        """
        Add a new task.
        
        Args:
            credentials: User's OAuth credentials
            title: Task title
            notes: Task notes/description
            due_date: Due date (date only, no time in Tasks API)
            task_list_id: Task list ID
            parent_task_id: Parent task ID for subtasks
            
        Returns:
            Created task details
        """
        service = self._get_service(credentials)
        
        task_body = {"title": title}
        
        if notes:
            task_body["notes"] = notes
        
        if due_date:
            if isinstance(due_date, str):
                from dateutil.parser import isoparse
                due_date = isoparse(due_date)
            # Tasks API only supports date, not time
            task_body["due"] = due_date.strftime("%Y-%m-%dT00:00:00.000Z")
        
        try:
            request_params = {
                "tasklist": task_list_id,
                "body": task_body
            }
            
            if parent_task_id:
                request_params["parent"] = parent_task_id
            
            task = service.tasks().insert(**request_params).execute()
            
            logger.info("Added task", task_id=task.get("id"), title=title)
            
            return self._format_task(task)
            
        except HttpError as e:
            logger.error("Failed to add task", error=str(e))
            raise
    
    async def update_task(
        self,
        credentials: dict,
        task_id: str,
        task_list_id: str = "@default",
        title: Optional[str] = None,
        notes: Optional[str] = None,
        due_date: Optional[datetime] = None,
        status: Optional[str] = None
    ) -> dict:
        """
        Update an existing task.
        
        Args:
            credentials: User's OAuth credentials
            task_id: Task ID to update
            task_list_id: Task list ID
            title: New title
            notes: New notes
            due_date: New due date
            status: "needsAction" or "completed"
            
        Returns:
            Updated task details
        """
        service = self._get_service(credentials)
        
        try:
            # Get existing task
            task = service.tasks().get(
                tasklist=task_list_id,
                task=task_id
            ).execute()
            
            # Apply updates
            if title is not None:
                task["title"] = title
            if notes is not None:
                task["notes"] = notes
            if due_date is not None:
                task["due"] = due_date.strftime("%Y-%m-%dT00:00:00.000Z")
            if status is not None:
                task["status"] = status
                if status == "completed":
                    task["completed"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
            
            updated_task = service.tasks().update(
                tasklist=task_list_id,
                task=task_id,
                body=task
            ).execute()
            
            logger.info("Updated task", task_id=task_id)
            
            return self._format_task(updated_task)
            
        except HttpError as e:
            logger.error("Failed to update task", error=str(e), task_id=task_id)
            raise
    
    async def complete_task(
        self,
        credentials: dict,
        task_id: str,
        task_list_id: str = "@default"
    ) -> dict:
        """Mark a task as completed."""
        return await self.update_task(
            credentials=credentials,
            task_id=task_id,
            task_list_id=task_list_id,
            status="completed"
        )
    
    async def uncomplete_task(
        self,
        credentials: dict,
        task_id: str,
        task_list_id: str = "@default"
    ) -> dict:
        """Mark a task as not completed."""
        return await self.update_task(
            credentials=credentials,
            task_id=task_id,
            task_list_id=task_list_id,
            status="needsAction"
        )
    
    async def delete_task(
        self,
        credentials: dict,
        task_id: str,
        task_list_id: str = "@default"
    ) -> bool:
        """Delete a task."""
        service = self._get_service(credentials)
        
        try:
            service.tasks().delete(
                tasklist=task_list_id,
                task=task_id
            ).execute()
            
            logger.info("Deleted task", task_id=task_id)
            return True
            
        except HttpError as e:
            logger.error("Failed to delete task", error=str(e), task_id=task_id)
            raise
    
    async def set_reminder(
        self,
        credentials: dict,
        title: str,
        remind_at: datetime,
        notes: Optional[str] = None,
        task_list_id: str = "@default"
    ) -> dict:
        """
        Set a reminder (creates a task with due date).
        
        Note: Google Tasks doesn't have true reminders with notifications.
        This creates a task with the specified due date.
        For actual reminders, consider using Google Calendar events.
        
        Args:
            credentials: User's OAuth credentials
            title: Reminder title
            remind_at: When to be reminded
            notes: Additional notes
            task_list_id: Task list ID
            
        Returns:
            Created task/reminder
        """
        if isinstance(remind_at, str):
            from dateutil.parser import isoparse
            remind_at = isoparse(remind_at)
            
        # Add a note indicating this is a reminder
        reminder_notes = f"⏰ Reminder set for {remind_at.strftime('%Y-%m-%d %H:%M')}"
        if notes:
            reminder_notes = f"{reminder_notes}\n\n{notes}"
        
        return await self.add_task(
            credentials=credentials,
            title=f"🔔 {title}",
            notes=reminder_notes,
            due_date=remind_at,
            task_list_id=task_list_id
        )
    
    async def get_tasks_due_today(
        self,
        credentials: dict,
        task_list_id: str = "@default"
    ) -> list[dict]:
        """Get all tasks due today."""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        return await self.list_tasks(
            credentials=credentials,
            task_list_id=task_list_id,
            due_min=today,
            due_max=tomorrow,
            show_completed=False
        )
    
    async def get_overdue_tasks(
        self,
        credentials: dict,
        task_list_id: str = "@default"
    ) -> list[dict]:
        """Get all overdue tasks."""
        now = datetime.utcnow()
        
        tasks = await self.list_tasks(
            credentials=credentials,
            task_list_id=task_list_id,
            show_completed=False
        )
        
        return [
            task for task in tasks
            if task.get("due") and datetime.fromisoformat(task["due"].replace("Z", "+00:00")) < now
        ]
    
    async def create_task_list(
        self,
        credentials: dict,
        title: str
    ) -> dict:
        """Create a new task list."""
        service = self._get_service(credentials)
        
        try:
            task_list = service.tasklists().insert(
                body={"title": title}
            ).execute()
            
            logger.info("Created task list", task_list_id=task_list.get("id"), title=title)
            
            return {
                "id": task_list.get("id"),
                "title": task_list.get("title"),
                "updated": task_list.get("updated")
            }
            
        except HttpError as e:
            logger.error("Failed to create task list", error=str(e))
            raise
    
    def _format_task(self, task: dict) -> dict:
        """Format a raw task into a cleaner structure."""
        return {
            "id": task.get("id"),
            "title": task.get("title"),
            "notes": task.get("notes"),
            "status": task.get("status"),
            "due": task.get("due"),
            "completed": task.get("completed"),
            "parent": task.get("parent"),
            "position": task.get("position"),
            "updated": task.get("updated"),
            "self_link": task.get("selfLink"),
            "is_completed": task.get("status") == "completed"
        }
