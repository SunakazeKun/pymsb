from .binIO import *
from .adapter import LMSAdapter
from .helper import LMSException
from . import helper

__all__ = ["LMSFlowNode", "LMSEntryNode", "LMSMessageNode", "LMSBranchNode", "LMSEventNode", "LMSFlows",
           "msbf_from_buffer", "msbf_pack_buffer", "msbf_from_file", "msbf_write_file"]


class LMSFlowNode:
    def __init__(self):
        self.next_node: LMSFlowNode | None = None
        self.arg0: int = 0
        self.arg1: int = 0
        self.arg2: int = 0
        self.arg3: int = 0
        self.arg4: int = 0

    def node_type(self) -> int:
        raise NotImplementedError

    def read(self, stream: BinaryMemoryIO):
        self.arg0 = stream.read_u16()
        self.arg1 = stream.read_u16()
        self.arg2 = stream.read_u16()
        self.arg3 = stream.read_u16()
        self.arg4 = stream.read_u16()

    def write(self, stream: BinaryMemoryIO):
        stream.write_u16(self.arg0)
        stream.write_u16(self.arg1)
        stream.write_u16(self.arg2)
        stream.write_u16(self.arg3)
        stream.write_u16(self.arg4)


class LMSEntryNode(LMSFlowNode):
    def __init__(self):
        super(LMSEntryNode, self).__init__()
        self.arg1 = 0xFFFF

        self.label: str = ""

    def node_type(self) -> int:
        return 4

    def __repr__(self):
        return self.label


class LMSMessageNode(LMSFlowNode):
    def __init__(self):
        super(LMSMessageNode, self).__init__()
        self.arg1 = 0x88
        self.arg2 = 0xFFFF
        self.arg3 = 0xFFFF

        self.message_label: str | None = None

    def node_type(self) -> int:
        return 1

    @property
    def msbt_entry_idx(self) -> int:
        return self.arg2

    @msbt_entry_idx.setter
    def msbt_entry_idx(self, msbt_entry_idx: int):
        self.arg2 = msbt_entry_idx


class LMSBranchNode(LMSFlowNode):
    def __init__(self):
        super(LMSBranchNode, self).__init__()
        self.arg1 = 2
        self.next_node_else: LMSFlowNode | None = None

    def node_type(self) -> int:
        return 2

    @property
    def condition_type(self) -> int:
        return self.arg2

    @condition_type.setter
    def condition_type(self, condition_type: int):
        self.arg2 = condition_type

    @property
    def condition_param(self) -> int:
        return self.arg3

    @condition_param.setter
    def condition_param(self, condition_param: int):
        self.arg3 = condition_param


class LMSEventNode(LMSFlowNode):
    def __init__(self):
        super(LMSEventNode, self).__init__()
        self.arg2 = 0xFFFF

    def node_type(self) -> int:
        return 3

    @property
    def event_type(self) -> int:
        return self.arg1

    @event_type.setter
    def event_type(self, event_type: int):
        self.arg1 = event_type

    @property
    def event_param(self) -> int:
        return self.arg4

    @event_param.setter
    def event_param(self, event_param: int):
        self.arg4 = event_param


# ----------------------------------------------------------------------------------------------------------------------


