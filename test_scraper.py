from app import create_app
from app.scrapers import scrape_all_domains

app = create_app()

with app.app_context():
    total = scrape_all_domains()
    print(f"\n🏆 Total jobs in database: {total}")