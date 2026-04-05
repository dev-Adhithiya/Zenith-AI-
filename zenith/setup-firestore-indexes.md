# Firestore Index Setup

## Required Indexes

This document lists all the composite indexes required for the Zenith AI application.

---

## Index 1: Notes Collection

### Issue
The Notes system is failing because Firestore requires a composite index for querying notes by `user_id` and sorting by `created_at`.

### Solution - Auto-Generated Link (Fastest)
Click this link to automatically create the required index:
```
https://console.firebase.google.com/v1/r/project/multi-agentproductivity/firestore/indexes?create_composite=ClVwcm9qZWN0cy9tdWx0aS1hZ2VudHByb2R1Y3Rpdml0eS9kYXRhYmFzZXMvKGRlZmF1bHQpL2NvbGxlY3Rpb25Hcm91cHMvbm90ZXMvaW5kZXhlcy9fEAEaCwoHdXNlcl9pZBABGg4KCmNyZWF0ZWRfYXQQAhoMCghfX25hbWVfXxAC
```

---

## Index 2: Conversations Collection (REQUIRED FOR CHAT HISTORY)

### Issue
The sessions/chat history feature fails because Firestore requires a composite index for querying conversations by `user_id` and sorting by `last_activity`.

### Solution - Auto-Generated Link (Fastest)
Click this link to automatically create the required index:
```
https://console.firebase.google.com/v1/r/project/multi-agentproductivity/firestore/indexes?create_composite=Cl1wcm9qZWN0cy9tdWx0aS1hZ2VudHByb2R1Y3Rpdml0eS9kYXRhYmFzZXMvKGRlZmF1bHQpL2NvbGxlY3Rpb25Hcm91cHMvY29udmVyc2F0aW9ucy9pbmRleGVzL18QARoLCgd1c2VyX2lkEAEaEQoNbGFzdF9hY3Rpdml0eRACGgwKCF9fbmFtZV9fEAI
```

### Manual Creation via Firebase Console
1. Go to [Firebase Console](https://console.firebase.google.com/project/multi-agentproductivity/firestore/indexes)
2. Click "Create Index"
3. Configure:
   - **Collection ID**: `conversations`
   - **Fields to index**:
     - Field: `user_id`, Order: Ascending
     - Field: `last_activity`, Order: Descending
   - **Query scope**: Collection
4. Click "Create Index"
5. Wait for the index to build (usually takes a few minutes)

---

## Complete firestore.indexes.json

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
    },
    {
      "collectionGroup": "conversations",
      "queryScope": "COLLECTION",
      "fields": [
        {
          "fieldPath": "user_id",
          "order": "ASCENDING"
        },
        {
          "fieldPath": "last_activity",
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

---

## Recommended Additional Indexes

For better performance, consider adding these indexes as well:

### For tag filtering (notes)
- Collection: `notes`
- Fields: `user_id` (Ascending) + `tags` (Array-contains) + `created_at` (Descending)

### For source filtering (notes)
- Collection: `notes`
- Fields: `user_id` (Ascending) + `source` (Ascending) + `created_at` (Descending)

---

## Status Check
After creating the indexes:
1. Wait for "Building" status to change to "Enabled" (2-10 minutes typically)
2. Test the functionality again
3. The "500 Internal Server Error" for `/sessions` should be resolved
