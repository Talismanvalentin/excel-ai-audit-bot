import pandas as pd


def detect_sheet_type(df):

    columns = [c.lower() for c in df.columns]

    if any(c in columns for c in ["price", "revenue", "sales", "amount"]):
        return "financial"

    if any(c in columns for c in ["product", "stock", "inventory", "quantity"]):
        return "inventory"

    if any(c in columns for c in ["customer", "client", "email"]):
        return "customer"

    return "generic"


def analyze_excel(file_path):

    report = []

    df = pd.read_excel(file_path)

# dataset info
    report.append(f"Rows: {df.shape[0]}, Columns: {df.shape[1]}")
    
    sheet_type = detect_sheet_type(df)

    report.append(f"Spreadsheet type detected: {sheet_type}")

    # Missing values
    for column in df.columns:
        if df[column].isnull().sum() > 0:
            report.append(f"Missing values detected in column: {column}")

    # Duplicates
    duplicates = df.duplicated().sum()
    if duplicates > 0:
        report.append(f"Duplicated rows detected: {duplicates}")

    # Outlier detection
    numeric_columns = df.select_dtypes(include="number").columns

    for column in numeric_columns:

        Q1 = df[column].quantile(0.25)
        Q3 = df[column].quantile(0.75)

        IQR = Q3 - Q1

        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

        outliers = df[(df[column] < lower_bound) | (df[column] > upper_bound)]

        if not outliers.empty:
            report.append(
                f"Possible anomalies detected in column '{column}': {len(outliers)} values outside expected range"
            )

    # Column type consistency check
    for column in df.columns:

        converted = pd.to_numeric(df[column], errors="coerce")

        invalid_values = converted.isna() & df[column].notna()

        count_invalid = invalid_values.sum()

        if count_invalid > 0:
            report.append(
                f"Non-numeric values detected in column '{column}': {count_invalid}"
            )

    if not report:
        report.append("No issues detected")

    return report