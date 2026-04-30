"""
Google Calendar Tools for Zenith AI
Provides calendar management capabilities: list, create, update, delete events
"""
from datetime import datetime, timedelta
from typing import Optional
import pytz
import structlog

def _parse_dt(dt):
    if isinstance(dt, str):
        from dateutil.parser import isoparse
        return isoparse(dt)
    return dt

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from auth.google_oauth import GoogleOAuthManager, get_oauth_manager

logger = structlog.get_logger()


class CalendarTools:
    """
    Google Calendar API integration.
    Handles all calendar operations for Zenith AI.
    """
    
    def __init__(self, oauth_manager: Optional[GoogleOAuthManager] = None):
        self.oauth = oauth_manager or get_oauth_manager()
    
    def _get_service(self, credentials_dict: dict):
        """Get Calendar API service."""
        return self.oauth.build_service("calendar", "v3", credentials_dict)
    
    async def list_events(
        self,
        credentials: dict,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 10,
        calendar_id: str = "primary",
        query: Optional[str] = None
    ) -> list[dict]:
        """
        List upcoming calendar events.
        
        Args:
            credentials: User's OAuth credentials
            time_min: Start of time range (defaults to now)
            time_max: End of time range (defaults to 7 days from now)
            max_results: Maximum number of events to return
            calendar_id: Calendar ID (default: primary)
            query: Optional search query
            
        Returns:
            List of events with details
        """
        service = self._get_service(credentials)
        
        # Default time range
        time_min = _parse_dt(time_min)
        if time_min is None:
            time_min = datetime.utcnow()
        time_max = _parse_dt(time_max)
        if time_max is None:
            time_max = time_min + timedelta(days=7)
        
        try:
            time_min_str = time_min.isoformat() if (time_min.tzinfo or "+" in time_min.isoformat()) else time_min.isoformat() + "Z"
            time_max_str = time_max.isoformat() if (time_max.tzinfo or "+" in time_max.isoformat()) else time_max.isoformat() + "Z"
            
            request_params = {
                "calendarId": calendar_id,
                "timeMin": time_min_str,
                "timeMax": time_max_str,
                "maxResults": max_results,
                "singleEvents": True,
                "orderBy": "startTime"
            }
            
            if query:
                request_params["q"] = query
            
            events_result = service.events().list(**request_params).execute()
            events = events_result.get("items", [])
            
            logger.info("Listed calendar events", count=len(events), calendar_id=calendar_id)
            
            return [self._format_event(event) for event in events]
            
        except HttpError as e:
            logger.error("Failed to list events", error=str(e))
            raise
    
    async def get_event(
        self,
        credentials: dict,
        event_id: str,
        calendar_id: str = "primary"
    ) -> Optional[dict]:
        """Get a specific event by ID."""
        service = self._get_service(credentials)
        
        try:
            event = service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            return self._format_event(event)
            
        except HttpError as e:
            if e.resp.status == 404:
                return None
            logger.error("Failed to get event", error=str(e), event_id=event_id)
            raise
    
    async def create_event(
        self,
        credentials: dict,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[list[str]] = None,
        timezone: str = "UTC",
        calendar_id: str = "primary",
        send_notifications: bool = True,
        conference_data: bool = False
    ) -> dict:
        """
        Create a new calendar event.
        
        Args:
            credentials: User's OAuth credentials
            summary: Event title
            start_time: Event start datetime
            end_time: Event end datetime
            description: Event description
            location: Event location
            attendees: List of attendee email addresses
            timezone: Timezone for the event
            calendar_id: Calendar ID (default: primary)
            send_notifications: Send email notifications to attendees
            conference_data: Add Google Meet link
            
        Returns:
            Created event details
        """
        service = self._get_service(credentials)
        start_time = _parse_dt(start_time)
        end_time = _parse_dt(end_time)
        
        if timezone == "UTC":
            try:
                import tzlocal
                timezone = tzlocal.get_localzone_name()
            except Exception:
                pass

        # Force naive datetime so calendar API adopts the timeZone setting completely
        start_time_naive = start_time.replace(tzinfo=None)
        end_time_naive = end_time.replace(tzinfo=None)

        event_body = {
            "summary": summary,
            "start": {
                "dateTime": start_time_naive.isoformat(),
                "timeZone": timezone
            },
            "end": {
                "dateTime": end_time_naive.isoformat(),
                "timeZone": timezone
            }
        }
        
        if description:
            event_body["description"] = description
        
        if location:
            event_body["location"] = location
        
        if attendees:
            if isinstance(attendees, str):
                attendees = [a.strip() for a in attendees.replace(';', ',').split(',')]
            
            valid_attendees = [{"email": email.strip()} for email in attendees if isinstance(email, str) and email.strip() and email.strip().lower() not in ['none', 'null', 'n/a']]
            if valid_attendees:
                event_body["attendees"] = valid_attendees
        
        if conference_data:
            event_body["conferenceData"] = {
                "createRequest": {
                    "requestId": f"zenith-{datetime.utcnow().timestamp()}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"}
                }
            }
        
        try:
            request_params = {
                "calendarId": calendar_id,
                "body": event_body,
                "sendUpdates": "all" if send_notifications else "none"
            }
            
            if conference_data:
                request_params["conferenceDataVersion"] = 1
            
            event = service.events().insert(**request_params).execute()
            
            logger.info("Created calendar event", 
                       event_id=event.get("id"), 
                       summary=summary)
            
            return self._format_event(event)
            
        except HttpError as e:
            logger.error("Failed to create event", error=str(e))
            raise
    
    async def quick_add(
        self,
        credentials: dict,
        text: str,
        calendar_id: str = "primary"
    ) -> dict:
        """
        Quick add an event using natural language.
        
        Examples:
            "Meeting with John tomorrow at 3pm"
            "Lunch at 12:30pm on Friday"
            "Call with team next Monday 10am-11am"
        
        Args:
            credentials: User's OAuth credentials
            text: Natural language event description
            calendar_id: Calendar ID
            
        Returns:
            Created event details
        """
        service = self._get_service(credentials)
        
        try:
            event = service.events().quickAdd(
                calendarId=calendar_id,
                text=text
            ).execute()
            
            logger.info("Quick added event", event_id=event.get("id"), text=text)
            
            return self._format_event(event)
            
        except HttpError as e:
            logger.error("Failed to quick add event", error=str(e), text=text)
            raise
    
    async def update_event(
        self,
        credentials: dict,
        event_id: str,
        updates: dict,
        calendar_id: str = "primary",
        send_notifications: bool = True
    ) -> dict:
        """
        Update an existing event.
        
        Args:
            credentials: User's OAuth credentials
            event_id: Event ID to update
            updates: Dictionary of fields to update
            calendar_id: Calendar ID
            send_notifications: Notify attendees of changes
            
        Returns:
            Updated event details
        """
        service = self._get_service(credentials)
        
        try:
            # Get existing event
            event = service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            # Apply updates
            for key, value in updates.items():
                if key in ["start", "end"]:
                    parsed_val = _parse_dt(value)
                    if isinstance(parsed_val, datetime):
                        event[key] = {
                            "dateTime": parsed_val.isoformat(),
                            "timeZone": event.get(key, {}).get("timeZone", "UTC") 
                        }
                    else:
                        event[key] = value
                elif key == "attendees" and isinstance(value, list):
                    event["attendees"] = [{"email": email} for email in value]
                else:
                    event[key] = value
            
            updated_event = service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event,
                sendUpdates="all" if send_notifications else "none"
            ).execute()
            
            logger.info("Updated calendar event", event_id=event_id)
            
            return self._format_event(updated_event)
            
        except HttpError as e:
            logger.error("Failed to update event", error=str(e), event_id=event_id)
            raise
    
    async def delete_event(
        self,
        credentials: dict,
        event_id: str,
        calendar_id: str = "primary",
        send_notifications: bool = True
    ) -> bool:
        """Delete an event."""
        service = self._get_service(credentials)
        
        try:
            service.events().delete(
                calendarId=calendar_id,
                eventId=event_id,
                sendUpdates="all" if send_notifications else "none"
            ).execute()
            
            logger.info("Deleted calendar event", event_id=event_id)
            return True
            
        except HttpError as e:
            logger.error("Failed to delete event", error=str(e), event_id=event_id)
            raise
    
    async def list_calendars(self, credentials: dict) -> list[dict]:
        """List all calendars the user has access to."""
        service = self._get_service(credentials)
        
        try:
            calendars_result = service.calendarList().list().execute()
            calendars = calendars_result.get("items", [])
            
            return [
                {
                    "id": cal.get("id"),
                    "summary": cal.get("summary"),
                    "description": cal.get("description"),
                    "primary": cal.get("primary", False),
                    "access_role": cal.get("accessRole"),
                    "background_color": cal.get("backgroundColor"),
                    "timezone": cal.get("timeZone")
                }
                for cal in calendars
            ]
            
        except HttpError as e:
            logger.error("Failed to list calendars", error=str(e))
            raise
    
    async def check_availability(
        self,
        credentials: dict,
        time_min: datetime,
        time_max: datetime,
        calendar_ids: Optional[list[str]] = None
    ) -> dict:
        """
        Check free/busy status for calendars.
        
        Args:
            credentials: User's OAuth credentials
            time_min: Start of time range
            time_max: End of time range
            calendar_ids: List of calendar IDs to check (default: primary)
            
        Returns:
            Free/busy information
        """
        time_min = _parse_dt(time_min)
        time_max = _parse_dt(time_max)
        service = self._get_service(credentials)

        if calendar_ids is None:
            calendar_ids = ["primary"]

        try:
            time_min_str = time_min.isoformat() if (time_min.tzinfo or "+" in time_min.isoformat()) else time_min.isoformat() + "Z"
            time_max_str = time_max.isoformat() if (time_max.tzinfo or "+" in time_max.isoformat()) else time_max.isoformat() + "Z"
            
            body = {
                "timeMin": time_min_str,
                "timeMax": time_max_str,
                "items": [{"id": cal_id} for cal_id in calendar_ids]
            }
            
            freebusy = service.freebusy().query(body=body).execute()
            
            result = {}
            for cal_id in calendar_ids:
                cal_data = freebusy.get("calendars", {}).get(cal_id, {})
                busy_periods = cal_data.get("busy", [])
                result[cal_id] = {
                    "busy_periods": [
                        {
                            "start": period.get("start"),
                            "end": period.get("end")
                        }
                        for period in busy_periods
                    ],
                    "is_busy": len(busy_periods) > 0
                }
            
            return result
            
        except HttpError as e:
            logger.error("Failed to check availability", error=str(e))
            raise
    
    def _format_event(self, event: dict) -> dict:
        """Format a raw event into a cleaner structure."""
        start = event.get("start", {})
        end = event.get("end", {})
        
        # Handle all-day vs timed events
        start_dt = start.get("dateTime") or start.get("date")
        end_dt = end.get("dateTime") or end.get("date")
        is_all_day = "date" in start and "dateTime" not in start
        
        # Extract Google Meet link if present
        meet_link = None
        if "conferenceData" in event:
            for entry_point in event["conferenceData"].get("entryPoints", []):
                if entry_point.get("entryPointType") == "video":
                    meet_link = entry_point.get("uri")
                    break
        
        return {
            "id": event.get("id"),
            "summary": event.get("summary", "(No title)"),
            "description": event.get("description"),
            "location": event.get("location"),
            "start": start_dt,
            "end": end_dt,
            "timezone": start.get("timeZone"),
            "is_all_day": is_all_day,
            "status": event.get("status"),
            "html_link": event.get("htmlLink"),
            "meet_link": meet_link,
            "organizer": event.get("organizer", {}).get("email"),
            "attendees": [
                {
                    "email": att.get("email"),
                    "name": att.get("displayName"),
                    "response_status": att.get("responseStatus"),
                    "organizer": att.get("organizer", False)
                }
                for att in event.get("attendees", [])
            ],
            "created": event.get("created"),
            "updated": event.get("updated"),
            "recurring_event_id": event.get("recurringEventId"),
            "recurrence": event.get("recurrence")
        }
