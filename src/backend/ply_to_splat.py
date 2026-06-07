"""
Convert a Gaussian-splatting .ply (INRIA training format) into the compact
.splat binary used by @mkkellogg/gaussian-splats-3d and the antimatter15
viewer.

Each output splat is 32 bytes:
  - position  : float32[3]  (12 bytes)
  - scale     : float32[3]  (12 bytes, exp() of the stored log-scales)
  - color     : uint8[4]    (RGBA; RGB from SH DC term, A from sigmoid opacity)
  - rotation  : uint8[4]    (normalized quaternion, mapped to 0..255)

Usage:
    python -m src.backend.ply_to_splat scene.ply assets/scene.splat
"""
import sys
import struct
import numpy as np

SH_C0 = 0.28209479177387814  # zeroth-order spherical-harmonic coefficient

# PLY property type -> numpy little-endian dtype string
_PLY_TYPES = {
    'float': '<f4', 'float32': '<f4',
    'double': '<f8', 'float64': '<f8',
    'uchar': 'u1', 'uint8': 'u1', 'char': 'i1', 'int8': 'i1',
    'ushort': '<u2', 'uint16': '<u2', 'short': '<i2', 'int16': '<i2',
    'uint': '<u4', 'uint32': '<u4', 'int': '<i4', 'int32': '<i4',
}

_REQUIRED = [
    'x', 'y', 'z',
    'scale_0', 'scale_1', 'scale_2',
    'f_dc_0', 'f_dc_1', 'f_dc_2',
    'opacity',
    'rot_0', 'rot_1', 'rot_2', 'rot_3',
]


def _parse_header(f):
    """Read a binary-little-endian PLY header. Returns (count, numpy dtype)."""
    magic = f.readline().strip()
    if magic != b'ply':
        raise ValueError('Not a PLY file (missing "ply" magic).')

    count = None
    props = []  # (name, dtype) in file order
    in_vertex = False
    while True:
        line = f.readline()
        if not line:
            raise ValueError('Unexpected EOF before end_header.')
        tokens = line.decode('latin-1').split()
        if not tokens:
            continue
        kw = tokens[0]
        if kw == 'format':
            if tokens[1] != 'binary_little_endian':
                raise ValueError(f'Unsupported PLY format: {tokens[1]}')
        elif kw == 'element':
            in_vertex = tokens[1] == 'vertex'
            if in_vertex:
                count = int(tokens[2])
        elif kw == 'property' and in_vertex:
            if tokens[1] == 'list':
                raise ValueError('List properties are not supported on vertices.')
            ply_type, name = tokens[1], tokens[2]
            if ply_type not in _PLY_TYPES:
                raise ValueError(f'Unsupported PLY property type: {ply_type}')
            props.append((name, _PLY_TYPES[ply_type]))
        elif kw == 'end_header':
            break

    if count is None:
        raise ValueError('No "vertex" element found in PLY header.')
    names = {n for n, _ in props}
    missing = [r for r in _REQUIRED if r not in names]
    if missing:
        raise ValueError(f'PLY is missing required Gaussian-splat fields: {missing}')
    return count, np.dtype(props)


def _col(data, name):
    return data[name].astype(np.float32)


def convert(ply_path, splat_path, sort_by_importance=True):
    """Convert a Gaussian-splat PLY into a .splat file. Returns the splat count."""
    with open(ply_path, 'rb') as f:
        count, dtype = _parse_header(f)
        data = np.fromfile(f, dtype=dtype, count=count)
    if data.shape[0] != count:
        raise ValueError(f'Expected {count} vertices, read {data.shape[0]}.')

    position = np.ascontiguousarray(
        np.stack([_col(data, 'x'), _col(data, 'y'), _col(data, 'z')], axis=1)
    )
    scales = np.ascontiguousarray(
        np.exp(np.stack([_col(data, 'scale_0'), _col(data, 'scale_1'), _col(data, 'scale_2')], axis=1))
    )

    rgb = 0.5 + SH_C0 * np.stack([_col(data, 'f_dc_0'), _col(data, 'f_dc_1'), _col(data, 'f_dc_2')], axis=1)
    alpha = 1.0 / (1.0 + np.exp(-_col(data, 'opacity')))
    color = np.concatenate([rgb, alpha[:, None]], axis=1)
    color_u8 = np.clip(color * 255.0, 0, 255).astype(np.uint8)

    rot = np.stack([_col(data, 'rot_0'), _col(data, 'rot_1'), _col(data, 'rot_2'), _col(data, 'rot_3')], axis=1)
    norm = np.linalg.norm(rot, axis=1, keepdims=True)
    norm[norm == 0] = 1.0
    rot_u8 = np.clip(rot / norm * 128.0 + 128.0, 0, 255).astype(np.uint8)

    if sort_by_importance:
        # Bigger, more opaque splats first — improves progressive reveal.
        importance = scales.prod(axis=1) * alpha
        order = np.argsort(-importance)
        position, scales = position[order], scales[order]
        color_u8, rot_u8 = color_u8[order], rot_u8[order]

    out = np.empty((count, 32), dtype=np.uint8)
    out[:, 0:12] = position.view(np.uint8).reshape(count, 12)
    out[:, 12:24] = scales.view(np.uint8).reshape(count, 12)
    out[:, 24:28] = color_u8
    out[:, 28:32] = rot_u8
    out.tofile(splat_path)
    return count


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 1
    count = convert(argv[1], argv[2])
    print(f'Wrote {count} splats -> {argv[2]} ({count * 32} bytes)')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
