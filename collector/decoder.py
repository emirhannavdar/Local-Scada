import struct


TYPE_FORMATS = {
    "INT16": (1, ">h"),
    "UINT16": (1, ">H"),
    "INT32": (2, ">i"),
    "UINT32": (2, ">I"),
    "FLOAT16": (1, ">e"),
    "FLOAT32": (2, ">f"),
    "FLOAT64": (4, ">d"),
}


def prepare_bytes(
    raw_registers,
    word_order,
    byte_order
):

    words = [
        value.to_bytes(
            2,
            byteorder="big",
            signed=False
        )
        for value in raw_registers
    ]

    if byte_order == "LITTLE":
        words = [
            word[::-1]
            for word in words
        ]

    if word_order in ("CDAB", "DCBA"):
        words.reverse()

    return b"".join(words)


def decode_string(
    raw_registers,
    word_order,
    byte_order
):

    raw_bytes = prepare_bytes(
        raw_registers,
        word_order,
        byte_order
    )

    return (
        raw_bytes
        .rstrip(b"\x00")
        .decode("utf-8", errors="replace")
    )


def decode_register(
    raw_registers,
    register
):

    data_type = (
        register["veri_tipi"]
        or ""
    ).upper()

    word_order = (
        register["word_order"]
        or "ABCD"
    ).upper()

    byte_order = (
        register["byte_order"]
        or "BIG"
    ).upper()

    multiplier = float(
        register["carpan"]
        if register["carpan"] is not None
        else 1
    )

    if not raw_registers:
        raise Exception(
            "Register verisi boş"
        )

    if data_type == "BOOL":
        return raw_registers[0] != 0

    if data_type == "STRING":
        return decode_string(
            raw_registers,
            word_order,
            byte_order
        )

    if data_type == "ENUM":
        return raw_registers[0]

    if data_type not in TYPE_FORMATS:
        raise Exception(
            f"Desteklenmeyen veri tipi: {data_type}"
        )

    required_count, format_code = (
        TYPE_FORMATS[data_type]
    )

    if len(raw_registers) != required_count:
        raise Exception(
            f"{data_type} için "
            f"{required_count} register gerekli, "
            f"{len(raw_registers)} geldi"
        )

    raw_bytes = prepare_bytes(
        raw_registers,
        word_order,
        byte_order
    )

    value = struct.unpack(
        format_code,
        raw_bytes
    )[0]

    return value * multiplier