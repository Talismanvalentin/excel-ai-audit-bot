"""AI DATA AUDIT BOT
Production-ready Telegram bot for spreadsheet auditing.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import UTC, datetime
from html import escape

import requests
from dotenv import load_dotenv
from excel_analyzer import ExcelParseError, analyze_excel
from telegram import Update
from telegram.error import NetworkError, TimedOut
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("excel_audit_bot")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
WORKER_COUNT = 4
ENABLE_TEXT_REPORT_EXPORT = True

# Queue safety: maxsize protects service from overload and keeps bot responsive.
processing_queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=200)


def _html(value: object) -> str:
    return escape(str(value))


def _format_seconds(seconds: float) -> str:
    return f"{seconds:.2f}s"


def _build_recommendations_from_ai(ai_output: str) -> list[str]:
    recommendations: list[str] = []
    for raw_line in ai_output.splitlines():
        line = raw_line.strip().lstrip("-").lstrip("•").strip()
        if line:
            recommendations.append(line)
        if len(recommendations) == 3:
            break
    return recommendations


def _default_recommendations(analysis_result: dict) -> list[str]:
    issues = analysis_result["issues"]
    anomalies = analysis_result["anomalies"]

    recommendations: list[str] = []
    if issues["missing_values"]:
        recommendations.append("Fill or remove missing values")
    if issues["duplicate_rows"] > 0:
        recommendations.append("Remove duplicate rows")
    if anomalies:
        recommendations.append("Investigate numeric outliers")
    if not recommendations:
        recommendations.append("Apply a data validation schema before import")
    return recommendations[:3]


def explain_report(structured_report_text: str) -> list[str]:
    prompt = f"""
You are a senior data auditor.
Return exactly 3 short bullet recommendations.
Each recommendation must be one line and less than 80 characters.
Do not include headings.

