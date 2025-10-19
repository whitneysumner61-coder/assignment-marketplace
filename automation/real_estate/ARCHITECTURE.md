# 🏗️ System Architecture - Advanced Real Estate Wholesaling System

## Overview

This document describes the architecture of the Advanced Real Estate Wholesaling Automation System, a production-ready Python application designed for real estate wholesalers.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLI Interface (argparse)                     │
│  Commands: run, scrape, match, add-buyer, export, stats        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              AdvancedRealEstateBot (Main Controller)            │
│  • Orchestrates all operations                                  │
│  • Manages configuration                                        │
│  • Coordinates components                                       │
└──────┬──────────┬──────────┬──────────┬──────────┬────────────┘
       │          │          │          │          │
       ▼          ▼          ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ Database │ │   Rate   │ │  Email   │ │ Scrapers │ │ Matching │
│ Manager  │ │ Limiter  │ │ Notifier │ │  (x4)    │ │ Engine   │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
     │                          │              │            │
     ▼                          ▼              ▼            ▼
┌──────────┐             ┌──────────┐   ┌──────────┐  ┌──────────┐
│  SQLite  │             │   SMTP   │   │   HTTP   │  │ Property │
│    DB    │             │  Server  │   │ Requests │  │  Models  │
└──────────┘             └──────────┘   └──────────┘  └──────────┘
```

---

## Component Architecture

### 1. Core Components

#### AdvancedRealEstateBot
**Responsibility**: Main orchestrator and entry point

```python
class AdvancedRealEstateBot:
    - db: DatabaseManager
    - rate_limiter: RateLimiter
    - notifier: EmailNotifier
    - session: requests.Session
    
    Methods:
    • run_scraping()          # Coordinate scraping
    • match_properties()      # Match properties to buyers
    • send_notifications()    # Email buyers
    • export_data()          # Export to files
```

**Key Responsibilities:**
- Configuration management
- Component initialization
- Workflow orchestration
- Error coordination
- Resource cleanup

---

#### DatabaseManager
**Responsibility**: Data persistence layer

```python
class DatabaseManager:
    - db_path: str
    
    Methods:
    • save_property()        # CRUD for properties
    • get_all_properties()   # Query properties
    • save_buyer()           # CRUD for buyers
    • get_all_buyers()       # Query buyers
    • save_match()           # Record matches
    • log_activity()         # Audit logging
