#!/usr/bin/env python3
"""
Example Usage of Advanced Real Estate Wholesaling System

This script demonstrates how to use the system programmatically.
"""

from advanced_real_estate_wholesaling import AdvancedRealEstateBot, Buyer, Property
import os

def main():
    print("🏠 Advanced Real Estate Wholesaling System - Example Usage\n")
    print("=" * 60)
    
    # Initialize the bot with custom configuration
    config = {
        'db_path': 'example_real_estate.db',
        'target_cities': [
            {"name": "Kokomo", "state": "IN"},
            {"name": "Logansport", "state": "IN"}
        ]
    }
    
    print("1. Initializing bot...")
    bot = AdvancedRealEstateBot(config)
    print("   ✓ Bot initialized successfully\n")
    
    # Add example buyers
    print("2. Adding example buyers...")
    
    buyer1 = bot.add_buyer(
        name="John Investor",
        email="john@example.com",
        max_price=150000,
        min_price=50000,
        preferred_areas=["Kokomo", "Logansport"],
        min_bedrooms=2,
        min_bathrooms=1,
        min_sqft=1000,
        property_types=["Foreclosure", "Auction"]
    )
    
    if buyer1:
        print(f"   ✓ Added buyer: {buyer1.name}")
    
    buyer2 = bot.add_buyer(
        name="Jane Developer",
        email="jane@example.com",
        max_price=200000,
        min_price=75000,
        preferred_areas=["Kokomo"],
        min_bedrooms=3,
        min_bathrooms=2,
        min_sqft=1500,
        property_types=["Foreclosure"]
    )
    
    if buyer2:
        print(f"   ✓ Added buyer: {buyer2.name}\n")
    
    # Display buyer information
    print("3. Retrieving all buyers from database...")
    buyers = bot.db.get_all_buyers()
    print(f"   Found {len(buyers)} active buyers:")
    for buyer in buyers:
        print(f"   - {buyer.name} ({buyer.email})")
        print(f"     Budget: ${buyer.min_price:,} - ${buyer.max_price:,}")
        print(f"     Areas: {', '.join(buyer.preferred_areas)}")
    print()
    
    # Example: Adding a manual property for testing
    print("4. Adding example properties for testing...")
    
    example_properties = [
        Property(
            address="123 Main Street, Kokomo, IN 46901",
            price="$125,000",
            link="https://example.com/property/1",
            date="2025-01-19",
            property_type="Foreclosure",
            bedrooms="3 bd",
            bathrooms="2 ba",
            sqft="1,500 sqft",
            year_built="1985",
            source="Example",
            city="Kokomo",
            state="IN"
        ),
        Property(
            address="456 Oak Avenue, Logansport, IN 46947",
            price="$95,000",
            link="https://example.com/property/2",
            date="2025-01-19",
            property_type="Auction",
            bedrooms="2 bd",
            bathrooms="1 ba",
            sqft="1,200 sqft",
            year_built="1978",
            source="Example",
            city="Logansport",
            state="IN"
        ),
        Property(
            address="789 Elm Drive, Kokomo, IN 46902",
            price="$175,000",
            link="https://example.com/property/3",
            date="2025-01-19",
            property_type="Foreclosure",
            bedrooms="4 bd",
            bathrooms="2.5 ba",
            sqft="2,000 sqft",
            year_built="2005",
            source="Example",
            city="Kokomo",
            state="IN"
        )
    ]
    
    for prop in example_properties:
        bot.db.save_property(prop)
        print(f"   ✓ Added: {prop.address} - {prop.price}")
    print()
    
    # Match properties to buyers
    print("5. Matching properties to buyers...")
    matches = bot.match_properties_to_buyers()
    
    print(f"   Found matches for {len(matches)} buyers:")
    for buyer_id, property_matches in matches.items():
        buyer = next((b for b in buyers if b.buyer_id == buyer_id), None)
        if buyer:
            print(f"\n   {buyer.name}:")
            for prop, score in property_matches[:5]:  # Show top 5 matches
                print(f"     • {prop.address}")
                print(f"       Price: {prop.price} | Score: {score}%")
    print()
    
    # Export data
    print("6. Exporting data...")
    csv_file = "example_properties.csv"
    json_file = "example_properties.json"
    
    if bot.export_to_csv(csv_file):
        print(f"   ✓ Exported to CSV: {csv_file}")
    
    if bot.export_to_json(json_file):
        print(f"   ✓ Exported to JSON: {json_file}")
    print()
    
    # Display statistics
    print("7. System Statistics:")
    print("=" * 60)
    properties = bot.db.get_all_properties()
    buyers_list = bot.db.get_all_buyers()
    
    print(f"   Total Properties: {len(properties)}")
    print(f"   Active Buyers: {len(buyers_list)}")
    
    if properties:
        from collections import defaultdict
        sources = defaultdict(int)
        cities = defaultdict(int)
        
        for prop in properties:
            sources[prop.source] += 1
            cities[f"{prop.city}, {prop.state}"] += 1
        
        print("\n   Properties by Source:")
        for source, count in sources.items():
            print(f"     - {source}: {count}")
        
        print("\n   Properties by City:")
        for city, count in sorted(cities.items(), key=lambda x: x[1], reverse=True):
            print(f"     - {city}: {count}")
    
    print("=" * 60)
    print("\n✓ Example completed successfully!")
    print("\nNOTE: This example used manual test data.")
    print("To scrape real properties, use:")
    print("  python advanced_real_estate_wholesaling.py scrape")
    print("\nOr run the full cycle with:")
    print("  python advanced_real_estate_wholesaling.py run")


if __name__ == "__main__":
    main()
