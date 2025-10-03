#!/usr/bin/env python3
"""
Category Seed Data Script
Creates synonym mappings and canonical categories for merchant category normalization.
"""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from db import get_db
from db.models import MerchantCategorySynonym, MerchantCategoryEmbedding


# Enhanced category synonym mapping based on:
# 1. REAL transaction data from data/credit_card_transactions.csv
# 2. Extended with natural language synonyms and MCC codes
# 3. User-friendly variations for semantic search
CATEGORY_SYNONYMS = {
    # === DINING & FOOD === (from real data: food_dining)
    "dining": [
        "food_dining", "dining", "food", "restaurant", "restaurants", "food & dining", 
        "eateries", "cafe", "cafes", "coffee", "coffee shop", "bakery", 
        "fast food", "takeout", "delivery", "catering", "bar", "bars",
        "pub", "pubs", "diner", "diners", "bistro", "grill", "pizza",
        "sushi", "chinese", "mexican", "italian", "thai", "indian",
        "5812", "5813", "5814"  # MCC codes for restaurants
    ],
    
    # === GROCERY & FOOD RETAIL === (from real data: grocery_pos, grocery_net)
    "grocery": [
        "grocery_pos", "grocery_net", "grocery", "groceries", "supermarket", 
        "food store", "market", "whole foods", "safeway", "kroger", 
        "costco", "food shopping", "provisions", "5411", "5499"  # MCC codes
    ],
    
    # === RETAIL & SHOPPING === (from real data: shopping_pos, shopping_net)
    "retail": [
        "shopping_pos", "shopping_net", "retail", "shopping", "store", 
        "department store", "mall", "amazon", "target", "walmart", 
        "merchandise", "apparel", "clothing", "fashion", "shoes", 
        "accessories", "5300", "5399"
    ],
    
    # === ENTERTAINMENT === (from real data: entertainment)
    "entertainment": [
        "entertainment", "movies", "cinema", "theater", "concert",
        "music", "games", "gaming", "sports", "tickets", "events",
        "amusement", "recreation", "7832", "7841", "7922", "7929"
    ],
    
    # === GAS & FUEL === (from real data: gas_transport)
    "fuel": [
        "gas_transport", "gas", "fuel", "gasoline", "gas station", "petrol", 
        "shell", "chevron", "exxon", "bp", "mobil", "texaco", "5541", "5542"
    ],
    
    # === HEALTH & FITNESS === (from real data: health_fitness)
    "health_fitness": [
        "health_fitness", "healthcare", "medical", "fitness", "gym", 
        "workout", "health", "doctor", "hospital", "pharmacy", "medicine", 
        "dental", "clinic", "cvs", "walgreens", "prescription", 
        "8011", "8021", "8031", "8041", "5912"
    ],
    
    # === PERSONAL CARE === (from real data: personal_care)
    "personal_care": [
        "personal_care", "beauty", "cosmetics", "salon", "spa", "haircut", 
        "barber", "skincare", "makeup", "hygiene", "grooming", "7230", "7298"
    ],
    
    # === TRAVEL === (from real data: travel)
    "travel": [
        "travel", "transportation", "transport", "uber", "lyft", "taxi", "cab",
        "bus", "train", "subway", "metro", "airline", "flight", "parking", 
        "toll", "hotel", "hotels", "motel", "accommodation", "stay",
        "marriott", "hilton", "hyatt", "booking", "airbnb", "vacation",
        "resort", "inn", "4111", "4121", "4131", "7511", "3501", "3502"
    ],
    
    # === HOME & HOUSEHOLD === (from real data: home)
    "home": [
        "home", "household", "garden", "hardware", "tools", "furniture", 
        "appliances", "home depot", "lowes", "ikea", "home improvement", 
        "renovation", "utilities", "electric", "electricity", "water", 
        "internet", "phone", "cable", "utility", "bill", "5200", "5211", 
        "5712", "5713", "5714", "5718", "4900", "4814", "4816"
    ],
    
    # === KIDS & PETS === (from real data: kids_pets)
    "kids_pets": [
        "kids_pets", "children", "kids", "baby", "toys", "pets", "pet store", 
        "veterinary", "vet", "pet food", "pet supplies", "daycare", 
        "school supplies", "education", "tuition", "5641", "0742", "8220"
    ],
    
    # === MISCELLANEOUS ONLINE === (from real data: misc_net)
    "misc_net": [
        "misc_net", "online", "digital", "software", "cloud services", 
        "saas", "subscription", "netflix", "spotify", "adobe", "microsoft", 
        "google", "aws", "azure", "github", "slack", "zoom", "dropbox", 
        "app store", "digital services", "5815", "7372"
    ],
    
    # === MISCELLANEOUS POS === (from real data: misc_pos)
    "misc_pos": [
        "misc_pos", "miscellaneous", "various", "general", "other", 
        "point of sale", "retail misc", "services", "professional", 
        "business", "office", "consulting", "7299", "7399"
    ]
}


