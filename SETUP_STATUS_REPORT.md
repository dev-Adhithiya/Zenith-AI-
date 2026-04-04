# Zenith AI - Model Configuration & Notes Setup Status

**Date:** 2026-04-04  
**GCP Project:** multi-agentproductivity

---

## ✅ Task 1: Change Model to gemini-2.5-flash - COMPLETE

All model references have been updated to `gemini-2.5-flash`:

### Files Updated:
1. **`zenith/.env.example`** ✅ 
   - Changed from: `VERTEX_AI_MODEL=gemini-1.5-pro-001`
   - Changed to: `VERTEX_AI_MODEL=gemini-2.5-flash`

### Already Configured (No changes needed):
2. **`zenith/.env`** ✅
   - Already set to: `VERTEX_AI_MODEL=gemini-2.5-flash`

3. **`zenith/config.py`** ✅
   - Default value: `gemini-2.5-flash` (line 33)

### Verification:
```bash
cd zenith
python -c "from config import settings; print(f'Model: {settings.vertex_ai_model}')"
# Output: Model: gemini-2.5-flash
```

---

## ❌ Task 2: Notes Connection Issue - REQUIRES ACTION

### Problem Identified:
The Notes system **cannot connect to Firestore** because a required composite index is missing.

### Error Details:
```
google.api_core.exceptions.FailedPrecondition: 400 The query requires an index
```

The notes system queries Firestore with:
- Filter by: `user_id == <user_id>`
- Order by: `created_at DESC`

This combination requires a composite index in Firestore.

### Root Cause:
The `notes.py` file (line 121-127) executes this query:
```python
notes = await self.db.query_documents(
    collection=self.collection,  # "notes"
    filters=[("user_id", "==", user_id)],
    order_by="created_at",
    order_direction="DESCENDING",
    limit=limit
)
```

Firestore requires an explicit index for queries that combine filtering + ordering on different fields.

---

## 🔧 Solutions to Fix Notes Connection

### Option 1: Quick Fix - Use Auto-Generated Link ⚡ (RECOMMENDED)
Click this link to create the index automatically:
```
https://console.firebase.google.com/v1/r/project/multi-agentproductivity/firestore/indexes?create_composite=ClVwcm9qZWN0cy9tdWx0aS1hZ2VudHByb2R1Y3Rpdml0eS9kYXRhYmFzZXMvKGRlZmF1bHQpL2NvbGxlY3Rpb25Hcm91cHMvbm90ZXMvaW5kZXhlcy9fEAEaCwoHdXNlcl9pZBABGg4KCmNyZWF0ZWRfYXQQAhoMCghfX25hbWVfXxAC
```

**Steps:**
1. Click the link above
2. You'll be redirected to Firebase Console
3. Review the index configuration
4. Click "Create Index"
5. Wait 2-10 minutes for the index to build
6. Status will change from "Building" → "Enabled"

### Option 2: Manual Creation via Firebase Console
1. Go to: https://console.firebase.google.com/project/multi-agentproductivity/firestore/indexes
2. Click "**Create Index**"
3. Configure:
   - **Collection ID**: `notes`
   - **Fields**:
     - `user_id` - Ascending
     - `created_at` - Descending
   - **Query scope**: Collection
4. Click "**Create Index**"
5. Wait for build to complete

### Option 3: Deploy via Firebase CLI (For Production)
We've created `infrastructure/firestore.indexes.json` with all required indexes.

**Deploy command:**
```bash
cd infrastructure
firebase deploy --only firestore:indexes --project multi-agentproductivity
```

This will create all indexes defined in the JSON file.

---

## 📋 All Required Indexes (Recommended)

The `firestore.indexes.json` file includes these indexes:

### 1. Notes - Basic Query (REQUIRED)
- Collection: `notes`
- Fields: `user_id` (ASC) + `created_at` (DESC)

### 2. Notes - Source Filter (OPTIONAL)
- Collection: `notes`
- Fields: `user_id` (ASC) + `source` (ASC) + `created_at` (DESC)

### 3. Conversations Query (OPTIONAL)
- Collection: `conversations`
- Fields: `user_id` (ASC) + `created_at` (DESC)

### 4. Messages Query (OPTIONAL)
- Collection Group: `messages`
- Fields: `session_id` (ASC) + `timestamp` (ASC)

---

## 🧪 Testing After Index Creation

Once the index is enabled, test the notes system:

```bash
cd zenith
python -c "
import asyncio
from tools.notes import NotesTools

async def test():
    notes = NotesTools()
    result = await notes.list_notes(user_id='test-user', limit=5)
    print(f'✅ Notes working! Found {len(result)} notes')

asyncio.run(test())
"
```

Expected output:
```
✅ Notes working! Found X notes
```

---

## 📁 Files Created

1. **`zenith/setup-firestore-indexes.md`** - Detailed setup instructions
2. **`infrastructure/firestore.indexes.json`** - Complete index definitions for Firebase CLI deployment

---

## Summary

### ✅ Completed:
- [x] Model changed to `gemini-2.5-flash` everywhere
- [x] Identified notes connection issue
- [x] Created Firestore index configuration files
- [x] Provided 3 solutions to fix the issue

### ⏳ Requires Your Action:
- [ ] Create Firestore composite index (choose one option above)
- [ ] Wait for index to build (2-10 minutes)
- [ ] Test notes functionality

### Next Steps:
1. Choose a solution (Option 1 recommended for speed)
2. Create the index
3. Wait for "Building" → "Enabled"
4. Run the test script to verify

---

**Note:** The index only needs to be created once. After it's enabled, all notes operations will work correctly.
