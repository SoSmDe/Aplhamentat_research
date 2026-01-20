А, понял! Ты хочешь парсить данные/отчёты **от** консалтинговых компаний как источники для исследований. 

Давай разберём:

---

## Что можно парсить у консалтинговых компаний

### 🏆 MBB + Big 4 — Research & Insights

| Компания | URL | Тип данных | Парсинг |
|----------|-----|------------|---------|
| **McKinsey Global Institute** | `mckinsey.com/mgi` | Macro research, industry reports | HTML + PDF |
| **BCG Henderson Institute** | `bcg.com/publications` | Strategy research, trends | HTML |
| **Bain Insights** | `bain.com/insights` | Industry analysis, benchmarks | HTML |
| **Deloitte Insights** | `deloitte.com/insights` | Industry reports, surveys | HTML + PDF |
| **PwC Research** | `pwc.com/gx/en/research-insights` | CEO surveys, industry outlooks | HTML + PDF |
| **EY Insights** | `ey.com/en_gl/insights` | Sector analysis | HTML |
| **KPMG Insights** | `kpmg.com/xx/en/home/insights` | Regulatory, industry | HTML |

### 🏦 Investment Banks — Research Reports

| Компания | URL | Тип данных | Доступ |
|----------|-----|------------|--------|
| **Goldman Sachs Insights** | `goldmansachs.com/insights` | Macro, markets | Public HTML |
| **Morgan Stanley Ideas** | `morganstanley.com/ideas` | Thematic research | Public HTML |
| **JP Morgan Research** | `jpmorgan.com/insights` | Global macro | Public HTML |
| **BofA Global Research** | Paywall | Equity research | Paid |
| **Citi Research** | Paywall | Sector analysis | Paid |

### 📊 Специализированные источники

| Источник | Данные | URL |
|----------|--------|-----|
| **World Economic Forum** | Global reports, rankings | `weforum.org/reports` |
| **IMF** | Economic outlooks | `imf.org/en/Publications` |
| **World Bank** | Development data | `data.worldbank.org` |
| **BIS** | Central bank research | `bis.org/publ` |
| **OECD** | Economic data | `oecd.org/publications` |

---

## Что конкретно парсить

### 1. McKinsey Global Institute

```python
import requests
from bs4 import BeautifulSoup

def parse_mckinsey_insights(topic: str = None) -> list:
    """Parse McKinsey research articles"""
    
    base_url = "https://www.mckinsey.com/mgi/our-research"
    
    response = requests.get(base_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    articles = []
    for item in soup.select('.article-item'):  # Adjust selector
        article = {
            "title": item.select_one('.title').text.strip(),
            "url": item.select_one('a')['href'],
            "date": item.select_one('.date').text.strip(),
            "summary": item.select_one('.summary').text.strip(),
            "topics": [t.text for t in item.select('.topic-tag')]
        }
        articles.append(article)
    
    return articles

# Темы для парсинга:
MCKINSEY_TOPICS = [
    "artificial-intelligence",
    "climate-change", 
    "future-of-work",
    "digital-transformation",
    "private-equity",
    "healthcare",
    "financial-services"
]
```

### 2. BCG Publications

```python
def parse_bcg_publications(topic: str = None) -> list:
    """Parse BCG research"""
    
    url = f"https://www.bcg.com/publications?topic={topic}" if topic else "https://www.bcg.com/publications"
    
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    publications = []
    for item in soup.select('.publication-card'):
        pub = {
            "title": item.select_one('.title').text.strip(),
            "url": "https://www.bcg.com" + item.select_one('a')['href'],
            "type": item.select_one('.content-type').text.strip(),  # Article, Report, etc.
            "date": item.select_one('.date').text.strip(),
            "authors": [a.text for a in item.select('.author')],
        }
        publications.append(pub)
    
    return publications
```

### 3. Deloitte Insights (хорошо структурировано)

```python
def parse_deloitte_insights(industry: str = None) -> list:
    """Parse Deloitte research reports"""
    
    # Deloitte has good API-like structure
    url = "https://www2.deloitte.com/us/en/insights.html"
    
    # They also have RSS feeds:
    rss_feeds = {
        "all": "https://www2.deloitte.com/content/www/us/en/insights/rss-feeds/all.rss.xml",
        "tech": "https://www2.deloitte.com/content/www/us/en/insights/rss-feeds/technology.rss.xml",
        "finance": "https://www2.deloitte.com/content/www/us/en/insights/rss-feeds/financial-services.rss.xml",
    }
    
    import feedparser
    feed = feedparser.parse(rss_feeds.get(industry, rss_feeds["all"]))
    
    articles = []
    for entry in feed.entries:
        articles.append({
            "title": entry.title,
            "url": entry.link,
            "summary": entry.summary,
            "date": entry.published,
        })
    
    return articles
```