async def clear_existing_data(session: AsyncSession) -> None:
    """Clear existing category data for clean seeding"""
    print("🧹 Clearing existing category synonym data...")
    
    # Clear synonyms
    await session.execute(delete(MerchantCategorySynonym))
    
    # Clear embeddings (will be repopulated by separate script)
    await session.execute(delete(MerchantCategoryEmbedding))
    
    await session.commit()
    print("✅ Cleared existing data")


async def seed_synonyms(session: AsyncSession) -> None:
    """Seed the merchant_category_synonyms table"""
    print("🌱 Seeding category synonyms...")
    
    synonym_count = 0
    
    for canonical_category, synonyms in CATEGORY_SYNONYMS.items():
        for synonym in synonyms:
            # Create synonym mapping (including self-reference)
            synonym_obj = MerchantCategorySynonym(
                synonym=synonym.lower(),
                canonical_category=canonical_category
            )
            session.add(synonym_obj)
            synonym_count += 1
    
    await session.commit()
    print(f"✅ Seeded {synonym_count} category synonyms for {len(CATEGORY_SYNONYMS)} canonical categories")


async def validate_seed_data(session: AsyncSession) -> None:
    """Validate that data was seeded correctly"""
    print("🔍 Validating seed data...")
    
    # Count total synonyms
    result = await session.execute(select(MerchantCategorySynonym))
    synonyms = result.scalars().all()
    
    print(f"✅ Found {len(synonyms)} synonyms in database")
    
    # Test a few lookups
    test_cases = [
        ("restaurant", "dining"),
        ("gas", "fuel"), 
        ("amazon", "retail"),
        ("hotel", "lodging"),
        ("5812", "dining")  # MCC code
    ]
    
    for test_synonym, expected_category in test_cases:
        result = await session.execute(
            select(MerchantCategorySynonym.canonical_category)
            .where(MerchantCategorySynonym.synonym == test_synonym.lower())
        )
        found_category = result.scalar()
        
        if found_category == expected_category:
            print(f"✅ '{test_synonym}' → '{found_category}' ✓")
        else:
            print(f"❌ '{test_synonym}' → expected '{expected_category}', got '{found_category}'")


async def main():
    """Main seeding function"""
    print("🚀 Starting Category Data Seeding...")
    print(f"📊 Will create {sum(len(synonyms) for synonyms in CATEGORY_SYNONYMS.values())} synonym mappings")
    print(f"📂 Across {len(CATEGORY_SYNONYMS)} canonical categories")
    
    # Get async database session  
    db_gen = get_db()
    session = await db_gen.__anext__()
    
    try:
        await clear_existing_data(session)
        await seed_synonyms(session) 
        await validate_seed_data(session)
    finally:
        await session.close()
    
    print("🎉 Category seeding completed successfully!")
    print()
    print("📋 Canonical Categories Created:")
    for category in sorted(CATEGORY_SYNONYMS.keys()):
        print(f"  • {category}")
    print()
    print("🔗 Next steps:")
    print("  1. Run: pnpm populate:embeddings")
    print("  2. Test normalization with existing transactions")


if __name__ == "__main__":
    asyncio.run(main())
