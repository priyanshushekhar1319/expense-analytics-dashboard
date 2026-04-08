import csv
import random
from faker import Faker
from datetime import datetime, timedelta

fake = Faker()

NUM_RECORDS = 55000
OUTPUT_FILE = "raw_transactions.csv"

# Expense Categories
CATEGORIES = [
    "Groceries", "Rent", "Utilities", "Entertainment", "Travel", 
    "Dining", "Healthcare", "Transportation", "Shopping", "Miscellaneous"
]

MERCHANTS = [
    "Walmart", "Whole Foods", "Amazon", "Netflix", "Uber", "Lyft", 
    "Shell", "Target", "Starbucks", "Delta Airlines", "Airbnb", 
    "PG&E", "Comcast", "Local Landlord Co.", "CVS Pharmacy",
    "Home Depot", "Best Buy", "Spotify", "Gym Membership", "Apple Store"
]

def generate_messy_date(start_date, end_date):
    """Generates a date with a 5% chance of being in inconsistent format."""
    delta = end_date - start_date
    random_days = random.randrange(delta.days)
    dt = start_date + timedelta(days=random_days)
    
    if random.random() < 0.05:
        # Messy format
        return dt.strftime("%m/%d/%Y")
    return dt.strftime("%Y-%m-%d")

def generate_messy_amount():
    """Generates an amount, with 2% chance of being string 'N/A' or negative."""
    if random.random() < 0.01:
        return "N/A"
    if random.random() < 0.01:
        return round(random.uniform(-500.0, -1.0), 2)
    return round(random.uniform(5.0, 3000.0), 2)

def generate_messy_category():
    """Generates a category, with 3% chance of being empty or null."""
    if random.random() < 0.03:
        return random.choice(["", "NULL", None])
    return random.choice(CATEGORIES)

def generate_messy_merchant():
    """Returns a merchant with potential trailing spaces or typos (mocking messy text)."""
    merchant = random.choice(MERCHANTS)
    if random.random() < 0.05:
        return merchant.lower() + "  " # Lowercase and trailing spaces
    return merchant

def main():
    print(f"Generating {NUM_RECORDS} raw transaction records...")
    start_date = datetime(2022, 1, 1)
    end_date = datetime(2024, 12, 31)

    with open(OUTPUT_FILE, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["transaction_id", "date", "amount", "merchant", "category", "description", "status"])
        
        for i in range(1, NUM_RECORDS + 1):
            txn_id = f"TXN-{100000 + i}"
            
            # Introduce duplicates (1% chance to write the same transaction again)
            is_duplicate = random.random() < 0.01
            
            row = [
                txn_id,
                generate_messy_date(start_date, end_date),
                generate_messy_amount(),
                generate_messy_merchant(),
                generate_messy_category(),
                fake.sentence(nb_words=4) if random.random() > 0.1 else "",
                random.choices(["Completed", "Pending", "Failed"], weights=[0.85, 0.10, 0.05])[0]
            ]
            
            writer.writerow(row)
            if is_duplicate:
                writer.writerow(row) # Write identical row to simulate duplicate entry
                
    print(f"Successfully generated dataset at {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
