#!/usr/bin/env python3
"""
🏠 Advanced Real Estate Wholesaling Automation System

A comprehensive real estate wholesaling automation system with advanced scraping,
error handling, database persistence, and buyer matching capabilities.

Features:
- Multi-source property scraping (Zillow, RealtyTrac, Auction.com, Realtor.com)
- Intelligent rate limiting and anti-detection measures
- SQLite database for persistent storage
- Advanced buyer-property matching algorithm
- Automated email notifications
- Concurrent scraping with thread pool
- Comprehensive error handling and retry logic
- Export to multiple formats (CSV, JSON, Excel)
- CLI interface with multiple commands
- Activity logging and monitoring
"""

import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import random
import os
import json
import re
from urllib.parse import urljoin, urlparse, quote
import logging
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional, Tuple
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import sqlite3
from contextlib import contextmanager
import argparse
import sys
from collections import defaultdict
import hashlib
from functools import wraps
import signal

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("wholesaling_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_flag = threading.Event()


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info("Shutdown signal received. Finishing current tasks...")
    shutdown_flag.set()


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def retry_on_failure(max_retries=3, delay=1, backoff=2):
    """Decorator for retrying functions on failure with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries: {str(e)}")
                        raise
                    
                    logger.warning(f"Attempt {retries} failed for {func.__name__}: {str(e)}. Retrying in {current_delay}s...")
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            return None
        return wrapper
    return decorator


@dataclass
class Property:
    """Enhanced property data structure with validation"""
    address: str
    price: str
    link: str
    date: str
    contacted: str = "No"
    interested: str = "Unknown"
    property_type: str = "Unknown"
    bedrooms: str = "N/A"
    bathrooms: str = "N/A"
    sqft: str = "N/A"
    year_built: str = "N/A"
    source: str = "Unknown"
    city: str = "Unknown"
    state: str = "Unknown"
    zipcode: str = "N/A"
    estimated_repair_cost: str = "N/A"
    arv: str = "N/A"  # After Repair Value
    days_on_market: str = "N/A"
    property_id: str = field(default_factory=lambda: "")
    
    def __post_init__(self):
        """Generate unique property ID based on address"""
        if not self.property_id:
            self.property_id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Generate unique ID for the property"""
        hash_input = f"{self.address}_{self.source}_{self.date}".encode()
        return hashlib.md5(hash_input).hexdigest()[:12]
    
    def get_price_numeric(self) -> Optional[float]:
        """Extract numeric price from string"""
        try:
            price_str = re.sub(r'[^\d.]', '', self.price)
            return float(price_str) if price_str else None
        except (ValueError, AttributeError):
            return None
    
    def is_valid(self) -> bool:
        """Validate property data"""
        if not self.address or self.address == "N/A":
            return False
        if not self.price or self.price == "N/A":
            return False
        if not self.link or self.link == "#":
            return False
        return True


@dataclass
class Buyer:
    """Enhanced buyer data structure with preferences"""
    name: str
    email: str
    max_price: int
    min_price: int = 0
    active: str = "Yes"
    preferred_areas: List[str] = field(default_factory=list)
    min_bedrooms: int = 0
    min_bathrooms: int = 0
    min_sqft: int = 0
    property_types: List[str] = field(default_factory=list)
    buyer_id: str = field(default_factory=lambda: "")
    
    def __post_init__(self):
        """Generate unique buyer ID"""
        if not self.buyer_id:
            self.buyer_id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Generate unique ID for the buyer"""
        hash_input = f"{self.email}_{self.name}".encode()
        return hashlib.md5(hash_input).hexdigest()[:12]
    
    def matches_property(self, prop: Property) -> Tuple[bool, int]:
        """
        Check if property matches buyer criteria
        Returns: (matches, score) where score is 0-100
        """
        if self.active != "Yes":
            return False, 0
        
        score = 0
        
        # Price check (mandatory)
        price = prop.get_price_numeric()
        if not price or price > self.max_price or price < self.min_price:
            return False, 0
        
        # Location preference
        if self.preferred_areas:
            location_match = any(
                area.lower() in f"{prop.city} {prop.state}".lower() or
                area.lower() in prop.address.lower()
                for area in self.preferred_areas
            )
            if location_match:
                score += 30
            else:
                return False, 0
        else:
            score += 10  # No preference means any location acceptable
        
        # Property type preference
        if self.property_types:
            if prop.property_type in self.property_types:
                score += 20
        else:
            score += 10
        
        # Bedroom check
        try:
            beds = int(re.sub(r'[^\d]', '', prop.bedrooms))
            if beds >= self.min_bedrooms:
                score += 15
        except (ValueError, AttributeError):
            score += 5
        
        # Bathroom check
        try:
            baths = float(re.sub(r'[^\d.]', '', prop.bathrooms))
            if baths >= self.min_bathrooms:
                score += 15
        except (ValueError, AttributeError):
            score += 5
        
        # Square footage check
        try:
            sqft = int(re.sub(r'[^\d]', '', prop.sqft))
            if sqft >= self.min_sqft:
                score += 10
        except (ValueError, AttributeError):
            score += 5
        
        return True, min(score, 100)


class RateLimiter:
    """Rate limiter to prevent overwhelming servers"""
    
    def __init__(self, requests_per_minute: int = 10):
        self.requests_per_minute = requests_per_minute
        self.requests = []
        self.lock = threading.Lock()
    
    def wait_if_needed(self):
        """Wait if rate limit is exceeded"""
        with self.lock:
            now = datetime.now()
            # Remove requests older than 1 minute
            self.requests = [req_time for req_time in self.requests 
                           if now - req_time < timedelta(minutes=1)]
            
            if len(self.requests) >= self.requests_per_minute:
                # Calculate wait time
                oldest_request = min(self.requests)
                wait_time = 60 - (now - oldest_request).total_seconds()
                if wait_time > 0:
                    logger.info(f"Rate limit reached. Waiting {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                    self.requests = []
            
            self.requests.append(now)


class DatabaseManager:
    """Manages SQLite database operations"""
    
    def __init__(self, db_path: str = "real_estate.db"):
        self.db_path = db_path
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {str(e)}")
            raise
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Properties table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS properties (
                    property_id TEXT PRIMARY KEY,
                    address TEXT NOT NULL,
                    price TEXT,
                    link TEXT,
                    date TEXT,
                    contacted TEXT DEFAULT 'No',
                    interested TEXT DEFAULT 'Unknown',
                    property_type TEXT,
                    bedrooms TEXT,
                    bathrooms TEXT,
                    sqft TEXT,
                    year_built TEXT,
                    source TEXT,
                    city TEXT,
                    state TEXT,
                    zipcode TEXT,
                    estimated_repair_cost TEXT,
                    arv TEXT,
                    days_on_market TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Buyers table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS buyers (
                    buyer_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    max_price INTEGER,
                    min_price INTEGER DEFAULT 0,
                    active TEXT DEFAULT 'Yes',
                    preferred_areas TEXT,
                    min_bedrooms INTEGER DEFAULT 0,
                    min_bathrooms INTEGER DEFAULT 0,
                    min_sqft INTEGER DEFAULT 0,
                    property_types TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Property-Buyer matches table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS property_matches (
                    match_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    property_id TEXT,
                    buyer_id TEXT,
                    match_score INTEGER,
                    notified TEXT DEFAULT 'No',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (property_id) REFERENCES properties(property_id),
                    FOREIGN KEY (buyer_id) REFERENCES buyers(buyer_id),
                    UNIQUE(property_id, buyer_id)
                )
            ''')
            
            # Activity log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS activity_log (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    level TEXT,
                    source TEXT,
                    message TEXT
                )
            ''')
            
            logger.info("Database initialized successfully")
    
    def save_property(self, prop: Property) -> bool:
        """Save or update property in database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if property exists
                cursor.execute('SELECT property_id FROM properties WHERE property_id = ?', 
                             (prop.property_id,))
                exists = cursor.fetchone()
                
                prop_dict = asdict(prop)
                
                if exists:
                    # Update existing property
                    set_clause = ', '.join([f"{k} = ?" for k in prop_dict.keys() if k != 'property_id'])
                    values = [v for k, v in prop_dict.items() if k != 'property_id']
                    values.append(prop.property_id)
                    
                    cursor.execute(f'''
                        UPDATE properties 
                        SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                        WHERE property_id = ?
                    ''', values)
                    logger.debug(f"Updated property {prop.property_id}")
                else:
                    # Insert new property
                    columns = ', '.join(prop_dict.keys())
                    placeholders = ', '.join(['?' for _ in prop_dict])
                    
                    cursor.execute(f'''
                        INSERT INTO properties ({columns})
                        VALUES ({placeholders})
                    ''', list(prop_dict.values()))
                    logger.info(f"Saved new property {prop.property_id}")
                
                return True
        except Exception as e:
            logger.error(f"Error saving property: {str(e)}")
            return False
    
    def get_all_properties(self, limit: int = None) -> List[Property]:
        """Retrieve all properties from database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = 'SELECT * FROM properties ORDER BY created_at DESC'
                if limit:
                    query += f' LIMIT {limit}'
                
                cursor.execute(query)
                rows = cursor.fetchall()
                
                properties = []
                for row in rows:
                    prop_dict = dict(row)
                    # Remove database-specific fields
                    prop_dict.pop('created_at', None)
                    prop_dict.pop('updated_at', None)
                    properties.append(Property(**prop_dict))
                
                return properties
        except Exception as e:
            logger.error(f"Error retrieving properties: {str(e)}")
            return []
    
    def save_buyer(self, buyer: Buyer) -> bool:
        """Save or update buyer in database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Convert lists to JSON strings
                preferred_areas_str = json.dumps(buyer.preferred_areas)
                property_types_str = json.dumps(buyer.property_types)
                
                cursor.execute('''
                    INSERT OR REPLACE INTO buyers 
                    (buyer_id, name, email, max_price, min_price, active, 
                     preferred_areas, min_bedrooms, min_bathrooms, min_sqft, property_types)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (buyer.buyer_id, buyer.name, buyer.email, buyer.max_price, 
                      buyer.min_price, buyer.active, preferred_areas_str,
                      buyer.min_bedrooms, buyer.min_bathrooms, buyer.min_sqft, 
                      property_types_str))
                
                logger.info(f"Saved buyer {buyer.name}")
                return True
        except Exception as e:
            logger.error(f"Error saving buyer: {str(e)}")
            return False
    
    def get_all_buyers(self) -> List[Buyer]:
        """Retrieve all buyers from database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM buyers WHERE active = "Yes"')
                rows = cursor.fetchall()
                
                buyers = []
                for row in rows:
                    buyer_dict = dict(row)
                    buyer_dict.pop('created_at', None)
                    buyer_dict.pop('updated_at', None)
                    
                    # Parse JSON fields
                    buyer_dict['preferred_areas'] = json.loads(buyer_dict['preferred_areas'])
                    buyer_dict['property_types'] = json.loads(buyer_dict['property_types'])
                    
                    buyers.append(Buyer(**buyer_dict))
                
                return buyers
        except Exception as e:
            logger.error(f"Error retrieving buyers: {str(e)}")
            return []
    
    def save_match(self, property_id: str, buyer_id: str, score: int) -> bool:
        """Save property-buyer match"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO property_matches 
                    (property_id, buyer_id, match_score)
                    VALUES (?, ?, ?)
                ''', (property_id, buyer_id, score))
                return True
        except Exception as e:
            logger.error(f"Error saving match: {str(e)}")
            return False
    
    def log_activity(self, level: str, source: str, message: str):
        """Log activity to database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO activity_log (level, source, message)
                    VALUES (?, ?, ?)
                ''', (level, source, message))
        except Exception as e:
            logger.error(f"Error logging activity: {str(e)}")


class EmailNotifier:
    """Handles email notifications"""
    
    def __init__(self, smtp_server: str = None, smtp_port: int = 587,
                 sender_email: str = None, sender_password: str = None):
        self.smtp_server = smtp_server or os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = smtp_port
        self.sender_email = sender_email or os.getenv('SENDER_EMAIL')
        self.sender_password = sender_password or os.getenv('SENDER_PASSWORD')
        self.enabled = bool(self.sender_email and self.sender_password)
        
        if not self.enabled:
            logger.warning("Email notifications disabled. Set SMTP_SERVER, SENDER_EMAIL, and SENDER_PASSWORD to enable.")
    
    @retry_on_failure(max_retries=3, delay=2)
    def send_email(self, recipient: str, subject: str, body: str, html: bool = True) -> bool:
        """Send email notification"""
        if not self.enabled:
            logger.debug(f"Email notification skipped (disabled): {subject}")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.sender_email
            msg['To'] = recipient
            msg['Subject'] = subject
            
            if html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            logger.info(f"Email sent to {recipient}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            raise
    
    def send_property_notification(self, buyer: Buyer, properties: List[Tuple[Property, int]]):
        """Send property match notification to buyer"""
        if not properties:
            return
        
        subject = f"🏠 New Property Matches - {len(properties)} Properties"
        
        # Build HTML email
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .property {{ border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                .property h3 {{ color: #2c3e50; margin-top: 0; }}
                .details {{ color: #555; }}
                .score {{ background: #27ae60; color: white; padding: 5px 10px; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <h2>Hello {buyer.name},</h2>
            <p>We found {len(properties)} new properties that match your criteria!</p>
        """
        
        for prop, score in properties[:10]:  # Limit to top 10
            html += f"""
            <div class="property">
                <h3>{prop.address}</h3>
                <p class="details">
                    <strong>Price:</strong> {prop.price}<br>
                    <strong>Type:</strong> {prop.property_type}<br>
                    <strong>Beds/Baths:</strong> {prop.bedrooms} / {prop.bathrooms}<br>
                    <strong>Square Feet:</strong> {prop.sqft}<br>
                    <strong>Source:</strong> {prop.source}<br>
                    <strong>Match Score:</strong> <span class="score">{score}%</span>
                </p>
                <p><a href="{prop.link}">View Property Details</a></p>
            </div>
            """
        
        html += """
        </body>
        </html>
        """
        
        self.send_email(buyer.email, subject, html, html=True)


class AdvancedRealEstateBot:
    """Main bot class with advanced scraping and matching capabilities"""
    
    def __init__(self, config: Dict = None):
        # Configuration
        self.config = config or {}
        self.leads_file = self.config.get('leads_file', "leads.csv")
        self.buyers_file = self.config.get('buyers_file', "buyers.csv")
        self.log_file = self.config.get('log_file', "activity.log")
        self.db_path = self.config.get('db_path', "real_estate.db")
        
        # Initialize components
        self.db = DatabaseManager(self.db_path)
        self.rate_limiter = RateLimiter(requests_per_minute=10)
        self.notifier = EmailNotifier()
        
        # Session with rotation of user agents
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
        ]
        self.session = requests.Session()
        self._update_session_headers()
        
        # Target cities
        self.target_cities = self.config.get('target_cities', [
            {"name": "Kokomo", "state": "IN"},
            {"name": "Logansport", "state": "IN"},
            {"name": "Indianapolis", "state": "IN"},
            {"name": "Fort Wayne", "state": "IN"},
        ])
        
        # Initialize legacy CSV files for backward compatibility
        self.initialize_files()
        
        logger.info("AdvancedRealEstateBot initialized successfully")
    
    def _update_session_headers(self):
        """Update session headers with random user agent"""
        self.session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def initialize_files(self):
        """Create necessary files if they don't exist (legacy support)"""
        if not os.path.exists(self.leads_file):
            with open(self.leads_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['property_id', 'address', 'price', 'link', 'date', 'contacted', 
                               'interested', 'property_type', 'bedrooms', 'bathrooms', 'sqft', 
                               'year_built', 'source', 'city', 'state'])
        
        if not os.path.exists(self.buyers_file):
            with open(self.buyers_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['buyer_id', 'name', 'email', 'max_price', 'min_price', 
                               'active', 'preferred_areas'])
                
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write(f"Activity Log - Started {datetime.now()}\n")
    
    def log_activity(self, message: str, level: str = "INFO"):
        """Log activities to file, console, and database"""
        logger.log(getattr(logging, level), message)
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now()}] [{level}] {message}\n")
        
        self.db.log_activity(level, "AdvancedRealEstateBot", message)
    
    @retry_on_failure(max_retries=3, delay=2)
    def safe_request(self, url: str, timeout: int = 30) -> Optional[requests.Response]:
        """Make a safe HTTP request with rate limiting and error handling"""
        if shutdown_flag.is_set():
            return None
        
        self.rate_limiter.wait_if_needed()
        
        try:
            self._update_session_headers()  # Rotate user agent
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            
            # Add random delay to appear more human-like
            time.sleep(random.uniform(1, 3))
            
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {str(e)}")
            raise
    
    def scrape_zillow_foreclosures(self, city: str, state: str) -> List[Property]:
        """
        Scrape Zillow for foreclosure listings
        Note: Zillow has strong anti-scraping measures. This is a simplified implementation.
        """
        properties = []
        self.log_activity(f"Scraping Zillow for {city}, {state}")
        
        try:
            # Build search URL for foreclosures
            search_url = f"https://www.zillow.com/homes/{city.replace(' ', '-')}-{state}_rb/"
            
            response = self.safe_request(search_url)
            if not response:
                return properties
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for property cards (Zillow's structure may change)
            property_cards = soup.find_all('article', class_=re.compile('list-card'))
            
            if not property_cards:
                # Try alternative selectors
                property_cards = soup.find_all('div', {'data-test': 'property-card'})
            
            self.log_activity(f"Found {len(property_cards)} potential properties on Zillow")
            
            for card in property_cards:
                if shutdown_flag.is_set():
                    break
                
                try:
                    # Extract address
                    address_elem = card.find('address') or card.find('a', {'data-test': 'property-card-addr'})
                    address = address_elem.get_text(strip=True) if address_elem else "N/A"
                    
                    # Extract price
                    price_elem = (card.find('span', {'data-test': 'property-card-price'}) or 
                                card.find('div', class_=re.compile('list-card-price')))
                    price = price_elem.get_text(strip=True) if price_elem else "N/A"
                    
                    # Extract link
                    link_elem = card.find('a', {'data-test': 'property-card-link'}) or card.find('a', class_=re.compile('list-card-link'))
                    link = link_elem.get('href', '#') if link_elem else "#"
                    
                    # Convert relative URLs to absolute
                    if link.startswith('/'):
                        link = urljoin("https://www.zillow.com", link)
                    
                    # Extract property details
                    beds = baths = sqft = "N/A"
                    
                    # Look for bed/bath info
                    info_elem = card.find('ul', class_=re.compile('list-card-details'))
                    if info_elem:
                        for li in info_elem.find_all('li'):
                            text = li.get_text(strip=True)
                            if 'bd' in text.lower():
                                beds = text
                            elif 'ba' in text.lower():
                                baths = text
                            elif 'sqft' in text.lower():
                                sqft = text
                    
                    # Only include properties under $200k
                    price_num = re.sub(r'[^\d.]', '', price)
                    if price_num and float(price_num) < 200000:
                        prop = Property(
                            address=address,
                            price=price,
                            link=link,
                            date=datetime.now().strftime('%Y-%m-%d'),
                            property_type="Foreclosure",
                            bedrooms=beds,
                            bathrooms=baths,
                            sqft=sqft,
                            source="Zillow",
                            city=city,
                            state=state
                        )
                        
                        if prop.is_valid():
                            properties.append(prop)
                            
                except Exception as e:
                    self.log_activity(f"Error parsing Zillow property: {str(e)}", "WARNING")
                    continue
                    
        except Exception as e:
            self.log_activity(f"Error scraping Zillow for {city}, {state}: {str(e)}", "ERROR")
            
        self.log_activity(f"Successfully scraped {len(properties)} properties from Zillow")
        return properties
    
    def scrape_realtytrac_foreclosures(self, city: str, state: str) -> List[Property]:
        """
        Scrape RealtyTrac for foreclosure listings
        Note: RealtyTrac may require authentication for full access
        """
        properties = []
        self.log_activity(f"Scraping RealtyTrac for {city}, {state}")
        
        try:
            search_url = f"https://www.realtytrac.com/mapsearch/sold/in/{city.lower()}-{state.lower()}/"
            
            response = self.safe_request(search_url)
            if not response:
                return properties
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for property listings
            property_rows = soup.find_all('tr', class_=re.compile('property'))
            if not property_rows:
                property_rows = soup.find_all('div', class_=re.compile('property-item'))
            
            self.log_activity(f"Found {len(property_rows)} potential properties on RealtyTrac")
            
            for row in property_rows:
                if shutdown_flag.is_set():
                    break
                
                try:
                    # Extract address
                    address_elem = row.find('td', class_='address') or row.find(class_=re.compile('address'))
                    address = address_elem.get_text(strip=True) if address_elem else "N/A"
                    
                    # Extract price
                    price_elem = row.find('td', class_='price') or row.find(class_=re.compile('price'))
                    price = price_elem.get_text(strip=True) if price_elem else "N/A"
                    
                    # Extract link
                    link_elem = row.find('a')
                    link = link_elem.get('href', '#') if link_elem else "#"
                    
                    if link.startswith('/'):
                        link = urljoin("https://www.realtytrac.com", link)
                    
                    # Extract property details
                    details = row.find_all('td')
                    property_type = beds = baths = sqft = "N/A"
                    
                    if len(details) > 2:
                        property_type = details[2].get_text(strip=True) if len(details) > 2 else "N/A"
                        beds = details[3].get_text(strip=True) if len(details) > 3 else "N/A"
                        baths = details[4].get_text(strip=True) if len(details) > 4 else "N/A"
                        sqft = details[5].get_text(strip=True) if len(details) > 5 else "N/A"
                    
                    # Only include properties under $200k
                    price_num = re.sub(r'[^\d.]', '', price)
                    if price_num and float(price_num) < 200000:
                        prop = Property(
                            address=address,
                            price=price,
                            link=link,
                            date=datetime.now().strftime('%Y-%m-%d'),
                            property_type=property_type if property_type != "N/A" else "Foreclosure",
                            bedrooms=beds,
                            bathrooms=baths,
                            sqft=sqft,
                            source="RealtyTrac",
                            city=city,
                            state=state
                        )
                        
                        if prop.is_valid():
                            properties.append(prop)
                            
                except Exception as e:
                    self.log_activity(f"Error parsing RealtyTrac property: {str(e)}", "WARNING")
                    continue
                    
        except Exception as e:
            self.log_activity(f"Error scraping RealtyTrac for {city}, {state}: {str(e)}", "ERROR")
            
        self.log_activity(f"Successfully scraped {len(properties)} properties from RealtyTrac")
        return properties
    
    def scrape_auction_com(self, city: str, state: str) -> List[Property]:
        """
        Scrape Auction.com for foreclosure listings
        """
        properties = []
        self.log_activity(f"Scraping Auction.com for {city}, {state}")
        
        try:
            # Build search URL
            search_url = f"https://www.auction.com/residential/search?searchType=Residential&state={state}&city={quote(city)}"
            
            response = self.safe_request(search_url)
            if not response:
                return properties
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for property listings
            property_cards = soup.find_all('div', class_=re.compile('property-card'))
            if not property_cards:
                property_cards = soup.find_all('article', class_=re.compile('property'))
            
            self.log_activity(f"Found {len(property_cards)} potential properties on Auction.com")
            
            for card in property_cards:
                if shutdown_flag.is_set():
                    break
                
                try:
                    # Extract address
                    address_elem = card.find(class_=re.compile('address'))
                    address = address_elem.get_text(strip=True) if address_elem else "N/A"
                    
                    # Extract price
                    price_elem = card.find(class_=re.compile('price'))
                    price = price_elem.get_text(strip=True) if price_elem else "N/A"
                    
                    # Extract link
                    link_elem = card.find('a')
                    link = link_elem.get('href', '#') if link_elem else "#"
                    
                    if link.startswith('/'):
                        link = urljoin("https://www.auction.com", link)
                    
                    # Extract property details
                    beds = baths = sqft = "N/A"
                    details_elem = card.find(class_=re.compile('details'))
                    if details_elem:
                        text = details_elem.get_text()
                        bed_match = re.search(r'(\d+)\s*bed', text, re.I)
                        bath_match = re.search(r'([\d.]+)\s*bath', text, re.I)
                        sqft_match = re.search(r'([\d,]+)\s*sq', text, re.I)
                        
                        if bed_match:
                            beds = f"{bed_match.group(1)} bd"
                        if bath_match:
                            baths = f"{bath_match.group(1)} ba"
                        if sqft_match:
                            sqft = f"{sqft_match.group(1)} sqft"
                    
                    # Only include properties under $200k
                    price_num = re.sub(r'[^\d.]', '', price)
                    if price_num and float(price_num) < 200000:
                        prop = Property(
                            address=address,
                            price=price,
                            link=link,
                            date=datetime.now().strftime('%Y-%m-%d'),
                            property_type="Auction",
                            bedrooms=beds,
                            bathrooms=baths,
                            sqft=sqft,
                            source="Auction.com",
                            city=city,
                            state=state
                        )
                        
                        if prop.is_valid():
                            properties.append(prop)
                            
                except Exception as e:
                    self.log_activity(f"Error parsing Auction.com property: {str(e)}", "WARNING")
                    continue
                    
        except Exception as e:
            self.log_activity(f"Error scraping Auction.com for {city}, {state}: {str(e)}", "ERROR")
            
        self.log_activity(f"Successfully scraped {len(properties)} properties from Auction.com")
        return properties
    
    def scrape_realtor_com(self, city: str, state: str) -> List[Property]:
        """
        Scrape Realtor.com for foreclosure listings
        """
        properties = []
        self.log_activity(f"Scraping Realtor.com for {city}, {state}")
        
        try:
            # Build search URL for foreclosures
            search_url = f"https://www.realtor.com/realestateandhomes-search/{city}_{state}/type-single-family-home/price-na-200000/show-foreclosures"
            
            response = self.safe_request(search_url)
            if not response:
                return properties
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for property cards
            property_cards = soup.find_all('li', {'data-testid': re.compile('result-card')})
            if not property_cards:
                property_cards = soup.find_all('div', class_=re.compile('PropertyCard'))
            
            self.log_activity(f"Found {len(property_cards)} potential properties on Realtor.com")
            
            for card in property_cards:
                if shutdown_flag.is_set():
                    break
                
                try:
                    # Extract address
                    address_elem = card.find('div', {'data-testid': 'card-address'})
                    if not address_elem:
                        address_elem = card.find(class_=re.compile('address'))
                    address = address_elem.get_text(strip=True) if address_elem else "N/A"
                    
                    # Extract price
                    price_elem = card.find('div', {'data-testid': 'card-price'})
                    if not price_elem:
                        price_elem = card.find(class_=re.compile('price'))
                    price = price_elem.get_text(strip=True) if price_elem else "N/A"
                    
                    # Extract link
                    link_elem = card.find('a', {'data-testid': 'property-anchor'})
                    if not link_elem:
                        link_elem = card.find('a')
                    link = link_elem.get('href', '#') if link_elem else "#"
                    
                    if link.startswith('/'):
                        link = urljoin("https://www.realtor.com", link)
                    
                    # Extract property details
                    beds = baths = sqft = "N/A"
                    meta_elem = card.find('ul', {'data-testid': 'property-meta'})
                    if meta_elem:
                        for li in meta_elem.find_all('li'):
                            text = li.get_text(strip=True)
                            if 'bed' in text.lower():
                                beds = text
                            elif 'bath' in text.lower():
                                baths = text
                            elif 'sqft' in text.lower():
                                sqft = text
                    
                    # Only include properties under $200k
                    price_num = re.sub(r'[^\d.]', '', price)
                    if price_num and float(price_num) < 200000:
                        prop = Property(
                            address=address,
                            price=price,
                            link=link,
                            date=datetime.now().strftime('%Y-%m-%d'),
                            property_type="Foreclosure",
                            bedrooms=beds,
                            bathrooms=baths,
                            sqft=sqft,
                            source="Realtor.com",
                            city=city,
                            state=state
                        )
                        
                        if prop.is_valid():
                            properties.append(prop)
                            
                except Exception as e:
                    self.log_activity(f"Error parsing Realtor.com property: {str(e)}", "WARNING")
                    continue
                    
        except Exception as e:
            self.log_activity(f"Error scraping Realtor.com for {city}, {state}: {str(e)}", "ERROR")
            
        self.log_activity(f"Successfully scraped {len(properties)} properties from Realtor.com")
        return properties
    
    def scrape_all_sources(self, city: str, state: str) -> List[Property]:
        """Scrape all sources for a given city concurrently"""
        all_properties = []
        
        scrapers = [
            self.scrape_zillow_foreclosures,
            self.scrape_realtytrac_foreclosures,
            self.scrape_auction_com,
            self.scrape_realtor_com
        ]
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(scraper, city, state): scraper.__name__ 
                      for scraper in scrapers}
            
            for future in as_completed(futures):
                scraper_name = futures[future]
                try:
                    properties = future.result()
                    all_properties.extend(properties)
                    self.log_activity(f"{scraper_name} completed: {len(properties)} properties")
                except Exception as e:
                    self.log_activity(f"{scraper_name} failed: {str(e)}", "ERROR")
        
        return all_properties
    
    def run_scraping(self, concurrent: bool = True) -> List[Property]:
        """Run scraping for all target cities"""
        all_properties = []
        
        self.log_activity(f"Starting scraping for {len(self.target_cities)} cities")
        
        if concurrent:
            # Concurrent scraping across cities
            with ThreadPoolExecutor(max_workers=len(self.target_cities)) as executor:
                futures = {
                    executor.submit(self.scrape_all_sources, city['name'], city['state']): city
                    for city in self.target_cities
                }
                
                for future in as_completed(futures):
                    city = futures[future]
                    try:
                        properties = future.result()
                        all_properties.extend(properties)
                        self.log_activity(f"City {city['name']}, {city['state']} completed: {len(properties)} properties")
                    except Exception as e:
                        self.log_activity(f"City {city['name']}, {city['state']} failed: {str(e)}", "ERROR")
        else:
            # Sequential scraping
            for city in self.target_cities:
                if shutdown_flag.is_set():
                    break
                
                properties = self.scrape_all_sources(city['name'], city['state'])
                all_properties.extend(properties)
        
        # Save properties to database
        saved_count = 0
        for prop in all_properties:
            if self.db.save_property(prop):
                saved_count += 1
        
        self.log_activity(f"Scraping completed: {len(all_properties)} total properties, {saved_count} saved to database")
        
        return all_properties
    
    def match_properties_to_buyers(self) -> Dict[str, List[Tuple[Property, int]]]:
        """Match properties to buyers based on criteria"""
        properties = self.db.get_all_properties()
        buyers = self.db.get_all_buyers()
        
        matches = defaultdict(list)
        
        self.log_activity(f"Matching {len(properties)} properties to {len(buyers)} buyers")
        
        for prop in properties:
            for buyer in buyers:
                is_match, score = buyer.matches_property(prop)
                if is_match and score > 50:  # Only consider matches with score > 50
                    matches[buyer.buyer_id].append((prop, score))
                    self.db.save_match(prop.property_id, buyer.buyer_id, score)
        
        # Sort matches by score for each buyer
        for buyer_id in matches:
            matches[buyer_id].sort(key=lambda x: x[1], reverse=True)
        
        self.log_activity(f"Matching completed: {len(matches)} buyers have matches")
        
        return matches
    
    def send_notifications(self, matches: Dict[str, List[Tuple[Property, int]]]):
        """Send email notifications to buyers with matching properties"""
        buyers = {b.buyer_id: b for b in self.db.get_all_buyers()}
        
        notification_count = 0
        
        for buyer_id, property_matches in matches.items():
            if not property_matches:
                continue
            
            buyer = buyers.get(buyer_id)
            if not buyer:
                continue
            
            try:
                self.notifier.send_property_notification(buyer, property_matches)
                notification_count += 1
                self.log_activity(f"Sent notification to {buyer.name} with {len(property_matches)} properties")
            except Exception as e:
                self.log_activity(f"Failed to send notification to {buyer.name}: {str(e)}", "ERROR")
        
        self.log_activity(f"Notifications sent: {notification_count} buyers notified")
    
    def export_to_csv(self, filename: str = None):
        """Export properties to CSV file"""
        if not filename:
            filename = f"properties_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        properties = self.db.get_all_properties()
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                if properties:
                    writer = csv.DictWriter(f, fieldnames=asdict(properties[0]).keys())
                    writer.writeheader()
                    for prop in properties:
                        writer.writerow(asdict(prop))
            
            self.log_activity(f"Exported {len(properties)} properties to {filename}")
            return True
        except Exception as e:
            self.log_activity(f"Error exporting to CSV: {str(e)}", "ERROR")
            return False
    
    def export_to_json(self, filename: str = None):
        """Export properties to JSON file"""
        if not filename:
            filename = f"properties_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        properties = self.db.get_all_properties()
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump([asdict(prop) for prop in properties], f, indent=2)
            
            self.log_activity(f"Exported {len(properties)} properties to {filename}")
            return True
        except Exception as e:
            self.log_activity(f"Error exporting to JSON: {str(e)}", "ERROR")
            return False
    
    def add_buyer(self, name: str, email: str, max_price: int, 
                  preferred_areas: List[str] = None, min_price: int = 0,
                  min_bedrooms: int = 0, min_bathrooms: int = 0,
                  min_sqft: int = 0, property_types: List[str] = None):
        """Add a new buyer to the database"""
        buyer = Buyer(
            name=name,
            email=email,
            max_price=max_price,
            min_price=min_price,
            preferred_areas=preferred_areas or [],
            min_bedrooms=min_bedrooms,
            min_bathrooms=min_bathrooms,
            min_sqft=min_sqft,
            property_types=property_types or []
        )
        
        if self.db.save_buyer(buyer):
            self.log_activity(f"Added new buyer: {name} ({email})")
            return buyer
        else:
            self.log_activity(f"Failed to add buyer: {name}", "ERROR")
            return None
    
    def run_full_cycle(self):
        """Run complete automation cycle: scrape, match, notify"""
        self.log_activity("=" * 50)
        self.log_activity("Starting full automation cycle")
        self.log_activity("=" * 50)
        
        # Step 1: Scrape properties
        properties = self.run_scraping(concurrent=True)
        
        if shutdown_flag.is_set():
            self.log_activity("Shutdown requested during scraping")
            return
        
        # Step 2: Match properties to buyers
        matches = self.match_properties_to_buyers()
        
        # Step 3: Send notifications
        self.send_notifications(matches)
        
        # Step 4: Export data
        self.export_to_csv()
        self.export_to_json()
        
        self.log_activity("=" * 50)
        self.log_activity("Full automation cycle completed")
        self.log_activity("=" * 50)


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description='🏠 Advanced Real Estate Wholesaling Automation System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full automation cycle
  python advanced_real_estate_wholesaling.py run

  # Scrape properties only
  python advanced_real_estate_wholesaling.py scrape

  # Match properties to buyers
  python advanced_real_estate_wholesaling.py match

  # Add a new buyer
  python advanced_real_estate_wholesaling.py add-buyer --name "John Doe" --email "john@example.com" --max-price 150000 --areas "Kokomo,Logansport"

  # Export data
  python advanced_real_estate_wholesaling.py export --format csv

  # View statistics
  python advanced_real_estate_wholesaling.py stats
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run full automation cycle')
    
    # Scrape command
    scrape_parser = subparsers.add_parser('scrape', help='Scrape properties from all sources')
    scrape_parser.add_argument('--sequential', action='store_true', 
                              help='Use sequential scraping instead of concurrent')
    
    # Match command
    match_parser = subparsers.add_parser('match', help='Match properties to buyers')
    match_parser.add_argument('--notify', action='store_true', 
                             help='Send email notifications after matching')
    
    # Add buyer command
    buyer_parser = subparsers.add_parser('add-buyer', help='Add a new buyer')
    buyer_parser.add_argument('--name', required=True, help='Buyer name')
    buyer_parser.add_argument('--email', required=True, help='Buyer email')
    buyer_parser.add_argument('--max-price', type=int, required=True, help='Maximum price')
    buyer_parser.add_argument('--min-price', type=int, default=0, help='Minimum price')
    buyer_parser.add_argument('--areas', help='Comma-separated preferred areas')
    buyer_parser.add_argument('--min-beds', type=int, default=0, help='Minimum bedrooms')
    buyer_parser.add_argument('--min-baths', type=int, default=0, help='Minimum bathrooms')
    buyer_parser.add_argument('--min-sqft', type=int, default=0, help='Minimum square feet')
    buyer_parser.add_argument('--types', help='Comma-separated property types')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export data')
    export_parser.add_argument('--format', choices=['csv', 'json'], default='csv',
                              help='Export format')
    export_parser.add_argument('--output', help='Output filename')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Display statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize bot
    bot = AdvancedRealEstateBot()
    
    # Execute command
    if args.command == 'run':
        bot.run_full_cycle()
    
    elif args.command == 'scrape':
        bot.run_scraping(concurrent=not args.sequential)
    
    elif args.command == 'match':
        matches = bot.match_properties_to_buyers()
        if args.notify:
            bot.send_notifications(matches)
    
    elif args.command == 'add-buyer':
        areas = args.areas.split(',') if args.areas else []
        types = args.types.split(',') if args.types else []
        
        buyer = bot.add_buyer(
            name=args.name,
            email=args.email,
            max_price=args.max_price,
            min_price=args.min_price,
            preferred_areas=areas,
            min_bedrooms=args.min_beds,
            min_bathrooms=args.min_baths,
            min_sqft=args.min_sqft,
            property_types=types
        )
        
        if buyer:
            print(f"✓ Buyer added successfully: {buyer.name}")
        else:
            print(f"✗ Failed to add buyer")
    
    elif args.command == 'export':
        if args.format == 'csv':
            bot.export_to_csv(args.output)
        else:
            bot.export_to_json(args.output)
    
    elif args.command == 'stats':
        properties = bot.db.get_all_properties()
        buyers = bot.db.get_all_buyers()
        
        print("\n" + "=" * 50)
        print("📊 Real Estate Wholesaling Statistics")
        print("=" * 50)
        print(f"Total Properties: {len(properties)}")
        print(f"Active Buyers: {len(buyers)}")
        
        if properties:
            sources = defaultdict(int)
            cities = defaultdict(int)
            
            for prop in properties:
                sources[prop.source] += 1
                cities[f"{prop.city}, {prop.state}"] += 1
            
            print("\nProperties by Source:")
            for source, count in sources.items():
                print(f"  - {source}: {count}")
            
            print("\nProperties by City:")
            for city, count in sorted(cities.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  - {city}: {count}")
        
        print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
