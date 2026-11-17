#!/usr/bin/env python3
"""Pure synthetic converter test; includes no user audio bytes."""
import importlib.util
import io
import struct
import tempfile
import wave
import zipfile
from pathlib import Path
file=Path(__file__).with_name("l6028_pack_wavs.py")
spec=importlib.util.spec_from_file_location("l6028_pack_wavs", file)
assert spec and spec.loader
packer=importlib.util.module_from_spec(spec)
spec.loader.exec_module(packer)
with tempfile.TemporaryDirectory() as d:
    base=Path(d)
    src=base/"input.zip"
    with zipfile.ZipFile(src,"w") as z:
        for i in range(1,9):
            stream=io.BytesIO()
            with wave.open(stream,"wb") as wav:
                wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(44100)
                wav.writeframes(struct.pack("<"+"h"*32,*([i*1000]*32)))
            z.writestr(f"samples/{i} synthetic.wav",stream.getvalue())
        z.writestr("__MACOSX/samples/._ignore.wav",b"bad")
    dst=base/"packed.bin"
    result=packer.convert(src,dst)
    data=dst.read_bytes()
    assert data[:8]==b"L6028PK1"
    assert struct.unpack_from("<II",data,8)==(8,0)
    assert all(struct.unpack_from("<II",data,16+8*i)==(32,48) for i in range(8))
    assert len(data)==80+8*48*2
    assert result["samples"][7]["start_word"]==0x39000
print("L6028 sample packer synthetic test: PASS")
