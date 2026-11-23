"""Service-only offline utility. Example: python provision_model_media.py --model ST-URBAN-2KW --file model.jpg"""
from pathlib import Path
import argparse, shutil
from app.catalog import MODELS
from app.media import validate_signature, ALLOWED
from app.model_media import ROOT

parser = argparse.ArgumentParser()
parser.add_argument('--model', required=True, choices=sorted(MODELS))
parser.add_argument('--file', required=True)
args=parser.parse_args()
source=Path(args.file).resolve()
if not source.is_file(): parser.error('Не е намерен файлът.')
mimes={v[0]: (mime,v[1]) for mime,v in ALLOWED.items()}
if source.suffix.lower() not in mimes: parser.error('Форматът трябва да е JPG, PNG, WebP, MP4 или WebM.')
mime, limit = mimes[source.suffix.lower()]
if source.stat().st_size > limit: parser.error('Файлът надвишава максималния допустим размер.')
with source.open('rb') as f: first=f.read(20)
if not validate_signature(mime,first): parser.error('Файловият формат не отговаря на разширението.')
ROOT.mkdir(parents=True,exist_ok=True)
for file in ROOT.glob(args.model + '.*'):
    file.unlink()
target=ROOT / (args.model + source.suffix.lower())
shutil.copyfile(source,target)
print('Модел:',args.model,'\nОфициален медиен файл:',target)
