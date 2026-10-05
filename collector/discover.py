import argparse
import json
import math
import struct
import sys
import time

from collector.api_client import get_data, post_data
from collector.modbus_client import (
    create_client,
    read_register_range,
    ModbusDeviceError,
    ModbusLinkError
)
from collector.decoder import decode_register, TYPE_FORMATS


# ---------------------------------------------------------------------------
# 1) Okunabilir adres tarama
# ---------------------------------------------------------------------------

def scan_valid_runs(
    client,
    device,
    function_code,
    low,
    high,
    chunk=100,
    progress=None
):
    """[low, high] icinde cihazin yanit verdigi bitisik adres araliklari.

    Buyuk blok okunur; basarisiz olursa ikiye bolunerek daraltilir. Boylece
    genis, bitisik haritalar az istekle, dagınık haritalar ise bisection ile
    taranir. Dönüs: [(baslangic, adet), ...] (artan, birlesik)."""

    valid = []
    reads = 0

    def probe(address, count):

        nonlocal reads

        reads += 1

        try:
            read_register_range(
                client,
                device,
                function_code,
                address,
                count
            )

            valid.append((address, count))
            return

        except ModbusDeviceError:
            pass

        if count == 1:
            return

        half = count // 2

        probe(address, half)
        probe(address + half, count - half)

    address = low

    while address <= high:

        count = min(chunk, high - address + 1)

        probe(address, count)

        if progress:
            progress(address, high, reads)

        address += count

    return merge_runs(valid), reads


def read_words(client, device, function_code, start, count, limit=125):
    """Modbus tek istekte en fazla 125 register okur; uzun araliklari boler."""

    words = []
    offset = 0

    while offset < count:

        part = min(limit, count - offset)

        words.extend(
            read_register_range(
                client,
                device,
                function_code,
                start + offset,
                part
            )
        )

        offset += part

    return words


def merge_runs(runs):

    merged = []

    for start, count in sorted(runs):

        if merged and start <= merged[-1][0] + merged[-1][1]:

            prev_start, prev_count = merged[-1]

            merged[-1] = (
                prev_start,
                max(
                    prev_count,
                    start + count - prev_start
                )
            )

        else:
            merged.append((start, count))

    return merged


# ---------------------------------------------------------------------------
# 2) Tip tahmini
# ---------------------------------------------------------------------------

def _pack(words, word_order):

    if word_order == "CDAB":
        words = list(reversed(words))

    return b"".join(
        w.to_bytes(2, "big")
        for w in words
    )


def as_float32(words, word_order):

    return struct.unpack(
        ">f",
        _pack(words, word_order)
    )[0]


def as_float64(words, word_order):

    return struct.unpack(
        ">d",
        _pack(words, word_order)
    )[0]


def plausible(value, low=1e-4, high=1e9):

    if not math.isfinite(value):
        return False

    if value == 0:
        return False

    return low <= abs(value) <= high


