from .binIO import BinaryMemoryIO


class LMSException(Exception):
    """Signals that some exception occurred while dealing with MSBT/MSBF data."""
    pass


# ----------------------------------------------------------------------------------------------------------------------
# String encoding
# ----------------------------------------------------------------------------------------------------------------------
def encoding_to_charset(encoding: int, is_big_endian: bool) -> str:
    if encoding == 0:
        return "utf-8"
    elif encoding == 1:
        return "utf-16-be" if is_big_endian else "utf-16-le"
    else:
        raise LMSException(f"Unsupported encoding type {encoding} found")


def charset_to_encoding(charset: str) -> int:
    if charset == "utf-8":
        return 0
    elif charset in ["utf-16-be", "utf-16-le"]:
        return 1
    else:
        raise LMSException(f"Unsupported charset {charset} found")


# ----------------------------------------------------------------------------------------------------------------------
# Hash tables
# ----------------------------------------------------------------------------------------------------------------------
def find_greater_prime(val: int) -> int:
    """
    Calculates and returns the first prime number that is greater than the specified input value. This is loosely based
    on the 6k+/-1 optimization algorithm for testing a number's primality.

    :param val: The starting value.
    :return: The first prime number that follows the input value.
    """
    # Standard cases
    if val < 5:
        if val < 2:   # Only even prime number
            return 2
        if val == 2:  # Needed due to "val % 3" below
            return 3
        return 5      # Needed due to "val % 5" below

    # Start at next odd number
    val = val + 2 if val & 1 else val + 1

    while True:
        if val % 3 == 0 or val % 5 == 0:
            val += 2  # Go to next odd number
            continue

        i = 5
        prime = True
        while i * i <= val and prime:
            if val % i == 0 or val % (i + 2) == 0:
                prime = False
            i += 6

        if prime:
            break
        else:
            val += 2  # Go to next odd number

    return val


def calc_hash_bucket_index(encoded_string: str, buckets: int) -> int:
    """
    Given the specified number of hash buckets, this function determines which bucket the label should be placed in.
    This is done by calculating the hash over the byte string and calculating the modulo of the hash and number of
    buckets.

    :param encoded_string: The encoded string that will be hashed.
    :param buckets: The number of available hash buckets.
    :return: The hash bucket index.
    """
    hsh = 0
    for b in encoded_string:
        hsh = (hsh * 0x492 + b) & 0xFFFFFFFF
    return hsh % buckets


def unpack_hash_table(stream: BinaryMemoryIO) -> dict[int, str]:
    off_start = stream.tell()
    num_buckets = stream.read_s32()
    off_buckets = stream.tell()

    label_indices: dict[int, str] = {}

    for i in range(num_buckets):
        stream.seek(off_buckets + i * 8)
        num_entries = stream.read_s32()
        off_labels = stream.read_s32()

        stream.seek(off_start + off_labels)

        for j in range(num_entries):
            len_label = stream.read_u8()
            label = stream.read(len_label).decode("ascii")
            index = stream.read_s32()
            label_indices[index] = label

    return label_indices


def pack_hash_table(stream: BinaryMemoryIO, labels: list[tuple[int, str]], num_buckets: int):
    # Initialize buckets and write count
    buckets = [list() for _ in range(num_buckets)]
    stream.write_s32(num_buckets)

    # Sort labels into buckets
    for label_id, label in labels:
        packed_label = label.encode("ascii")

        if len(packed_label) > 255:
            raise LMSException(f"Label name {label} too long")

        bucket_index = calc_hash_bucket_index(packed_label, num_buckets)
        buckets[bucket_index].append((packed_label, label_id))

    # Write all buckets
    off_labels = 0x04 + num_buckets * 0x08

    for bucket in buckets:
        stream.write_s32(len(bucket))
        stream.write_s32(off_labels)
        next_offset = stream.tell()
        stream.seek(off_labels)

        for packed_label, label_id in bucket:
            stream.write_u8(len(packed_label))
            stream.write(packed_label)
            stream.write_s32(label_id)

        off_labels = stream.tell()
        stream.seek(next_offset)
