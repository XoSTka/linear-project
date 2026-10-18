# Examples

Small scripts that reproduce the hand calculations in the report (chapter 4) with the project code.
Run from the repository root:

```
pip install -e .            # or: set PYTHONPATH=src
python examples/ex2_svd_2x2.py
```

| Script | Report section |
|---|---|
| `ex1_vectors.py` | 4.1 norm, dot product, cosine (NCC), bits mod 2 |
| `ex2_svd_2x2.py` | 4.2 SVD of a 2x2 matrix by hand and with numpy |
| `ex3_qim_block.py` | 4.3 hide one bit in sigma_1 of a block (QIM) |
| `ex4_watermark.py` | 4.4 Liu-Tan watermark and the never-marked check |
| `ex5_hamming.py` | 4.5 Hamming(7,4) encode / correct |
| `ex6_hide_text.py` | whole pipeline on a real photo |
