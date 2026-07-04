from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import re
from app import db
from app.models import Job, Skill, JobSkill


# ─────────────────────────────────────
# BROWSER SETUP
# ─────────────────────────────────────
def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')           # run in background
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--window-size=1920,1080')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    )
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    return driver


# ─────────────────────────────────────
# SKILL EXTRACTOR
# ─────────────────────────────────────
COMMON_SKILLS = [
    'python', 'java', 'javascript', 'sql', 'mysql', 'postgresql',
    'mongodb', 'flask', 'django', 'react', 'node.js', 'html', 'css',
    'machine learning', 'deep learning', 'nlp', 'data analysis',
    'tableau', 'power bi', 'excel', 'r', 'tensorflow', 'keras',
    'scikit-learn', 'pandas', 'numpy', 'aws', 'azure', 'gcp',
    'docker', 'kubernetes', 'git', 'linux', 'rest api', 'graphql',
    'c++', 'c#', 'php', 'ruby', 'swift', 'kotlin', 'spark', 'hadoop',
    'selenium', 'junit', 'jenkins', 'devops', 'agile', 'scrum'
]

def extract_skills(text):
    text_lower = text.lower()
    found = []
    for skill in COMMON_SKILLS:
        if skill in text_lower:
            found.append(skill)
    return found


# ─────────────────────────────────────
# SALARY PARSER
# ─────────────────────────────────────
def parse_salary(salary_text):
    if not salary_text or 'not disclosed' in salary_text.lower():
        return None, None
    numbers = re.findall(r'\d+\.?\d*', salary_text)
    if len(numbers) >= 2:
        return float(numbers[0]), float(numbers[1])
    elif len(numbers) == 1:
        return float(numbers[0]), float(numbers[0])
    return None, None


# ─────────────────────────────────────
# SAVE JOB TO DATABASE
# ─────────────────────────────────────
def save_job(job_data):
    # Check if job already exists (avoid duplicates)
    existing = Job.query.filter_by(job_url=job_data['url']).first()
    if existing:
        return False

    salary_min, salary_max = parse_salary(job_data.get('salary', ''))

    job = Job(
        title       = job_data.get('title', '')[:200],
        company     = job_data.get('company', '')[:150],
        location    = job_data.get('location', '')[:100],
        salary_min  = salary_min,
        salary_max  = salary_max,
        experience  = job_data.get('experience', '')[:50],
        description = job_data.get('description', ''),
        portal      = 'naukri',
        job_url     = job_data.get('url', '')[:500],
        domain      = job_data.get('domain', '')[:100]
    )
    db.session.add(job)
    db.session.flush()  # get job.id before commit

    # Save skills
    skills_found = extract_skills(
        job_data.get('description', '') + ' ' + job_data.get('title', '')
    )
    for skill_name in skills_found:
        # Get or create skill
        skill = Skill.query.filter_by(name=skill_name).first()
        if not skill:
            skill = Skill(name=skill_name)
            db.session.add(skill)
            db.session.flush()

        # Link skill to job
        job_skill = JobSkill(job_id=job.id, skill_id=skill.id)
        db.session.add(job_skill)

    db.session.commit()
    return True


# ─────────────────────────────────────
# MAIN NAUKRI SCRAPER
# ─────────────────────────────────────
def scrape_naukri(search_query="software developer", location="india", pages=3):
    print(f"\n🔍 Scraping Naukri for: '{search_query}' in '{location}'")
    driver = get_driver()
    jobs_saved = 0

    try:
        for page in range(1, pages + 1):
            url = (
                f"https://www.naukri.com/{search_query.replace(' ', '-')}"
                f"-jobs-in-{location.replace(' ', '-')}-{page}"
            )
            print(f"📄 Scraping page {page}: {url}")
            driver.get(url)

            # Wait for job cards to load
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located(
                        (By.CLASS_NAME, "srp-jobtuple-wrapper")
                    )
                )
            except:
                print(f"⚠️  Page {page} took too long or no jobs found")
                continue

            time.sleep(3)  # let page fully render

            # Parse with BeautifulSoup
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            job_cards = soup.find_all('div', class_='srp-jobtuple-wrapper')
            print(f"   Found {len(job_cards)} job cards")

            for card in job_cards:
                try:
                    # Extract job details
                    title_tag   = card.find('a', class_='title')
                    company_tag = card.find('a', class_='comp-name')
                    location_tag = card.find('span', class_='locWdth')
                    exp_tag     = card.find('span', class_='expwdth')
                    salary_tag  = card.find('span', class_='sal-wrap')
                    desc_tag    = card.find('span', class_='job-desc')

                    title    = title_tag.text.strip()    if title_tag    else ''
                    company  = company_tag.text.strip()  if company_tag  else ''
                    location = location_tag.text.strip() if location_tag else ''
                    exp      = exp_tag.text.strip()      if exp_tag      else ''
                    salary   = salary_tag.text.strip()   if salary_tag   else ''
                    desc     = desc_tag.text.strip()     if desc_tag     else ''
                    job_url  = title_tag['href']         if title_tag    else ''

                    if not title or not job_url:
                        continue

                    job_data = {
                        'title':       title,
                        'company':     company,
                        'location':    location,
                        'experience':  exp,
                        'salary':      salary,
                        'description': desc,
                        'url':         job_url,
                        'domain':      search_query
                    }

                    saved = save_job(job_data)
                    if saved:
                        jobs_saved += 1
                        print(f"   ✅ Saved: {title} @ {company}")
                    else:
                        print(f"   ⏭️  Duplicate skipped: {title}")

                except Exception as e:
                    print(f"   ❌ Error parsing card: {e}")
                    continue

            time.sleep(2)  # be polite between pages

    except Exception as e:
        print(f"❌ Scraper error: {e}")

    finally:
        driver.quit()

    print(f"\n✅ Done! Saved {jobs_saved} new jobs to database.\n")
    return jobs_saved


# ─────────────────────────────────────
# SCRAPE MULTIPLE DOMAINS AT ONCE
# ─────────────────────────────────────
def scrape_all_domains():
    domains = [
        "data analyst",
        "python developer",
        "backend developer",
        "machine learning engineer",
        "web developer",
        "devops engineer",
        "business analyst",
        "full stack developer"
    ]
    total = 0
    for domain in domains:
        count = scrape_naukri(
            search_query=domain,
            location="india",
            pages=2
        )
        total += count
    print(f"\n🎯 Total jobs scraped: {total}")
    return total