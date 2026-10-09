"""SKU catalog of config/donghan/demo_original6/order.json (integrated repo), as
``pac_runtime.order.cell_from_order`` builds it (nominal weight = range max)."""
from pac_common import Size3D, SkuSpec

YAWS = (0.0, 1.5707963267948966)
ORDER = {
    "K03": ((0.27, 0.18, 0.15), (1.394617, 1.394617)),
    "K04": ((0.27, 0.20, 0.13), (0.860186, 0.860186)),
    "K08": ((0.34, 0.25, 0.21), (1.741063, 4.800477)),
    "K13": ((0.52, 0.48, 0.40), (13.087056, 28.486273)),
}
CATALOG = {sku: SkuSpec(sku, Size3D(*size), hi, YAWS, 400.0) for sku, (size, (lo, hi)) in ORDER.items()}
WEIGHT_RANGES = {sku: rng for sku, (_, rng) in ORDER.items()}
