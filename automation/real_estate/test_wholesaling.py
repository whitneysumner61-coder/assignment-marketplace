#!/usr/bin/env python3
"""
Basic tests for Advanced Real Estate Wholesaling System
"""

import pytest
import os
import tempfile
from datetime import datetime
from advanced_real_estate_wholesaling import (
    Property, Buyer, RateLimiter, DatabaseManager, 
    AdvancedRealEstateBot, retry_on_failure
)


class TestProperty:
    """Test Property class"""
    
    def test_property_creation(self):
        """Test creating a property"""
        prop = Property(
            address="123 Main St, Kokomo, IN",
            price="$150,000",
            link="https://example.com/property/123",
            date="2025-01-01",
            property_type="Foreclosure",
            source="Zillow",
            city="Kokomo",
            state="IN"
        )
        
        assert prop.address == "123 Main St, Kokomo, IN"
        assert prop.price == "$150,000"
        assert prop.property_id  # Should have auto-generated ID
    
    def test_property_validation(self):
        """Test property validation"""
        # Valid property
        valid_prop = Property(
            address="123 Main St",
            price="$150,000",
            link="https://example.com",
            date="2025-01-01"
        )
        assert valid_prop.is_valid()
        
        # Invalid property (no address)
        invalid_prop = Property(
            address="N/A",
            price="$150,000",
            link="https://example.com",
            date="2025-01-01"
        )
        assert not invalid_prop.is_valid()
    
    def test_property_price_extraction(self):
        """Test numeric price extraction"""
        prop = Property(
            address="123 Main St",
            price="$150,000",
            link="https://example.com",
            date="2025-01-01"
        )
        
        assert prop.get_price_numeric() == 150000.0
        
        # Test with different formats
        prop2 = Property(
            address="456 Oak Ave",
            price="$75,500",
            link="https://example.com",
            date="2025-01-01"
        )
        assert prop2.get_price_numeric() == 75500.0


class TestBuyer:
    """Test Buyer class"""
    
    def test_buyer_creation(self):
        """Test creating a buyer"""
        buyer = Buyer(
            name="John Doe",
            email="john@example.com",
            max_price=200000,
            min_price=50000,
            preferred_areas=["Kokomo", "Logansport"]
        )
        
        assert buyer.name == "John Doe"
        assert buyer.email == "john@example.com"
        assert buyer.buyer_id  # Should have auto-generated ID
    
    def test_buyer_property_matching(self):
        """Test buyer-property matching"""
        buyer = Buyer(
            name="Jane Smith",
            email="jane@example.com",
            max_price=175000,
            min_price=50000,
            preferred_areas=["Kokomo"],
            min_bedrooms=2,
            min_bathrooms=1
        )
        
        # Property that should match
        matching_prop = Property(
            address="123 Main St, Kokomo, IN",
            price="$150,000",
            link="https://example.com",
            date="2025-01-01",
            bedrooms="3 bd",
            bathrooms="2 ba",
            city="Kokomo",
            state="IN"
        )
        
        is_match, score = buyer.matches_property(matching_prop)
        assert is_match
        assert score > 50
        
        # Property that shouldn't match (too expensive)
        non_matching_prop = Property(
            address="456 Oak Ave, Indianapolis, IN",
            price="$250,000",
            link="https://example.com",
            date="2025-01-01",
            city="Indianapolis",
            state="IN"
        )
        
        is_match, score = non_matching_prop.get_price_numeric() and buyer.matches_property(non_matching_prop)
        # Price is out of range, so should not match
        assert not is_match or score == 0


class TestRateLimiter:
    """Test RateLimiter class"""
    
    def test_rate_limiter_creation(self):
        """Test creating a rate limiter"""
        limiter = RateLimiter(requests_per_minute=10)
        assert limiter.requests_per_minute == 10
        assert len(limiter.requests) == 0
    
    def test_rate_limiter_basic(self):
        """Test basic rate limiting (without actual waiting)"""
        limiter = RateLimiter(requests_per_minute=100)  # High limit for testing
        
        # Should not wait on first request
        limiter.wait_if_needed()
        assert len(limiter.requests) == 1


