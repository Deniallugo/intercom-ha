"""Voice S3 desk puck — the model, split as the OpenSCAD modules were.

`params` and `checks` are pure Python and import nothing from Fusion, so the design's
numbers and constraints can be checked without opening any CAD package. Everything else
builds geometry through `build`, which is the only module that touches the adsk API.
"""
