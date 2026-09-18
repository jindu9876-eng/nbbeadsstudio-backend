import asyncio
import os
import sys

# Ensure parent dir in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import init_db
from backend.models.admin import Admin
from backend.models.product import Product
from backend.models.category import Category
from backend.models.order import Order
from backend.models.user import User
from backend.utils.bulk_import import generate_csv_template, generate_excel_template, validate_bulk_file, execute_bulk_import
from backend.utils.security import verify_password, create_access_token

async def test_admin_suite():
    print("=== STARTING BACKEND ADMIN SUITE TESTS ===")
    
    # 1. Init DB & Seeding
    await init_db()
    print("[PASS] Database and Beanie ODM initialized.")
    
    # 2. Verify Admin Exists
    admin = await Admin.find_one(Admin.username == "admin")
    assert admin is not None, "Admin user 'admin' not found!"
    assert verify_password("admin123", admin.password_hash), "Admin password verification failed!"
    print(f"[PASS] Admin found: {admin.username} ({admin.email}) with valid password hash.")
    
    # 3. Create Admin JWT
    token = create_access_token({"sub": str(admin.id), "role": "admin"})
    assert token, "Failed to create access token"
    print("[PASS] Admin JWT generated successfully.")
    
    # 4. Product CRUD & Duplicate & Archive
    test_sku = "TEST-SUITE-001"
    existing = await Product.find_one(Product.sku == test_sku)
    if existing:
        await existing.delete()
        
    p = Product(
        name="Test Suite Diamond Pendant",
        slug="test-suite-diamond-pendant",
        category="Jewellery",
        mrp=999.0,
        sale_price=799.0,
        stock=15,
        sku=test_sku,
        description="A test product created by the test suite",
        tags=["test", "suite", "diamond"],
        status="active"
    )
    p.calculate_discount()
    await p.insert()
    print(f"[PASS] Product created with discount: {p.discount_percent}%")
    
    # Duplicate
    dup_sku = f"{test_sku}-COPY"
    dup = Product(
        name=f"{p.name} (Copy)",
        slug=f"{p.slug}-copy",
        category=p.category,
        mrp=p.mrp,
        sale_price=p.sale_price,
        stock=p.stock,
        sku=dup_sku,
        status="inactive",
        description=p.description
    )
    await dup.insert()
    assert await Product.find_one(Product.sku == dup_sku) is not None
    print("[PASS] Product duplicate verified.")
    
    # Archive
    p.status = "archived"
    await p.save()
    refreshed = await Product.get(p.id)
    assert refreshed.status == "archived", "Product archive failed"
    print("[PASS] Product archive status verified.")
    
    # Clean up test products
    await p.delete()
    await dup.delete()
    print("[PASS] Product cleanup verified.")
    
    # 5. Bulk Template Generation
    csv_bytes = generate_csv_template()
    assert len(csv_bytes) > 100, "CSV template generated empty"
    print(f"[PASS] CSV template generated: {len(csv_bytes)} bytes.")
    
    xlsx_bytes = generate_excel_template()
    assert len(xlsx_bytes) > 1000, "Excel template generated empty"
    print(f"[PASS] Excel template generated: {len(xlsx_bytes)} bytes.")
    
    # 6. Bulk Validation Test
    validation_report = await validate_bulk_file(csv_bytes, "template.csv")
    assert validation_report["total_rows"] >= 3, "Expected at least 3 rows in template"
    print(f"[PASS] Bulk file validation passed: {validation_report['valid_count']} valid out of {validation_report['total_rows']} rows.")
    
    # 7. Bulk Import Execution Test
    sample_import_rows = [
        {
            "row_index": 1,
            "status": "valid",
            "data": {
                "name": "Suite Emerald Ring",
                "sku": "SUITE-EMR-999",
                "category": "Jewellery",
                "mrp": 1200.0,
                "sale_price": 950.0,
                "stock": 8,
                "description": "Emerald ring for testing bulk import",
                "status": "active"
            }
        }
    ]
    # Ensure not existing beforehand
    old_prod = await Product.find_one(Product.sku == "SUITE-EMR-999")
    if old_prod:
        await old_prod.delete()
        
    res = await execute_bulk_import(sample_import_rows, duplicate_action="skip", upload_images_to_cloudinary=False)
    assert res["imported_count"] == 1, "Failed to import row via execute_bulk_import"
    print("[PASS] Bulk import execution verified (1 imported).")
    
    # Test Duplicate Update
    res_update = await execute_bulk_import(sample_import_rows, duplicate_action="update", upload_images_to_cloudinary=False)
    assert res_update["updated_count"] == 1, "Failed to update duplicate via execute_bulk_import"
    print("[PASS] Duplicate SKU update strategy verified (1 updated).")
    
    # Clean up
    created_prod = await Product.find_one(Product.sku == "SUITE-EMR-999")
    if created_prod:
        await created_prod.delete()
        
    print("=== ALL 7 BACKEND TEST SUITES PASSED WITH 100% SUCCESS ===")

if __name__ == "__main__":
    asyncio.run(test_admin_suite())
