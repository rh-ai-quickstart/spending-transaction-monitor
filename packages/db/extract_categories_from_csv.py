#!/usr/bin/env python3
"""
Extract unique merchant categories from split CSV chunks
Analyzes real transaction data to build comprehensive category mappings
"""

import pandas as pd
import glob
from collections import Counter
import re

def extract_categories_from_chunks():
    """Extract and analyze categories from all CSV chunks"""
    all_categories = []
    chunk_files = glob.glob('../../data/cc_chunk_*')
    
    print(f"🔍 Processing {len(chunk_files)} chunks...")
    
    for i, chunk_file in enumerate(sorted(chunk_files), 1):
        print(f"  [{i}/{len(chunk_files)}] Processing {chunk_file}...")
        
        try:
            # Read chunk - handle potential encoding issues
            df = pd.read_csv(chunk_file, encoding='utf-8', low_memory=False)
            
            # Extract categories (assuming 'category' column exists)
            if 'category' in df.columns:
                categories = df['category'].dropna().unique()
                all_categories.extend(categories)
                print(f"    Found {len(categories)} unique categories in this chunk")
            else:
                print(f"    ⚠️  No 'category' column found in {chunk_file}")
                
        except Exception as e:
            print(f"    ❌ Error processing {chunk_file}: {e}")
            continue
    
    # Count and analyze all categories
    category_counts = Counter(all_categories)
    unique_categories = list(category_counts.keys())
    
    print(f"\n📊 Analysis Results:")
    print(f"   Total category instances: {len(all_categories)}")
    print(f"   Unique categories: {len(unique_categories)}")
    print(f"\n🔝 Top 20 Most Common Categories:")
    
    for category, count in category_counts.most_common(20):
        print(f"   {category:<25} {count:>8,} transactions")
    
    print(f"\n📝 All Unique Categories ({len(unique_categories)} total):")
    for category in sorted(unique_categories):
        print(f"   • {category}")
    
    return unique_categories, category_counts

def create_category_mappings(categories):
    """Create canonical category mappings from real data"""
    
    # Group similar categories into canonical ones
    category_mappings = {}
    
    # Pattern-based grouping
    patterns = {
        'dining': [
            r'.*restaurant.*', r'.*food.*', r'.*dining.*', r'.*cafe.*', 
            r'.*coffee.*', r'.*bar.*', r'.*pub.*', r'.*pizza.*',
            r'.*fast.?food.*', r'.*takeout.*', r'.*bakery.*'
        ],
        'grocery': [
            r'.*grocery.*', r'.*supermarket.*', r'.*food.?store.*',
            r'.*market.*', r'.*provisions.*'
        ],
        'fuel': [
            r'.*gas.*', r'.*fuel.*', r'.*petrol.*', r'.*station.*'
        ],
        'retail': [
            r'.*retail.*', r'.*shop.*', r'.*store.*', r'.*mall.*',
            r'.*department.*', r'.*merchandise.*'
        ],
        'transport': [
            r'.*transport.*', r'.*taxi.*', r'.*uber.*', r'.*lyft.*',
            r'.*bus.*', r'.*train.*', r'.*airline.*', r'.*parking.*'
        ],
        'entertainment': [
            r'.*entertainment.*', r'.*movie.*', r'.*cinema.*', r'.*theater.*',
            r'.*concert.*', r'.*music.*', r'.*game.*', r'.*sport.*'
        ]
    }
    
    # Categorize each unique category
    uncategorized = []
    
    for category in categories:
        category_lower = category.lower()
        mapped = False
        
        for canonical, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.match(pattern, category_lower):
                    if canonical not in category_mappings:
                        category_mappings[canonical] = []
                    category_mappings[canonical].append(category.lower())
                    mapped = True
                    break
            if mapped:
                break
        
        if not mapped:
            uncategorized.append(category)
    
    print(f"\n🗂️  Category Mappings Created:")
    for canonical, synonyms in category_mappings.items():
        print(f"   {canonical}: {len(synonyms)} synonyms")
    
    print(f"\n❓ Uncategorized ({len(uncategorized)}):")
    for cat in sorted(uncategorized)[:10]:  # Show first 10
        print(f"   • {cat}")
    if len(uncategorized) > 10:
        print(f"   ... and {len(uncategorized)-10} more")
    
    return category_mappings, uncategorized

def generate_updated_seed_script(category_mappings, uncategorized):
    """Generate updated seed_category_data.py with real data"""
    
    print(f"\n📝 Generating updated category seed data...")
    
    # Add uncategorized as their own canonical categories
    for uncat in uncategorized[:10]:  # Add top 10 uncategorized as canonical
        clean_name = re.sub(r'[^a-zA-Z0-9]', '_', uncat.lower())
        category_mappings[clean_name] = [uncat.lower()]
    
    # Generate the mapping dict for seed script
    mapping_str = "CATEGORY_SYNONYMS = {\n"
    for canonical, synonyms in category_mappings.items():
        mapping_str += f'    "{canonical}": [\n'
        for synonym in sorted(set(synonyms)):  # Remove duplicates
            mapping_str += f'        "{synonym}",\n'
        mapping_str += f'    ],\n'
    mapping_str += "}\n"
    
    print("✅ Updated category mappings ready!")
    print(f"   📊 {len(category_mappings)} canonical categories")
    print(f"   📝 {sum(len(synonyms) for synonyms in category_mappings.values())} total synonyms")
    
    return mapping_str

if __name__ == "__main__":
    print("🚀 Extracting Categories from Transaction Data...")
    
    categories, counts = extract_categories_from_chunks()
    
    if categories:
        mappings, uncategorized = create_category_mappings(categories)
        updated_script = generate_updated_seed_script(mappings, uncategorized)
        
        # Save to file
        with open('real_category_mappings.py', 'w') as f:
            f.write(f"# Generated from real transaction data\n")
            f.write(f"# {len(categories)} unique categories found\n\n")
            f.write(updated_script)
        
        print(f"\n💾 Saved mappings to: real_category_mappings.py")
        print("🔗 Next: Update seed_category_data.py with these real mappings")
    
    else:
        print("❌ No categories found in CSV chunks")