def infer_registers(address, samples, hints=None):
    """Bitisik bir okunabilir aralik icin register onerileri uretir.

    address: araligin baslangic adresi
    samples: [[word, ...], ...] ayni aralikten alinmis birden fazla okuma
    """

    hints = hints or {}
    n = len(samples[0])
    result = []
    i = 0

    def column(offset, count):
        return [s[offset:offset + count] for s in samples]

    # Kisa, izole adalar (cevresi gecersiz adres olan) tek bir register
    # olarak yorumlanir: yan yana iki ayri register olma ihtimali dusuktur.
    if not any(
        str(address + k) in hints for k in range(n)
    ):

        if n == 1:

            return [
                dict(address=address, count=1, type="UINT16",
                     word_order="ABCD", confidence="high")
            ]

        if n == 2:

            col = column(0, 2)

            for order in ("ABCD", "CDAB"):

                if all(plausible(as_float32(w, order)) for w in col):

                    return [
                        dict(address=address, count=2, type="FLOAT32",
                             word_order=order,
                             confidence=(
                                 "high" if order == "ABCD" else "low"
                             ))
                    ]

            return [
                dict(address=address, count=2, type="UINT32",
                     word_order="ABCD", confidence="low")
            ]

        if n == 4:

            col = column(0, 4)

            if all(
                plausible(as_float64(w, "ABCD"), 1e-4, 1e15)
                for w in col
            ):

                return [
                    dict(address=address, count=4, type="FLOAT64",
                         word_order="ABCD", confidence="high")
                ]

    while i < n:

        absolute = address + i
        hint = hints.get(str(absolute))

        # --- kullanici ipucu ---
        if hint and hint.get("type"):

            dtype = hint["type"].upper()
            count = TYPE_FORMATS.get(dtype, (1, None))[0]

            if i + count <= n:

                result.append(
                    dict(
                        address=absolute,
                        count=count,
                        type=dtype,
                        word_order=hint.get("word_order", "ABCD"),
                        confidence="hint"
                    )
                )

                i += count
                continue

        # --- FLOAT64 (4 word) ---
        if i + 4 <= n:

            col = column(i, 4)

            ok64 = all(
                plausible(as_float64(w, "ABCD"), 1e-4, 1e15)
                for w in col
            )

            # dusuk 32 bit (mantis) iki ayri makul FLOAT32 gibi gorunuyorsa
            # belirsizdir; yuksek 32 bit float32 olarak makulse F64 olma
            # ihtimali de yuksektir, fakat dusuk kisim 'rastgele' oldugu
            # icin cogu zaman makul float32 cikmaz.
            low_looks_float = all(
                plausible(as_float32(w[2:4], "ABCD"))
                for w in col
            )

            # Gercek bir FLOAT64'un dusuk 32 biti (mantis) sifir olmaz;
            # 'FLOAT32 + sifir dolgu' durumunu F64 sanma.
            low_nonzero = all(any(w[2:4]) for w in col)

            if ok64 and not low_looks_float and low_nonzero:

                result.append(
                    dict(
                        address=absolute,
                        count=4,
                        type="FLOAT64",
                        word_order="ABCD",
                        confidence="high"
                    )
                )

                i += 4
                continue

        # --- FLOAT32 (2 word) ---
        if i + 2 <= n:

            col = column(i, 2)

            for order in ("ABCD", "CDAB"):

                if order == "CDAB" and i + 3 <= n and all(
                    plausible(as_float32(w, "ABCD"))
                    for w in column(i + 1, 2)
                ):
                    # Bir sonraki konumda ABCD makul bir float var; buradaki
                    # 'CDAB' eslesmesi buyuk olasilikla sifir dolgu word'u +
                    # bir sonraki float'in ilk word'u. Hizayi koru.
                    continue

                if all(
                    plausible(as_float32(w, order))
                    for w in col
                ):

                    result.append(
                        dict(
                            address=absolute,
                            count=2,
                            type="FLOAT32",
                            word_order=order,
                            confidence=(
                                "high"
                                if order == "ABCD"
                                else "low"
                            )
                        )
                    )

                    i += 2
                    break

            else:
                order = None

            if result and result[-1]["address"] == absolute:
                continue

        # --- tek word: ham 16 bit ---
        result.append(
            dict(
                address=absolute,
                count=1,
                type="UINT16",
                word_order="ABCD",
                confidence="low"
            )
        )

        i += 1

    return result


# ---------------------------------------------------------------------------
# 3) Konfigurasyon olusturma
# ---------------------------------------------------------------------------

def signal_name(function_code, proposal, hints):

    hint = (hints or {}).get(str(proposal["address"]), {})

    return hint.get("name") or (
        f"{'hr' if function_code == 3 else 'ir'}_"
        f"{proposal['address']}"
    )


