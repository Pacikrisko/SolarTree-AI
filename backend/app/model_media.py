"""Trusted, service-provisioned model imagery, shared by all units of a model."""
from pathlib import Path
from fastapi import HTTPException
from .catalog import MODELS

ROOT = Path(__file__).resolve().parents[1] / 'model_media'
MIMES = {'.jpg':'image/jpeg', '.jpeg':'image/jpeg', '.png':'image/png', '.webp':'image/webp',
         '.mp4':'video/mp4', '.webm':'video/webm', '.svg':'image/svg+xml'}

def find_model_media(model_code: str):
    if model_code not in MODELS:
        raise HTTPException(status_code=404, detail='Непознат модел')
    for suffix, mimetype in MIMES.items():
        path = ROOT / f'{model_code}{suffix}'
        if path.is_file():
            return path, mimetype
    raise HTTPException(status_code=404, detail='За модела няма зададено изображение')

def media_kind(model_code: str):
    try:
        _, mime = find_model_media(model_code)
    except HTTPException:
        return None
    return 'video' if mime.startswith('video/') else 'image'