```

**Database Schema:**

```sql
-- Properties Table
CREATE TABLE properties (
    property_id TEXT PRIMARY KEY,
    address TEXT NOT NULL,
    price TEXT,
    link TEXT,
    date TEXT,
    contacted TEXT,
    interested TEXT,
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
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Buyers Table
CREATE TABLE buyers (
    buyer_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    max_price INTEGER,
    min_price INTEGER,
    active TEXT,
    preferred_areas TEXT,
    min_bedrooms INTEGER,
    min_bathrooms INTEGER,
    min_sqft INTEGER,
    property_types TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Property Matches Table
CREATE TABLE property_matches (
    match_id INTEGER PRIMARY KEY,
    property_id TEXT,
    buyer_id TEXT,
    match_score INTEGER,
    notified TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY (property_id) REFERENCES properties(property_id),
    FOREIGN KEY (buyer_id) REFERENCES buyers(buyer_id)
);

-- Activity Log Table
CREATE TABLE activity_log (
    log_id INTEGER PRIMARY KEY,
    timestamp TIMESTAMP,
    level TEXT,
    source TEXT,
    message TEXT
);
```

---

#### RateLimiter
**Responsibility**: Request throttling

```python
class RateLimiter:
    - requests_per_minute: int
    - requests: List[datetime]
    - lock: threading.Lock
    
    Methods:
    • wait_if_needed()       # Throttle requests
```

**Algorithm:**
1. Track request timestamps
2. Remove requests older than 1 minute
3. If limit exceeded, calculate wait time
4. Sleep until rate window resets

---

#### EmailNotifier
**Responsibility**: Email communications

```python
class EmailNotifier:
    - smtp_server: str
    - smtp_port: int
    - sender_email: str
    - sender_password: str
    
    Methods:
    • send_email()                    # Generic email
    • send_property_notification()    # Buyer alerts
```

**Email Template Structure:**
```html
<html>
  <body>
    <h2>Hello {buyer_name},</h2>
    <p>We found {count} new properties...</p>
    
    <div class="property">
      <h3>{address}</h3>
      <p>Price: {price}</p>
      <p>Beds/Baths: {beds} / {baths}</p>
      <p>Match Score: {score}%</p>
      <a href="{link}">View Property</a>
    </div>
  </body>
</html>
```

---

### 2. Data Models

#### Property (Dataclass)
```python
@dataclass
class Property:
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
    arv: str = "N/A"
    days_on_market: str = "N/A"
    property_id: str = field(default_factory=lambda: "")
    
    Methods:
    • _generate_id()         # Hash-based ID
    • get_price_numeric()    # Parse price
    • is_valid()             # Validation
```

**ID Generation:**
```python
def _generate_id(self) -> str:
    hash_input = f"{self.address}_{self.source}_{self.date}"
    # Note: MD5 is used for non-cryptographic ID generation only
    # For security-critical applications, use SHA-256
    return hashlib.md5(hash_input.encode()).hexdigest()[:12]
```

---

#### Buyer (Dataclass)
```python
@dataclass
class Buyer:
    name: str
    email: str
    max_price: int
    min_price: int = 0
    active: str = "Yes"
    preferred_areas: List[str]
    min_bedrooms: int = 0
    min_bathrooms: int = 0
    min_sqft: int = 0
    property_types: List[str]
    buyer_id: str
    
    Methods:
    • _generate_id()         # Hash-based ID
    • matches_property()     # Matching algorithm
```

---

### 3. Scraping Engine

#### Multi-Source Scraping Architecture

```
                    ┌─────────────────┐
                    │ AdvancedBot     │
                    │ run_scraping()  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  ThreadPoolExec │
                    │  (concurrent)   │
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
    ┌───────▼───────┐ ┌─────▼─────┐ ┌───────▼───────┐
    │  Zillow       │ │ RealtyTrac│ │  Auction.com  │
    │  Scraper      │ │  Scraper  │ │  Scraper      │
    └───────┬───────┘ └─────┬─────┘ └───────┬───────┘
            │                │                │
            └────────────────┼────────────────┘
                             │
                    ┌────────▼────────┐
                    │  Rate Limiter   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  HTTP Session   │
                    │  (with headers) │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  BeautifulSoup  │
                    │  HTML Parser    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Property List  │
                    └─────────────────┘
```

#### Scraping Methods

Each scraper follows this pattern:

```python
def scrape_source(self, city: str, state: str) -> List[Property]:
    1. Build search URL
    2. Make HTTP request (with rate limiting)
    3. Parse HTML with BeautifulSoup
    4. Extract property data
    5. Validate and filter
    6. Return Property objects
```

**Anti-Detection Measures:**
- Rotating user agents
- Random delays (1-3 seconds)
- Rate limiting (10 req/min default)
- Session persistence
- Proper headers

---

### 4. Matching Engine

#### Matching Algorithm

```python
def matches_property(self, prop: Property) -> Tuple[bool, int]:
    score = 0
    
    # 1. Price Check (Mandatory)
    if not (min_price <= price <= max_price):
        return False, 0
    
    # 2. Location (30 points)
    if prop.city in preferred_areas:
        score += 30
    elif preferred_areas:  # Has preferences but doesn't match
        return False, 0
    else:  # No preferences
        score += 10
    
    # 3. Property Type (20 points)
    if prop.type in property_types:
        score += 20
    else:
        score += 10  # No preference
    
    # 4. Bedrooms (15 points)
    if prop.beds >= min_bedrooms:
        score += 15
    else:
        score += 5  # Partial credit
    
    # 5. Bathrooms (15 points)
    if prop.baths >= min_bathrooms:
        score += 15
    else:
        score += 5  # Partial credit
    
    # 6. Square Footage (10 points)
    if prop.sqft >= min_sqft:
        score += 10
    else:
        score += 5  # Partial credit
    
    # Note: Minimum threshold of 50 is enforced at match time
    # This allows flexibility in the matching algorithm
    return True, min(score, 100)
```

**Match Flow:**
```
Properties → For Each Property
              ↓
          For Each Buyer
              ↓
          Check Criteria
              ↓
          Calculate Score (0-100)
              ↓
          Score ≥ 50? → Save Match to DB
              │            (enforced in match_properties_to_buyers)
              ↓
          Sort by Score (DESC)
              ↓
          Return Top Matches
```

**Note:** The 50-point threshold is applied when saving matches, not in the
scoring function itself. This allows the algorithm to be flexible while still
filtering low-quality matches.

---

## Data Flow Diagrams

### Full Automation Cycle

```
1. SCRAPE PHASE
   ┌──────────┐
   │  Cities  │
   └────┬─────┘
        │
   ┌────▼─────────────────────┐
   │  For Each City:          │
   │  • Zillow                │
   │  • RealtyTrac            │
   │  • Auction.com           │
   │  • Realtor.com           │
   └────┬─────────────────────┘
        │
   ┌────▼─────┐
   │  Props   │
   └────┬─────┘
        │
   ┌────▼─────┐
   │ Database │
   └──────────┘

2. MATCH PHASE
   ┌──────────┐     ┌──────────┐
   │  Props   │     │  Buyers  │
   └────┬─────┘     └────┬─────┘
        │                │
        └────────┬───────┘
                 │
        ┌────────▼────────┐
        │  Match Engine   │
        │  • Price Check  │
        │  • Location     │
        │  • Criteria     │
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │  Match Scores   │
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │    Database     │
        └─────────────────┘

3. NOTIFY PHASE
   ┌──────────┐
   │  Matches │
   └────┬─────┘
        │
   ┌────▼────────────┐
   │  For Each Buyer:│
   │  • Get Matches  │
   │  • Format Email │
   │  • Send         │
   └────┬────────────┘
        │
   ┌────▼─────┐
   │  SMTP    │
   └──────────┘

4. EXPORT PHASE
   ┌──────────┐
   │ Database │
   └────┬─────┘
        │
   ┌────▼─────────┐
   │  Properties  │
   └────┬─────────┘
        │
   ┌────▼─────┬─────┐
   │   CSV    │ JSON│
   └──────────┴─────┘
```

---

## Error Handling Strategy

### Retry Decorator Pattern

```python
@retry_on_failure(max_retries=3, delay=1, backoff=2)
def function():
    # Attempt 1: delay = 1s
    # Attempt 2: delay = 2s
    # Attempt 3: delay = 4s
    pass
```

### Error Propagation

```
Scraper Error → Log Warning → Continue
Database Error → Log Error → Raise
Network Error → Retry → Eventually Fail
Rate Limit → Wait → Retry
CAPTCHA → Log → Skip Source
```

---

## Performance Optimization

### Concurrent Processing

**Thread Pool Configuration:**
```python
# Concurrent city scraping
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(scrape_city, city) 
               for city in cities]
```

**Benefits:**
- 4x faster scraping (4 cities in parallel)
- Non-blocking I/O operations
- Efficient CPU utilization

### Database Optimization

**Strategies:**
- Indexed primary keys
- Prepared statements
- Transaction batching
- Connection reuse

---

## Security Architecture

### Credential Management

```
Environment Variables (.env)
        ↓
    os.getenv()
        ↓
  Secure Storage
        ↓
  Runtime Memory
```

**Best Practices:**
- No hardcoded secrets
- .env in .gitignore
- Environment-specific configs
- App passwords for Gmail

### SQL Injection Prevention

```python
# ✓ Safe: Parameterized queries
cursor.execute("SELECT * FROM properties WHERE id = ?", (prop_id,))

# ✗ Unsafe: String concatenation
cursor.execute(f"SELECT * FROM properties WHERE id = {prop_id}")
```

---

## Deployment Architecture

### Local Deployment
```
Python 3.8+
    ↓
pip install
    ↓
Configure .env
    ↓
Run CLI commands
```

### Scheduled Deployment
```
Cron Job
    ↓
Python Script
    ↓
Database Update
    ↓
Email Notifications
```

### Cloud Deployment (Future)
```
Docker Container
    ↓
Kubernetes Pod
    ↓
Cloud Database
    ↓
Email Service
```

---

## Extensibility Points

### Adding New Data Sources

```python
def scrape_new_source(self, city: str, state: str) -> List[Property]:
    """
    1. Build URL
    2. Make request
    3. Parse HTML
    4. Extract data
    5. Return properties
    """
    pass
```

### Adding New Matching Criteria

```python
# In Buyer.matches_property():
if custom_criteria:
    score += points
```

### Adding New Export Formats

```python
def export_to_excel(self, filename: str):
    # Use pandas or openpyxl
    pass
```

---

## Monitoring & Observability

### Logging Levels

```
DEBUG:   Detailed diagnostic info
INFO:    General informational messages
WARNING: Potential issues
ERROR:   Errors that need attention
```

### Log Destinations

```
1. Console (StreamHandler)
2. File (FileHandler → wholesaling_bot.log)
3. Database (activity_log table)
```

### Metrics Tracked

- Properties scraped per source
- Match scores distribution
- Email success rate
- Scraping duration
- Database query performance

---

## Testing Strategy

### Unit Tests
- Property validation
- Buyer matching logic
- Database operations
- Rate limiter behavior

### Integration Tests
- Full scraping cycle
- Database persistence
- Email sending
- Export functionality

### Manual Testing
- Example usage script
- CLI command validation
- Error scenarios

---

## Conclusion

This architecture provides:

✅ **Modularity** - Independent, reusable components
✅ **Scalability** - Concurrent processing, efficient DB
✅ **Reliability** - Error handling, retries, logging
✅ **Security** - Credential management, SQL safety
✅ **Maintainability** - Clean code, documentation
✅ **Extensibility** - Easy to add features

---

*Architecture v1.0 - Last Updated: 2025-10-19*
