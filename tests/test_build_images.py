"""Exercise real image decoding/encoding, not the logo passthrough path."""
import base64
import io
import re
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

REPO = Path(__file__).resolve().parent.parent


def build_fixture(tmp_path, filename, content):
    deck = tmp_path / "中文 image fixture"
    (deck / "slides").mkdir(parents=True)
    (deck / filename).write_bytes(content)
    (deck / "deck.json").write_text('{"title":"合成图片验证","style":"苹果风"}', encoding="utf-8")
    (deck / "slides/01_image.html").write_text(
        '<section class="slide"><h2>合成图片</h2><img id="fixture" src="{{img:'
        + filename + '}}" style="max-width:100%;max-height:70vh"></section>', encoding="utf-8")
    output = tmp_path / "single-file.html"
    result = subprocess.run([sys.executable, str(REPO / "tools/build_deck.py"),
                             "--deck", str(deck), "--engine-root", str(REPO), "--out", str(output)],
                            capture_output=True, text=True, encoding="utf-8")
    return result, output


@pytest.mark.parametrize("mode,size,filename,expected_format,expected_size", [
    ("RGB", (80, 40), "普通图片.png", "JPEG", (80, 40)),
    ("RGBA", (80, 40), "透明图片.png", "JPEG", (80, 40)),
    ("RGB", (2800, 1400), "大图.png", "JPEG", (1400, 700)),
    ("RGBA", (80, 40), "二维码.png", "PNG", (80, 40)),
    ("RGBA", (2800, 1400), "qr-large.png", "PNG", (1400, 700)),
])
def test_real_builder_image_contract(tmp_path, mode, size, filename, expected_format, expected_size):
    color = (30, 80, 160, 77) if mode == "RGBA" else (30, 80, 160)
    source = Image.new(mode, size, color)
    buffer = io.BytesIO()
    source.save(buffer, format="PNG")
    result, output = build_fixture(tmp_path, filename, buffer.getvalue())
    assert result.returncode == 0, result.stderr
    text = output.read_text(encoding="utf-8")
    assert "合成图片" in text and "{{img:" not in text
    match = re.search(r'id="fixture" src="data:image/(jpeg|png);base64,([^"]+)"', text)
    assert match, "Image must be embedded in the single-file output"
    assert match[1] == expected_format.lower()
    with Image.open(io.BytesIO(base64.b64decode(match[2]))) as decoded:
        assert decoded.format == expected_format
        assert decoded.size == expected_size
        if expected_format == "JPEG":
            assert decoded.mode == "RGB"
        else:
            assert decoded.mode == "RGBA"
            assert decoded.getchannel("A").getextrema() == (77, 77)
            if size == expected_size:
                assert decoded.tobytes() == source.tobytes(), "Unscaled QR PNG must stay lossless"


def test_corrupt_image_fails_real_builder_without_success_output(tmp_path):
    result, output = build_fixture(tmp_path, "broken.png", b"not an image")
    assert result.returncode != 0
    assert "cannot identify image file" in result.stderr
    assert not output.exists()
