from .helper import LMSException
from .binIO import BinaryMemoryIO
from typing import Callable, Any
from abc import ABC

__all__ = ["LMSAdapter"]


class LMSAdapter(ABC):
    """
    An interface that can be implemented to adapt features specific to some games, such as special message tags, styles,
    attributes, and more. In other words, an adapter controls can control how the library will deal with MSBT and MSBF
    files.
    """
    def __init__(self):
        self._charset_: str = "utf-16-be"
        self._is_big_endian_: bool = True
        self._read_char_func_: Callable[[BinaryMemoryIO], str] = __read_utf_16_be_char__
        self._write_char_func_: Callable[[BinaryMemoryIO, str], int] = __write_utf_16_be__

    def create_stream(self, initial_capacity: int = 0) -> BinaryMemoryIO:
        """
        Creates a new in-memory byte stream with the specified initial capacity. The stream will use the adapter's
        endianness.

        :param initial_capacity: the initial capacity.
        :return: the newly constructed stream.
        """
        stream = BinaryMemoryIO(bytes(initial_capacity), big_endian=self._is_big_endian_)
        stream.seek(0)
        return stream

    @property
    def charset(self) -> str:
        """
        Gets or sets the charset's name to be used when reading or writing string. Supported charsets are 'utf-8',
        'utf-16-be' and 'utf-16-le'.
        """
        return self._charset_

    @charset.setter
    def charset(self, charset: str):
        if charset == "utf-8":
            self._read_char_func_ = __read_utf_8_char__
            self._write_char_func_ = __write_utf_8__
        elif charset == "utf-16-be":
            self._read_char_func_ = __read_utf_16_be_char__
            self._write_char_func_ = __write_utf_16_be__
        elif charset == "utf-16-le":
            self._read_char_func_ = __read_utf_16_le_char__
            self._write_char_func_ = __write_utf_16_le__
        else:
            raise LMSException("Invalid charset")

        self._charset_ = charset

    def set_big_endian(self):
        """
        Forces the usage of big endian byte order when reading or writing. If the current charset is 'utf-16-le', it
        will be changed to 'utf-16-be'.
        """
        if self._charset_ == "utf-16-le":
            self._charset_ = "utf-16-be"
            self._read_char_func_ = __read_utf_16_be_char__
            self._write_char_func_ = __write_utf_16_be__

        self._is_big_endian_ = True

    def set_little_endian(self):
        """
        Forces the usage of little endian byte order when reading or writing. If the current charset is 'utf-16-be', it
        will be changed to 'utf-16-le'.
        """
        if self._charset_ == "utf-16-be":
            self._charset_ = "utf-16-le"
            self._read_char_func_ = __read_utf_16_le_char__
            self._write_char_func_ = __write_utf_16_le__

        self._is_big_endian_ = False

    @property
    def is_big_endian(self) -> bool:
        """True if big endian byte order should be used, otherwise False."""
        return self._is_big_endian_

    @property
    def is_little_endian(self) -> bool:
        """True if little endian byte order should be used, otherwise False."""
        return not self._is_big_endian_

    # ------------------------------------------------------------------------------------------------------------------
    # General MSBT/MSBF properties
    # ------------------------------------------------------------------------------------------------------------------
    @property
    def use_fixed_buckets(self) -> bool:
        """True if MSBT or MSBF files should use a fixed number of hash buckets, otherwise False."""
        return False

    @property
    def supports_flows(self) -> bool:
        """True if the game associated with the adapter supports flowcharts (i.e. MSBF files), otherwise False."""
        return False

    # ------------------------------------------------------------------------------------------------------------------
    # Text I/O
    # ------------------------------------------------------------------------------------------------------------------
    def read_char(self, stream: BinaryMemoryIO) -> str:
        """
        Reads from the stream a character and returns it.

        :param stream: the stream to read from.
        :return: the read character.
        """
        return self._read_char_func_(stream)

    def write_chars(self, stream: BinaryMemoryIO, string: str) -> int:
        """
        Writes a raw string of characters to the specified stream and returns the number of bytes written.

        :param stream: the stream to write to.
        :param string: the characters to be written.
        :return: the number of bytes written.
        """
        return self._write_char_func_(stream, string)

    def read_text(self, stream: BinaryMemoryIO) -> str:
        """
        Reads from the given stream a null-terminated text string and returns it. If a tag character (\\u000E) is read,
        the adapter's ``read_tag`` function will be invoked to parse the tag. The readable tag representations are
        usually encapsulated between square brackets ('[', ']'). To preserve this characters outside of tags, a
        backslash will be added in front of them. Similarly, a single backslash will be represented by two backslashes.

        :param stream: the stream to read from.
        :return: the read text.
        """
        text = ""

        while True:
            ch = self.read_char(stream)

            if ch == "\u0000":
                break
            elif ch == "\u000E":
                text += self.read_tag(stream)
            elif ch == "[":
                text += '\\['
            elif ch == "]":
                text += "\\]"
            elif ch == "\\":
                text += "\\\\"
            else:
                text += ch

        return text

    def read_tag(self, stream: BinaryMemoryIO) -> str:
        """
        Parses from the given stream a special tag and returns a string representation of it. The string representation
        should be enclosed between square brackets ('[', ']'). Tags always start out with the same three unsigned shorts
        values, group ID, tag ID and data size. Following these values, the tag's data follows.

        :param stream: the stream to read from.
        :return: the parsed tag.
        """
        raise NotImplementedError()

    def write_text(self, stream: BinaryMemoryIO, text: str):
        """
        Writes the given text string to the stream. Texts encapsulated between square brackets ('[', ']') are treated as
        tag strings and will be processed by ``write_tag``. However, if a backslash preceeds any character, including
        square brackets, the character will be written as is. The text string will be null-terminated.

        :param stream: the stream to write to.
        :param text: the text to be written.
        """
        tag_start = 0
        escape = False
        index = 0

        while index < len(text):
            if escape:
                self.write_chars(stream, text[index])
                escape = False
            elif text[index] == "\\":
                escape = True
            elif text[index] == "]":
                if tag_start > 0:
                    tag_string = text[tag_start:index]
                    self.write_tag(stream, tag_string)
                    tag_start = 0
                else:
                    raise LMSException("Tag closer found without opener")
            elif text[index] == "[":
                tag_start = index + 1
            elif tag_start == 0:
                self.write_chars(stream, text[index])

            index += 1

        if tag_start > 0:
            raise LMSException("Tag not closed")
        if escape:
            raise LMSException("No character to escape")

        self.write_chars(stream, "\u0000")

    def write_tag(self, stream: BinaryMemoryIO, tag: str):
        """
        Creates a binary representation of the given tag string and writes it to the stream. See ``read_tag`` for the
        general structure of a tag. The default implementation of ``write_text`` invokes this method by passing over the
        tag string *without* square brackets.

        :param stream: the stream to write to.
        :param tag: the tag to be written.
        """
        raise NotImplementedError()

    # ------------------------------------------------------------------------------------------------------------------
    # Attributes interface
    # ------------------------------------------------------------------------------------------------------------------
    @property
    def supports_attributes(self) -> bool:
        """True if the adapter supports message attributes (i.e. ATR1 section), otherwise False."""
        return False

    @property
    def attributes_size(self) -> int:
        """The length (in bytes) of every message's attributes. This should return a positive integer or zero."""
        return 0

    def create_default_attributes(self) -> dict[str, Any]:
        """
        Creates and returns a dictionary consisting of default message attributes.

        :return: the dictionary of default attributes.
        """
        raise NotImplementedError()

    def parse_attributes(self, stream: BinaryMemoryIO, root_offset: int, root_size: int) -> dict[str, Any]:
        """
        Reads and parses message attributes from the given stream.

        :param stream: the stream to read from.
        :param root_offset: the start of the ATR1 section.
        :param root_size: the valid length of the ATR1 section.
        :return: the dictionary of parsed message attributes.
        """
        raise NotImplementedError()

    def write_attributes(self, stream: BinaryMemoryIO, attributes: dict[str, Any]):
        """
        Encodes and writes the message attributes to the stream.

        :param stream: the stream to write to.
        :param attributes: the message attributes to be written.
        """
        raise NotImplementedError()

    # ------------------------------------------------------------------------------------------------------------------
    # Styles interface
    # ------------------------------------------------------------------------------------------------------------------
    @property
    def supports_styles(self) -> bool:
        """True if the adapter supports message styles (i.e. TSY1 section), otherwise False."""
        return False

    def create_default_style(self) -> int:
        """
        Returns the ID of the default style.

        :return: the default style ID.
        """
        raise NotImplementedError()


