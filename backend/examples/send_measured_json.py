"""Forward a sensor record from a real data source to SolarTree AI.

Requires JSON file with actual sensor measurements, never creates fake values.
Usage from backend directory:
  set SOLARTREE_DEVICE_KEY=<secret device telemetry key>
  python examples/send_measured_json.py --code IVAN-TREE-0001 --file readings.json --base http://192.168.1.20:8000

Python standard library only. For LAN testing use HTTP; for internet use HTTPS and proper certificates.
"""
import argparse
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

REQUIRED={'power_w','temperature_c','humidity_pct','h2_sensor_value','water_pct'}
OPTIONAL={'oxygen_flow_lph','electrolyzer_power_w'}


def main():
    p=argparse.ArgumentParser(description='Send a real sensor JSON record to SolarTree AI')
    p.add_argument('--code',required=True)
    p.add_argument('--file',required=True,help='JSON produced from actual sensors')
    p.add_argument('--base',default='http://127.0.0.1:8000',help='FastAPI address reachable from this computer')
    args=p.parse_args()
    key=os.environ.get('SOLARTREE_DEVICE_KEY','')
    if not key: p.error('Set SOLARTREE_DEVICE_KEY to the PRIVATE device telemetry key.')
    payload=json.loads(Path(args.file).read_text(encoding='utf-8'))
    if not isinstance(payload,dict): p.error('File must contain a single JSON object.')
    missing=REQUIRED-set(payload)
    if missing: p.error(f'Missing sensor fields: {", ".join(sorted(missing))}')
    unsupported=set(payload)-(REQUIRED|OPTIONAL)
    if unsupported: p.error(f'Unexpected fields: {", ".join(sorted(unsupported))}')
    if not all(isinstance(x,(float,int)) and not isinstance(x,bool) for x in payload.values() if x is not None):
        p.error('All fields must contain real numeric measurements or null for optional sensors.')
    url=f'{args.base.rstrip("/")}/api/device/{args.code.strip().upper()}/reading'
    req=Request(url,data=json.dumps(payload).encode('utf-8'),method='POST',
                headers={'Content-Type':'application/json','X-Device-Key':key})
    try:
        with urlopen(req,timeout=15) as resp:
            print(f'Received {resp.status}: {resp.read().decode("utf-8")}')
    except HTTPError as exc:
        print(f'API returned {exc.code}: {exc.read().decode("utf-8",errors="replace")}')
        raise SystemExit(1)
    except URLError as exc:
        print(f'Cannot reach backend: {exc.reason}')
        raise SystemExit(1)

if __name__=='__main__': main()