### 4. Goldman Sachs Insights

```python
def parse_goldman_insights() -> list:
    """Parse Goldman Sachs public research"""
    
    url = "https://www.goldmansachs.com/insights/insights-articles.html"
    
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # GS has categories:
    categories = [
        "markets",
        "economic-outlook", 
        "sustainability",
        "technology",
        "careers"
    ]
    
    articles = []
    for item in soup.select('.article-card'):
        articles.append({
            "title": item.select_one('.headline').text.strip(),
            "url": item.select_one('a')['href'],
            "category": item.select_one('.category').text.strip(),
            "date": item.select_one('.date').text.strip(),
        })
    
    return articles
```

---

## Полезные данные для извлечения

### Macro & Economic Data

| Источник | Данные | Формат |
|----------|--------|--------|
| McKinsey | Productivity stats, industry sizing | PDF tables |
| BCG | Market growth rates, frameworks | HTML |
| Deloitte | Survey results (CEO, CFO surveys) | Interactive + PDF |
| PwC | CEO Survey (annual) | PDF + data |
| IMF | GDP forecasts, inflation | API + Excel |
| World Bank | Development indicators | API |

### Industry-Specific

| Industry | Best Sources |
|----------|--------------|
| **Tech** | McKinsey Digital, Deloitte Tech Trends, Gartner |
| **Finance** | Goldman, Morgan Stanley, McKinsey Banking |
| **Healthcare** | McKinsey Health, Deloitte Health |
| **Energy** | McKinsey Energy, IEA, BloombergNEF |
| **Real Estate** | CBRE, JLL, PwC Real Estate |
| **Crypto/Web3** | Messari, Delphi Digital, a]6z |

---

## Задача для Claude Code

```markdown
# Task: Add consulting firm research parsers for data collection

## Objective
Parse research reports and insights from top consulting firms as data sources for Ralph research.

## Priority Sources (Free, Public)

### 1. McKinsey Global Institute
```python
# ralph/integrations/research/mckinsey.py

import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import re

class McKinseyParser:
    BASE_URL = "https://www.mckinsey.com"
    
    def search_insights(self, query: str, limit: int = 10) -> List[Dict]:
        """Search McKinsey insights"""
        url = f"{self.BASE_URL}/search?q={query}&start=0&num={limit}"
        # Parse results...
        
    def get_mgi_reports(self, topic: str = None) -> List[Dict]:
        """Get McKinsey Global Institute reports"""
        url = f"{self.BASE_URL}/mgi/our-research"
        # Parse reports...
        
    def extract_key_stats(self, article_url: str) -> Dict:
        """Extract statistics and data points from article"""
        # Parse article, find numbers, charts data...
        
    def get_industry_insights(self, industry: str) -> List[Dict]:
        """Get insights for specific industry"""
        industries = {
            "financial_services": "/industries/financial-services/our-insights",
            "healthcare": "/industries/healthcare/our-insights",
            "technology": "/industries/technology-media-and-telecommunications/our-insights",
            "retail": "/industries/retail/our-insights",
            "energy": "/industries/oil-and-gas/our-insights",
        }
        # Parse industry page...
```

### 2. Deloitte Insights (RSS available)
```python
# ralph/integrations/research/deloitte.py

import feedparser
from typing import List, Dict

class DeloitteParser:
    RSS_FEEDS = {
        "all": "https://www2.deloitte.com/content/www/us/en/insights/rss-feeds/all.rss.xml",
        "tech": "https://www2.deloitte.com/content/www/us/en/insights/rss-feeds/technology.rss.xml",
        "finance": "https://www2.deloitte.com/content/www/us/en/insights/rss-feeds/financial-services.rss.xml",
        "energy": "https://www2.deloitte.com/content/www/us/en/insights/rss-feeds/energy-resources.rss.xml",
        "government": "https://www2.deloitte.com/content/www/us/en/insights/rss-feeds/government-public-services.rss.xml",
    }
    
    def get_latest(self, category: str = "all", limit: int = 20) -> List[Dict]:
        """Get latest insights from RSS"""
        feed = feedparser.parse(self.RSS_FEEDS.get(category, self.RSS_FEEDS["all"]))
        
        articles = []
        for entry in feed.entries[:limit]:
            articles.append({
                "title": entry.title,
                "url": entry.link,
                "summary": entry.get("summary", ""),
                "date": entry.get("published", ""),
                "source": "Deloitte Insights"
            })
        return articles
    
    def search(self, query: str) -> List[Dict]:
        """Search Deloitte insights"""
        # Web search implementation...