class TestDatabaseManager:
    """Test DatabaseManager class"""
    
    def test_database_initialization(self):
        """Test database initialization"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            db = DatabaseManager(db_path)
            
            # Check that tables were created
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                assert 'properties' in tables
                assert 'buyers' in tables
                assert 'property_matches' in tables
                assert 'activity_log' in tables
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_save_and_retrieve_property(self):
        """Test saving and retrieving a property"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            db = DatabaseManager(db_path)
            
            prop = Property(
                address="123 Test St",
                price="$100,000",
                link="https://example.com",
                date="2025-01-01",
                source="Test"
            )
            
            # Save property
            assert db.save_property(prop)
            
            # Retrieve properties
            properties = db.get_all_properties()
            assert len(properties) == 1
            assert properties[0].address == "123 Test St"
            assert properties[0].property_id == prop.property_id
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_save_and_retrieve_buyer(self):
        """Test saving and retrieving a buyer"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            db = DatabaseManager(db_path)
            
            buyer = Buyer(
                name="Test User",
                email="test@example.com",
                max_price=150000,
                preferred_areas=["Kokomo"]
            )
            
            # Save buyer
            assert db.save_buyer(buyer)
            
            # Retrieve buyers
            buyers = db.get_all_buyers()
            assert len(buyers) == 1
            assert buyers[0].name == "Test User"
            assert buyers[0].buyer_id == buyer.buyer_id
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)


class TestAdvancedRealEstateBot:
    """Test AdvancedRealEstateBot class"""
    
    def test_bot_initialization(self):
        """Test bot initialization"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                'db_path': os.path.join(tmpdir, 'test.db'),
                'leads_file': os.path.join(tmpdir, 'leads.csv'),
                'buyers_file': os.path.join(tmpdir, 'buyers.csv'),
                'log_file': os.path.join(tmpdir, 'activity.log')
            }
            
            bot = AdvancedRealEstateBot(config)
            
            assert bot.db is not None
            assert bot.rate_limiter is not None
            assert bot.notifier is not None
            assert len(bot.target_cities) > 0
    
    def test_add_buyer(self):
        """Test adding a buyer through bot"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                'db_path': os.path.join(tmpdir, 'test.db'),
                'leads_file': os.path.join(tmpdir, 'leads.csv'),
                'buyers_file': os.path.join(tmpdir, 'buyers.csv'),
                'log_file': os.path.join(tmpdir, 'activity.log')
            }
            
            bot = AdvancedRealEstateBot(config)
            
            buyer = bot.add_buyer(
                name="Test Buyer",
                email="buyer@example.com",
                max_price=150000,
                preferred_areas=["Kokomo", "Logansport"]
            )
            
            assert buyer is not None
            assert buyer.name == "Test Buyer"
            
            # Verify buyer was saved
            buyers = bot.db.get_all_buyers()
            assert len(buyers) == 1
    
    def test_export_to_csv(self):
        """Test CSV export"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                'db_path': os.path.join(tmpdir, 'test.db'),
                'leads_file': os.path.join(tmpdir, 'leads.csv'),
                'buyers_file': os.path.join(tmpdir, 'buyers.csv'),
                'log_file': os.path.join(tmpdir, 'activity.log')
            }
            
            bot = AdvancedRealEstateBot(config)
            
            # Add a property
            prop = Property(
                address="123 Test St",
                price="$100,000",
                link="https://example.com",
                date="2025-01-01",
                source="Test"
            )
            bot.db.save_property(prop)
            
            # Export to CSV
            csv_path = os.path.join(tmpdir, 'test_export.csv')
            result = bot.export_to_csv(csv_path)
            
            assert result
            assert os.path.exists(csv_path)
    
    def test_export_to_json(self):
        """Test JSON export"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                'db_path': os.path.join(tmpdir, 'test.db'),
                'leads_file': os.path.join(tmpdir, 'leads.csv'),
                'buyers_file': os.path.join(tmpdir, 'buyers.csv'),
                'log_file': os.path.join(tmpdir, 'activity.log')
            }
            
            bot = AdvancedRealEstateBot(config)
            
            # Add a property
            prop = Property(
                address="123 Test St",
                price="$100,000",
                link="https://example.com",
                date="2025-01-01",
                source="Test"
            )
            bot.db.save_property(prop)
            
            # Export to JSON
            json_path = os.path.join(tmpdir, 'test_export.json')
            result = bot.export_to_json(json_path)
            
            assert result
            assert os.path.exists(json_path)


class TestRetryDecorator:
    """Test retry decorator"""
    
    def test_retry_on_success(self):
        """Test that function succeeds on first try"""
        call_count = 0
        
        @retry_on_failure(max_retries=3, delay=0.1)
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_function()
        assert result == "success"
        assert call_count == 1
    
    def test_retry_on_failure(self):
        """Test that function retries on failure"""
        call_count = 0
        
        @retry_on_failure(max_retries=3, delay=0.1)
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = failing_function()
        assert result == "success"
        assert call_count == 3


def test_property_id_uniqueness():
    """Test that different properties get different IDs"""
    prop1 = Property(
        address="123 Main St",
        price="$150,000",
        link="https://example.com",
        date="2025-01-01"
    )
    
    prop2 = Property(
        address="456 Oak Ave",
        price="$150,000",
        link="https://example.com",
        date="2025-01-01"
    )
    
    assert prop1.property_id != prop2.property_id


def test_buyer_id_uniqueness():
    """Test that different buyers get different IDs"""
    buyer1 = Buyer(
        name="John Doe",
        email="john@example.com",
        max_price=200000
    )
    
    buyer2 = Buyer(
        name="Jane Smith",
        email="jane@example.com",
        max_price=200000
    )
    
    assert buyer1.buyer_id != buyer2.buyer_id


if __name__ == "__main__":
    # Run tests with pytest if available, otherwise run basic tests
    try:
        pytest.main([__file__, "-v"])
    except:
        print("Running basic tests without pytest...")
        
        # Run some basic tests
        test_prop = TestProperty()
        test_prop.test_property_creation()
        test_prop.test_property_validation()
        test_prop.test_property_price_extraction()
        
        test_buyer = TestBuyer()
        test_buyer.test_buyer_creation()
        
        print("✓ Basic tests passed!")
