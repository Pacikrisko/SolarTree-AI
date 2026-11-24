"""Format and size checks for catalog media imported by the operator."""
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
