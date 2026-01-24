# Deployment Guide - Railway

## Firebase Service Account Setup for Railway

Since Railway doesn't support committing binary files, you need to provide the Firebase service account credentials as an environment variable.

### Step 1: Get Your Firebase Service Account Key

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project: **system-32-70354**
3. Go to **Project Settings** → **Service Accounts**
4. Click **Generate New Private Key**
5. A JSON file will download: `serviceAccountKey.json`

### Step 2: Add to Railway

1. Go to your Railway project dashboard
2. Select the **interview-ai** service
3. Click on the **Variables** tab
4. Click **Add Variable**
5. Set the following:
   - **Key:** `FIREBASE_SERVICE_ACCOUNT_JSON`
   - **Value:** Copy the entire contents of `serviceAccountKey.json` (the raw JSON text)

   Example format:

   ```json
   {"type":"service_account","project_id":"system-32-70354","private_key_id":"...","private_key":"-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",...}
   ```

### Step 3: Optional - Other Environment Variables

If needed, add these variables to Railway:

- `GEMINI_API_KEY` - Your Gemini API key
- `LOG_LEVEL` - DEBUG, INFO, WARNING, ERROR
- `WHISPER_MODEL` - tiny, base, small, medium, large

### Step 4: Deploy

Push your changes and Railway will automatically redeploy:

```bash
git add -A
git commit -m "Update Firebase initialization for Railway deployment"
git push
```

### Verification

After deployment, check the Railway logs. You should see:

```
✅ Firebase credentials loaded from FIREBASE_SERVICE_ACCOUNT_JSON environment variable
✅ Firebase Admin initialized successfully
```

Not:

```
❌ Failed to initialize Firebase: [Errno 2] No such file or directory
```

## Local Development

For local development, you can use either:

1. **Environment Variable Method** (recommended - matches Railway):

   ```bash
   export FIREBASE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'
   python3 main.py
   ```

2. **File Method** (legacy):
   - Place `serviceAccountKey.json` in the project root
   - Set `FIREBASE_CREDENTIALS_PATH=serviceAccountKey.json` in `.env`

## Troubleshooting

### "No such file or directory: serviceAccountKey.json"

- Make sure `FIREBASE_SERVICE_ACCOUNT_JSON` is set in Railway variables
- Check that the JSON content is valid (no extra spaces or quotes)

### Firebase features still not working

- Verify the service account has appropriate permissions in Firebase Console
- Check Railway logs for detailed error messages
- Ensure the `firestore` database is created in your Firebase project

## Security Notes

⚠️ **NEVER commit `serviceAccountKey.json` to Git**

The file is already in `.gitignore` to prevent accidental commits. Keep this file safe and only share the contents through secure channels like Railway's dashboard.
