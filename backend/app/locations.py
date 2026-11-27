"""Offline Bulgarian settlement coordinates from Kostadin/Places-in-Bulgaria (MIT)."""
import re
from functools import lru_cache
from pathlib import Path

LETTERS=dict(zip('абвгдежзийклмнопрстуфхцчшщъьюя',
                 'a b v g d e zh z i y k l m n o p r s t u f h ts ch sh sht a y yu ya'.split()))

def key(text):
    text=text.casefold().replace('ия','ia')
    text=''.join(LETTERS.get(ch,ch) for ch in text)
    return ' '.join(re.findall('[a-z0-9]+',text))

@lru_cache(maxsize=1)
def places():
    index={}
    for line in Path(__file__).with_name('bg_places.tsv').read_text(encoding='utf8').splitlines():
        name,municipality,region,lat,lng=line.split('\t')
        index.setdefault(key(name),[]).append((key(municipality),key(region),(float(lat),float(lng))))
    return index

def locate(text):
    parts=[key(re.sub(r'^(?:гр\.|с\.|град |село |обл\.|общ\.)\s*','',part.strip(),flags=re.I)) for part in text.split(',')]
    aliases={'sofiya':'sofia','bourgas':'burgas','rousse':'ruse','turnovo':'tarnovo'}
    name=' '.join(aliases.get(word,word) for word in parts[0].split())
    matches=places().get(name,[])
    if len(matches)>1:
        matches=[row for row in matches if any(p in row[:2] for p in parts[1:] if p)]
    return matches[0][2] if len(matches)==1 else (None,None)
