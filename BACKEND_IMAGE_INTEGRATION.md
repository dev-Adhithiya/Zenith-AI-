# Backend Integration Guide - Image Upload Support

## FastAPI Endpoint Updates

Your current chat endpoint needs to be updated to handle image uploads via FormData.

### Current Endpoint Structure
```python
@app.post("/chat")
async def chat(request: ChatRequest, session_id: str = None):
    # Current implementation
```

### Updated Endpoint (Required)

```python
from fastapi import File, Form, UploadFile
from typing import List, Optional

@app.post("/chat")
async def chat(
    message: str = Form(...),
    session_id: Optional[str] = Form(None),
    images: Optional[List[UploadFile]] = File(None),
) -> ChatResponse:
    """
    Handle chat messages with optional image attachments.
    
    Args:
        message: Text message content
        session_id: Optional conversation session ID
        images: Optional list of image files (max 5MB each)
    
    Returns:
        ChatResponse with assistant's reply
    """
    try:
        # Process images if provided
        image_data = []
        if images:
            for image_file in images:
                # Validate file type
                if not image_file.content_type.startswith('image/'):
                    raise ValueError(f"Invalid file type: {image_file.content_type}")
                
                # Read file content
                content = await image_file.read()
                
                # Validate size
                if len(content) > 5 * 1024 * 1024:
                    raise ValueError(f"File too large: {image_file.filename}")
                
                image_data.append({
                    'filename': image_file.filename,
                    'content_type': image_file.content_type,
                    'content': content
                })
        
        # Get or create session
        if not session_id:
            session_id = uuid.uuid4().hex
        
        # Store user message with images
        user_message = {
            'role': 'user',
            'content': message,
            'timestamp': datetime.now().isoformat(),
            'metadata': {
                'image_count': len(image_data) if image_data else 0,
                'images': [{'filename': img['filename']} for img in image_data]
            }
        }
        
        # Add to conversation history
        # (store in Firestore/database)
        
        # Call Gemini with images
        response = await call_gemini_with_images(message, image_data)
        
        # Store assistant response
        assistant_message = {
            'role': 'assistant',
            'content': response.response,
            'timestamp': datetime.now().isoformat(),
            'metadata': response.metadata or {}
        }
        
        # Return response
        return ChatResponse(
            response=response.response,
            session_id=session_id,
            suggestions=response.suggestions,
            intent=response.intent,
            execution_success=response.execution_success,
            requires_confirmation=response.requires_confirmation,
            pending_plan=response.pending_plan
        )
        
    except Exception as e:
        # Error handling
        return ChatResponse(
            response=f"Error processing request: {str(e)}",
            session_id=session_id,
            error=str(e),
            execution_success=False
        )
```

## Gemini Vision Integration

### Setup
```python
from vertexai.generative_model import GenerativeModel, Part, Content
import base64

async def call_gemini_with_images(message: str, images: List[dict]):
    """Call Gemini with text and image content."""
    
    model = GenerativeModel("gemini-2.5-flash")
    
    # Build content parts
    parts = []
    
    # Add text message
    parts.append(Part.from_text(message))
    
    # Add images
    if images:
        for image in images:
            # Create image part from binary content
            part = Part.from_data(
                data=image['content'],
                mime_type=image['content_type']
            )
            parts.append(part)
    
    # Generate response
    response = await model.generate_content_async(parts)
    
    return {
        'response': response.text,
        'metadata': {
            'model': 'gemini-2.5-flash',
            'images_processed': len(images) if images else 0
        }
    }
```

### Alternative: Using Base64

If you prefer to encode images as base64:

```python
async def call_gemini_with_images_base64(message: str, images: List[dict]):
    """Call Gemini with base64 encoded images."""
    
    import base64
    from vertexai.generative_model import GenerativeModel, Part
    
    model = GenerativeModel("gemini-2.5-flash")
    
    # Build content parts
    parts = []
    
    # Add text message
    parts.append(Part.from_text(message))
    
    # Add base64 images
    if images:
        for image in images:
            base64_content = base64.b64encode(image['content']).decode()
            part = Part.from_data(
                data=base64_content,
                mime_type=image['content_type']
            )
            parts.append(part)
    
    # Generate response
    response = model.generate_content(parts)
    
    return {
        'response': response.text,
        'metadata': {
            'model': 'gemini-2.5-flash',
            'images_processed': len(images) if images else 0
        }
    }
```

## Database Schema Update

### Store images with messages

