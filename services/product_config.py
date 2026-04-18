from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProductConfig:
    name: str
    hs_codes: tuple[str, ...]
    fao_column: str
    months_table: str


PRODUCTS: dict[str, ProductConfig] = {
    "shrimp": ProductConfig(
        name="shrimp",
        hs_codes=("030616", "030617"),
        fao_column="Shrimp",
        months_table="months_shrimp",
    ),
    "salmon": ProductConfig(
        name="salmon",
        hs_codes=("030313",),
        fao_column="Salmon",
        months_table="months_salmon",
    ),
    "tuna": ProductConfig(
        name="tuna",
        hs_codes=("030342",),
        fao_column="Tuna",
        months_table="months_tuna",
    ),
    "whitefish": ProductConfig(
        name="whitefish",
        hs_codes=("030389",),
        fao_column="Whitefish",
        months_table="months_whitefish",
    ),
}


def get_product_config(product: str) -> ProductConfig:
    normalized = product.strip().lower()
    try:
        return PRODUCTS[normalized]
    except KeyError as exc:
        valid = ", ".join(sorted(PRODUCTS))
        raise ValueError(f"Unknown product '{product}'. Expected one of: {valid}") from exc
