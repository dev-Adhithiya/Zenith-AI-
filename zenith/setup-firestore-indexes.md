# Firestore Index Setup for Notes

## Issue
The Notes system is failing because Firestore requires a composite index for querying notes by `user_id` and sorting by `created_at`.

## Error
```
400 The query requires an index
```

## Solution Options

### Option 1: Use the Auto-Generated Link (Fastest)
Click this link to automatically create the required index:
```
https://console.firebase.google.com/v1/r/project/multi-agentproductivity/firestore/indexes?create_composite=ClVwcm9qZWN0cy9tdWx0aS1hZ2VudHByb2R1Y3Rpdml0eS9kYXRhYmFzZXMvKGRlZmF1bHQpL2NvbGxlY3Rpb25Hcm91cHMvbm90ZXMvaW5kZXhlcy9fEAEaCwoHdXNlcl9pZBABGg4KCmNyZWF0ZWRfYXQQAhoMCghfX25hbWVfXxAC
```

### Option 2: Manual Creation via Firebase Console
1. Go to [Firebase Console](https://console.firebase.google.com/project/multi-agentproductivity/firestore/indexes)
2. Click "Create Index"
3. Configure:
   - **Collection ID**: `notes`
   - **Fields to index**:
     - Field: `user_id`, Order: Ascending
     - Field: `created_at`, Order: Descending
   - **Query scope**: Collection
4. Click "Create Index"
5. Wait for the index to build (usually takes a few minutes)

### Option 3: Use firestore.indexes.json File
Create a `firestore.indexes.json` file and deploy with Firebase CLI:

```json
{
  "indexes": [
    {
      "collectionGroup": "notes",
      "queryScope": "COLLECTION",
      "fields": [
        {
          "fieldPath": "user_id",
          "order": "ASCENDING"
        },
        {
          "fieldPath": "created_at",
          "order": "DESCENDING"
        }
      ]
    }
  ],
  "fieldOverrides": []
}
```

Then run:
```bash
firebase deploy --only firestore:indexes
```

## Recommended Additional Indexes

For better performance, consider adding these indexes as well:

### For tag filtering
- Collection: `notes`
- Fields: `user_id` (Ascending) + `tags` (Array-contains) + `created_at` (Descending)

### For source filtering
- Collection: `notes`
- Fields: `user_id` (Ascending) + `source` (Ascending) + `created_at` (Descending)

## Status
After creating the index:
1. Wait for "Building" status to change to "Enabled" (2-10 minutes typically)
2. Test the notes functionality again
3. Run the test script: `python -c "import asyncio; from tools.notes import NotesTools; asyncio.run(NotesTools().list_notes('test-user', limit=5))"`
