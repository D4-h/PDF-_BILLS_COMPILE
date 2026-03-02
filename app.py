import streamlit as st
import os
import io
import re
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from pypdf import PdfMerger, PdfReader
import tempfile
from pathlib import Path

# Page config
st.set_page_config(
    page_title="Google Drive PDF Merger",
    page_icon="📄",
    layout="wide"
)

# OAuth2 configuration
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_google_auth_flow():
    """Create OAuth flow from Streamlit secrets"""
    client_config = {
        "web": {
            "client_id": st.secrets["google"]["client_id"],
            "client_secret": st.secrets["google"]["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [st.secrets["google"]["redirect_uri"]]
        }
    }
    
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=st.secrets["google"]["redirect_uri"]
    )
    return flow

def parse_date_from_folder_name(folder_name):
    """
    Extract date from folder name. Supports various formats:
    - 2024-10-10
    - 10-Oct-2024
    - 10_Oct_2024
    - 2024_10_10
    - Oct 10 2024
    - 10th Oct 2024
    """
    folder_name = folder_name.strip()
    
    # Try different date patterns
    patterns = [
        (r'(\d{4})-(\d{2})-(\d{2})', '%Y-%m-%d'),  # 2024-10-10
        (r'(\d{4})_(\d{2})_(\d{2})', '%Y_%m_%d'),  # 2024_10_10
        (r'(\d{2})-([A-Za-z]{3})-(\d{4})', '%d-%b-%Y'),  # 10-Oct-2024
        (r'(\d{2})_([A-Za-z]{3})_(\d{4})', '%d_%b_%Y'),  # 10_Oct_2024
        (r'([A-Za-z]{3})\s+(\d{2})\s+(\d{4})', '%b %d %Y'),  # Oct 10 2024
        (r'(\d{2})(?:st|nd|rd|th)?\s+([A-Za-z]{3})\s+(\d{4})', '%d %b %Y'),  # 10th Oct 2024
    ]
    
    for pattern, date_format in patterns:
        match = re.search(pattern, folder_name, re.IGNORECASE)
        if match:
            try:
                date_str = match.group(0)
                # Remove ordinal suffixes (st, nd, rd, th)
                date_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)
                return datetime.strptime(date_str, date_format)
            except ValueError:
                continue
    
    return None

def get_drive_service(credentials):
    """Build Google Drive service"""
    return build('drive', 'v3', credentials=credentials)

def list_folders(service, parent_id=None, prefix=""):
    """Recursively list all folders with hierarchy"""
    folders = []
    query = "mimeType='application/vnd.google-apps.folder'"
    
    if parent_id:
        query += f" and '{parent_id}' in parents"
    else:
        query += " and 'root' in parents"
    
    query += " and trashed=false"
    
    results = service.files().list(
        q=query,
        fields="files(id, name)",
        pageSize=1000
    ).execute()
    
    items = results.get('files', [])
    
    for item in items:
        folder_info = {
            'id': item['id'],
            'name': item['name'],
            'display_name': f"{prefix}{item['name']}",
            'date': parse_date_from_folder_name(item['name'])
        }
        folders.append(folder_info)
        
        # Recursively get subfolders
        subfolders = list_folders(service, item['id'], prefix + "  ↳ ")
        folders.extend(subfolders)
    
    return folders

def find_pdfs_in_folder(service, folder_id, folder_date):
    """Find all PDFs in a folder and its subfolders"""
    pdfs = []
    
    def _search_folder(fid, date):
        # Get PDFs directly in this folder
        query = f"'{fid}' in parents and mimeType='application/pdf' and trashed=false"
        results = service.files().list(
            q=query,
            fields="files(id, name, createdTime, modifiedTime)",
            pageSize=1000
        ).execute()
        
        for pdf in results.get('files', []):
            pdfs.append({
                'id': pdf['id'],
                'name': pdf['name'],
                'date': date,
                'created': pdf.get('createdTime', ''),
                'modified': pdf.get('modifiedTime', '')
            })
        
        # Get subfolders
        query = f"'{fid}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(
            q=query,
            fields="files(id, name)",
            pageSize=1000
        ).execute()
        
        for subfolder in results.get('files', []):
            # Try to parse date from subfolder name, fallback to parent date
            subfolder_date = parse_date_from_folder_name(subfolder['name']) or date
            _search_folder(subfolder['id'], subfolder_date)
    
    _search_folder(folder_id, folder_date)
    return pdfs