class LMSFlows:
    """
    A document that can hold flowcharts and their nodes (i.e. LMSFlowNode). It provides the general blueprints for MSBF
    files, however, only specific games support MSBF files. Check the LMSAdapter interface for more information.
    """
    _MAGIC_HEADER_ = b"MsgFlwBn"
    _MAGIC_FLW2_ = b'FLW2'
    _MAGIC_FEN1_ = b'FEN1'
    _MAGIC_REF1_ = b'REF1'

    def __init__(self, adapter_maker: type[LMSAdapter]):
        if not adapter_maker.supports_flows:
            raise LMSException("Adapter does not support flowcharts")

        self._flowcharts_: list[LMSEntryNode] = []
        self._adapter_: LMSAdapter = adapter_maker()

        self._temp_nodes_: list[LMSFlowNode]
        self._temp_labels_: dict[int, str]
        self._temp_indices_: list[int]

    @property
    def flowcharts(self) -> list[LMSEntryNode]:
        """The list of flowcharts."""
        return self._flowcharts_

    @property
    def adapter(self) -> LMSAdapter:
        """The adapter that handles game-dependent behavior."""
        return self._adapter_

    def set_big_endian(self):
        """
        Forces the usage of big endian byte order when reading or writing. If the current charset is 'utf-16-le', it
        will be changed to 'utf-16-be'.
        """
        self._adapter_.set_big_endian()

    def set_little_endian(self):
        """
        Forces the usage of little endian byte order when reading or writing. If the current charset is 'utf-16-be', it
        will be changed to 'utf-16-le'.
        """
        self._adapter_.set_little_endian()

    @property
    def is_big_endian(self) -> bool:
        """True if big endian byte order should be used, otherwise False."""
        return self._adapter_.is_big_endian

    @property
    def is_little_endian(self) -> bool:
        """True if little endian byte order should be used, otherwise False."""
        return self._adapter_.is_little_endian

    def new_flowchart(self, label: str) -> LMSEntryNode:
        """
        Creates and returns a new flowchart using the given label and adds it to the list of flowcharts. If a flowchart
        with the same label already exists, an LMSException will be thrown.

        :param label: the new message's label.
        :return: the new flowchart.
        """
        # Check if flowchart with label already exists
        for flowchart in self._flowcharts_:
            if flowchart.label == label:
                raise LMSException(f"A flowchart with the label {label} already exists!")

        # Create and append new flowchart
        flowchart = LMSEntryNode()
        flowchart.label = label

        self._flowcharts_.append(flowchart)

        return flowchart

    # ------------------------------------------------------------------------------------------------------------------
    # Unpacking
    # ------------------------------------------------------------------------------------------------------------------
    def _unpack_(self, stream: BinaryMemoryIO):
        # Verify magic
        magic = stream.read(8)

        if magic != self._MAGIC_HEADER_:
            raise Exception("Stream does not contain MSBF data")

        # Verify BOM
        bom = stream.read_u16()

        if bom == 0xFFFE:
            stream.swap_byte_order()
        elif bom != 0xFEFF:
            raise BOMException("No proper UTF-16 BOM found")

        # Read remaining header stuff
        stream.skip(3)
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

        # Parse all sections
        current_section_offset = 32
        stream.seek(current_section_offset)

        for i in range(num_sections):
            section_magic = stream.read(4)
            section_size = stream.read_u32()
            stream.skip(8)
            section_offset = stream.tell()

            if section_magic == self._MAGIC_FLW2_:
                self._unpack_flw2_(stream, section_offset, section_size)

            if section_magic == self._MAGIC_FEN1_:
                self._unpack_fen1_(stream, section_offset, section_size)

            if section_magic == self._MAGIC_REF1_:
                self._unpack_ref1_(stream, section_offset, section_size)

            current_section_offset = (section_offset + section_size + 15) & ~15
            stream.seek(current_section_offset)

        # Verify contents
        if self._temp_nodes_ is None:
            raise LMSException("No nodes section (FLW2) found")

        if self._temp_labels_ is None:
            raise LMSException("No labels section (FEN1) found")

        def try_get_node(next_node_idx: int) -> LMSFlowNode | None:
            if next_node_idx == 0xFFFF:
                return None
            elif next_node_idx < len(self._temp_nodes_):
                return self._temp_nodes_[next_node_idx]
            else:
                raise LMSException(f"No node at index {next_node_idx} found")

        # Join nodes and labels
        for i, node in enumerate(self._temp_nodes_):
            if type(node) == LMSEntryNode:
                if i in self._temp_labels_:
                    node.label = self._temp_labels_[i]
                else:
                    raise LMSException(f"No label for entry node {i}")

                self._flowcharts_.append(node)
                node.next_node = try_get_node(node.arg1)

            elif type(node) == LMSMessageNode:
                node.next_node = try_get_node(node.arg3)

            elif type(node) == LMSBranchNode:
                node.next_node = try_get_node(self._temp_indices_[node.arg4])
                node.next_node_else = try_get_node(self._temp_indices_[node.arg4 + 1])

            elif type(node) == LMSEventNode:
                node.next_node = try_get_node(node.arg2)

        # Cleanup
        del self._temp_labels_
        del self._temp_nodes_
        del self._temp_indices_

    def _unpack_flw2_(self, stream: BinaryMemoryIO, offset: int, size: int):
        stream.seek(offset)

        num_nodes = stream.read_u16()
        num_indices = stream.read_u16()
        stream.skip(4)

        # Read all nodes
        self._temp_nodes_ = []

        for _ in range(num_nodes):
            node: LMSFlowNode
            node_type = stream.read_u16()

            if node_type == 1:
                node = LMSMessageNode()
            elif node_type == 2:
                node = LMSBranchNode()
            elif node_type == 3:
                node = LMSEventNode()
            elif node_type == 4:
                node = LMSEntryNode()
            else:
                raise LMSException(f"Unknown flow node type {node_type}")

            node.read(stream)
            self._temp_nodes_.append(node)

        # Read all branch indices
        self._temp_indices_ = [stream.read_u16() for _ in range(num_indices)]

    def _unpack_fen1_(self, stream: BinaryMemoryIO, offset: int, size: int):
        stream.seek(offset)
        self._temp_labels_ = helper.unpack_hash_table(stream)

    def _unpack_ref1_(self, stream: BinaryMemoryIO, offset: int, size: int):
        raise NotImplementedError("REF1 not supported yet")

    # ------------------------------------------------------------------------------------------------------------------
    # Packing
    # ------------------------------------------------------------------------------------------------------------------
    def makebin(self) -> bytes:
        """
        Packs all flowcharts according to the MSBF format and returns the resulting bytes buffer.

        :return: the packed bytes buffer.
        """
        # Create stream and write initial content
        stream = self._adapter_.create_stream(32)

        stream.write(self._MAGIC_HEADER_)
        stream.write_u16(0xFEFF)
        stream.skip(3)
        stream.write_u8(3)
        stream.write_u16(0)
        stream.skip(2)
        stream.write_u32(0)
        stream.skip(10)

        # Pack the sections
        self._pack_flw2_(stream)
        self._pack_fen1_(stream)
        num_sections = 2

        # Update header and get result
        stream.seek(0x000E)
        stream.write_u16(num_sections)
        stream.seek(0x0012)
        stream.write_u32(stream.size)

        result = stream.getbuffer().tobytes()
        del stream
        return result

    def _pack_flw2_(self, main_stream: BinaryMemoryIO):
        self._temp_nodes_ = []
        self._temp_indices_ = []

        # Flatten all flowcharts
        for flowchart in self._flowcharts_:
            remaining_nodes = [flowchart]

            while len(remaining_nodes):
                node = remaining_nodes.pop(0)
                next_node = node.next_node

                if node not in self._temp_nodes_:
                    self._temp_nodes_.append(node)

                if next_node is not None and next_node not in self._temp_nodes_:
                    remaining_nodes.append(node.next_node)

                if type(node) == LMSBranchNode:
                    next_node = node.next_node_else

                    if next_node is not None and next_node not in self._temp_nodes_:
                        remaining_nodes.append(node.next_node_else)

        # Prepare header and stream
        num_nodes = len(self._temp_nodes_)
        initial_capacity = 0x08 + num_nodes * 0x0C

        stream = self._adapter_.create_stream(initial_capacity)
        stream.write_u16(num_nodes)
        stream.skip(6)

        # Write all nodes
        def get_node_index(node: LMSFlowNode) -> int:
            return 0xFFFF if node is None else self._temp_nodes_.index(node)

        for node in self._temp_nodes_:
            if type(node) == LMSEntryNode:
                node.arg1 = get_node_index(node.next_node)

            elif type(node) == LMSMessageNode:
                node.arg3 = get_node_index(node.next_node)

            elif type(node) == LMSBranchNode:
                node.arg4 = len(self._temp_indices_)
                self._temp_indices_.append(get_node_index(node.next_node))
                self._temp_indices_.append(get_node_index(node.next_node_else))

            elif type(node) == LMSEventNode:
                node.arg2 = get_node_index(node.next_node)

            stream.write_u16(node.node_type())
            node.write(stream)

        # Write branch indices
        for index in self._temp_indices_:
            stream.write_u16(index)

        stream.seek(0x0002)
        stream.write_u16(len(self._temp_indices_))

        # Write section to main stream
        main_stream.write(self._MAGIC_FLW2_)
        main_stream.write_u32(stream.size)
        main_stream.skip(8)
        main_stream.write(stream.getbuffer().tobytes())

        while main_stream.size & 15:
            main_stream.write_u8(0xAB)

        del stream

    def _pack_fen1_(self, main_stream: BinaryMemoryIO):
        if self._adapter_.use_fixed_buckets:
            num_buckets = 59
        else:
            num_buckets = helper.find_greater_prime(len(self._flowcharts_))

        # Create stream and write hash table
        stream = self._adapter_.create_stream(0x04 + num_buckets * 0x08)
        indices_and_labels = [(self._temp_nodes_.index(f), f.label) for f in self._flowcharts_]
        helper.pack_hash_table(stream, indices_and_labels, num_buckets)

        # Write section to main stream
        main_stream.write(self._MAGIC_FEN1_)
        main_stream.write_u32(stream.size)
        main_stream.skip(8)
        main_stream.write(stream.getbuffer().tobytes())

        while main_stream.size & 15:
            main_stream.write_u8(0xAB)

        del stream