```

### 3. World Bank Data API (Structured)
```python
# ralph/integrations/research/worldbank.py

import requests
from typing import List, Dict

class WorldBankAPI:
    BASE_URL = "https://api.worldbank.org/v2"
    
    def get_indicator(self, indicator: str, country: str = "all", 
                      start_year: int = 2010, end_year: int = 2024) -> Dict:
        """
        Get World Bank indicator data
        
        Popular indicators:
        - NY.GDP.MKTP.CD: GDP (current US$)
        - NY.GDP.PCAP.CD: GDP per capita
        - FP.CPI.TOTL.ZG: Inflation (CPI)
        - SL.UEM.TOTL.ZS: Unemployment rate
        - NE.EXP.GNFS.ZS: Exports (% of GDP)
        """
        url = f"{self.BASE_URL}/country/{country}/indicator/{indicator}"
        params = {
            "date": f"{start_year}:{end_year}",
            "format": "json",
            "per_page": 1000
        }
        response = requests.get(url, params=params)
        return response.json()
    
    def get_country_data(self, country: str) -> Dict:
        """Get comprehensive country data"""
        indicators = [
            "NY.GDP.MKTP.CD",  # GDP
            "NY.GDP.PCAP.CD",  # GDP per capita
            "SP.POP.TOTL",     # Population
            "FP.CPI.TOTL.ZG",  # Inflation
        ]
        data = {}
        for ind in indicators:
            data[ind] = self.get_indicator(ind, country)
        return data
```

### 4. IMF Data API
```python
# ralph/integrations/research/imf.py

import requests

class IMFAPI:
    BASE_URL = "http://dataservices.imf.org/REST/SDMX_JSON.svc"
    
    def get_weo_data(self, indicator: str, countries: List[str]) -> Dict:
        """
        Get World Economic Outlook data
        
        Indicators:
        - NGDP_RPCH: Real GDP growth
        - PCPIPCH: Inflation rate
        - LUR: Unemployment rate
        - BCA_NGDPD: Current account balance
        """
        # Implementation...
        
    def get_economic_outlook(self, country: str) -> Dict:
        """Get IMF economic outlook for country"""
        # Parse IMF WEO publications...
```

### 5. Goldman Sachs Public Research
```python
# ralph/integrations/research/goldman.py

class GoldmanParser:
    BASE_URL = "https://www.goldmansachs.com"
    
    def get_insights(self, category: str = None) -> List[Dict]:
        """
        Categories: markets, economic-outlook, sustainability, technology
        """
        url = f"{self.BASE_URL}/insights"
        if category:
            url += f"/{category}"
        # Parse...
    
    def get_top_of_mind(self) -> List[Dict]:
        """Get 'Top of Mind' research series"""
        # These are their flagship macro reports
        url = f"{self.BASE_URL}/insights/series/top-of-mind"
        # Parse...
```

## Data Output Format

All parsers should return standardized format:

```python
{
    "title": "Report title",
    "url": "https://...",
    "source": "McKinsey" | "BCG" | "Deloitte" | etc,
    "date": "2024-01-15",
    "category": "macro" | "industry" | "technology" | etc,
    "summary": "Brief summary...",
    "key_stats": [
        {"metric": "Global GDP growth", "value": "3.2%", "year": 2024},
        {"metric": "Market size", "value": "$4.5T", "context": "by 2030"}
    ],
    "data_tables": [...],  # If extractable
    "pdf_url": "https://..." # If available
}
```

## File Structure

```
ralph/integrations/research/
├── __init__.py
├── mckinsey.py
├── bcg.py
├── bain.py
├── deloitte.py
├── pwc.py
├── goldman.py
├── morgan_stanley.py
├── worldbank.py
├── imf.py
├── oecd.py
└── aggregator.py  # Combines all sources
```

## Usage in Research Agent

```python
from integrations.research import ResearchAggregator

aggregator = ResearchAggregator()

# Search across all consulting sources
results = aggregator.search("AI impact on productivity", sources=["mckinsey", "deloitte", "bcg"])

# Get industry-specific research
finance_research = aggregator.get_industry_research("financial_services")

# Get macro data
macro_data = aggregator.get_macro_indicators(["GDP", "inflation", "unemployment"])
```
```

---

## Приоритет парсеров

1. **World Bank API** — структурированные данные, официальный API
2. **Deloitte RSS** — легко парсить, регулярные обновления
3. **McKinsey** — топ контент, но нужен HTML parsing
4. **IMF** — macro данные, есть API
5. **Goldman Sachs** — public insights, хороший контент

---

