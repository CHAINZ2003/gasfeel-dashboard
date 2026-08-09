# ============================================================
# TEST SUPABASE CONNECTION
# Run this to confirm Supabase is connecting and returning data.
# Delete this file after testing is complete.
# ============================================================

from supabase import create_client

SUPABASE_URL = "https://mvbcevkxcuexilqqksou.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im12YmNldmt4Y3VleGlscXFrc291Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjczNTc5OCwiZXhwIjoyMDk4MzExNzk4fQ.-3-OijZOipp8-As5obQnmmHQWT9pYNpaxHDIMJ-vXqM"

print("Connecting to Supabase...")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Test 1 — Count orders
print("\n=== TEST 1: Orders table ===")
result = supabase.table("orders").select("id", count="exact").execute()
print(f"Total orders in database: {result.count}")

# Test 2 — Sample 3 orders
print("\n=== TEST 2: Sample orders ===")
result = supabase.table("orders").select(
    "id,created_at,product,status,zone,grand_total"
).limit(3).execute()
for row in result.data:
    print(row)

# Test 3 — Count customers
print("\n=== TEST 3: Customers table ===")
result = supabase.table("customers").select("whatsapp_number", count="exact").execute()
print(f"Total customers: {result.count}")

# Test 4 — Count completed orders
print("\n=== TEST 4: Completed orders only ===")
result = supabase.table("orders").select(
    "id", count="exact"
).eq("status", "completed").execute()
print(f"Completed orders: {result.count}")

# Test 5 — ops_targets
print("\n=== TEST 5: Targets table ===")
result = supabase.table("ops_targets").select("*").limit(3).execute()
print(f"Targets rows found: {len(result.data)}")
for row in result.data:
    print(row)

# Test 6 — Interactions and Agents
print("\n=== TEST 6: Interactions and Agents ===")
result = supabase.table("interactions").select("id", count="exact").execute()
print(f"Total interactions: {result.count}")

result = supabase.table("profiles").select("id", count="exact").execute()
print(f"Total agents: {result.count}")

# Test 7 — Sample interaction to see structure
print("\n=== TEST 7: Sample interaction ===")
result = supabase.table("interactions").select("*").limit(2).execute()
for row in result.data:
    print(row)

# Test 8 — Petrol orders per customer per month from Supabase
print("\n=== TEST 8: Petrol orders count ===")
result = supabase.table("orders").select(
    "id,product,customer_whatsapp,created_at"
).eq("status", "closed").execute()
print(f"Total closed orders: {len(result.data)}")
petrol = [r for r in result.data if r.get("product") == "petrol"]
print(f"Petrol orders: {len(petrol)}")
gas = [r for r in result.data if r.get("product") == "gas"]
print(f"Gas orders: {len(gas)}")



print("\n=== ALL TESTS COMPLETE ===")


