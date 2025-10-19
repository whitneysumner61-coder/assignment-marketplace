# 🏠 Advanced Real Estate Wholesaling Automation System

A comprehensive, production-ready real estate wholesaling automation system with advanced web scraping, intelligent property-buyer matching, and automated notification capabilities.

## ✨ Features

### Core Functionality
- **Multi-Source Scraping**: Scrapes properties from Zillow, RealtyTrac, Auction.com, and Realtor.com
- **Intelligent Matching**: Advanced algorithm matches properties to buyers based on multiple criteria
- **Database Persistence**: SQLite database for reliable data storage and retrieval
- **Email Notifications**: Automated email alerts to buyers with matching properties
- **Concurrent Processing**: Thread-based concurrent scraping for faster data collection

### Advanced Features
- **Rate Limiting**: Built-in rate limiter to prevent overwhelming target servers
- **Anti-Detection**: Rotating user agents and human-like behavior patterns
- **Error Handling**: Comprehensive error handling with retry logic and exponential backoff
- **Graceful Shutdown**: Handles interrupt signals cleanly, finishing current tasks
- **Activity Logging**: Multi-level logging to files, console, and database
- **Data Validation**: Property data validation and sanitization
- **Multiple Export Formats**: Export to CSV, JSON, and Excel formats

### CLI Interface
- Multiple commands for different operations
- Add buyers, scrape properties, match listings, and export data
- View statistics and system status

## 📋 Requirements

- Python 3.8 or higher
- Internet connection for web scraping
- SMTP server credentials (optional, for email notifications)

## 🚀 Installation

1. **Clone the repository** (or navigate to the automation directory):
```bash
cd automation/real_estate
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Set up environment variables** (optional, for email notifications):
Create a `.env` file in the same directory:
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
```

**Note**: For Gmail, you'll need to use an [App Password](https://support.google.com/accounts/answer/185833) instead of your regular password.

## 📖 Usage

### Quick Start

Run the complete automation cycle (scrape, match, notify, export):
```bash
python advanced_real_estate_wholesaling.py run
```

### Command Reference

#### 1. Scrape Properties
Scrape properties from all sources:
```bash
python advanced_real_estate_wholesaling.py scrape
```

Use sequential scraping (slower but more stable):
```bash
python advanced_real_estate_wholesaling.py scrape --sequential
```

#### 2. Add Buyers
Add a new buyer with specific criteria:
```bash
python advanced_real_estate_wholesaling.py add-buyer \
  --name "John Doe" \
  --email "john@example.com" \
  --max-price 150000 \
  --min-price 50000 \
  --areas "Kokomo,Logansport,Indianapolis" \
  --min-beds 2 \
  --min-baths 1 \
  --min-sqft 1000 \
  --types "Foreclosure,Auction"
```

#### 3. Match Properties to Buyers
Match properties to buyers based on their criteria:
```bash
python advanced_real_estate_wholesaling.py match
```

Match and send email notifications:
```bash
python advanced_real_estate_wholesaling.py match --notify
```

#### 4. Export Data
Export properties to CSV:
```bash
python advanced_real_estate_wholesaling.py export --format csv --output my_properties.csv
```

Export to JSON:
```bash
python advanced_real_estate_wholesaling.py export --format json --output my_properties.json
```

#### 5. View Statistics
Display system statistics:
```bash
python advanced_real_estate_wholesaling.py stats
```

### Programmatic Usage

You can also use the system as a Python library:

```python
from advanced_real_estate_wholesaling import AdvancedRealEstateBot, Buyer

# Initialize the bot
config = {
    'target_cities': [
        {"name": "Kokomo", "state": "IN"},
        {"name": "Logansport", "state": "IN"}
    ]
}
bot = AdvancedRealEstateBot(config)

# Add a buyer
buyer = bot.add_buyer(
    name="Jane Smith",
    email="jane@example.com",
    max_price=175000,
    preferred_areas=["Kokomo", "Logansport"],
    min_bedrooms=3,
    min_bathrooms=2
)

# Run scraping
properties = bot.run_scraping()

# Match properties to buyers
matches = bot.match_properties_to_buyers()

# Send notifications
bot.send_notifications(matches)

# Export data
bot.export_to_csv("my_export.csv")
bot.export_to_json("my_export.json")
```

## 🏗️ Architecture

### Components

#### 1. **Property** (Data Class)
Represents a real estate property with:
- Basic info: address, price, link
- Details: bedrooms, bathrooms, square footage
- Metadata: source, date, property type
- Unique property ID generation

#### 2. **Buyer** (Data Class)
Represents a buyer with:
- Contact info: name, email
- Budget constraints: min/max price
- Preferences: areas, property types
- Requirements: min beds/baths/sqft
- Smart property matching algorithm

#### 3. **RateLimiter**
Controls request frequency to:
- Prevent overwhelming target servers
- Avoid IP blocking
- Maintain ethical scraping practices

#### 4. **DatabaseManager**
Handles all database operations:
- SQLite database management
- CRUD operations for properties and buyers
- Match tracking and activity logging
- Transaction management

#### 5. **EmailNotifier**
Manages email notifications:
- SMTP integration
- HTML email templates
- Retry logic for failed sends
- Batch notifications

#### 6. **AdvancedRealEstateBot** (Main Class)
Orchestrates all operations:
- Multi-source web scraping
- Concurrent processing
- Property-buyer matching
- Data export functionality

### Database Schema

#### Properties Table
```sql
properties (
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
)
```

#### Buyers Table
```sql
buyers (
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
)
```

#### Property Matches Table
```sql
property_matches (
  match_id INTEGER PRIMARY KEY,
  property_id TEXT,
  buyer_id TEXT,
  match_score INTEGER,
  notified TEXT,
  created_at TIMESTAMP
)
```