def download_pdf(service, file_id):
    """Download PDF from Google Drive"""
    request = service.files().get_media(fileId=file_id)
    file_content = io.BytesIO()
    downloader = MediaIoBaseDownload(file_content, request)
    
    done = False
    while not done:
        status, done = downloader.next_chunk()
    
    file_content.seek(0)
    return file_content

def merge_pdfs(pdf_files, service, progress_bar):
    """Merge multiple PDFs into one"""
    merger = PdfMerger()
    
    for idx, pdf_info in enumerate(pdf_files):
        try:
            progress_bar.progress((idx + 1) / len(pdf_files), 
                                 text=f"Merging {pdf_info['name']}... ({idx+1}/{len(pdf_files)})")
            
            pdf_content = download_pdf(service, pdf_info['id'])
            merger.append(pdf_content)
        except Exception as e:
            st.warning(f"⚠️ Could not merge {pdf_info['name']}: {str(e)}")
    
    output = io.BytesIO()
    merger.write(output)
    merger.close()
    output.seek(0)
    
    return output

# Main app
st.title("📄 Google Drive PDF Merger")
st.markdown("Merge PDFs from Google Drive folders based on date ranges")

# Initialize session state
if 'credentials' not in st.session_state:
    st.session_state.credentials = None
if 'folders' not in st.session_state:
    st.session_state.folders = None
if 'selected_folders' not in st.session_state:
    st.session_state.selected_folders = []

# Authentication
if st.session_state.credentials is None:
    st.subheader("🔐 Step 1: Connect to Google Drive")
    
    # Check if returning from OAuth
    query_params = st.query_params
    
    if 'code' in query_params:
        # Exchange code for credentials
        try:
            flow = get_google_auth_flow()
            flow.fetch_token(code=query_params['code'])
            st.session_state.credentials = flow.credentials
            
            # Clear URL parameters
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"❌ Authentication failed: {str(e)}")
    else:
        # Show login button
        st.info("Click below to authorize access to your Google Drive (read-only)")
        
        if st.button("🔗 Connect Google Drive", type="primary"):
            flow = get_google_auth_flow()
            auth_url, _ = flow.authorization_url(prompt='consent')
            st.markdown(f"[Click here to authorize]({auth_url})")
            st.info("After authorizing, you'll be redirected back to this app")
