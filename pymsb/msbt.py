from typing import Any

from .binIO import *
from .adapter import LMSAdapter
from .helper import LMSException
from . import helper

__all__ = ["LMSMessage", "LMSDocument", "msbt_from_buffer", "msbt_pack_buffer", "msbt_from_file", "msbt_write_file"]


class LMSMessage:
    def __init__(self, text: str):
        self.label = ""
        self.text = text
        self.attributes = {}
        self.style = -1


class LMSDocument:
    _MAGIC_HEADER_ = b"MsgStdBn"
    _MAGIC_LBL1_ = b'LBL1'
    _MAGIC_TXT2_ = b'TXT2'
    _MAGIC_ATR1_ = b'ATR1'
    _MAGIC_ATO1_ = b'ATO1'
    _MAGIC_TSY1_ = b'TSY1'

    def __init__(self, adapter_maker: type[LMSAdapter]):
        self._messages_: list[LMSMessage] = []
        self._adapter_ = adapter_maker()

        self._temp_labels_: dict[int, str]
        self._temp_attrs_: list[dict[str, Any]]
        self._temp_styles_: list[int]

    @property
    def messages(self) -> list[LMSMessage]:
        return self._messages_

    @property
    def adapter(self) -> LMSAdapter:
        return self._adapter_

    @property
    def charset(self) -> str:
        return self._adapter_.charset

    @charset.setter
    def charset(self, charset: str):
        self._adapter_.charset = charset

    def set_big_endian(self):
        self._adapter_.set_big_endian()

    def set_little_endian(self):
        self._adapter_.set_little_endian()

    @property
    def is_big_endian(self) -> bool:
        return self._adapter_.is_big_endian

    @property
    def is_little_endian(self) -> bool:
        return self._adapter_.is_little_endian

    def new_message(self, label: str) -> LMSMessage:
        # Check if message with label already exists
        for message in self.messages:
            if message.label == label:
                raise LMSException(f"A message with the label {label} already exists!")

        # Create and append new message
        message = LMSMessage("")
        message.label = label

        if self.adapter.supports_attributes:
            message.attributes = self.adapter.create_default_attributes()

        if self.adapter.supports_styles:
            message.style = self.adapter.create_default_style()

        self.messages.append(message)

        return message

    # ------------------------------------------------------------------------------------------------------------------
    # Unpacking
    # ------------------------------------------------------------------------------------------------------------------
    def _unpack_(self, stream: BinaryMemoryIO):
        # Verify magic
        magic = stream.read(8)

        if magic != self._MAGIC_HEADER_:
            raise Exception("Stream does not contain MSBT data")

        # Verify BOM
        bom = stream.read_u16()

        if bom == 0xFFFE:
            stream.swap_byte_order()
        elif bom != 0xFEFF:
            raise BOMException("No proper UTF-16 BOM found")

        # Read remaining header stuff
        stream.skip(2)
        encoding = stream.read_u8()
        version = stream.read_u8()
        num_sections = stream.read_u16()
        stream.skip(2)
        file_size = stream.read_u32()
        stream.skip(10)

        # Verify header contents
        if version != 3:
            raise LMSException(f"Unsupported version detected: {version}")

        if file_size != stream.size:
            raise LMSException("Written file size does not equal stream size")

        # Set adapter context
        if stream.is_big_endian:
            self._adapter_.set_big_endian()
        else:
            self._adapter_.set_little_endian()

        self._adapter_.charset = helper.encoding_to_charset(encoding, stream.is_big_endian)

        # Parse all sections
        current_section_offset = 32
        stream.seek(current_section_offset)

        for i in range(num_sections):
            section_magic = stream.read(4)
            section_size = stream.read_u32()
            stream.skip(8)
            section_offset = stream.tell()

            if section_magic == self._MAGIC_LBL1_:
                self._unpack_lbl1_(stream, section_offset, section_size)

            elif section_magic == self._MAGIC_TXT2_:
                self._unpack_txt2_(stream, section_offset, section_size)

            elif section_magic == self._MAGIC_ATR1_:
                self._unpack_atr1_(stream, section_offset, section_size)

            elif section_magic == self._MAGIC_ATO1_:
                self._unpack_ato1_(stream, section_offset, section_size)

            elif section_magic == self._MAGIC_TSY1_:
                self._unpack_tsy1_(stream, section_offset, section_size)

            current_section_offset = (section_offset + section_size + 15) & ~15
            stream.seek(current_section_offset)

        # Verify contents
        if self._temp_labels_ is None:
            raise LMSException("No labels section found")

        if self._adapter_.supports_attributes and self._temp_attrs_ is None:
            raise LMSException("No attributes section found")

        if self._adapter_.supports_styles and self._temp_styles_ is None:
            raise LMSException("No styles section found")

        # Join messages, labels, attributes & styles
        for i, message in enumerate(self._messages_):
            if self._temp_labels_:
                if i in self._temp_labels_:
                    message.label = self._temp_labels_[i]
                else:
                    raise LMSException(f"No label for message no. {i}")

            if self._temp_attrs_:
                if i < len(self._temp_attrs_):
                    message.attributes = self._temp_attrs_[i]
                else:
                    message.attributes = self._adapter_.create_default_attributes()

            if self._temp_styles_:
                if i < len(self._temp_styles_):
                    message.style = self._temp_styles_[i]
                else:
                    message.style = self._adapter_.create_default_style()

        # Cleanup
        del self._temp_labels_
        del self._temp_attrs_
        del self._temp_styles_

    def _unpack_lbl1_(self, stream: BinaryMemoryIO, offset: int, size: int):
        stream.seek(offset)
        self._temp_labels_ = helper.unpack_hash_table(stream)

    def _unpack_txt2_(self, stream: BinaryMemoryIO, offset: int, size: int):
        stream.seek(offset)
        num_entries = stream.read_s32()

        for i in range(num_entries):
            stream.seek(offset + 0x04 + i * 0x04)
            off_text = stream.read_u32()
            stream.seek(offset + off_text)

            message = LMSMessage(self._adapter_.read_text(stream))
            self._messages_.append(message)

    def _unpack_atr1_(self, stream: BinaryMemoryIO, offset: int, size: int):
        if not self._adapter_.supports_attributes:
            raise LMSException("Adapter does not support message attributes, cannot parse ATR1 section")

        stream.seek(offset)
        num_entries = stream.read_s32()
        len_entries = stream.read_s32()

        all_attributes: list[dict[str, Any]] = []

        for i in range(num_entries):
            stream.seek(offset + 0x08 + i * len_entries)
            attributes = self._adapter_.parse_attributes(stream, offset, size)
            all_attributes.append(attributes)

        self._temp_attrs_ = all_attributes

    def _unpack_ato1_(self, stream: BinaryMemoryIO, offset: int, size: int):
        raise NotImplementedError("ATO1 not supported yet")

    def _unpack_tsy1_(self, stream: BinaryMemoryIO, offset: int, size: int):
        if not self._adapter_.supports_styles:
            raise LMSException("Adapter does not support styles, cannot parse TSY1 section")

        stream.seek(offset)
        num_entries = size // 4

        all_styles: list[int] = []

        for _ in range(num_entries):
            all_styles.append(stream.read_s32())

        self._temp_styles_ = all_styles

    # ------------------------------------------------------------------------------------------------------------------
    # Packing
    # ------------------------------------------------------------------------------------------------------------------
    def makebin(self) -> bytes:
        # Create stream and write initial content
        stream = self.adapter.create_stream(32)

        stream.write(self._MAGIC_HEADER_)
        stream.write_u16(0xFEFF)
        stream.skip(2)
        stream.write_u8(helper.charset_to_encoding(self.adapter.charset))
        stream.write_u8(3)
        stream.write_u16(0)
        stream.skip(2)
        stream.write_u32(0)
        stream.skip(10)

        # Pack the sections
        num_sections = 0

        self._pack_lbl1_(stream)
        num_sections += 1

        if self._adapter_.supports_attributes:
            self._pack_atr1_(stream)
            num_sections += 1

        self._pack_txt2_(stream)
        num_sections += 1

        if self._adapter_.supports_styles:
            self._pack_tsy1_(stream)
            num_sections += 1

        # Update header and get result
        stream.seek(0x000E)
        stream.write_u16(num_sections)
        stream.seek(0x0012)
        stream.write_u32(stream.size)

        result = stream.getbuffer().tobytes()
        del stream
        return result

    def _pack_lbl1_(self, main_stream: BinaryMemoryIO):
        if self._adapter_.use_fixed_buckets:
            num_buckets = 101
        else:
            num_buckets = helper.find_greater_prime(len(self._messages_))

        # Create stream and write hash table
        stream = self._adapter_.create_stream(0x04 + num_buckets * 0x08)
        indices_and_labels = [(i, m.label) for i, m in enumerate(self._messages_)]
        helper.pack_hash_table(stream, indices_and_labels, num_buckets)

        # Write section to main stream
        main_stream.write(self._MAGIC_LBL1_)
        main_stream.write_u32(stream.size)
        main_stream.skip(8)
        main_stream.write(stream.getbuffer().tobytes())

        while main_stream.size & 15:
            main_stream.write_u8(0xAB)

        del stream

    def _pack_txt2_(self, main_stream: BinaryMemoryIO):
        # Prepare information and stream
        num_messages = len(self._messages_)
        initial_capacity = 0x04 + num_messages * 0x04

        stream = self._adapter_.create_stream(initial_capacity)
        stream.write_s32(num_messages)

        # Write all texts
        for i, message in enumerate(self._messages_):
            stream.seek(0x04 + i * 0x04)
            stream.write_u32(stream.size)

            stream.seek(stream.size)
            self._adapter_.write_text(stream, message.text)

        # Write section to main stream
        main_stream.write(self._MAGIC_TXT2_)
        main_stream.write_u32(stream.size)
        main_stream.skip(8)
        main_stream.write(stream.getbuffer().tobytes())

        while main_stream.size & 15:
            main_stream.write_u8(0xAB)

        del stream

    def _pack_atr1_(self, main_stream: BinaryMemoryIO):
        if not self._adapter_.supports_attributes:
            return

        # Prepare information and stream
        num_attributes = len(self._messages_)
        attributes_size = self._adapter_.attributes_size
        initial_capacity = 0x08 + num_attributes * attributes_size

        stream = self._adapter_.create_stream(initial_capacity)
        stream.write_s32(num_attributes)
        stream.write_s32(attributes_size)

        # Write all attributes
        for i, message in enumerate(self._messages_):
            stream.seek(0x08 + i * attributes_size)
            self._adapter_.write_attributes(stream, message.attributes)

        # Write section to main stream
        main_stream.write(self._MAGIC_ATR1_)
        main_stream.write_u32(stream.size)
        main_stream.skip(8)
        main_stream.write(stream.getbuffer().tobytes())

        while main_stream.size & 15:
            main_stream.write_u8(0xAB)

        del stream

    def _pack_ato1_(self):
        raise NotImplementedError("ATO1 not supported yet")

    def _pack_tsy1_(self, main_stream: BinaryMemoryIO):
        if not self._adapter_.supports_styles:
            return

        # Prepare information and stream
        stream = self._adapter_.create_stream(len(self._messages_) * 0x04)

        # Write all styles
        for message in self._messages_:
            stream.write_s32(message.style)

        # Write section to main stream
        main_stream.write(self._MAGIC_TSY1_)
        main_stream.write_u32(stream.size)
        main_stream.skip(8)
        main_stream.write(stream.getbuffer().tobytes())

        while main_stream.size & 15:
            main_stream.write_u8(0xAB)

        del stream


# ----------------------------------------------------------------------------------------------------------------------
# Helper I/O functions
# ----------------------------------------------------------------------------------------------------------------------
def msbt_from_buffer(adapter, buffer) -> LMSDocument:
    stream = BinaryMemoryIO(buffer)
    document = LMSDocument(adapter)
    document._unpack_(stream)
    del stream
    return document


def msbt_pack_buffer(document: LMSDocument) -> bytes:
    return document.makebin()


def msbt_from_file(adapter, file_path: str) -> LMSDocument:
    with open(file_path, "rb") as f:
        stream = BinaryMemoryIO(f.read())
        document = LMSDocument(adapter)
        document._unpack_(stream)
        del stream
        return document


def msbt_write_file(document: LMSDocument, file_path: str):
    with open(file_path, "wb") as f:
        f.write(document.makebin())