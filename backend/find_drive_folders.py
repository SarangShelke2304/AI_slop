
import asyncio
from src.uploaders.drive_uploader import drive_uploader

async def find_gameplay_folder():
    if not drive_uploader.service:
        print("Drive service not initialized!")
        return

    print("Listing all folders to help find the gameplay folder...")
    query = "mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    
    results = drive_uploader.service.files().list(
        q=query,
        pageSize=50,
        fields="files(id, name)"
    ).execute()
    
    folders = results.get('files', [])
    for f in folders:
        print(f"Folder: {f['name']} (ID: {f['id']})")

if __name__ == "__main__":
    asyncio.run(find_gameplay_folder())