def apply_plan(device, plans, hints):
    """plans: {function_code: [(proposal, value), ...]}"""

    signals = get_data("signalDict")
    profile_registers = get_data("profile_register")
    groups = get_data("readGroup")
    registers = get_data("register")

    if not signals:
        raise SystemExit(
            "HATA | Sinyal sozlugunde hic kayit yok. Enum alanlari "
            "(cihaz_tipi, alarm_sinifi, ...) tahmin edilemedigi icin "
            "once arayuzden en az bir sinyal tanimi olustur; discover "
            "onu sablon olarak kullanir."
        )

    signal_template = signals[0]

    created = {"signal": 0, "profile": 0, "group": 0, "register": 0}

    for fc, items in plans.items():

        start = min(p["address"] for p, _ in items)
        end = max(p["address"] + p["count"] - 1 for p, _ in items)

        group = next(
            (
                g for g in groups
                if g["cihaz_id"] == device["id"]
                and g["function_code"] == fc
                and g.get("aktif", True)
            ),
            None
        )

        if group is None:

            group_id = post_data(
                "readGroup",
                {
                    "cihaz_id": device["id"],
                    "name": f"{device['ad']} AUTO FC0{fc}",
                    "function_code": fc,
                    "baslangic_adresi": start,
                    "bitis_adresi": end,
                    "okuma_periyodu_ms": 1000,
                    "maksimum_register": 125,
                    "aktif": True,
                    "aciklama": "collector.discover tarafindan olusturuldu"
                }
            )

            created["group"] += 1

        else:
            group_id = group["id"]

        for proposal, value in items:

            address = proposal["address"]

            exists = any(
                r["cihaz_id"] == device["id"]
                and r["function_code"] == fc
                and r["baslangic_adresi"] == address
                for r in registers
            )

            if exists:
                continue

            name = signal_name(fc, proposal, hints)
            hint = (hints or {}).get(str(address), {})
            unit = hint.get("unit", "")

            signal = next(
                (s for s in signals if s.get("sinyal_adi") == name),
                None
            )

            if signal is None:

                body = {
                    key: signal_template.get(key)
                    for key in (
                        "cihaz_tipi", "min_deger", "max_deger",
                        "alarm_sinifi", "arsiv_kurali", "okuma_sinifi",
                        "deadband", "periyot_saniye", "gosterim_formati"
                    )
                }

                body.update(
                    sinyal_adi=name,
                    aciklama=(
                        f"AUTO {proposal['type']} "
                        f"FC0{fc} PDU {address} "
                        f"({proposal['confidence']})"
                    ),
                    veri_tipi=proposal["type"],
                    birim=unit,
                    aktif=True
                )

                for key in ("min_deger", "max_deger", "deadband"):
                    if body.get(key) is None:
                        body[key] = 0.0

                if body.get("periyot_saniye") is None:
                    body["periyot_saniye"] = 1

                signal_id = post_data("signalDict", body)
                signals.append({**body, "id": signal_id})
                created["signal"] += 1

            else:
                signal_id = signal["id"]

            profile_register = next(
                (
                    p for p in profile_registers
                    if p.get("profil_id") == device["profil_id"]
                    and p["register_adresi"] == address
                    and p["function_code"] == fc
                ),
                None
            )

            if profile_register is None:

                profile_register_id = post_data(
                    "profile_register",
                    {
                        "profile_id": device["profil_id"],
                        "register_adresi": address,
                        "function_code": fc,
                        "register_sayisi": proposal["count"],
                        "veri_tipi": proposal["type"],
                        "byte_order": "BIG",
                        "word_order": proposal["word_order"],
                        "olcek": 1,
                        "offset_degeri": 0,
                        "bit_index": 0,
                        "sinyal_sozlugu_id": signal_id,
                        "aciklama": "AUTO"
                    }
                )

                profile_registers.append(
                    {
                        "id": profile_register_id,
                        "profil_id": device["profil_id"],
                        "register_adresi": address,
                        "function_code": fc
                    }
                )

                created["profile"] += 1

            else:
                profile_register_id = profile_register["id"]

            register_id = post_data(
                "register",
                {
                    "cihaz_id": device["id"],
                    "profil_register_id": profile_register_id,
                    "sinyal_sozlugu_id": signal_id,
                    "name": name,
                    "baslangic_adresi": address,
                    "register_sayisi": proposal["count"],
                    "function_code": fc,
                    "veri_tipi": proposal["type"],
                    "word_order": proposal["word_order"],
                    "byte_order": "BIG",
                    "birim": unit,
                    "carpan": 1,
                    "min_deger": 0,
                    "max_deger": 0,
                    "aktif": True,
                    "aciklama": "AUTO",
                    "okuma_grubu_id": group_id
                }
            )

            registers.append(
                {
                    "id": register_id,
                    "cihaz_id": device["id"],
                    "function_code": fc,
                    "baslangic_adresi": address
                }
            )

            created["register"] += 1

    return created


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def run(args):

    devices = get_data("device")

    device = next(
        (d for d in devices if d["id"] == args.device_id),
        None
    )

    if device is None:
        raise SystemExit(f"Cihaz #{args.device_id} bulunamadi")

    hints = {}

    if args.hints:
        with open(args.hints, encoding="utf-8") as f:
            hints = json.load(f)

    lines = (
        get_data("serialLine")
        if device["protokol"] == "MODBUS_RTU"
        else []
    )

    client = create_client(device, lines)

    if not client.connect():
        raise SystemExit("Modbus baglantisi kurulamadi")

    plans = {}

    try:

        for fc in args.fc:

            started = time.monotonic()

            def progress(address, high, reads):
                if args.verbose:
                    print(
                        f"  FC{fc:02} tarama {address}/{high} "
                        f"({reads} istek)",
                        file=sys.stderr,
                        flush=True
                    )

            runs, reads = scan_valid_runs(
                client,
                device,
                fc,
                args.start,
                args.end,
                args.chunk,
                progress
            )

            took = time.monotonic() - started

            print(
                f"FC{fc:02} | {len(runs)} okunabilir aralik | "
                f"{reads} istek | {took:.1f}s"
            )

            proposals = []

            for start, count in runs:

                samples = []

                for k in range(args.samples):

                    samples.append(
                        read_words(
                            client,
                            device,
                            fc,
                            start,
                            count
                        )
                    )

                    if k + 1 < args.samples:
                        time.sleep(args.interval)

                for proposal in infer_registers(
                    start,
                    samples,
                    hints
                ):

                    offset = proposal["address"] - start

                    raw = samples[-1][
                        offset:offset + proposal["count"]
                    ]

                    fake_register = {
                        "veri_tipi": proposal["type"],
                        "word_order": proposal["word_order"],
                        "byte_order": "BIG",
                        "carpan": 1
                    }

                    value = decode_register(raw, fake_register)

                    proposals.append((proposal, value))

            if not args.include_zero:

                # Uzun bitisik bloklardaki 0 degerli ham word'ler cogunlukla
                # dolgu (cihazin tanimsiz adresleri 0 dondurmesi) olur.
                # Kisa, izole adalardaki 0 degerler gercek register sayilir.
                long_runs = [
                    (s, c) for s, c in runs if c > 8
                ]

                def in_long_run(address):
                    return any(
                        s <= address < s + c for s, c in long_runs
                    )

                proposals = [
                    (p, v) for p, v in proposals
                    if not (
                        p["type"] == "UINT16"
                        and v == 0
                        and p["confidence"] != "hint"
                        and in_long_run(p["address"])
                    )
                ]

            plans[fc] = proposals

            for proposal, value in proposals:

                print(
                    f"  PDU {proposal['address']:>5} | "
                    f"{proposal['type']:<8} | "
                    f"{proposal['word_order']} | "
                    f"{proposal['confidence']:<5} | "
                    f"{value}"
                )

    except ModbusLinkError as e:
        raise SystemExit(f"Baglanti hatasi: {e}")

    finally:
        client.close()

    total = sum(len(v) for v in plans.values())

    print(f"\nToplam oneri: {total} register")

    if not args.apply:
        print(
            "Hicbir sey yazilmadi. Olusturmak icin --apply ekle; "
            "yanlis tip tahminleri icin --hints kullan."
        )
        return

    created = apply_plan(device, plans, hints)

    print(f"Olusturuldu: {created}")
    print(
        "Collector bir sonraki yapilandirma yenilemesinde (<=5 sn) "
        "tag'leri otomatik olusturup okumaya baslar."
    )


def main():

    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--device-id", type=int, required=True)
    parser.add_argument("--fc", type=lambda s: [int(x) for x in s.split(",")],
                        default=[3])
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=65535)
    parser.add_argument("--chunk", type=int, default=100)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("--hints")
    parser.add_argument("--include-zero", action="store_true",
                        help="Degeri 0 olan ham 16 bit registerlari da ekle")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args()

    for fc in args.fc:
        if fc not in (3, 4):
            parser.error("--fc yalnizca 3 ve/veya 4 olabilir")

    if not 0 <= args.start <= args.end <= 65535:
        parser.error("--start/--end 0..65535 araliginda olmali")

    if not 1 <= args.chunk <= 125:
        parser.error("--chunk 1..125 olmali")

    run(args)


if __name__ == "__main__":
    main()
