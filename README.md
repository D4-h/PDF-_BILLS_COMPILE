# 📄 Google Drive PDF Merger

A Streamlit app that merges PDFs from Google Drive folders based on date ranges. The date is extracted from folder names.

## Features

✅ **Connect to Google Drive** via OAuth 2.0 (read-only access)  
✅ **Browse nested folders** - recursively scans all subfolders  
✅ **Date-based filtering** - extracts dates from folder names  
✅ **Select date range** - merge PDFs only from specific dates  
✅ **Automatic merging** - combines PDFs chronologically  
✅ **Download** - get your merged PDF instantly  

## Supported Date Formats in Folder Names

The app recognizes these date patterns:
- `2024-10-10`
- `2024_10_10`
- `10-Oct-2024`
- `10_Oct_2024`
- `Oct 10 2024`
- `10th Oct 2024`

## Setup Instructions

### Part 1: Google Cloud Console Setup

1. **Go to Google Cloud Console**
   - Visit: https://console.cloud.google.com/

2. **Create a New Project**
   - Click "Select a project" → "New Project"
   - Name it: `PDF Merger` (or any name)
   - Click "Create"

3. **Enable Google Drive API**
   - In the search bar, type "Google Drive API"
   - Click on "Google Drive API"
   - Click "Enable"

4. **Configure OAuth Consent Screen**
   - Go to: APIs & Services → OAuth consent screen
   - Select "External" → Click "Create"
   - Fill in:
     - **App name**: `PDF Merger`
     - **User support email**: Your email
     - **Developer contact**: Your email
   - Click "Save and Continue"
   - On "Scopes" page: Click "Add or Remove Scopes"
     - Search for: `../auth/drive.readonly`
     - Select it and click "Update"
   - Click "Save and Continue"
   - On "Test users": Click "Add Users"
     - Add your Gmail address
   - Click "Save and Continue"

5. **Create OAuth 2.0 Credentials**
   - Go to: APIs & Services → Credentials
   - Click "+ Create Credentials" → "OAuth client ID"
   - Application type: "Web application"
   - Name: `PDF Merger Web Client`
   - **Authorized redirect URIs**: 
     - For local testing: `http://localhost:8501`
     - For Streamlit Cloud: `https://your-app-name.streamlit.app` (we'll update this later)
   - Click "Create"
   - **IMPORTANT**: Copy the `Client ID` and `Client Secret` - you'll need these!

### Part 2: Streamlit Cloud Deployment

1. **Push Code to GitHub**
   - Create a new GitHub repository
   - Upload these files:
     - `app.py`
     - `requirements.txt`
     - `README.md`
     - `.gitignore` (add `secrets.toml` to it)
   - **DO NOT** commit any secrets or credentials

2. **Deploy to Streamlit Cloud**
   - Go to: https://share.streamlit.io/
   - Click "New app"
   - Connect your GitHub account
   - Select your repository
   - Main file path: `app.py`
   - Click "Deploy"

3. **Note Your App URL**
   - After deployment, you'll get a URL like: `https://your-app-name.streamlit.app`
   - **Copy this URL** - you need it for the next step!

4. **Update Google OAuth Redirect URI**
   - Go back to Google Cloud Console
   - Go to: APIs & Services → Credentials
   - Click on your OAuth client ID
   - Under "Authorized redirect URIs", add:
     - `https://your-app-name.streamlit.app` (your actual Streamlit app URL)
   - Click "Save"

5. **Configure Streamlit Secrets**
   - In Streamlit Cloud, go to your app
   - Click the menu (⋮) → "Settings" → "Secrets"
   - Add the following (replace with your actual values):

```toml
[google]
client_id = "YOUR_CLIENT_ID_HERE.apps.googleusercontent.com"
client_secret = "YOUR_CLIENT_SECRET_HERE"
redirect_uri = "https://your-app-name.streamlit.app"
```

   - Click "Save"
   - Your app will automatically restart

### Part 3: Using the App

1. **Open Your Streamlit App**
   - Visit: `https://your-app-name.streamlit.app`

2. **Connect Google Drive**
   - Click "Connect Google Drive"
   - Sign in with your Google account
   - Grant read-only access to your Drive

3. **Select Folders**
   - The app will scan all your folders
   - Select folders you want to merge PDFs from
   - Folders must have dates in their names

4. **Choose Date Range**
   - Select "From date" and "To date"
   - Click "Find and Merge PDFs"

5. **Download**
   - Wait for the merge to complete
   - Click "Download Merged PDF"

## Local Testing (Optional)

If you want to test locally before deploying:

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Create secrets file**:
   - Create `.streamlit/secrets.toml`:
   ```toml
   [google]
   client_id = "YOUR_CLIENT_ID"
   client_secret = "YOUR_CLIENT_SECRET"
   redirect_uri = "http://localhost:8501"
   ```

3. **Run the app**:
   ```bash
   streamlit run app.py
   ```

4. **Open browser**:
   - Go to: http://localhost:8501

## Troubleshooting

### "OAuth Error: redirect_uri_mismatch"
- Make sure your Streamlit app URL exactly matches the redirect URI in Google Cloud Console
- Common mistake: forgetting `https://` or having a trailing `/`

### "No folders with recognizable dates found"
- Check your folder names - they must contain dates like `2024-10-10` or `10-Oct-2024`
- The app shows supported formats in the footer

### "Authorization Error: Access Blocked"
- In Google Cloud Console, make sure you added your email to "Test users"
- Make sure the OAuth consent screen is published (or in Testing mode with your email added)

### "Error merging PDFs"
- Some PDFs might be corrupted or password-protected
- The app will skip problematic PDFs and show a warning

## Privacy & Security

- ✅ **Read-only access**: The app can only read your files, never modify or delete
- ✅ **No data storage**: PDFs are processed in memory and not stored anywhere
- ✅ **Secure authentication**: Uses official Google OAuth 2.0
- ✅ **Public deployment**: Anyone can use the app, but they need to authorize their own Google account

## File Structure

```
pdf-merger/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
├── README.md          # This file
└── .gitignore         # Git ignore file
```

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Make sure all setup steps were completed
3. Check Streamlit Cloud logs for detailed error messages

## License

MIT License - Feel free to use and modify!

---

**Made with ❤️ using Streamlit**
