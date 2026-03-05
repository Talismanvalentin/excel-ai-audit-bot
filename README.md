# AI Excel Error Detector Bot

## Overview

**AI Excel Error Detector Bot** is a Telegram bot that analyzes Excel spreadsheets and detects common data issues that can cause financial mistakes, reporting errors, or operational problems.

The bot automatically scans uploaded Excel files and generates a report highlighting potential problems such as missing values, duplicated rows, inconsistent data types, and suspicious anomalies.

This project is designed as a lightweight **automation and data auditing tool** that helps analysts, developers, and businesses quickly identify spreadsheet risks.

---

## Problem

Spreadsheets are widely used in businesses, finance, and analytics. However, they are prone to human errors such as:

* Broken formulas
* Incorrect totals
* Missing values
* Data inconsistencies
* Duplicated entries
* Hidden anomalies

These errors can lead to serious consequences including incorrect financial decisions or corrupted reports.

The **AI Excel Error Detector Bot** helps reduce these risks by performing automated spreadsheet checks.

---

## Features

### Excel File Analysis

Users can send `.xlsx` files directly to the Telegram bot.

The bot automatically processes the spreadsheet and runs a set of validation checks.

---

### Missing Data Detection

Detects columns containing missing or empty values.

Example output:

```
Missing values detected in column: revenue
```

---

### Duplicate Row Detection

Identifies duplicated entries that could lead to double counting.

Example output:

```
Duplicated rows detected: 3
```

---

### Data Consistency Checks

Detects columns where data types may be inconsistent.

Example:

```
Column "price" contains non-numeric values
```

---

### Anomaly Detection (planned)

Future versions will include statistical anomaly detection to identify suspicious values such as unusually large financial numbers.

Example:

```
Possible anomaly detected in row 42
```

---

## How It Works

The system follows a simple workflow:

```
User sends Excel file
        ↓
Telegram bot receives file
        ↓
File is downloaded locally
        ↓
Excel analyzer processes the spreadsheet
        ↓
Issues are detected
        ↓
Bot returns a formatted report
```

---

## Project Structure

```
AI-Excel-Error-Detector-Bot

bot.py               # Telegram bot main logic
excel_analyzer.py    # Excel analysis module
requirements.txt     # Project dependencies
README.md            # Project documentation
downloads/           # Temporary storage for uploaded files
```

---

## Technologies Used

* **Python 3**
* **Telegram Bot API**
* **python-telegram-bot**
* **pandas**
* **openpyxl**
* **numpy**

Optional future integrations:

* AI models for advanced error explanations
* anomaly detection algorithms
* cloud storage for reports

---

## Installation

### 1. Clone the repository

```
git clone https://github.com/YOUR_USERNAME/AI-Excel-Error-Detector-Bot.git
cd AI-Excel-Error-Detector-Bot
```

---

### 2. Install dependencies

```
pip install -r requirements.txt
```

---

### 3. Configure environment variables

Create a `.env` file and add your Telegram bot token.

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

---

### 4. Run the bot

```
python bot.py
```

---

## Usage

1. Open Telegram.
2. Start the bot.
3. Upload an Excel `.xlsx` file.
4. Wait a few seconds.
5. Receive an automated analysis report.

Example response:

```
Excel Analysis Complete

Issues detected:

• Missing values in column "price"
• 2 duplicated rows
• Possible anomaly detected
```

---

## Example Use Cases

* Financial spreadsheet validation
* Data quality verification
* Internal business audits
* Preventing spreadsheet mistakes
* Data cleaning assistance

---

## Roadmap

Planned improvements:

* AI-powered formula analysis
* Financial anomaly detection
* Spreadsheet security scanning
* Report export (PDF / JSON)
* Web dashboard
* SaaS version

---

## Security Considerations

Uploaded files are processed locally and can be automatically deleted after analysis.

Future improvements will include:

* automatic file cleanup
* file size limits
* sandboxed processing environment

---

## License

MIT License

---

## Author

Developed by **Talismanvalentin**

This project explores automation, data validation, and AI-assisted auditing tools designed to reduce spreadsheet errors and improve data reliability.

