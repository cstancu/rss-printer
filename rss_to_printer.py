"""
RSS-to-Printer News Digest Script

- Randomly selects one news source from the FEED_SOURCES list each cycle.
- Fetches and parses the feed using feedparser.
- Generates a PDF formatted for easy reading on A4 paper (with date, title, and summary).
- The printable output is strictly limited to a single A4 page per cycle.
- Prints the PDF to the network printer specified via PRINTER_NAME.
- Optionally deletes the generated PDF after printing to save disk space (controlled by KEEP_PDF).
- Runs the process repeatedly every INTERVAL_MINUTES; all configuration is at the top of the script.

Requirements:
    - lpr: command-line print tool (CUPS/Unix printing system). 
    - feedparser: Python library to parse RSS and Atom feeds. Install with: pip install feedparser
    - reportlab: Python library to generate PDFs from Python. Install with: pip install reportlab
"""

import time
import feedparser
import subprocess
import sys
import os
import html
import datetime
import random
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepInFrame
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm

FEED_SOURCES = [
    ("CNN Top Stories", "http://rss.cnn.com/rss/cnn_topstories.rss"),
    ("Guardian World", "https://www.theguardian.com/world/rss"),
    ("NOAA Climate Highlights", "https://www.climate.gov/feeds/news-features/highlights.rss"),
    ("Civil Georgia", "https://civil.ge/feed"),
    ("Fox News World", "https://moxie.foxnews.com/google-publisher/world.xml"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/technology-lab"),
    # ("Hacker News", "https://hnrss.org/newest.jsonfeed"), # doesn't contain summaries
    # ("AP Climate/Environment", "https://apnews.com/climate-and-environment.rss"), # needs subscription
]
PRINTER_NAME = "TS9500" # Change to your printer name.
INTERVAL_MINUTES = 7 # Change to increase/decrease printing interval.
KEEP_PDF = False  # Set to True to keep the PDF after printing.

def fetch_feed(url):
    try:
        feed = feedparser.parse(url)
        if feed.bozo:
            print(f"Error parsing feed: {feed.bozo_exception}", file=sys.stderr)
            return None
        return feed
    except Exception as e:
        print(f"Exception fetching feed: {e}", file=sys.stderr)
        return None

def format_entries(feed):
    # Build a list of dicts: [{'title': ..., 'published':..., 'summary':...}, ...]
    if not feed or 'entries' not in feed:
        return []
    entries = feed.entries
    result = []
    for entry in entries:
        title = entry.get('title', 'No title')
        published = entry.get('published', 'No date')
        summary = entry.get('summary', '')
        result.append({
            'title': html.escape(title),
            'published': html.escape(published),
            'summary': summary  # leave as-is to allow some inline HTML in summary
        })
    return result

def print_to_printer(pdf_path, printer_name):
    try:
        # Use lpr to send the PDF file to the named printer
        subprocess.run([
            "lpr", "-P", printer_name, pdf_path
        ], check=True)
        print(f"Printed PDF {pdf_path} to {printer_name} successfully.")
    except Exception as e:
        print(f"Printing failed: {e}", file=sys.stderr)

def save_as_pdf(entries, directory="."):
    # Ensure content never exceeds one A4 page by using KeepInFrame
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{directory}/rss_printout_{timestamp}.pdf"
    try:
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'feedTitle',
            parent=styles['Heading2'],
            fontName="Times-Roman",
            fontSize=17,
            leading=21,
            spaceAfter=3*mm,
            spaceBefore=2*mm,
            textColor=colors.darkblue,
        )
        date_style = ParagraphStyle(
            'feedDate',
            parent=styles['Normal'],
            fontName="Times-Roman",
            fontSize=11,
            leading=13,
            textColor=colors.darkgrey,
            leftIndent=2*mm,
        )
        summary_style = ParagraphStyle(
            'feedSummary',
            parent=styles['Normal'],
            fontName="Times-Roman",
            fontSize=13,
            leading=16,
            leftIndent=3*mm,
            spaceAfter=7,
        )

        # Variables for page layout
        width, height = A4
        leftMargin = rightMargin = topMargin = bottomMargin = 18
        available_width = width - leftMargin - rightMargin
        available_height = height - topMargin - bottomMargin

        # Revert to: add all items and use KeepInFrame with mode='truncate' so content is scaled/truncated to fit
        item_list = []
        for entry in entries:
            item_list.append(Paragraph(f"<b>{entry['title']}</b>", title_style))
            item_list.append(Paragraph(f"{entry['published']}", date_style))
            item_list.append(Paragraph(entry['summary'], summary_style))
            item_list.append(Spacer(1, 6))
        if not item_list:
            item_list.append(Paragraph("No entries found.", styles['Normal']))

        elements = [
            KeepInFrame(available_width, available_height, item_list, mergeSpace=1, mode='truncate')
        ]

        doc = SimpleDocTemplate(
            filename, pagesize=A4,
            leftMargin=leftMargin, rightMargin=rightMargin,
            topMargin=topMargin, bottomMargin=bottomMargin
        )
        doc.build(elements)
        print(f"Saved PDF: {filename}")
        return filename
    except Exception as e:
        print(f"Failed to save PDF: {e}", file=sys.stderr)
        return None

def main():
    print("Starting RSS to printer script. Press Ctrl+C to stop.")
    while True:
        chosen_fullname, chosen_feed_url = random.choice(FEED_SOURCES)
        print(f"Fetching from: {chosen_feed_url} ({chosen_fullname})")
        feed = fetch_feed(chosen_feed_url)
        entries = format_entries(feed)
        # Prepend information about the selected feed as a paragraph
        if entries:
            entries = [{
                'title': f"Feed Source: {chosen_fullname}",
                'published': "",
                'summary': ""
            }] + entries
        else:
            entries = [{
                'title': f"Feed Source: {chosen_fullname}",
                'published': "",
                'summary': ""
            }]
        # Save the printable text as HTML-PDF first
        pdf_path = save_as_pdf(entries)
        if pdf_path:
            print_to_printer(pdf_path, PRINTER_NAME)
            if not KEEP_PDF:
                try:
                    os.remove(pdf_path)
                    print(f"Deleted PDF: {pdf_path}")
                except Exception as e:
                    print(f"Failed to delete PDF: {e}", file=sys.stderr)
        print(f"Next run in {INTERVAL_MINUTES} minutes...")
        time.sleep(INTERVAL_MINUTES * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stopped by user.")
