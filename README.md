# LinkedIn Job Post Scraper

A simple Python script that automates LinkedIn job post discovery by scraping the latest posts made by recruiters.  
It filters posts based on parameters you define (like keywords or locations) and outputs a `.md` file with the relevant results.

---

## 🚀 Features

- Uses LinkedIn post search (not job board)
- Filters by:
  - Keywords (tech stack, roles)
  - Location
  - Email presence
- Outputs a clean `.md` file with:
  - Post link
  - Timestamp
  - Formatted content (suitable for manual review)
- Ignores posts with Gmail addresses (for cleaner outreach)
- Optionally collects public recruiter email (non-Gmail only)

---

## 🛠️ Setup

1. Clone the repo:
   ```bash
   git clone https://github.com/yourusername/advance-search-linkedin
   cd advance-search-linkedin
2. Edit .env file
3. python main.py

## ⚠️ Disclaimer

This tool uses automation on LinkedIn. Use responsibly, and do not abuse platform limitations.
It's built for learning and outreach streamlining — not for spam or commercial scraping.
