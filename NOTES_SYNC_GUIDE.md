# Notes Synchronization with Google Drive

## Overview
Your notes in Zenith AI are now automatically synchronized with Google Drive. This means you can create notes in Zenith and have them appear in a dedicated "Zenith Notes" folder in your Google Drive.

## Features

### ✅ What's Synced
- **Note Title** - Full title preserved
- **Note Content** - Full content preserved  
- **Note Metadata** - Tags, creation date, update date
- **Bidirectional Sync** - Pull notes from Drive or push from Zenith

### 📝 Supported Operations

#### 1. Create New Notes
```
POST /notes
{
  "title": "My Meeting Notes",
  "content": "Key points from the meeting...",
  "tags": ["meeting", "important"],
  "source": "manual"
}
```
✨ **Result**: Note appears in both Zenith and Google Drive's "Zenith Notes" folder

#### 2. Update Existing Notes
```
PUT /notes/{note_id}
{
  "title": "Updated Title",
  "content": "Updated content...",
  "tags": ["meeting", "important", "followup"]
}
```
✨ **Result**: Changes sync to Google Drive automatically

#### 3. Delete Notes
```
DELETE /notes/{note_id}
```
✨ **Result**: Note removed from both Zenith and Google Drive

#### 4. Import Notes from Drive
```
POST /notes/import-from-drive
```
✨ **Result**: All notes from your Google Drive's "Zenith Notes" folder are imported to Zenith

**Response**:
```json
{
  "imported_count": 5,
  "skipped_count": 2,
  "errors": []
}
```

#### 5. Check Sync Status
```
GET /notes/{note_id}/sync-status
```
**Response**:
```json
{
  "note_id": "abc123",
  "sync_status": "synced",
  "drive_file_id": "xyz789",
  "last_sync": "2024-01-15T10:30:00.000Z"
}
```

## How It Works

### Storage Format
Notes are stored as `.txt` files in Google Drive with a metadata header:

```
[Zenith AI Note]
ID: abc123
Synced: 2024-01-15T10:30:00.000Z

---

Your actual note content goes here...
```

### Synchronization Timeline
1. **Create** → Note saved to Firestore → Synced to Google Drive (2-5 seconds)
2. **Update** → Note updated in Firestore → Synced to Google Drive (2-5 seconds)
3. **Delete** → Note removed from Firestore → Removed from Google Drive (1-3 seconds)
4. **Import** → Pull all Drive notes → Create/update in Firestore (5-10 seconds)

### Sync Status
Each note has a `sync_status`:
- **`synced`** - Note is up-to-date in both places
- **`pending`** - Note is waiting to be synced to Drive (usually < 5 seconds)
- **`not_synced`** - Note exists only in Zenith (if Drive access isn't available)

## Requirements

### OAuth Permissions
You need to grant Zenith these permissions:
- ✅ **Google Calendar** - Create and manage events
- ✅ **Gmail** - Read and send emails  
- ✅ **Google Tasks** - Create and manage tasks
- ✅ **Google Drive** - `NEW` - Store and sync notes

**If you see "Drive sync failed"**, you may need to re-authenticate:
1. Click Sign Out
2. Click Sign In again
3. Grant permission for "Google Drive access"

## Access Your Notes

### In Zenith App
- List: `GET /notes` - See all your notes
- Search: `POST /notes/search` - Find notes by keyword
- View: Appears in NotesPanel component

### In Google Drive
1. Open [Google Drive](https://drive.google.com)
2. Look for folder: **"Zenith Notes"**
3. Open any `.txt` file to view or edit

> ⚠️ **Important**: Edit notes in Zenith for auto-sync. Changes made directly in Drive files won't sync back to Zenith.

## Troubleshooting

### "Drive sync failed" error
**Solution**: Re-authenticate to grant Google Drive permissions
```
1. Logout from Zenith
2. Login again
3. Accept "Google Drive" permission
```

### Notes not appearing in Drive
**Check**:
1. Are you logged in to Google Drive?
2. Did you click "Allow" for Google Drive permissions?
3. Is the "Zenith Notes" folder visible in your Drive?

**If folder doesn't exist**:
- Create a note in Zenith → Folder is auto-created
- Or run the import endpoint → Folder is auto-created if empty

### Duplicate notes after import
This can happen if notes already exist. The import endpoint checks for duplicates using:
- Note ID from metadata header
- If ID matches, note is skipped (won't duplicate)

## Best Practices

✅ **Do This**:
- Create notes in Zenith for auto-sync
- Use tags to organize notes (`#meeting`, `#todo`, `#idea`)
- Import from Drive once to get existing notes
- Review sync status for important notes

❌ **Don't Do This**:
- Edit note files directly in Google Drive (changes won't sync back)
- Create notes in Google Drive manually (they'll import as "imported_from_drive")
- Rename files in Drive (metadata header might break)
- Share Zenith Notes folder with others (sync may conflict)

## API Reference

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/notes` | Create new note |
| GET | `/notes` | List all notes |
| PUT | `/notes/{id}` | Update note |
| DELETE | `/notes/{id}` | Delete note |
| POST | `/notes/search` | Search notes |
| POST | `/notes/import-from-drive` | Import from Drive |
| GET | `/notes/{id}/sync-status` | Check sync status |

## Coming Soon

- 📱 **Offline Notes** - Access notes without internet
- 🔍 **Full-Text Search** - Semantic search powered by AI
- 🏷️ **Smart Tags** - Auto-tag notes by content
- 📌 **Pinned Notes** - Quick access favorites
- 🔗 **Note Links** - Cross-reference between notes

## Questions?

Check the main [README.md](./README.md) or [QUICKSTART.md](./QUICKSTART.md)
