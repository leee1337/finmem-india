import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import requests
from loguru import logger
import json
from pathlib import Path
from bs4 import BeautifulSoup
import time

class CredentialsManager:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Initialize session storage
        self.sessions: Dict[str, Any] = {}
        self.tokens: Dict[str, str] = {}
        
        # Load credentials
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.screener_username = os.getenv('SCREENER_USERNAME')
        self.screener_password = os.getenv('SCREENER_PASSWORD')
        self.mc_username = os.getenv('MC_USERNAME')
        self.mc_password = os.getenv('MC_PASSWORD')
        self.nse_api_key = os.getenv('NSE_API_KEY')
        self.nse_api_secret = os.getenv('NSE_API_SECRET')
        
        # Validate required credentials
        if not self.google_api_key:
            raise ValueError("Google API key is required")
    
    def get_screener_session(self) -> Optional[requests.Session]:
        """Get authenticated Screener.in session"""
        if 'screener' in self.sessions:
            return self.sessions['screener']
            
        if not (self.screener_username and self.screener_password):
            logger.warning("Screener.in credentials not provided")
            return None
            
        try:
            session = requests.Session()
            
            # Set headers to mimic browser
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
            # Get CSRF token
            response = session.get('https://www.screener.in/login/')
            if response.status_code != 200:
                raise Exception("Failed to get login page")
            
            # Login
            login_data = {
                'username': self.screener_username,
                'password': self.screener_password,
                'csrfmiddlewaretoken': session.cookies.get('csrftoken'),
                'next': '/'
            }
            
            response = session.post(
                'https://www.screener.in/login/',
                data=login_data,
                headers={'Referer': 'https://www.screener.in/login/'}
            )
            
            if response.status_code != 200:
                raise Exception("Login failed")
                
            self.sessions['screener'] = session
            return session
            
        except Exception as e:
            logger.error(f"Error authenticating with Screener.in: {e}")
            return None
    
    def get_moneycontrol_session(self) -> Optional[requests.Session]:
        """Get authenticated MoneyControl session"""
        if 'moneycontrol' in self.sessions:
            return self.sessions['moneycontrol']
            
        if not (self.mc_username and self.mc_password):
            logger.warning("MoneyControl credentials not provided")
            return None
            
        try:
            session = requests.Session()
            
            # Set common headers to look more like a real browser
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0'
            })
            
            # Function for exponential backoff
            def exponential_backoff(attempt):
                wait_time = min(300, (2 ** attempt)) # Cap at 5 minutes
                logger.info(f"Rate limit hit, waiting {wait_time} seconds before retry (attempt {attempt + 1})")
                time.sleep(wait_time)
            
            # Try to get login page with retries
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    response = session.get(
                        'https://www.moneycontrol.com/india/login',
                        timeout=30
                    )
                    if response.status_code == 200:
                        break
                    elif response.status_code == 429:  # Rate limit hit
                        exponential_backoff(attempt)
                        continue
                    else:
                        raise Exception(f"Failed to get login page: {response.status_code}")
                except requests.exceptions.RequestException as e:
                    if attempt == max_retries - 1:
                        raise Exception(f"Max retries reached: {str(e)}")
                    exponential_backoff(attempt)
                    continue
                
            # Extract CSRF token from the page
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_token = soup.find('input', {'name': 'csrf_token'})
            if not csrf_token:
                raise Exception("Could not find CSRF token")
            
            # Get required cookies
            cookies = session.cookies.get_dict()
            if 'mc_session' not in cookies:
                raise Exception("Required cookies not found")
            
            # Add required headers for login request
            session.headers.update({
                'Origin': 'https://www.moneycontrol.com',
                'Referer': 'https://www.moneycontrol.com/india/login',
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest'
            })
            
            # Prepare login data
            login_data = {
                'csrf_token': csrf_token['value'],
                'email': self.mc_username,
                'password': self.mc_password,
                'rememberme': 'on',
                'redirect_url': '/'
            }
            
            # Submit login form with retries
            for attempt in range(max_retries):
                try:
                    response = session.post(
                        'https://www.moneycontrol.com/india/login/process',
                        data=login_data,
                        allow_redirects=True,
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        break
                    elif response.status_code == 429:  # Rate limit hit
                        exponential_backoff(attempt)
                        continue
                    else:
                        raise Exception(f"Login failed with status code: {response.status_code}")
                except requests.exceptions.RequestException as e:
                    if attempt == max_retries - 1:
                        raise Exception(f"Max retries reached during login: {str(e)}")
                    exponential_backoff(attempt)
                    continue
            
            # Verify login success by checking for authentication cookie
            cookies = session.cookies.get_dict()
            if 'mc_userdata' not in cookies:
                raise Exception("Login failed - authentication cookie not found")
            
            # Test the session by accessing a protected endpoint with retries
            for attempt in range(max_retries):
                try:
                    test_response = session.get(
                        'https://www.moneycontrol.com/india/my-profile',
                        timeout=30
                    )
                    if test_response.status_code == 200 and 'login' not in test_response.url.lower():
                        break
                    elif test_response.status_code == 429:  # Rate limit hit
                        exponential_backoff(attempt)
                        continue
                    else:
                        raise Exception("Session validation failed")
                except requests.exceptions.RequestException as e:
                    if attempt == max_retries - 1:
                        raise Exception(f"Max retries reached during session validation: {str(e)}")
                    exponential_backoff(attempt)
                    continue
            
            self.sessions['moneycontrol'] = session
            return session
            
        except Exception as e:
            logger.error(f"Error authenticating with MoneyControl: {e}")
            return None
    
    def get_nse_headers(self) -> Optional[Dict[str, str]]:
        """Get NSE API headers with authentication"""
        if not (self.nse_api_key and self.nse_api_secret):
            logger.warning("NSE API credentials not provided")
            return None
            
        return {
            'X-API-KEY': self.nse_api_key,
            'X-API-SECRET': self.nse_api_secret,
            'Content-Type': 'application/json'
        }
    
    def save_session_cookies(self, cache_dir: str = ".cache"):
        """Save session cookies for reuse"""
        try:
            cache_dir = Path(cache_dir)
            cache_dir.mkdir(exist_ok=True)
            
            for name, session in self.sessions.items():
                cookie_file = cache_dir / f"{name}_cookies.json"
                with open(cookie_file, 'w') as f:
                    json.dump(requests.utils.dict_from_cookiejar(session.cookies), f)
                    
        except Exception as e:
            logger.error(f"Error saving session cookies: {e}")
    
    def load_session_cookies(self, cache_dir: str = ".cache"):
        """Load saved session cookies"""
        try:
            cache_dir = Path(cache_dir)
            if not cache_dir.exists():
                return
                
            for cookie_file in cache_dir.glob("*_cookies.json"):
                name = cookie_file.stem.replace("_cookies", "")
                with open(cookie_file) as f:
                    cookies = json.load(f)
                    
                session = requests.Session()
                session.cookies.update(requests.utils.cookiejar_from_dict(cookies))
                self.sessions[name] = session
                
        except Exception as e:
            logger.error(f"Error loading session cookies: {e}")
            
    def clear_sessions(self):
        """Clear all active sessions"""
        self.sessions.clear()
        self.tokens.clear() 

def get_browser_headers() -> Dict[str, str]:
    """Get common browser headers for web scraping"""
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    } 