## 🔧 Configuration

### Target Cities
Modify target cities in the code or pass them in the config:
```python
target_cities = [
    {"name": "Kokomo", "state": "IN"},
    {"name": "Logansport", "state": "IN"},
    {"name": "Indianapolis", "state": "IN"},
    {"name": "Fort Wayne", "state": "IN"}
]

bot = AdvancedRealEstateBot({'target_cities': target_cities})
```

### Rate Limiting
Adjust requests per minute:
```python
bot.rate_limiter = RateLimiter(requests_per_minute=5)  # Slower, more conservative
```

### Database Location
Specify custom database path:
```python
bot = AdvancedRealEstateBot({'db_path': '/path/to/custom.db'})
```

## 🎯 Property-Buyer Matching Algorithm

The matching algorithm calculates a score (0-100) based on:

1. **Price Range** (Mandatory): Property must be within buyer's budget
2. **Location** (30 points): Matches buyer's preferred areas
3. **Property Type** (20 points): Matches buyer's preferred types
4. **Bedrooms** (15 points): Meets minimum bedroom requirement
5. **Bathrooms** (15 points): Meets minimum bathroom requirement
6. **Square Footage** (10 points): Meets minimum sqft requirement

**Minimum Match Score**: 50 (properties with scores below 50 are filtered out)

## 📊 Output Files

### Generated Files

1. **real_estate.db**: SQLite database with all data
2. **wholesaling_bot.log**: Detailed activity log
3. **activity.log**: Legacy activity log
4. **leads.csv**: Legacy CSV export (backward compatibility)
5. **buyers.csv**: Legacy CSV export (backward compatibility)
6. **properties_export_[timestamp].csv**: Property exports
7. **properties_export_[timestamp].json**: Property exports

### Email Notifications

Buyers receive HTML emails with:
- List of matching properties
- Property details (price, beds, baths, sqft)
- Direct links to property listings
- Match scores for each property

## 🛡️ Error Handling

### Retry Logic
- Automatic retries with exponential backoff
- Configurable max retries and delay
- Graceful degradation on persistent failures

### Rate Limiting
- Prevents overwhelming target servers
- Automatic throttling and wait times
- Per-minute request tracking

### Graceful Shutdown
- Handles SIGINT and SIGTERM signals
- Completes current tasks before exiting
- Saves all data before shutdown

### Logging
- Multi-level logging (DEBUG, INFO, WARNING, ERROR)
- Logs to file, console, and database
- Timestamped entries for debugging

## ⚠️ Important Notes

### Legal and Ethical Considerations

1. **Terms of Service**: Always review and comply with the terms of service of websites you scrape
2. **robots.txt**: Respect robots.txt directives
3. **Rate Limiting**: Use reasonable request rates to avoid overwhelming servers
4. **Data Usage**: Use scraped data only for legitimate purposes
5. **Privacy**: Respect privacy laws and regulations

### Technical Limitations

1. **Anti-Scraping Measures**: Websites may use CAPTCHAs, IP blocking, or other anti-scraping techniques
2. **Structure Changes**: Website HTML structure may change, breaking scrapers
3. **Authentication**: Some sites require authentication for full access
4. **Data Accuracy**: Scraped data may be incomplete or inaccurate

### Best Practices

1. **Test First**: Test scraping on a small scale before running large operations
2. **Monitor Logs**: Regularly check logs for errors or issues
3. **Backup Data**: Regularly backup the database
4. **Update Scrapers**: Keep scrapers updated as websites change
5. **Respect Resources**: Use concurrent scraping judiciously

## 🧪 Testing

Run tests (if implemented):
```bash
pytest tests/ -v --cov=advanced_real_estate_wholesaling
```

## 🐛 Troubleshooting

### Common Issues

#### Issue: "No properties found"
**Solutions**:
- Check internet connection
- Verify target websites are accessible
- Review logs for specific errors
- Try sequential scraping: `--sequential`

#### Issue: "Email notifications not sending"
**Solutions**:
- Verify SMTP credentials in `.env` file
- Check SMTP server and port settings
- Use App Password for Gmail
- Check email logs for specific errors

#### Issue: "Rate limiting errors"
**Solutions**:
- Reduce `requests_per_minute` setting
- Use sequential scraping instead of concurrent
- Add delays between scraping sessions

#### Issue: "Database locked"
**Solutions**:
- Close other connections to the database
- Ensure only one instance is running
- Check file permissions on database file

## 📝 Development

### Code Style
The code follows PEP 8 guidelines. Format with:
```bash
black advanced_real_estate_wholesaling.py
```

### Type Checking
Run type checking with:
```bash
mypy advanced_real_estate_wholesaling.py
```

### Linting
Lint the code with:
```bash
flake8 advanced_real_estate_wholesaling.py
```

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

1. Additional data sources
2. Machine learning for better matching
3. Web dashboard interface
4. Mobile app integration
5. Advanced analytics and reporting
6. Cloud deployment options

## 📄 License

This project is provided as-is for educational and commercial purposes. Please ensure compliance with all applicable laws and website terms of service when using this software.

## 🙏 Acknowledgments

- BeautifulSoup4 for HTML parsing
- Requests library for HTTP operations
- SQLite for lightweight database functionality
- Python standard library for robust foundations

## 📞 Support

For issues or questions:
1. Check the logs in `wholesaling_bot.log`
2. Review this README thoroughly
3. Check Python and dependency versions
4. Verify network connectivity and permissions

---

**Built with ❤️ for real estate wholesalers**

*Last Updated: 2025-10-19*
