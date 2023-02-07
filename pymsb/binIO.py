import io
import struct
import os

__all__ = ["BinaryMemoryIO", "EOFException", "BOMException"]


class EOFException(Exception):
    """Signals an attempt at reading beyond a stream."""
    pass


class BOMException(Exception):
    """Signals that some value is not a proper BOM."""
    pass


class BinaryMemoryIO(io.BytesIO):
    """
    A buffered I/O implementation using an in-memory bytes buffer to store data. Provides methods to read or write
    primitive data.
    """
    __STR_BOOL__ = struct.Struct("?")
    __STR_U8__ = struct.Struct("B")
    __STR_S8__ = struct.Struct("b")
    __STR_U16_BE__ = struct.Struct(">H")
    __STR_U16_LE__ = struct.Struct("<H")
    __STR_S16_BE__ = struct.Struct(">h")
    __STR_S16_LE__ = struct.Struct("<h")
    __STR_U32_BE__ = struct.Struct(">I")
    __STR_U32_LE__ = struct.Struct("<I")
    __STR_S32_BE__ = struct.Struct(">i")
    __STR_S32_LE__ = struct.Struct("<i")
    __STR_U64_BE__ = struct.Struct(">Q")
    __STR_U64_LE__ = struct.Struct("<Q")
    __STR_S64_BE__ = struct.Struct(">q")
    __STR_S64_LE__ = struct.Struct("<q")
    __STR_F32_BE__ = struct.Struct(">f")
    __STR_F32_LE__ = struct.Struct("<f")
    __STR_F64_BE__ = struct.Struct(">d")
    __STR_F64_LE__ = struct.Struct("<d")

    def __init__(self, initial_bytes=bytes(), big_endian: bool = True):
        super().__init__(initial_bytes)
        self.__big_endian__ = big_endian

    def set_big_endian(self):
        """Forces the usage of big endian byte order when reading or writing."""
        self.__big_endian__ = True

    def set_little_endian(self):
        """Forces the usage of little endian byte order when reading or writing."""
        self.__big_endian__ = False

    def swap_byte_order(self):
        """Swaps the current byte order (big <-> little)."""
        self.__big_endian__ = not self.__big_endian__

    @property
    def is_big_endian(self) -> bool:
        """True if big endian byte order should be used, otherwise False."""
        return self.__big_endian__

    @property
    def is_little_endian(self) -> bool:
        """True if little endian byte order should be used, otherwise False."""
        return not self.__big_endian__

    @property
    def size(self) -> int:
        """Returns the current size in bytes."""
        old = self.tell()
        self.seek(0, os.SEEK_END)
        size = self.tell()
        self.seek(old)
        return size

    # ------------------------------------------------------------------------------------------------------------------

    def __get_struct__(self, big_endian_struct: struct.Struct, little_endian_struct: struct.Struct):
        return big_endian_struct if self.__big_endian__ else little_endian_struct

    def __read_primitive__(self, big_endian_struct: struct.Struct, little_endian_struct: struct.Struct):
        strct = self.__get_struct__(big_endian_struct, little_endian_struct)
        raw = self.read(strct.size)

        if len(raw) == strct.size:
            return strct.unpack_from(raw, 0)[0]
        else:
            raise EOFException

    def __write_primitive__(self, val, big_endian_struct: struct.Struct, little_endian_struct: struct.Struct):
        strct = self.__get_struct__(big_endian_struct, little_endian_struct)
        raw = strct.pack(val)
        self.write(raw)

    # ------------------------------------------------------------------------------------------------------------------

    def skip(self, count: int):
        """
        Skips the specified number of upcoming bytes. Negative values are not allowed.

        :param count: the number of bytes to skip by.
        """
        if count < 0:
            raise ValueError("Negative skipping is not allowed")

        self.seek(self.tell() + count)

    def read_u8(self):
        """Reads from the stream an unsigned byte ([0, 255]) and returns it."""
        v = self.read(1)

        if len(v) == 1:
            return v[0]
        else:
            raise EOFException

    def read_s8(self) -> int:
        """Reads from the stream a signed byte ([-128, 127]) and returns it."""
        return self.__read_primitive__(self.__STR_S8__, self.__STR_S8__)

    def read_bool(self) -> bool:
        """Reads from the stream an unsigned byte ([0, 255]) and returns it."""
        return self.__read_primitive__(self.__STR_BOOL__, self.__STR_BOOL__)

    def read_u16(self):
        """Reads from the stream an unsigned short ([0, 65535]) and returns it."""
        return self.__read_primitive__(self.__STR_U16_BE__, self.__STR_U16_LE__)

    def read_s16(self):
        """Reads from the stream a signed short ([-32768, 32767]) and returns it."""
        return self.__read_primitive__(self.__STR_S16_BE__, self.__STR_S16_LE__)

    def read_u32(self):
        """Reads from the stream an unsigned int ([0, 2^32-1]) and returns it."""
        return self.__read_primitive__(self.__STR_U32_BE__, self.__STR_U32_LE__)

    def read_s32(self):
        """Reads from the stream a signed int ([-2^31, 2^31-1]) and returns it."""
        return self.__read_primitive__(self.__STR_S32_BE__, self.__STR_S32_LE__)

    def read_u64(self):
        """Reads from the stream an unsigned long ([0, 2^64-1]) and returns it."""
        return self.__read_primitive__(self.__STR_U64_BE__, self.__STR_U64_LE__)

    def read_s64(self):
        """Reads from the stream a signed long ([-2^63, 2^63-1]) and returns it."""
        return self.__read_primitive__(self.__STR_S64_BE__, self.__STR_S64_LE__)

    def read_f32(self):
        """Reads from the stream a single-precision float and returns it."""
        return self.__read_primitive__(self.__STR_F32_BE__, self.__STR_F32_LE__)

    def read_f64(self):
        """Reads from the stream a double-precision float and returns it."""
        return self.__read_primitive__(self.__STR_F64_BE__, self.__STR_F64_LE__)

    # ------------------------------------------------------------------------------------------------------------------

    def write_u8(self, val: int):
        """Writes the specified unsigned byte to the stream."""
        self.__write_primitive__(val, self.__STR_U8__, self.__STR_U8__)

    def write_s8(self, val: int):
        """Writes the specified signed byte to the stream."""
        self.__write_primitive__(val, self.__STR_S8__, self.__STR_S8__)

    def write_bool(self, val: int):
        """Writes the specified bool to the stream."""
        self.__write_primitive__(val, self.__STR_BOOL__, self.__STR_BOOL__)

    def write_u16(self, val: int):
        """Writes the specified unsigned short to the stream."""
        self.__write_primitive__(val, self.__STR_U16_BE__, self.__STR_U16_LE__)

    def write_s16(self, val: int):
        """Writes the specified signed short to the stream."""
        self.__write_primitive__(val, self.__STR_S16_BE__, self.__STR_S16_LE__)

    def write_u32(self, val: int):
        """Writes the specified unsigned int to the stream."""
        self.__write_primitive__(val, self.__STR_U32_BE__, self.__STR_U32_LE__)

    def write_s32(self, val: int):
        """Writes the specified signed int to the stream."""
        self.__write_primitive__(val, self.__STR_S32_BE__, self.__STR_S32_LE__)

    def write_u64(self, val: int):
        """Writes the specified unsigned long to the stream."""
        self.__write_primitive__(val, self.__STR_U64_BE__, self.__STR_U64_LE__)

    def write_s64(self, val: int):
        """Writes the specified signed long to the stream."""
        self.__write_primitive__(val, self.__STR_S64_BE__, self.__STR_S64_LE__)

    def write_f32(self, val: float):
        """Writes the specified single-precision float to the stream."""
        self.__write_primitive__(val, self.__STR_F32_BE__, self.__STR_F32_LE__)

    def write_f64(self, val: float):
        """Writes the specified double-precision float to the stream."""
        self.__write_primitive__(val, self.__STR_F64_BE__, self.__STR_F64_LE__)