# ------------------------------------------------------------------------------------------------------------------
# Helper functions to read and write characters
# ------------------------------------------------------------------------------------------------------------------
def __read_utf_8_char__(stream: BinaryMemoryIO) -> str:
    """
    Reads from the stream a character encoded in 'utf-8' format and returns it.

    :param stream: the stream to read from.
    :return: the read character.
    """
    byte = stream.read_u8()
    buffer = bytearray()
    buffer.append(byte)

    if byte >= 0xFE:
        pass
    elif byte >= 0xFC:
        buffer += stream.read(5)
    elif byte >= 0xF8:
        buffer += stream.read(4)
    elif byte >= 0xF0:
        buffer += stream.read(3)
    elif byte >= 0xE0:
        buffer += stream.read(2)
    elif byte >= 0xC0:
        buffer += stream.read(1)

    return buffer.decode("utf-8")


def __write_utf_8__(stream: BinaryMemoryIO, string: str) -> int:
    """
    Encodes a raw string of characters in 'utf-8', writes the encoded bytes to the specified stream and returns the
    number of bytes written.

    :param stream: the stream to write to.
    :param string: the characters to be written.
    :return: the number of bytes written.
    """
    buffer = string.encode("utf-8")
    stream.write(buffer)
    return len(buffer)


def __read_utf_16_be_char__(stream: BinaryMemoryIO) -> str:
    """
    Reads from the stream a character encoded in 'utf-16-be' format and returns it.

    :param stream: the stream to read from.
    :return: the read character.
    """
    buffer = stream.read(2)
    return buffer.decode("utf-16-be")


def __write_utf_16_be__(stream: BinaryMemoryIO, string: str) -> int:
    """
    Encodes a raw string of characters in 'utf-16-be', writes the encoded bytes to the specified stream and returns the
    number of bytes written.

    :param stream: the stream to write to.
    :param string: the characters to be written.
    :return: the number of bytes written.
    """
    buffer = string.encode("utf-16-be")
    stream.write(buffer)
    return len(buffer)


def __read_utf_16_le_char__(stream: BinaryMemoryIO) -> str:
    """
    Reads from the stream a character encoded in 'utf-16-le' format and returns it.

    :param stream: the stream to read from.
    :return: the read character.
    """
    buffer = stream.read(2)
    return buffer.decode("utf-16-le")


def __write_utf_16_le__(stream: BinaryMemoryIO, string: str) -> int:
    """
    Encodes a raw string of characters in 'utf-16-le', writes the encoded bytes to the specified stream and returns the
    number of bytes written.

    :param stream: the stream to write to.
    :param string: the characters to be written.
    :return: the number of bytes written.
    """
    buffer = string.encode("utf-16-le")
    stream.write(buffer)
    return len(buffer)