else:
    # User is authenticated
    st.success("✅ Connected to Google Drive")
    
    if st.button("🔓 Disconnect"):
        st.session_state.credentials = None
        st.session_state.folders = None
        st.session_state.selected_folders = []
        st.rerun()
    
    # Load folders
    if st.session_state.folders is None:
        with st.spinner("📂 Loading your Google Drive folders..."):
            service = get_drive_service(st.session_state.credentials)
            st.session_state.folders = list_folders(service)
    
    st.subheader("📁 Step 2: Select Folders")
    
    # Filter folders with dates
    dated_folders = [f for f in st.session_state.folders if f['date'] is not None]
    
    if not dated_folders:
        st.warning("⚠️ No folders with recognizable dates found. Folder names should contain dates like '2024-10-10', '10-Oct-2024', etc.")
    else:
        st.info(f"Found {len(dated_folders)} folders with dates")
        
        # Show folder selection
        selected_folder_names = st.multiselect(
            "Select folders to merge PDFs from:",
            options=[f['display_name'] for f in dated_folders],
            help="Select one or more folders. PDFs from all selected folders will be merged."
        )
        
        # Update selected folders in session state
        st.session_state.selected_folders = [
            f for f in dated_folders if f['display_name'] in selected_folder_names
        ]
        
        if st.session_state.selected_folders:
            st.subheader("📅 Step 3: Select Date Range")
            
            # Get min and max dates from selected folders
            folder_dates = [f['date'] for f in st.session_state.selected_folders]
            min_date = min(folder_dates).date()
            max_date = max(folder_dates).date()
            
            col1, col2 = st.columns(2)
            with col1:
                from_date = st.date_input("From date:", value=min_date, min_value=min_date, max_value=max_date)
            with col2:
                to_date = st.date_input("To date:", value=max_date, min_value=min_date, max_value=max_date)
            
            if from_date > to_date:
                st.error("❌ 'From date' must be before 'To date'")
            else:
                # Filter folders by date range
                filtered_folders = [
                    f for f in st.session_state.selected_folders
                    if from_date <= f['date'].date() <= to_date
                ]
                
                if not filtered_folders:
                    st.warning(f"⚠️ No folders found in date range {from_date} to {to_date}")
                else:
                    st.success(f"✅ Found {len(filtered_folders)} folders in selected date range")
                    
                    # Show preview
                    with st.expander("📋 Preview selected folders"):
                        for folder in sorted(filtered_folders, key=lambda x: x['date']):
                            st.write(f"• **{folder['date'].strftime('%Y-%m-%d')}**: {folder['name']}")
                    
                    st.subheader("🔄 Step 4: Merge PDFs")
                    
                    if st.button("🚀 Find and Merge PDFs", type="primary"):
                        service = get_drive_service(st.session_state.credentials)
                        
                        # Find all PDFs
                        all_pdfs = []
                        
                        with st.spinner("🔍 Scanning folders for PDFs..."):
                            progress = st.progress(0)
                            for idx, folder in enumerate(filtered_folders):
                                progress.progress((idx + 1) / len(filtered_folders), 
                                                text=f"Scanning {folder['name']}...")
                                pdfs = find_pdfs_in_folder(service, folder['id'], folder['date'])
                                all_pdfs.extend(pdfs)
                        
                        if not all_pdfs:
                            st.warning("⚠️ No PDFs found in selected folders")
                        else:
                            # Sort by date
                            all_pdfs.sort(key=lambda x: (x['date'], x['name']))
                            
                            st.success(f"✅ Found {len(all_pdfs)} PDFs")
                            
                            # Show preview
                            with st.expander("📄 PDFs to be merged (in order)"):
                                for pdf in all_pdfs:
                                    st.write(f"• **{pdf['date'].strftime('%Y-%m-%d')}**: {pdf['name']}")
                            
                            # Merge PDFs
                            st.info("🔄 Merging PDFs... This may take a while.")
                            merge_progress = st.progress(0)
                            
                            try:
                                merged_pdf = merge_pdfs(all_pdfs, service, merge_progress)
                                
                                st.success("✅ PDFs merged successfully!")
                                
                                # Generate filename
                                filename = f"merged_pdfs_{from_date}_to_{to_date}.pdf"
                                
                                # Download button
                                st.download_button(
                                    label="⬇️ Download Merged PDF",
                                    data=merged_pdf,
                                    file_name=filename,
                                    mime="application/pdf",
                                    type="primary"
                                )
                                
                                # Show stats
                                st.metric("Total PDFs Merged", len(all_pdfs))
                                st.metric("Date Range", f"{from_date} to {to_date}")
                                
                            except Exception as e:
                                st.error(f"❌ Error merging PDFs: {str(e)}")

# Footer
st.markdown("---")
st.markdown("💡 **Tip**: Folder names should contain dates like `2024-10-10`, `10-Oct-2024`, or `Oct 10 2024`")
