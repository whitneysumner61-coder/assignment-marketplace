# 🚀 Quick Start Guide - Real Estate Wholesaling System

Get up and running in **5 minutes**!

---

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Internet connection

---

## Step 1: Installation (30 seconds)

```bash
# Navigate to the automation directory
cd automation/real_estate

# Install dependencies
pip install -r requirements.txt
```

---

## Step 2: Basic Usage (1 minute)

### Add Your First Buyer

```bash
python advanced_real_estate_wholesaling.py add-buyer \
  --name "John Investor" \
  --email "john@example.com" \
  --max-price 150000 \
  --areas "Kokomo,Logansport"
```

**Output:**
```
✓ Buyer added successfully: John Investor
```

---

## Step 3: Run Example (2 minutes)

Try the example script to see how it works:

```bash
python example_usage.py
```

This will:
- ✅ Add sample buyers
- ✅ Add sample properties
- ✅ Match properties to buyers
- ✅ Export data to CSV and JSON
- ✅ Show statistics

---

## Step 4: View Your Data (30 seconds)

```bash
# Check statistics
python advanced_real_estate_wholesaling.py stats

# Export data
python advanced_real_estate_wholesaling.py export --format csv
```

---

## Step 5: Configure Email (Optional)

To enable email notifications:

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Add your SMTP settings:
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
```

**Note:** For Gmail, create an [App Password](https://support.google.com/accounts/answer/185833)

---

## Next Steps

### Scrape Real Properties

⚠️ **Important:** Review website terms of service before scraping

```bash
# Scrape properties from all sources
python advanced_real_estate_wholesaling.py scrape
```

### Match Properties to Buyers

```bash
# Match and send notifications
python advanced_real_estate_wholesaling.py match --notify
```

### Full Automation Cycle

```bash
# Run everything: scrape → match → notify → export
python advanced_real_estate_wholesaling.py run
```

---

## Common Commands

| Command | Description |
|---------|-------------|
| `python advanced_real_estate_wholesaling.py run` | Full automation cycle |
| `python advanced_real_estate_wholesaling.py scrape` | Scrape properties only |
| `python advanced_real_estate_wholesaling.py match` | Match properties to buyers |
| `python advanced_real_estate_wholesaling.py stats` | View statistics |
| `python advanced_real_estate_wholesaling.py export --format csv` | Export to CSV |
| `python advanced_real_estate_wholesaling.py --help` | View all commands |

---

## Troubleshooting

### "Module not found" error

```bash
pip install -r requirements.txt
```

### No properties found

- Check internet connection
- Review logs: `cat wholesaling_bot.log`
- Try sequential scraping: `--sequential` flag

### Email not sending

- Verify SMTP settings in `.env`
- Check for App Password (Gmail)
- Review email logs

---

## File Locations

After running, you'll find:

```
automation/real_estate/
├── real_estate.db          # Database with all data
├── wholesaling_bot.log     # Activity log
├── properties_export_*.csv # Exported properties
├── properties_export_*.json # Exported properties
└── leads.csv               # Legacy format
```

---

## Need Help?

1. **Check the logs**: `cat wholesaling_bot.log`
2. **Read the README**: `cat README.md`
3. **View features**: `cat FEATURES.md`
4. **Run tests**: `python test_wholesaling.py`

---

## Pro Tips 💡

1. **Start small**: Test with one city first
2. **Monitor logs**: Keep an eye on `wholesaling_bot.log`
3. **Backup database**: Copy `real_estate.db` regularly
4. **Use cron**: Schedule automated runs
5. **Respect limits**: Use reasonable scraping rates

---

## Example Cron Schedule

Run every day at 8 AM:

```bash
0 8 * * * cd /path/to/automation/real_estate && python advanced_real_estate_wholesaling.py run
```

---

## Success! 🎉

You're now ready to automate your real estate wholesaling business!

For detailed documentation, see [README.md](README.md)

---

*Happy Wholesaling! 🏠*
