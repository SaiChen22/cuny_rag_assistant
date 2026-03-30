import json
from datetime import date

documents = [
    {
        "text": "Baruch College is a place of opportunity and exploration...",
        "source": "https://www.baruch.cuny.edu/our-mission/",
        "title": "Our Mission",
        "section": "about",
        "scraped_date": str(date.today())
    }
]

with open("data/raw/your_category.json", "w") as f:
    json.dump(documents, f, indent=2)