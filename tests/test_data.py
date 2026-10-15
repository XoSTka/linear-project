import numpy as np
import pandas as pd
from PIL import Image

from svdmark.data import crop_to_multiple, load_gray, sample_images, to_gray


def test_crop_is_centred_and_multiple():
    a = np.arange(321 * 481, dtype=float).reshape(321, 481)
    c = crop_to_multiple(a, 16)
    assert c.shape == (320, 480)
    assert c[0, 0] == a[0, 0]                       # 1 leftover row/col: cropped from the end side
    b = crop_to_multiple(np.zeros((70, 70)), 16)    # 6 leftover: 3 each side
    assert b.shape == (64, 64)


def test_load_gray_luma_and_shape(tmp_path):
    im = Image.new("RGB", (33, 17), (200, 100, 50))
    p = tmp_path / "x.png"; im.save(p)
    g = load_gray(p, 16)
    assert g.shape == (16, 32)
    assert g[0, 0] == round(0.299 * 200 + 0.587 * 100 + 0.114 * 50)


def test_transparent_png_flattened_on_white():
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    assert to_gray(im).min() == 255


def test_sampling_is_reproducible_and_unique():
    df = pd.DataFrame({"filename": [f"{i}.jpg" for i in range(500)]})
    a, b = sample_images(df), sample_images(df)
    assert a.equals(b) and len(a) == 150 and a["filename"].is_unique
    assert not a.equals(sample_images(df, seed=1))
