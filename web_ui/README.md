# Inhaus Marketing API - Web UI

This is a premium Flutter Web interface for the Inhaus Marketing Data API, built using Riverpod, Dio, and Material 3.

## Requirements

- Flutter SDK (Web support enabled)
- Firebase CLI (for deployment)

## Local Development

To run the project locally against your local FastAPI backend:

1. Ensure the Python backend is running:
   ```bash
   cd ../
   uvicorn app.main:app --reload
   ```

2. Run the Flutter web app:
   ```bash
   cd web_ui
   flutter run -d chrome
   ```

3. Upon first launch, the UI will redirect you to the **Settings** screen.
   - Set **Base URL** to `http://127.0.0.1:8000`
   - Enter your **API Key** (e.g. `your-secret-api-key`)
   - Click "Test Connection" to verify, then save.

## Production Build

To build the project for production, run:

```bash
flutter build web --release --web-renderer canvaskit
```

This creates a highly optimized build inside `build/web/`.

## Deployment (Firebase Hosting)

Deploying to Firebase Hosting is highly recommended for Flutter Web apps due to its global CDN and ease of use.

### Step-by-Step Guide

1. **Install Firebase CLI** (if not installed):
   ```bash
   npm install -g firebase-tools
   ```

2. **Login to Firebase**:
   ```bash
   firebase login
   ```

3. **Initialize Firebase in this folder**:
   ```bash
   cd web_ui
   firebase init hosting
   ```
   - **Select Project**: Select an existing project or create a new one. Recommended naming: `inhaus-marketing-api`.
   - **Public directory**: Type `build/web` (IMPORTANT)
   - **Configure as single-page app**: Type `y` (Yes)
   - **Set up automatic builds/deploys with GitHub?**: Up to you (`N` is fine for manual deploys)
   - **Overwrite build/web/index.html?**: Type `N` (No - keep Flutter's `index.html`)

4. **Build and Deploy**:
   ```bash
   flutter build web --release
   firebase deploy --only hosting
   ```

You will get a Hosting URL (e.g. `https://inhaus-marketing-api.web.app`) where your app is now live!

## Cloud Run Migration Notes

If the traffic scales significantly or you need to bundle this UI directly with the Python API container, you can migrate to Google Cloud Run:
- You would modify the existing `Dockerfile` in the root project to perform a multi-stage build:
  1. Build the Flutter web app.
  2. Copy `build/web` to a static directory in the Python container.
  3. Serve those static files via FastAPI (`from fastapi.staticfiles import StaticFiles`).
- For now, Firebase Hosting offers the best CDN performance and easiest developer experience.

## OAuth Integration

The Web UI supports OAuth authentication for Meta Ads and Google Ads. By default, it operates in a mock mode for UI development.

### Backend Requirements

To enable real OAuth flows (setting `useMockOAuth = false` in `api_client.dart`), the backend API must implement the following endpoints:

- `GET /api/v1/oauth/authorize?platform={platform}`
  - Returns: `{ "authorization_url": "https://..." }`
- `GET /api/v1/oauth/callback`
  - Handles the OAuth provider redirect, exchanges the code for a token, stores it in Firestore, and redirects the user back to the web UI at `/?oauth=success&platform={platform}`.
- `GET /api/v1/oauth/connections?platform={platform}`
  - Returns a list of connected accounts: `[{ "account_id": "...", "account_name": "...", "connected_at": "..." }]`
- `DELETE /api/v1/oauth/connections/{platform}/{account_id}`
  - Deletes the token from Firestore.

### Firestore CredentialStore Structure

OAuth tokens should be stored within the existing `CredentialStore` collection/structure. Since users must manually select which connected account to query, the backend should associate tokens with a specific platform and potentially the user's tenant ID, maintaining support for multiple ad accounts per platform.
