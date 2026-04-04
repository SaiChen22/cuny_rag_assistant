# Data Collection Guide

## Schema
Each scraped page should produce one JSON object with the following fields:

{
    "text": "cleaned page text",
    "source": "https://...",
    "title": "page title",
    "college": "Baruch College",  # must match exactly: see college list below
    "category": "financial_aid",  # must match exactly: see category list below
    "section": "",                # optional, sub-heading if page has one
    "scraped_date": "2025-04-04"
}

## Controlled Vocabulary

COLLEGES (use exactly as written):
Baruch College, Brooklyn College, City College, College of Staten Island,
Hunter College, John Jay College, Lehman College, Medgar Evers College,
Queens College, York College, NYC College of Technology, CUNY System-wide

Use "CUNY System-wide" for pages sourced from cuny.edu that apply 
across all colleges rather than one specific institution.

CATEGORIES (use exactly as written):
financial_aid, tuition_and_fees, admissions, transfer, degree_requirements,
graduation, academic_policies, registration_enrollment, advising, campus_resources

## Week 3 Assignments

Sai     → financial_aid, tuition_and_fees
Roland  → transfer, registration_enrollment
Aleksia → admissions, degree_requirements
Patrick → academic_policies, campus_resources, advising
Monda   → graduation + eval question set

## Setup

1. Create a virtual environment:
   python -m venv venv
   or
   python3 -m venv venv

2. Activate it:
   Mac/Linux:  source venv/bin/activate
   Windows:    venv\Scripts\activate

3. Install dependencies:
   pip install -r requirements.txt

## Important Notes

- Run the script from the root of the repo, not from inside any subfolder:
    python scraper.py
    or
    python3 scraper.py
- Do NOT push scraper.py to the repo—only push your JSON output files
- Do NOT push your venv folder (it is already in .gitignore)
- The JSON output will be automatically saved to data/raw/[your_category]/

## Instructions

1. Find the relevant pages for your assigned categories across all 11 colleges
   - You are looking for official pages only—no blogs, news, events, or announcements
   - Aim for at least one page per college per category where it exists

2. For each topic, fill in pages_to_scrape in scraper.py with the relevant URLs
   for that topic across all colleges, then run the script
   - e.g. for financial_aid: run it once for work_study pages, once for fafsa pages, etc.
   - Clear out pages_to_scrape before each new topic run
   - Do not modify anything else in the script

3. Open your output JSON and check it looks right
   - Read through a few text fields and make sure they look clean and readable
   - If a page is scraping badly (tons of garbage characters, navigation junk, etc.)
     flag it in the group chat and we'll fix the cleaning logic together
   - Do not just leave it and say nothing

4. Rename the output file to match the topic before running the script again,
   or it will be overwritten
   - e.g. work_study.json, fafsa.json — not financial_aid.json or baruch.json
   - Verify it is saved in data/raw/[your_category]/

5. Commit and push your JSON files to the repo
   - Only add your JSON files, do not use git add . as it may catch unintended files:
       git add data/raw/[your_category]/[your_file].json
       git commit -m "add [topic] [category] data"
       git push

## Definition of Done

- Your JSON files are in the correct category folder
- You have covered all 11 colleges for your categories where pages exist
- Each file is named descriptively after the topic, not the college
  e.g. work_study.json, fafsa.json — not baruch.json
- The text fields are clean and readable
- college and category fields match the controlled vocabulary exactly
- All files are committed and pushed before our next meeting

## Monda: Eval Question Set

In addition to your scraping categories, you will be building our evaluation
question set in this [Google Sheet](https://docs.google.com/spreadsheets/d/1UR0T-FlzR837CaEL-gw8FnTcG7h6Irh0PDU1yESdEVA/edit?usp=sharing)

The sheet has the following columns:
question | expected_answer | category | college | notes

Write 25-30 realistic questions a CUNY student might actually ask.
Examples: "How do I apply for financial aid at Lehman College?"
          "What GPA do I need to graduate from Hunter?"
          "Can I transfer credits from a community college to Baruch?"

Aim for a mix of colleges and categories. Expected answers can be rough,
not exact: we just need to know what a good answer looks like.

notes: use this column to flag anything unusual about the question
e.g. "answer may vary by college", "couldn't find a clear answer online", 
"good edge case", "ambiguous question"