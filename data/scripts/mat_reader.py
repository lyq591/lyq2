"""
纯 Python MATLAB 5.0 .mat 文件解析器
不依赖 numpy/scipy，仅使用标准库
支持压缩数据元素、数值数组、元胞数组、结构体数组
"""
import struct
import zlib


class MatReader:
    # MATLAB 数据类型
    miINT8 = 1
    miUINT8 = 2
    miINT16 = 3
    miUINT16 = 4
    miINT32 = 5
    miUINT32 = 6
    miSINGLE = 7
    miDOUBLE = 9
    miINT64 = 12
    miUINT64 = 13
    miMATRIX = 14
    miCOMPRESSED = 15
    miUTF8 = 16
    miUTF16 = 17
    miUTF32 = 18

    # MATLAB 数组类
    mxCELL_CLASS = 1
    mxSTRUCT_CLASS = 2
    mxOBJECT_CLASS = 3
    mxCHAR_CLASS = 4
    mxSPARSE_CLASS = 5
    mxDOUBLE_CLASS = 6
    mxSINGLE_CLASS = 7
    mxINT8_CLASS = 8
    mxUINT8_CLASS = 9
    mxINT16_CLASS = 10
    mxUINT16_CLASS = 11
    mxINT32_CLASS = 12
    mxUINT32_CLASS = 13
    mxINT64_CLASS = 14
    mxUINT64_CLASS = 15

    TYPE_SIZE = {
        miINT8: 1, miUINT8: 1,
        miINT16: 2, miUINT16: 2,
        miINT32: 4, miUINT32: 4,
        miSINGLE: 4, miDOUBLE: 8,
        miINT64: 8, miUINT64: 8,
    }

    TYPE_FMT = {
        miINT8: 'b', miUINT8: 'B',
        miINT16: 'h', miUINT16: 'H',
        miINT32: 'i', miUINT32: 'I',
        miSINGLE: 'f', miDOUBLE: 'd',
        miINT64: 'q', miUINT64: 'Q',
    }

    def __init__(self, filepath):
        self.filepath = filepath
        self.variables = {}

    def load(self):
        with open(self.filepath, 'rb') as f:
            # 读取 128 字节头
            header = f.read(128)
            self.endian = '<'  # 默认小端
            # 解析数据元素
            while True:
                pos = f.tell()
                tag = f.read(8)
                if len(tag) < 8:
                    break
                dtype, nbytes = struct.unpack(self.endian + 'II', tag)
                if dtype == 0 and nbytes == 0:
                    break
                data = f.read(nbytes)
                # 注意：本数据集文件元素间无8字节填充
                if dtype == self.miCOMPRESSED:
                    decompressed = zlib.decompress(data)
                    # 解压后的数据包含 miMATRIX 标签(8字节) + 数据
                    if len(decompressed) >= 8:
                        inner_type, inner_size = struct.unpack_from(self.endian + 'II', decompressed, 0)
                        if inner_type == self.miMATRIX:
                            self._parse_matrix_data(decompressed[8:8 + inner_size])
                        else:
                            self._parse_matrix_data(decompressed)
                elif dtype == self.miMATRIX:
                    self._parse_matrix_data(data)
        return self.variables

    def _parse_matrix_data(self, data):
        """解析 miMATRIX 类型的数据块"""
        offset = 0
        array_flags = None
        dims = None
        name = None
        real_data = None
        imag_data = None
        field_names = None
        cells_data = []
        struct_fields_data = []

        while offset < len(data):
            if offset + 8 > len(data):
                break
            raw_type, raw_nbytes = struct.unpack_from(self.endian + 'II', data, offset)
            # 检测小数据元素：类型值超过正常范围(>255)时，高16位是size，低16位是type
            if raw_type > 0xFF:
                dtype = raw_type & 0xFFFF
                nbytes = (raw_type >> 16) & 0xFFFF
                payload = data[offset + 4:offset + 4 + nbytes]
                offset += 8  # 小数据元素只占8字节(标签+数据)
            else:
                dtype = raw_type
                nbytes = raw_nbytes
                offset += 8
                payload = data[offset:offset + nbytes]
                offset += nbytes
                # 注意：本数据集子元素间无8字节填充

            if dtype == self.miUINT32 and array_flags is None:
                # 数组标志
                flags_val = struct.unpack_from(self.endian + 'I', payload, 0)[0]
                array_flags = {
                    'class': flags_val & 0xFF,
                    'complex': bool(flags_val & 0x800),
                    'global': bool(flags_val & 0x400),
                    'logical': bool(flags_val & 0x200),
                }
            elif dtype == self.miINT32 and dims is None:
                # 维度
                n = nbytes // 4
                dims = list(struct.unpack_from(self.endian + str(n) + 'i', payload, 0))
            elif dtype in (self.miINT8, self.miUTF8) and name is None:
                # 变量名
                name = payload.decode('ascii', errors='replace').rstrip('\x00')
            elif dtype == self.miINT32 and field_names is None and array_flags and array_flags['class'] == self.mxSTRUCT_CLASS:
                # 结构体字段名长度
                field_name_length = struct.unpack_from(self.endian + 'i', payload, 0)[0]
            elif dtype == self.miINT8 and field_names is None and array_flags and array_flags['class'] == self.mxSTRUCT_CLASS:
                # 结构体字段名
                raw = payload.decode('ascii', errors='replace')
                field_names = [f for f in raw.split('\x00') if f]
            elif dtype in (self.miDOUBLE, self.miSINGLE, self.miINT8, self.miUINT8,
                           self.miINT16, self.miUINT16, self.miINT32, self.miUINT32,
                           self.miINT64, self.miUINT64) and array_flags:
                if array_flags['class'] == self.mxCELL_CLASS:
                    # 元胞数组的每个元素是嵌套的 miMATRIX
                    # 但实际上 cell 元素的 tag 类型应该是 miMATRIX(14)
                    # 这里处理的是数值类型作为 real_data
                    if real_data is None:
                        real_data = self._parse_numeric(dtype, payload, dims)
                    elif imag_data is None:
                        imag_data = self._parse_numeric(dtype, payload, dims)
                else:
                    if real_data is None:
                        real_data = self._parse_numeric(dtype, payload, dims)
                    elif imag_data is None:
                        imag_data = self._parse_numeric(dtype, payload, dims)
            elif dtype == self.miMATRIX and array_flags:
                # 嵌套矩阵（元胞数组元素或结构体字段）
                nested = self._parse_nested_matrix(payload)
                if array_flags['class'] == self.mxCELL_CLASS:
                    cells_data.append(nested)
                elif array_flags['class'] == self.mxSTRUCT_CLASS:
                    struct_fields_data.append(nested)

        # 构建结果
        if array_flags is None:
            return

        cls = array_flags['class']
        if cls == self.mxCELL_CLASS:
            result = self._build_cell_array(cells_data, dims)
        elif cls == self.mxSTRUCT_CLASS:
            result = self._build_struct_array(struct_fields_data, field_names, dims)
        elif cls == self.mxCHAR_CLASS:
            result = self._build_char_array(real_data, dims)
        else:
            result = real_data

        if name:
            self.variables[name] = result
        return result

    def _parse_nested_matrix(self, data):
        """解析嵌套的 miMATRIX 数据，返回解析后的值"""
        reader = MatReader.__new__(MatReader)
        reader.endian = self.endian
        reader.variables = {}
        result = reader._parse_matrix_data(data)
        return result

    def _parse_numeric(self, dtype, payload, dims):
        """解析数值数组"""
        if dtype not in self.TYPE_FMT:
            return None
        elem_size = self.TYPE_SIZE[dtype]
        fmt = self.TYPE_FMT[dtype]
        n = len(payload) // elem_size
        values = list(struct.unpack_from(self.endian + str(n) + fmt, payload, 0))

        if dims is None or len(dims) == 0:
            return values[0] if values else None
        if len(dims) == 1:
            return values
        if len(dims) == 2:
            rows, cols = dims
            # MATLAB 列优先存储
            result = []
            for i in range(rows):
                row = []
                for j in range(cols):
                    idx = j * rows + i
                    row.append(values[idx] if idx < len(values) else 0)
                result.append(row)
            return result
        # 高维简化处理
        return values

    def _build_cell_array(self, cells_data, dims):
        """构建元胞数组"""
        if not dims or len(dims) < 2:
            return cells_data
        rows, cols = dims[0], dims[1]
        result = []
        idx = 0
        for i in range(rows):
            row = []
            for j in range(cols):
                if idx < len(cells_data):
                    row.append(cells_data[idx])
                else:
                    row.append(None)
                idx += 1
            result.append(row)
        return result

    def _build_struct_array(self, fields_data, field_names, dims):
        """构建结构体数组"""
        if not field_names:
            return fields_data
        n_fields = len(field_names)
        result = []
        for i in range(0, len(fields_data), n_fields):
            struct_obj = {}
            for j, fname in enumerate(field_names):
                if i + j < len(fields_data):
                    struct_obj[fname] = fields_data[i + j]
            result.append(struct_obj)
        if len(result) == 1:
            return result[0]
        return result

    def _build_char_array(self, real_data, dims):
        """构建字符数组"""
        if real_data is None:
            return ''
        if isinstance(real_data, list):
            if isinstance(real_data[0], list):
                # 2D char array
                lines = []
                for row in real_data:
                    chars = [chr(int(c)) for c in row if c != 0]
                    lines.append(''.join(chars))
                return lines
            else:
                chars = [chr(int(c)) for c in real_data if c != 0]
                return ''.join(chars)
        return str(real_data)


def loadmat(filepath):
    """加载 .mat 文件，返回变量字典"""
    reader = MatReader(filepath)
    return reader.load()
