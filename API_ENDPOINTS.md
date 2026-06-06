# API Endpoints Documentation

## Base URL

`http://127.0.0.1:8000/api/v1/`

## User Management APIs

### User Profile

- **Endpoint**: `/api/v1/users/profile/`
- **Methods**: GET, POST, PUT, DELETE
- **Description**: Manage user profiles
- **Action**: `GET /users/profile/me/` - Get current user's profile

### User Sessions

- **Endpoint**: `/api/v1/users/sessions/`
- **Methods**: GET, POST, PUT, DELETE
- **Description**: View and manage user sessions

### User Preferences

- **Endpoint**: `/api/v1/users/preferences/`
- **Methods**: GET, POST, PUT, DELETE
- **Description**: Manage user UI and display preferences

### User Notifications

- **Endpoint**: `/api/v1/users/notifications/`
- **Methods**: GET, POST, PUT, DELETE
- **Description**: Manage user notifications
- **Actions**:
  - `POST /notifications/{id}/mark_as_read/` - Mark notification as read
  - `POST /notifications/mark_all_as_read/` - Mark all notifications as read

## File Management APIs

### Files

- **Endpoint**: `/api/v1/files/`
- **Methods**: GET, POST, PUT, DELETE
- **Description**: Upload, rename, preview, and organize files
- **Action**: `GET /files/search/?q=query` - Search files

### File Paths

- **Endpoint**: `/api/v1/files/paths/`
- **Methods**: GET, POST, PUT, DELETE
- **Description**: Manage file path hierarchies

### File Revisions

- **Endpoint**: `/api/v1/files/revisions/`
- **Methods**: GET (Read-Only)
- **Description**: View file revision history
- **Filter**: `?file_id=<file_id>`

### File Content Hints

- **Endpoint**: `/api/v1/files/content-hints/`
- **Methods**: GET, POST, PUT, DELETE
- **Description**: Manage file content metadata

### Image Metadata

- **Endpoint**: `/api/v1/files/image-metadata/`
- **Methods**: GET, POST, PUT, DELETE
- **Description**: Manage image metadata (dimensions, format, etc.)

### Video Metadata

- **Endpoint**: `/api/v1/files/video-metadata/`
- **Methods**: GET, POST, PUT, DELETE
- **Description**: Manage video metadata (duration, codec, resolution, etc.)

## Permissions & Sharing APIs

### Permissions

- **Endpoint**: `/api/v1/permissions/`
- **Methods**: GET, POST, PUT, DELETE
- **Description**: Manage file access permissions

### Share Links

- **Endpoint**: `/api/v1/share-links/`
- **Methods**: GET, POST, PUT, DELETE
- **Description**: Create and manage shareable links
- **Action**: `POST /share-links/{id}/revoke/` - Revoke share link

### Share Link Accesses

- **Endpoint**: `/api/v1/share-link-accesses/`
- **Methods**: GET (Read-Only)
- **Description**: View who accessed shared links

## File Request APIs

### File Requests

- **Endpoint**: `/api/v1/file-requests/`
- **Methods**: GET, POST, PUT, DELETE
- **Description**: Create and manage file requests

### File Request Submissions

- **Endpoint**: `/api/v1/file-request-submissions/`
- **Methods**: GET, POST, PUT, DELETE
- **Description**: Manage submissions to file requests

## Trash & Security APIs

### Trash

- **Endpoint**: `/api/v1/trash/`
- **Methods**: GET, POST, PUT, DELETE
- **Description**: Manage trashed files
- **Actions**:
  - `POST /trash/{id}/restore/` - Restore file from trash
  - `DELETE /trash/{id}/purge/` - Permanently delete file

### Spam Flags

- **Endpoint**: `/api/v1/spam-flags/`
- **Methods**: GET, POST, PUT, DELETE
- **Description**: Flag and manage spam files

## Comments APIs

### Comments

- **Endpoint**: `/api/v1/comments/`
- **Methods**: GET, POST, PUT, DELETE
- **Description**: Add and manage file comments
- **Action**: `POST /comments/{id}/resolve/` - Resolve comment
- **Filter**: `?file_id=<file_id>`

### Comment Replies

- **Endpoint**: `/api/v1/comment-replies/`
- **Methods**: GET, POST, PUT, DELETE
- **Description**: Reply to comments
- **Filter**: `?comment_id=<comment_id>`

### Comment Mentions

- **Endpoint**: `/api/v1/comment-mentions/`
- **Methods**: GET, POST, PUT, DELETE
- **Description**: Manage user mentions in comments

## Activity & Audit APIs

### Activity Feed

- **Endpoint**: `/api/v1/activity/`
- **Methods**: GET (Read-Only)
- **Description**: View file activity and changes

### Audit Logs

- **Endpoint**: `/api/v1/audit-logs/`
- **Methods**: GET (Read-Only)
- **Description**: View audit logs (Admin only)

### DLP Violations

- **Endpoint**: `/api/v1/dlp-violations/`
- **Methods**: GET (Read-Only)
- **Description**: View Data Loss Prevention violations (Admin only)

## Labels APIs

### Labels

- **Endpoint**: `/api/v1/labels/`
- **Methods**: GET, POST, PUT, DELETE
- **Description**: Manage file labels and categories

### Label Fields

- **Endpoint**: `/api/v1/label-fields/`
- **Methods**: GET, POST, PUT, DELETE
- **Description**: Manage label field definitions

### File Labels

- **Endpoint**: `/api/v1/file-labels/`
- **Methods**: GET, POST, PUT, DELETE
- **Description**: Apply labels to files

## Search APIs

### Search Index

- **Endpoint**: `/api/v1/search-index/`
- **Methods**: GET, POST, PUT, DELETE
- **Description**: Manage search indexes

### Saved Searches

- **Endpoint**: `/api/v1/saved-searches/`
- **Methods**: GET, POST, PUT, DELETE
- **Description**: Save and manage search queries

### Search History

- **Endpoint**: `/api/v1/search-history/`
- **Methods**: GET (Read-Only)
- **Description**: View search history

## Products APIs

### Products

- **Endpoint**: `/api/v1/apiproducts/products/`
- **Methods**: GET, POST, PUT, DELETE
- **Description**: Manage product listings
- **Fields**:
  - `id`: Product ID
  - `productName`: Name of the product
  - `price`: Product price
  - `productImage`: Product image URL
  - `productDate`: Creation date

## Response Format

All successful responses return JSON with the following format:

```json
{
  "id": "...",
  "field1": "value1",
  "field2": "value2",
  ...
}
```

For list endpoints, responses are wrapped in a results array:

```json
{
  "count": 100,
  "next": "http://api.example.com/accounts/?page=2",
  "previous": null,
  "results": [...]
}
```

## Authentication

Most endpoints require authentication. Include the token in the request header:

```
Authorization: Token <your_token>
```

## Pagination

List endpoints support pagination with the following query parameters:

- `?page=1` - Page number
- `?page_size=20` - Items per page

## Filtering

Most list endpoints support filtering. Common filters:

- `?user_id=<id>` - Filter by user
- `?file_id=<id>` - Filter by file
- `?created_after=<date>` - Filter by creation date

## Status Codes

- `200 OK` - Request succeeded
- `201 Created` - Resource created
- `204 No Content` - No content to return
- `400 Bad Request` - Invalid request
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Permission denied
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error
