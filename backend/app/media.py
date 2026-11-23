"""Safe, account-scoped media storage for a SolarTree device.

Media are not publicly mounted. Routes in main.py authorize every read or write.
"""
from pathlib import Path
import os
import uuid
from fastapi import HTTPException, UploadFile

ROOT = Path(os.getenv('SOLARTREE_MEDIA_DIR', str(Path(__file__).resolve().parents[1] / 'user_media'))).resolve()
MAX_IMAGE = 12 * 1024 * 1024
MAX_VIDEO = 75 * 1024 * 1024
ALLOWED = {
    'image/jpeg': ('.jpg', MAX_IMAGE),
    'image/png': ('.png', MAX_IMAGE),
    'image/webp': ('.webp', MAX_IMAGE),
    'video/mp4': ('.mp4', MAX_VIDEO),
    'video/webm': ('.webm', MAX_VIDEO),
}


def validate_signature(content_type: str, first: bytes):
    if content_type == 'image/jpeg': return first.startswith(b'\xff\xd8\xff')
    if content_type == 'image/png': return first.startswith(b'\x89PNG\r\n\x1a\n')
    if content_type == 'image/webp': return first[:4] == b'RIFF' and first[8:12] == b'WEBP'
    if content_type == 'video/mp4': return first[4:8] == b'ftyp'
    if content_type == 'video/webm': return first.startswith(b'\x1a\x45\xdf\xa3')
    return False


async def save_media(upload: UploadFile) -> tuple[str, str]:
    mimetype = (upload.content_type or '').lower()
    if mimetype not in ALLOWED:
        raise HTTPException(status_code=415, detail='Избери JPG, PNG, WebP, MP4 или WebM файл.')
    extension, limit = ALLOWED[mimetype]
    first = await upload.read(20)
    if not validate_signature(mimetype, first):
        raise HTTPException(status_code=415, detail='Файлът не отговаря на избрания медиен формат.')
    ROOT.mkdir(parents=True, exist_ok=True)
    filename = uuid.uuid4().hex + extension
    path = ROOT / filename
    size = 0
    try:
        with path.open('wb') as handle:
            handle.write(first)
            size += len(first)
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk: break
                size += len(chunk)
                if size > limit:
                    raise HTTPException(status_code=413, detail=f'Файлът е твърде голям (лимит: {limit // (1024*1024)} MB).')
                handle.write(chunk)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()
    return filename, mimetype


def safe_media_path(filename: str) -> Path:
    # Persisted filenames are server-generated UUIDs, not client-provided paths.
    if not filename or not all(c in '0123456789abcdef' for c in filename.split('.')[0]) or len(filename.split('.')[0]) != 32:
        raise HTTPException(status_code=404, detail='Няма изображение или видео.')
    resolved = (ROOT / filename).resolve()
    if resolved.parent != ROOT or not resolved.is_file():
        raise HTTPException(status_code=404, detail='Медийният файл не е намерен.')
    return resolved
