"""AI DATA AUDIT BOT
Production-ready Telegram bot for spreadsheet auditing.
"""

from __future__ import annotations

import pandas as pd

MAX_ANALYSIS_ROWS = 50_000
MAX_NUMERIC_COLUMNS = 20


class ExcelParseError(Exception):
    """Raised when an Excel file cannot be parsed safely."""


def detect_sheet_type(df: pd.DataFrame) -> str:
    columns = [c.lower() for c in df.columns]

    if any(c in columns for c in ["price", "revenue", "sales", "amount"]):
        return "financial"
    if any(c in columns for c in ["product", "stock", "inventory", "quantity"]):
        return "inventory"
    if any(c in columns for c in ["customer", "client", "email"]):
        return "customer"
    return "generic"


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lookup = {column.lower(): column for column in df.columns}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    return None


def _build_report_text(result: dict) -> str:
    summary = result["dataset_summary"]
    metrics = result["metrics"]
    issues = result["issues"]
    anomalies = result["anomalies"]
    score = result["score"]

    lines = [
        "AI DATA AUDIT REPORT",
        "",
        "Dataset",
        f"Rows: {summary['rows']}",
        f"Columns: {summary['columns']}",
        f"Type: {summary['detected_type'].title()}",
        "",
        "Metrics",
        f"Rows: {metrics['rows']}",
        f"Columns: {metrics['columns']}",
    ]

    if "average_price" in metrics:
        lines.append(f"Average price: {metrics['average_price']}")
    if "total_revenue" in metrics:
        lines.append(f"Total revenue: {metrics['total_revenue']}")
    if "max_revenue" in metrics:
        lines.append(f"Max revenue: {metrics['max_revenue']}")

    lines.extend(
        [
            "",
            "Issues Detected",
            f"Missing values: {issues['missing_values']}",
            f"Duplicate rows: {issues['duplicate_rows']}",
            f"Type errors: {issues['type_errors']}",
            f"Outliers detected: {anomalies}",
            "",
            "Data Quality Score",
            f"{score}/100",
        ]
    )

    if result["partial_analysis"]:
        lines.extend(
            [
                "",
                "Note: Partial analysis performed due to dataset size limit.",
            ]
        )

    return "\n".join(lines).strip()


def analyze_excel(file_path: str) -> dict:
    try:
        df = pd.read_excel(file_path)
    except Exception as exc:  # noqa: BLE001
        raise ExcelParseError("Could not parse excel file") from exc

    original_rows = int(df.shape[0])
    partial_analysis = False

    # Dataset protection: bounding rows prevents expensive scans from stalling workers.
    if original_rows > MAX_ANALYSIS_ROWS:
        df = df.head(MAX_ANALYSIS_ROWS).copy()
        partial_analysis = True

    rows = int(df.shape[0])
    columns = int(df.shape[1])
    detected_type = detect_sheet_type(df)

    numeric_columns = list(df.select_dtypes(include="number").columns[:MAX_NUMERIC_COLUMNS])

    missing_values = {}
    for column in df.columns:
        count = int(df[column].isna().sum())
        if count > 0:
            missing_values[column] = count

    duplicate_rows = int(df.duplicated().sum())

    anomalies = {}
    total_anomalies = 0
    # Anomaly detection runs only on numeric columns to avoid text-type false positives.
    for column in numeric_columns:
        series = df[column].dropna()
        if series.empty:
            continue
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        outlier_count = int(((series < lower_bound) | (series > upper_bound)).sum())
        if outlier_count > 0:
            anomalies[column] = outlier_count
            total_anomalies += outlier_count

    type_errors = {}
    # Numeric type checks are scoped to numeric columns for precise validations.
    for column in numeric_columns:
        converted = pd.to_numeric(df[column], errors="coerce")
        invalid_values = int((converted.isna() & df[column].notna()).sum())
        if invalid_values > 0:
            type_errors[column] = invalid_values

    metrics = {"rows": rows, "columns": columns}

    price_column = _find_column(df, ["price"])
    revenue_column = _find_column(df, ["revenue", "sales", "amount"])
    quantity_column = _find_column(df, ["quantity"])

    if price_column:
        price_series = pd.to_numeric(df[price_column], errors="coerce")
        average_price = float(price_series.mean(skipna=True)) if not price_series.empty else 0.0
        metrics["average_price"] = round(average_price, 2)

    if revenue_column:
        revenue_series = pd.to_numeric(df[revenue_column], errors="coerce")
        metrics["total_revenue"] = round(float(revenue_series.fillna(0).sum()), 2)
        max_revenue = float(revenue_series.max(skipna=True)) if not revenue_series.empty else 0.0
        metrics["max_revenue"] = round(max_revenue, 2)

    if quantity_column:
        quantity_series = pd.to_numeric(df[quantity_column], errors="coerce")
        metrics["total_quantity"] = round(float(quantity_series.fillna(0).sum()), 2)

    # Quality score summarizes health signals for easy auditing.
    score = 100
    score -= 5 * len(missing_values)
    score -= 10 * duplicate_rows
    score -= 5 * total_anomalies
    score -= 3 * sum(type_errors.values())
    score = max(0, min(100, score))

    result = {
        "dataset_summary": {
            "rows": rows,
            "columns": columns,
            "detected_type": detected_type,
            "numeric_columns_analyzed": len(numeric_columns),
        },
        "metrics": metrics,
        "issues": {
            "missing_values": missing_values,
            "duplicate_rows": duplicate_rows,
            "type_errors": type_errors,
        },
        "anomalies": anomalies,
        "score": score,
        "partial_analysis": partial_analysis,
    }
    result["report_text"] = _build_report_text(result)
    return result
