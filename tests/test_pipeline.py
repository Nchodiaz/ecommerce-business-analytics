import pandas as pd

from src.pipeline import clean_source, snake_case


def test_snake_case_source_headers() -> None:
    assert snake_case("InvoiceNo") == "invoice_no"
    assert snake_case("UnitPrice") == "unit_price"


def test_clean_source_separates_sales_and_returns() -> None:
    source = pd.DataFrame(
        {
            "InvoiceNo": ["100", "C101"],
            "StockCode": ["A", "A"],
            "Description": [" Product ", "Product"],
            "Quantity": [2, -1],
            "InvoiceDate": ["2024-01-01", "2024-01-02"],
            "UnitPrice": [10.0, 10.0],
            "CustomerID": [1, 1],
            "Country": ["United Kingdom", "United Kingdom"],
        }
    )

    result = clean_source(source)

    assert result["is_sale"].tolist() == [True, False]
    assert result["is_return"].tolist() == [False, True]
    assert result["sales_revenue"].tolist() == [20.0, 0.0]
    assert result["return_value"].tolist() == [0.0, 10.0]
    assert result.loc[0, "description"] == "Product"

