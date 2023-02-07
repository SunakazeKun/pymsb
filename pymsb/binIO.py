import io
import struct
import os

__all__ = ["BinaryMemoryIO", "EOFException", "BOMException"]


class EOFException(Exception):
    pass


class BOMException(Exception):
    pass


class BinaryMemoryIO(io.BytesIO):
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
        self.__big_endian__ = True

    def set_little_endian(self):
        self.__big_endian__ = False

    def swap_byte_order(self):
        self.__big_endian__ = not self.__big_endian__

    @property
    def is_big_endian(self) -> bool:
        return self.__big_endian__

    @property
    def is_little_endian(self) -> bool:
        return not self.__big_endian__

    @property
    def size(self) -> int:
        old = self.tell()
        self.seek(0, os.SEEK_END)
        size = self.tell()
        self.seek(old)
        return size

    # ------------------------------------------------------------------------------------------------------------------

    def __get_struct__(self, big_endian_struct: struct.Struct, little_endian_struct: struct.Struct):
        if self.__big_endian__:
            return big_endian_struct
        else:
            return little_endian_struct

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
        self.seek(self.tell() + count)

    def read_u8(self):
        v = self.read(1)
        return v[0] if len(v) else None

    def read_s8(self):
        return self.__read_primitive__(self.__STR_S8__, self.__STR_S8__)

    def read_bool(self):
        return self.__read_primitive__(self.__STR_BOOL__, self.__STR_BOOL__)

    def read_u16(self):
        return self.__read_primitive__(self.__STR_U16_BE__, self.__STR_U16_LE__)

    def read_s16(self):
        return self.__read_primitive__(self.__STR_S16_BE__, self.__STR_S16_LE__)

    def read_u32(self):
        return self.__read_primitive__(self.__STR_U32_BE__, self.__STR_U32_LE__)

    def read_s32(self):
        return self.__read_primitive__(self.__STR_S32_BE__, self.__STR_S32_LE__)

    def read_u64(self):
        return self.__read_primitive__(self.__STR_U64_BE__, self.__STR_U64_LE__)

    def read_s64(self):
        return self.__read_primitive__(self.__STR_S64_BE__, self.__STR_S64_LE__)

    def read_f32(self):
        return self.__read_primitive__(self.__STR_F32_BE__, self.__STR_F32_LE__)

    def read_f64(self):
        return self.__read_primitive__(self.__STR_F64_BE__, self.__STR_F64_LE__)

    # ------------------------------------------------------------------------------------------------------------------

    def write_u8(self, val: int):
        self.__write_primitive__(val, self.__STR_U8__, self.__STR_U8__)

    def write_s8(self, val: int):
        self.__write_primitive__(val, self.__STR_S8__, self.__STR_S8__)

    def write_bool(self, val: int):
        self.__write_primitive__(val, self.__STR_BOOL__, self.__STR_BOOL__)

    def write_u16(self, val: int):
        self.__write_primitive__(val, self.__STR_U16_BE__, self.__STR_U16_LE__)

    def write_s16(self, val: int):
        self.__write_primitive__(val, self.__STR_S16_BE__, self.__STR_S16_LE__)

    def write_u32(self, val: int):
        self.__write_primitive__(val, self.__STR_U32_BE__, self.__STR_U32_LE__)

    def write_s32(self, val: int):
        self.__write_primitive__(val, self.__STR_S32_BE__, self.__STR_S32_LE__)

    def write_u64(self, val: int):
        self.__write_primitive__(val, self.__STR_U64_BE__, self.__STR_U64_LE__)

    def write_s64(self, val: int):
        self.__write_primitive__(val, self.__STR_S64_BE__, self.__STR_S64_LE__)

    def write_f32(self, val: float):
        self.__write_primitive__(val, self.__STR_F32_BE__, self.__STR_F32_LE__)

    def write_f64(self, val: float):
        self.__write_primitive__(val, self.__STR_F64_BE__, self.__STR_F64_LE__)

