import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import math
import time

from collector.api_client import API_BASE_URL, get_data


def active(row):
    return row.get('aktif', True) not in (False, 0)


def diagnose(device_id=None, host='127.0.0.1', port=5420, maximum=10):
    config, errors = {}, []
    print(f'API | {API_BASE_URL}', flush=True)
    def fetch(path):
        started = time.monotonic()
        return get_data(path), round(time.monotonic() - started, 2)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fetch, path): path for path in ('device', 'readGroup', 'register', 'tag', 'measurement')}
        for future in as_completed(futures):
            path = futures[future]
            try:
                rows, elapsed = future.result()
                config[path] = rows
                print(f'API_OK | /{path} | {len(rows)} kayit | {elapsed}s', flush=True)
            except Exception as error:
                errors.append(path)
                print(f'API_ERROR | {error}', flush=True)
    if errors:
        print('STOP | API listeleri okunamadi. Docs acilmasi DB endpointlerinin cevap verdigini kanitlamaz.', flush=True)
        return 2
    devices = [d for d in config['device'] if (str(d['id']) == str(device_id) if device_id is not None else d.get('ip') == host and d.get('port') == port)]
    if len(devices) != 1:
        print('DEVICE_SELECT | Tam bir cihaz eslesmeli; --device-id kullan.', flush=True)
        for d in config['device']:
            print(f"  #{d['id']} | {d.get('ad', d.get('name'))} | {d.get('ip')}:{d.get('port')} | Unit {d.get('slave_id')}", flush=True)
        return 2
    d = devices[0]
    print(f"DEVICE | #{d['id']} | {d.get('protokol')} | {d.get('ip')}:{d.get('port')} | Unit {d.get('slave_id')}", flush=True)
    if not active(d) or d.get('bakim_modu'):
        print('STOP | Cihaz pasif veya bakimda; collector okumaz.', flush=True)
        return 2
    groups = {g['id']: g for g in config['readGroup'] if g.get('cihaz_id') == d['id'] and active(g) and g.get('function_code') in (3, 4)}
    regs = [r for r in config['register'] if r.get('cihaz_id') == d['id'] and active(r) and r.get('okuma_grubu_id') in groups and r.get('function_code') == groups[r['okuma_grubu_id']]['function_code']]
    tags = [t for t in config['tag'] if t.get('cihaz_id') == d['id'] and active(t) and any(r['id'] == t.get('register_id') for r in regs)]
    print(f'CHAIN | {len(groups)} aktif grup | {len(regs)} register | {len(tags)} bagli tag', flush=True)
    if not regs or not tags:
        print('STOP | Okuma grubu -> register -> tag zinciri eksik. Arayuzde Profilden okuma kur veya mevcut kayitlari duzelt.', flush=True)
        return 2
    # Use exactly the project's Modbus adapter and decoder, not a second codec.
    from collector.modbus_client import create_client, read_register_range
    from collector.decoder import decode_register
    lines = get_data('serialLine') if d.get('protokol') == 'MODBUS_RTU' else []
    client = None
    failed = False
    try:
        client = create_client(d, lines)
        if not client.connect():
            raise ConnectionError('Modbus TCP / RTU baglantisi kurulamadi')
        for r in regs[:maximum]:
            address, count, fc = int(r['baslangic_adresi']), int(r['register_sayisi']), int(r['function_code'])
            if fc not in (3, 4) or address < 0 or count < 1 or count > 125 or address + count > 65536:
                failed = True
                print(f"CONFIG_ERROR | register #{r['id']} | PDU / FC / boyut gecersiz", flush=True)
                continue
            try:
                raw = read_register_range(client, d, fc, address, count)
                value = decode_register(raw, r)
                if isinstance(value, (int, float)) and not math.isfinite(value):
                    raise ValueError('NaN / Infinity')
                own_tags = [t for t in tags if t.get('register_id') == r['id']]
                samples = [m for m in config['measurement'] if any(str(t['id']) == str(m.get('tag_id')) for t in own_tags)]
                print(f"MODBUS_OK | register #{r['id']} | FC{fc:02} | PDU={address} count={count} | raw={raw} | decoded={value} {r.get('birim', '')} | {r.get('word_order')} / {r.get('byte_order')}", flush=True)
                print('API_COMPARE | ' + json.dumps(samples, ensure_ascii=False, default=str), flush=True)
            except Exception as error:
                failed = True
                print(f"MODBUS_ERROR | register #{r['id']} | FC{fc:02} PDU={address} | {type(error).__name__}: {error}", flush=True)
    except Exception as error:
        failed = True
        print(f'MODBUS_ERROR | {type(error).__name__}: {error}', flush=True)
    finally:
        if client is not None:
            client.close()
    print('DONE | Salt okunur kontrol tamamlandi; API veya Modbus yazma istegi gonderilmedi.', flush=True)
    return 1 if failed else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device-id', type=int)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=5420)
    parser.add_argument('--max-registers', type=int, default=10)
    args = parser.parse_args()
    if not 1 <= args.max_registers <= 125:
        parser.error('--max-registers 1-125 arasinda olmali')
    raise SystemExit(diagnose(args.device_id, args.host, args.port, args.max_registers))
