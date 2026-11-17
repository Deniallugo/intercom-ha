"""Voice S3 wall unit — the Fusion model.

`placement`, `params`, `elec`, `checks` and `xf` are pure Python and import nothing from Fusion,
so the numbers, the electronics layout and every constraint can be checked without opening any
CAD package (../../test.sh). Everything else builds geometry through `build`, the only module
that touches the adsk API for modelling.
"""
