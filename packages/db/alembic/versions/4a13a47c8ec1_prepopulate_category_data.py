"""prepopulate_category_data

Revision ID: 4a13a47c8ec1
Revises: eb7dc605eb0f
Create Date: 2025-09-26 10:44:26.971729

This migration prepopulates the merchant category synonym table with 
comprehensive category mappings for semantic search functionality.
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision = '4a13a47c8ec1'
down_revision = 'merge_all_heads_final'
branch_labels = None
depends_on = None


# Category synonym data (extracted from seed_category_data.py)
CATEGORY_SYNONYMS = {
    "dining": [
        "dining", "food", "restaurant", "restaurants", "food & dining", 
        "eateries", "cafe", "cafes", "coffee", "coffee shop", "bakery", 
        "fast food", "takeout", "delivery", "catering", "bar", "bars",
        "pub", "pubs", "diner", "diners", "bistro", "grill", "pizza",
        "sushi", "chinese", "mexican", "italian", "thai", "indian",
        "5812", "5813", "5814"  # MCC codes for restaurants
    ],
    "grocery": [
        "grocery", "groceries", "supermarket", "food store", "market",
        "whole foods", "safeway", "kroger", "walmart", "costco",
        "food shopping", "provisions", "5411", "5499"  # MCC codes
    ],
    "electronics": [
        "electronics", "technology", "tech", "computer", "computers",
        "laptop", "phone", "mobile", "smartphone", "tablet", "ipad",
        "apple", "microsoft", "software", "hardware", "gadgets",
        "best buy", "apple store", "5732", "5734"  # MCC codes
    ],
    "software": [
        "software", "cloud services", "saas", "subscription", "netflix",
        "spotify", "adobe", "microsoft", "google", "amazon web services",
        "aws", "azure", "github", "slack", "zoom", "dropbox", "stripe",
        "app store", "digital services", "online services", "5815", "7372"
    ],
    "retail": [
        "retail", "shopping", "store", "department store", "mall",
        "amazon", "target", "walmart", "merchandise", "apparel",
        "clothing", "fashion", "shoes", "accessories", "5300", "5399"
    ],
    "fuel": [
        "gas", "fuel", "gasoline", "gas station", "petrol", "shell",
        "chevron", "exxon", "bp", "mobil", "texaco", "5541", "5542"
    ],
    "transport": [
        "transportation", "transport", "uber", "lyft", "taxi", "cab",
        "bus", "train", "subway", "metro", "airline", "flight",
        "parking", "toll", "4111", "4121", "4131", "7511"
    ],
    "lodging": [
        "lodging", "hotel", "hotels", "motel", "accommodation", "stay",
        "marriott", "hilton", "hyatt", "booking", "airbnb", "vacation",
        "resort", "inn", "3501", "3502", "3503", "7011"
    ],
    "healthcare": [
        "healthcare", "medical", "doctor", "hospital", "pharmacy",
        "medicine", "health", "dental", "clinic", "cvs", "walgreens",
        "prescription", "8011", "8021", "8031", "8041", "5912"
    ],
    "financial": [
        "financial", "bank", "banking", "atm", "wire transfer", 
        "transfer", "payment", "paypal", "venmo", "fee", "interest",
        "loan", "mortgage", "insurance", "6010", "6011", "6012"
    ],
    "business": [
        "business", "office", "professional", "consulting", "legal",
        "accounting", "marketing", "advertising", "printing", "supplies",
        "office depot", "staples", "fedex", "ups", "7338", "7339"
    ],
    "entertainment": [
        "entertainment", "movies", "cinema", "theater", "concert",
        "music", "games", "gaming", "sports", "tickets", "events",
        "amusement", "recreation", "7832", "7841", "7922", "7929"
    ],
    "automotive": [
        "automotive", "car", "auto", "vehicle", "repair", "maintenance",
        "parts", "service", "mechanic", "oil change", "tires",
        "car wash", "5533", "5541", "7531", "7534", "7535"
    ],
    "education": [
        "education", "school", "college", "university", "tuition",
        "books", "supplies", "learning", "course", "training",
        "8220", "8244", "8249", "8299"
    ],
    "home_garden": [
        "home", "garden", "hardware", "tools", "furniture", "appliances",
        "home depot", "lowes", "ikea", "home improvement", "renovation",
        "5200", "5211", "5712", "5713", "5714", "5718"
    ],
    "utilities": [
        "utilities", "electric", "electricity", "gas", "water", "internet",
        "phone", "cable", "utility", "bill", "4900", "4814", "4816"
    ]
}


def upgrade() -> None:
    """Populate merchant category synonym table - moved to script"""
    # Data population moved to seed_category_data.py script
    print("✅ Category data should be populated using: pnpm seed:categories")
    pass


def downgrade() -> None:
    """Remove category synonym data"""
    connection = op.get_bind()
    
    # Clear all synonym data
    connection.execute(sa.text("DELETE FROM merchant_category_synonyms"))
    
    print("🧹 Removed all category synonym data")
