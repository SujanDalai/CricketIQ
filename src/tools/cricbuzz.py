import requests
# pyrefly: ignore [missing-import]
from bs4 import BeautifulSoup
import re

class CricbuzzScraper:
    """
    Scraper for cricbuzz.com to get live scores and upcoming match schedules.
    Does not require any API keys.
    """
    URL = "https://www.cricbuzz.com/cricket-match/live-scores"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    def _fetch_matches(self) -> list[dict]:
        try:
            r = requests.get(self.URL, headers=self.HEADERS, timeout=15)
            r.raise_for_status()
            # Force apparent encoding or utf-8 to handle unicode bullets/dashes properly
            r.encoding = r.apparent_encoding or 'utf-8'
        except Exception as e:
            return [{"error": f"Failed to fetch Cricbuzz data: {e}"}]

        soup = BeautifulSoup(r.text, 'html.parser')
        cards = soup.find_all('a', href=True, class_=True)
        
        matches = []
        seen_hrefs = set()
        
        for card in cards:
            href = card['href']
            if '/live-cricket-scores/' not in href or href in seen_hrefs:
                continue
                
            classes = card.get('class', [])
            # Target the container links of match cards
            if 'flex-col' in classes or len(card.text.strip()) > 80:
                seen_hrefs.add(href)
                
                # 1. Match Name/Title
                name = card.get('title', '').strip()
                if not name:
                    name = card.text.strip().split('\n')[0]
                name = re.sub(r',\s*$', '', name)
                name = name.replace('\ufffd', '-').replace('\u2013', '-').replace('\u2014', '-').replace('\u2022', '-')
                
                # 2. Venue/Series
                venue_span = card.find('span', class_=lambda c: c and 'text-cbTxtSec' in c)
                venue = ""
                if venue_span:
                    venue = venue_span.text.strip()
                    venue = venue.replace('\ufffd', '-').replace('\u2013', '-').replace('\u2014', '-').replace('\u2022', '-')
                    venue = re.sub(r'\s+', ' ', venue)
                
                # 3. Teams & Scores
                teams = []
                scores = []
                team_rows = card.select('div.flex.items-center.gap-4.justify-between')
                for row in team_rows:
                    name_span = row.find('span', class_=lambda c: c and 'hidden wb:block' in c)
                    if not name_span:
                        name_span = row.find('span', class_=lambda c: c and 'block wb:hidden' in c)
                    
                    team_name = name_span.text.strip() if name_span else ""
                    
                    score_span = row.find('span', class_=lambda c: c and 'font-medium' in c)
                    team_score = score_span.text.strip() if score_span else ""
                    
                    if team_name:
                        teams.append(team_name)
                        if team_score:
                            scores.append(f"{team_name} {team_score}")
                        else:
                            scores.append(team_name)
                
                # 4. Status
                spans = card.find_all('span')
                status = ""
                if spans:
                    status = spans[-1].text.strip()
                    status = status.replace('\ufffd', '-').replace('\u2013', '-').replace('\u2014', '-').replace('\u2022', '-')
                    status = re.sub(r'\s+', ' ', status)
                
                if not status or status in teams:
                    status = card.text.strip().split('\n')[-1].strip()
                
                # Determine state grouping
                date_info = "Live Now"
                status_lower = status.lower()
                if any(w in status_lower for w in ["won by", "won the", "loss", "draw", "tied", "abandoned", "no result"]):
                    date_info = "Completed"
                elif any(w in status_lower for w in ["preview", "starts", "upcoming", "delayed"]):
                    if "delayed" in status_lower and any(w in status_lower for w in ["rain", "wet"]):
                        date_info = "Live Now"
                    else:
                        date_info = "Upcoming"
                
                matches.append({
                    "name": name,
                    "status": status,
                    "venue": venue,
                    "date": date_info,
                    "teams": teams,
                    "score": " vs ".join(scores) if scores else "No score yet",
                    "url": f"https://www.cricbuzz.com{href}"
                })
                
        return matches

    def get_live_scores(self) -> list[dict]:
        """
        Get live and recently completed match scores.
        """
        all_matches = self._fetch_matches()
        if all_matches and "error" in all_matches[0]:
            return all_matches
            
        return [m for m in all_matches if m.get("date") in ["Live Now", "Completed"]]

    def get_match_schedule(self) -> list[dict]:
        """
        Get upcoming matches schedule.
        """
        all_matches = self._fetch_matches()
        if all_matches and "error" in all_matches[0]:
            return all_matches
            
        return [m for m in all_matches if m.get("date") == "Upcoming"]