```python
# Firestore document structure
message_doc = {
    'role': 'user',
    'content': 'What is in this image?',
    'timestamp': '2024-01-15T10:30:00Z',
    'session_id': 'abc123...',
    'metadata': {
        'image_count': 2,
        'images': [
            {
                'id': 'img1_timestamp',
                'filename': 'screenshot.png',
                'content_type': 'image/png',
                'size_bytes': 125000,
                'storage_path': 'users/{user_id}/images/img1_timestamp.png'
            },
            {
                'id': 'img2_timestamp',
                'filename': 'diagram.jpg',
                'content_type': 'image/jpeg',
                'size_bytes': 250000,
                'storage_path': 'users/{user_id}/images/img2_timestamp.jpg'
            }
        ]
    }
}
```

## Optional: Store Images in Cloud Storage

For better scalability, store images separately:

```python
from google.cloud import storage

async def store_image_in_cloud_storage(
    user_id: str,
    image: dict,
    bucket_name: str = "my-zenith-images"
):
    """Store image in Cloud Storage and return reference."""
    
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    
    # Create unique filename
    image_id = f"{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
    blob_name = f"users/{user_id}/images/{image_id}.{get_extension(image['content_type'])}"
    
    # Upload image
    blob = bucket.blob(blob_name)
    blob.upload_from_string(
        image['content'],
        content_type=image['content_type']
    )
    
    # Make readable (if needed)
    blob.make_public()
    
    return {
        'id': image_id,
        'storage_path': blob_name,
        'public_url': blob.public_url
    }

def get_extension(mime_type: str) -> str:
    """Get file extension from MIME type."""
    mapping = {
        'image/png': 'png',
        'image/jpeg': 'jpg',
        'image/webp': 'webp',
        'image/gif': 'gif'
    }
    return mapping.get(mime_type, 'jpg')
```

## Firestore Indexes (if needed)

For session queries with images:

```json
{
  "fields": [
    {
      "fieldPath": "session_id",
      "order": "ASCENDING"
    },
    {
      "fieldPath": "timestamp",
      "order": "DESCENDING"
    }
  ],
  "queryScope": "COLLECTION"
}
```

## Testing

### Test with cURL

```bash
# Single image
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "message=What is in this image?" \
  -F "images=@screenshot.png" \
  -F "session_id=abc123"

# Multiple images
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "message=Compare these diagrams" \
  -F "images=@diagram1.jpg" \
  -F "images=@diagram2.jpg" \
  -F "session_id=abc123"
```

### Test with Python

```python
import requests
from pathlib import Path

# Single image
with open('screenshot.png', 'rb') as f:
    files = {'images': f}
    data = {
        'message': 'What is in this image?',
        'session_id': 'abc123'
    }
    response = requests.post(
        'http://localhost:8000/chat',
        headers={'Authorization': f'Bearer {token}'},
        files=files,
        data=data
    )
    print(response.json())

# Multiple images
with open('image1.jpg', 'rb') as f1, open('image2.jpg', 'rb') as f2:
    files = [
        ('images', f1),
        ('images', f2)
    ]
    data = {
        'message': 'Compare these images',
        'session_id': 'abc123'
    }
    response = requests.post(
        'http://localhost:8000/chat',
        headers={'Authorization': f'Bearer {token}'},
        files=files,
        data=data
    )
    print(response.json())
```

## Migration Notes

If you have an existing chat endpoint:

1. **Backward Compatible**: The endpoint accepts messages without images
2. **Old format still works**: `message` as Form field instead of JSON body
3. **No breaking changes**: Existing clients continue to work

Before deploying:
- [ ] Test with and without images
- [ ] Test with multiple images
- [ ] Verify file validation works
- [ ] Check Gemini Vision API costs
- [ ] Set up Cloud Storage if storing images
- [ ] Configure proper CORS for image uploads
- [ ] Add rate limiting for image uploads

## Firestore Update

Update your chat creation/update functions to handle image metadata:

```python
@app.post("/sessions")
async def create_session(current_user: dict = Depends(get_current_user)):
    """Create new chat session."""
    session_id = uuid.uuid4().hex
    
    session_ref = db.collection("users").document(current_user["user_id"]).collection("sessions").document(session_id)
    
    session_ref.set({
        'session_id': session_id,
        'created_at': datetime.now(),
        'updated_at': datetime.now(),
        'title': 'New Chat',
        'message_count': 0,
        'image_count': 0,  # Track images in session
        'tags': []
    })
    
    return {'session_id': session_id}
```

## Monitoring

Log image uploads for debugging:

```python
import logging

logger = logging.getLogger(__name__)

async def chat(message: str = Form(...), images: Optional[List[UploadFile]] = File(None)):
    if images:
        logger.info(f"Processing message with {len(images)} images")
        for img in images:
            logger.info(f"  - {img.filename} ({img.content_type}, size: {img.size})")
    
    # Rest of function...
```