AUDIT REPORT:
{structured_report_text}
"""

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "openrouter/free",
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=40,
    )
    response.raise_for_status()
    data = response.json()
    content = data["choices"][0]["message"]["content"].strip()
    return _build_recommendations_from_ai(content)


def format_report_html(report_data: dict) -> str:
    analysis_result = report_data["analysis_result"]
    recommendations = report_data["recommendations"]
    ai_fallback_used = report_data["ai_fallback_used"]

    summary = analysis_result["dataset_summary"]
    issues = analysis_result["issues"]
    anomalies = analysis_result["anomalies"]
    metrics = analysis_result["metrics"]

    missing_columns = ", ".join(issues["missing_values"].keys()) if issues["missing_values"] else "None"
    outlier_columns = ", ".join(anomalies.keys()) if anomalies else "None"

    lines = [
        "<b>AI DATA AUDIT REPORT</b>",
        "",
        "<b>Dataset</b>",
        f"Rows: {_html(summary['rows'])}",
        f"Columns: {_html(summary['columns'])}",
        f"Type: {_html(summary['detected_type'].title())}",
        "",
        "<b>Issues Detected</b>",
        f"• Missing values: {_html(missing_columns)}",
        f"• Duplicate rows: {_html(issues['duplicate_rows'])}",
        f"• Outliers detected: {_html(outlier_columns)}",
        "",
        "<b>Data Quality Score</b>",
        f"{_html(analysis_result['score'])} / 100",
    ]

    if "average_price" in metrics or "total_revenue" in metrics or "max_revenue" in metrics:
        lines.extend(
            [
                "",
                "<b>Business Metrics</b>",
            ]
        )
        if "average_price" in metrics:
            lines.append(f"• Average price: {_html(metrics['average_price'])}")
        if "total_revenue" in metrics:
            lines.append(f"• Total revenue: {_html(metrics['total_revenue'])}")
        if "max_revenue" in metrics:
            lines.append(f"• Max revenue: {_html(metrics['max_revenue'])}")

    lines.extend(["", "<b>Recommended Fixes</b>"])
    for recommendation in recommendations[:3]:
        lines.append(f"• {_html(recommendation)}")

    lines.extend(["", "Full report saved for download."])
    if ai_fallback_used:
        lines.append("⚠️ AI analysis temporarily unavailable.")
    lines.append("")
    lines.append("<i>Generated by AI Data Audit Bot</i>")
    return "\n".join(lines)


def _split_message(text: str, max_len: int = 3500) -> list[str]:
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= max_len:
            chunks.append(remaining)
            break
        split_at = remaining.rfind("\n", 0, max_len)
        if split_at <= 0:
            split_at = max_len
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].lstrip()
    return chunks


async def _send_html_report(application: Application, chat_id: int, report_html: str) -> None:
    for chunk in _split_message(report_html, max_len=3500):
        await application.bot.send_message(
            chat_id=chat_id,
            text=chunk,
            parse_mode="HTML",
        )


def _format_text_report(
    analysis_result: dict, recommendations: list[str], ai_fallback_used: bool
) -> str:
    summary = analysis_result["dataset_summary"]
    issues = analysis_result["issues"]
    anomalies = analysis_result["anomalies"]
    metrics = analysis_result["metrics"]

    missing_columns = ", ".join(issues["missing_values"].keys()) if issues["missing_values"] else "None"
    outlier_columns = ", ".join(anomalies.keys()) if anomalies else "None"

    lines = [
        "AI DATA AUDIT REPORT",
        "",
        "Dataset",
        f"Rows: {summary['rows']}",
        f"Columns: {summary['columns']}",
        f"Type: {summary['detected_type'].title()}",
        "",
        "Issues Detected",
        f"- Missing values: {missing_columns}",
        f"- Duplicate rows: {issues['duplicate_rows']}",
        f"- Outliers detected: {outlier_columns}",
        "",
        "Data Quality Score",
        f"{analysis_result['score']} / 100",
    ]

    if "average_price" in metrics or "total_revenue" in metrics or "max_revenue" in metrics:
        lines.extend(["", "Business Metrics"])
        if "average_price" in metrics:
            lines.append(f"- Average price: {metrics['average_price']}")
        if "total_revenue" in metrics:
            lines.append(f"- Total revenue: {metrics['total_revenue']}")
        if "max_revenue" in metrics:
            lines.append(f"- Max revenue: {metrics['max_revenue']}")

    lines.extend(["", "Recommended Fixes"])
    for recommendation in recommendations[:3]:
        lines.append(f"- {recommendation}")

    if ai_fallback_used:
        lines.extend(["", "AI analysis temporarily unavailable. Basic report returned."])

    lines.extend(["", "Generated by AI Data Audit Bot"])
    return "\n".join(lines)


def save_report_files(
    analysis_result: dict,
    chat_id: int,
    file_name: str,
    txt_report: str,
) -> dict:
    os.makedirs("reports", exist_ok=True)
    created_at = datetime.now(UTC)
    timestamp = created_at.strftime("%Y%m%dT%H%M%SZ")
    suffix = uuid.uuid4().hex[:6]
    base_name = f"report_{timestamp}_{suffix}"

    json_path = os.path.join("reports", f"{base_name}.json")
    txt_path = os.path.join("reports", f"{base_name}.txt")

    # SaaS-ready persistence: structured JSON for later querying or dashboards.
    json_payload = {
        "chat_id": chat_id,
        "source_file": file_name,
        "created_at_utc": created_at.isoformat(),
        "dataset_summary": analysis_result["dataset_summary"],
        "metrics": analysis_result["metrics"],
        "issues": analysis_result["issues"],
        "anomalies": analysis_result["anomalies"],
        "score": analysis_result["score"],
        "report_text": txt_report,
    }
    with open(json_path, "w", encoding="utf-8") as json_file:
        json.dump(json_payload, json_file, ensure_ascii=False, indent=2)

    if ENABLE_TEXT_REPORT_EXPORT:
        with open(txt_path, "w", encoding="utf-8") as txt_file:
            txt_file.write(txt_report)

    return {"json_path": json_path, "txt_path": txt_path if ENABLE_TEXT_REPORT_EXPORT else None}


async def _send_delayed_status(chat_id: int, completion_event: asyncio.Event, application: Application):
    await asyncio.sleep(5)
    if not completion_event.is_set():
        await application.bot.send_message(
            chat_id=chat_id,
            text="⏳ AI analysis in progress...",
        )


async def worker(application: Application):
    while True:
        task = await processing_queue.get()
        start_time = time.time()

        path = task["path"]
        chat_id = task["chat_id"]
        file_name = task["file_name"]
        file_size = task.get("file_size", 0)

        completion_event = asyncio.Event()
        delayed_status_task = asyncio.create_task(
            _send_delayed_status(chat_id, completion_event, application)
        )

        try:
            logger.info(
                "event=file_processing_start chat_id=%s file_name=%s file_size=%s queue_size=%s",
                chat_id,
                file_name,
                file_size,
                processing_queue.qsize(),
            )

            analysis_result = await asyncio.to_thread(analyze_excel, path)
            ai_fallback_used = False
            try:
                recommendations = await asyncio.to_thread(
                    explain_report, analysis_result["report_text"]
                )
                if not recommendations:
                    recommendations = _default_recommendations(analysis_result)
                    ai_fallback_used = True
            except Exception:
                logger.exception(
                    "event=ai_analysis_error chat_id=%s file_name=%s",
                    chat_id,
                    file_name,
                )
                recommendations = _default_recommendations(analysis_result)
                ai_fallback_used = True

            report_html = format_report_html(
                {
                    "analysis_result": analysis_result,
                    "recommendations": recommendations,
                    "ai_fallback_used": ai_fallback_used,
                }
            )
            txt_report = _format_text_report(analysis_result, recommendations, ai_fallback_used)
            report_paths = await asyncio.to_thread(
                save_report_files, analysis_result, chat_id, file_name, txt_report
            )

            if ai_fallback_used:
                await application.bot.send_message(
                    chat_id=chat_id,
                    text="⚠️ AI analysis temporarily unavailable.",
                )
            await _send_html_report(application, chat_id, report_html)

            processing_time = time.time() - start_time
            rows = analysis_result["dataset_summary"]["rows"]
            cols = analysis_result["dataset_summary"]["columns"]
            logger.info(
                "analysis_complete rows=%s cols=%s time=%s queue_size=%s",
                rows,
                cols,
                _format_seconds(processing_time),
                processing_queue.qsize(),
            )
            logger.info(
                "event=file_processing_finished chat_id=%s file_name=%s processing_time_seconds=%.3f queue_size=%s report_json=%s report_txt=%s",
                chat_id,
                file_name,
                processing_time,
                processing_queue.qsize(),
                report_paths["json_path"],
                report_paths["txt_path"],
            )
        except ExcelParseError:
            logger.exception(
                "event=excel_parse_error chat_id=%s file_name=%s queue_size=%s",
                chat_id,
                file_name,
                processing_queue.qsize(),
            )
            await application.bot.send_message(
                chat_id=chat_id,
                text="⚠️ Could not read this Excel file.",
            )
        except Exception:
            logger.exception(
                "event=file_processing_error chat_id=%s file_name=%s queue_size=%s",
                chat_id,
                file_name,
                processing_queue.qsize(),
            )
            await application.bot.send_message(
                chat_id=chat_id,
                text="An error occurred while processing your file. Please try again.",
            )
        finally:
            completion_event.set()
            delayed_status_task.cancel()
            await asyncio.gather(delayed_status_task, return_exceptions=True)
            if os.path.exists(path):
                os.remove(path)
            processing_queue.task_done()


async def post_init(application: Application):
    worker_tasks = [
        asyncio.create_task(worker(application), name=f"worker-{i}")
        for i in range(WORKER_COUNT)
    ]
    application.bot_data["worker_tasks"] = worker_tasks
    logger.info("event=worker_pool_started worker_count=%s", WORKER_COUNT)


async def post_shutdown(application: Application):
    worker_tasks = application.bot_data.get("worker_tasks", [])
    for task in worker_tasks:
        task.cancel()
    await asyncio.gather(*worker_tasks, return_exceptions=True)
    logger.info("event=worker_pool_stopped worker_count=%s", len(worker_tasks))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 AI Data Audit Bot\n\n"
        "Send an Excel file (.xlsx) and receive a concise data audit report."
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    file_size = document.file_size or 0

    if file_size > MAX_FILE_SIZE:
        await update.message.reply_text("File too large. Maximum allowed size is 10MB.")
        return

    if processing_queue.full():
        logger.warning(
            "event=queue_full chat_id=%s queue_size=%s file_name=%s file_size=%s",
            update.effective_chat.id,
            processing_queue.qsize(),
            os.path.basename(document.file_name or "uploaded.xlsx"),
            file_size,
        )
        await update.message.reply_text("⚠️ Server busy. Please try again in a moment.")
        return

    os.makedirs("downloads", exist_ok=True)
    safe_name = os.path.basename(document.file_name or "uploaded.xlsx")
    unique_name = f"{uuid.uuid4()}_{safe_name}"
    path = os.path.join("downloads", unique_name)

    file = await document.get_file()
    await file.download_to_drive(path)
    logger.info(
        "event=file_received chat_id=%s file_name=%s size_bytes=%s path=%s",
        update.effective_chat.id,
        safe_name,
        file_size,
        path,
    )

    try:
        processing_queue.put_nowait(
            {
                "chat_id": update.effective_chat.id,
                "path": path,
                "file_name": safe_name,
                "file_size": file_size,
            }
        )
    except asyncio.QueueFull:
        if os.path.exists(path):
            os.remove(path)
        logger.warning(
            "event=queue_full_after_download chat_id=%s queue_size=%s file_name=%s file_size=%s",
            update.effective_chat.id,
            processing_queue.qsize(),
            safe_name,
            file_size,
        )
        await update.message.reply_text("⚠️ Server busy. Please try again in a moment.")
        return

    logger.info(
        "event=task_enqueued chat_id=%s file_name=%s queue_size=%s file_size=%s",
        update.effective_chat.id,
        safe_name,
        processing_queue.qsize(),
        file_size,
    )
    await update.message.reply_text("📥 File received. Analyzing dataset...")


def build_application():
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    return app


if __name__ == "__main__":
    if not TELEGRAM_TOKEN:
        raise RuntimeError(
            "Missing Telegram token. Set TELEGRAM_TOKEN (or TELEGRAM_BOT_TOKEN) in .env."
        )

    print("BOT INICIADO ✅")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    retry_delay = 5
    max_retry_delay = 60
    while True:
        try:
            app = build_application()
            # Keep loop open across retries to avoid "Event loop is closed" on Python 3.14+.
            app.run_polling(close_loop=False)
            break
        except (TimedOut, NetworkError):
            logger.warning(
                "event=bot_startup_retry reason=network_timeout retry_in_seconds=%s",
                retry_delay,
            )
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_retry_delay)