# ----------------------------------------------------------------------------------------------------------------------
# Helper I/O functions
# ----------------------------------------------------------------------------------------------------------------------
def msbf_from_buffer(adapter_maker: type[LMSAdapter], buffer) -> LMSFlows:
    """
    Creates and returns a new LMS flowcharts document by unpacking the content from the specified buffer. The data is
    expected to be in the MSBF format.

    :param adapter_maker: the adapter class to be used.
    :param buffer: the byte buffer.
    :return: the unpacked LMSFlows.
    """
    flowdoc = LMSFlows(adapter_maker)
    flowdoc._unpack_(BinaryMemoryIO(buffer))
    return flowdoc


def msbf_pack_buffer(flowdoc: LMSFlows) -> bytes:
    """
    Packs the given LMS flowcharts document according to the MSBF format and returns the resulting bytes buffer.

    :param flowdoc: the LMSFlows to be packed.
    :return: the buffer containing the stored data.
    """
    return flowdoc.makebin()


def msbf_from_file(adapter_maker: type[LMSAdapter], file_path: str) -> LMSFlows:
    """
    Creates and returns a new LMS flowcharts document by unpacking the contents from the file at the given path. The
    data is expected to be in the MSBF format.

    :param adapter_maker: the adapter class to be used.
    :param file_path: the file path to the MSBF file.
    :return: the unpacked LMSFlows.
    """
    with open(file_path, "rb") as f:
        flowdoc = LMSFlows(adapter_maker)
        flowdoc._unpack_(BinaryMemoryIO(f.read()))
        return flowdoc


def msbf_write_file(flowdoc: LMSFlows, file_path: str):
    """
    Packs the given flowcharts document according to the MSBF format and writes the contents to the file at the given
    path.

    :param flowdoc: the LMSFlows to be written.
    :param file_path: the file path to write the MSBF file to.
    """
    with open(file_path, "wb") as f:
        f.write(flowdoc.makebin())
