
import asyncio
from src.uploaders.drive_uploader import drive_uploader
from src.config import settings

async def debug_drive():
    print(f"Checking Folder ID: {settings.DRIVE_INPUT_FOLDER_ID}")
    if not drive_uploader.service:
        print("Drive service not initialized!")
        return

    # 1. Broad search (no mimetype filter)
    query = f"'{settings.DRIVE_INPUT_FOLDER_ID}' in parents and trashed = false"
    print(f"Running Broad Query: {query}")
    
    results = drive_uploader.service.files().list(
        q=query,
        pageSize=100,
        fields="files(id, name, mimeType, size)"
    ).execute()
    
    files = results.get('files', [])
    print(f"Found {len(files)} total files in folder.")
    for f in files:
        print(f"- {f['name']} ({f['mimeType']}) ID: {f['id']}")

    # 2. Check permissions
    try:
        about = drive_uploader.service.about().get(fields="user").execute()
        print(f"Authenticated as: {about['user']['emailAddress']}")
    except Exception as e:
        print(f"Could not get user info: {e}")

if __name__ == "__main__":
    asyncio.run(debug_drive())
