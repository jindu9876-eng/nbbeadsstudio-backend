import csv
import io
import re
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from backend.models.product import Product
from backend.models.category import Category
from backend.utils.cloudinary_service import upload_image_from_url, is_cloudinary_configured

# Standard column definition
TEMPLATE_COLUMNS = [
    {"key": "name", "title": "Product Name*", "required": True, "type": "string", "example": "Diamond Solitaire Ring"},
    {"key": "sku", "title": "SKU*", "required": True, "type": "string", "example": "JW-DSR-101"},
    {"key": "category", "title": "Category*", "required": True, "type": "string", "example": "Jewellery"},
    {"key": "subcategory", "title": "Subcategory", "required": False, "type": "string", "example": "Rings"},
    {"key": "brand", "title": "Brand", "required": False, "type": "string", "example": "NB BEADS STUDIO Collection"},
    {"key": "mrp", "title": "MRP (Original Price)*", "required": True, "type": "float", "example": 1499.00},
    {"key": "sale_price", "title": "Sale Price*", "required": True, "type": "float", "example": 1299.00},
    {"key": "stock", "title": "Stock Quantity*", "required": True, "type": "int", "example": 25},
    {"key": "description", "title": "Description", "required": False, "type": "string", "example": "Handcrafted diamond solitaire ring set in 18k solid gold."},
    {"key": "short_description", "title": "Short Description", "required": False, "type": "string", "example": "Timeless 18k gold diamond solitaire ring."},
    {"key": "tags", "title": "Tags (comma separated)", "required": False, "type": "string", "example": "ring, diamond, gold, luxury"},
    {"key": "color", "title": "Color", "required": False, "type": "string", "example": "Gold"},
    {"key": "size", "title": "Size", "required": False, "type": "string", "example": "7"},
    {"key": "thumbnail_url", "title": "Thumbnail Image URL", "required": False, "type": "string", "example": "https://images.unsplash.com/photo-1739591414031-edd27896c8bf"},
    {"key": "gallery_image_urls", "title": "Gallery Image URLs (comma separated)", "required": False, "type": "string", "example": "https://images.unsplash.com/photo-1758995115560-59c10d6cc28f, https://images.unsplash.com/photo-1767210338407-54b9264c326b"},
    {"key": "status", "title": "Status (active/inactive/archived)", "required": False, "type": "string", "example": "active"},
    {"key": "featured", "title": "Featured (TRUE/FALSE)", "required": False, "type": "bool", "example": "TRUE"},
    {"key": "trending", "title": "Trending (TRUE/FALSE)", "required": False, "type": "bool", "example": "FALSE"},
    {"key": "best_seller", "title": "Best Seller (TRUE/FALSE)", "required": False, "type": "bool", "example": "TRUE"},
    {"key": "meta_title", "title": "SEO Meta Title", "required": False, "type": "string", "example": "Buy Diamond Solitaire Ring - NB BEADS STUDIO"},
    {"key": "meta_description", "title": "SEO Meta Description", "required": False, "type": "string", "example": "Discover luxury diamond solitaire rings crafted with precision."}
]

SAMPLE_ROWS = [
    {
        "name": "Diamond Solitaire Ring",
        "sku": "JW-DSR-101",
        "category": "Jewellery",
        "subcategory": "Rings",
        "brand": "NB BEADS STUDIO Fine",
        "mrp": 1499.00,
        "sale_price": 1299.00,
        "stock": 25,
        "description": "Handcrafted diamond solitaire ring set in 18k solid gold.",
        "short_description": "Timeless 18k gold diamond solitaire ring.",
        "tags": "ring, diamond, gold, luxury",
        "color": "Yellow Gold",
        "size": "7",
        "thumbnail_url": "https://images.unsplash.com/photo-1739591414031-edd27896c8bf?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080",
        "gallery_image_urls": "https://images.unsplash.com/photo-1758995115560-59c10d6cc28f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080",
        "status": "active",
        "featured": "TRUE",
        "trending": "FALSE",
        "best_seller": "TRUE",
        "meta_title": "Diamond Solitaire Ring - Fine Jewellery",
        "meta_description": "Shop fine diamond solitaire rings in 18k gold."
    },
    {
        "name": "Boho Macrame Wall Hanging",
        "sku": "MC-MWH-202",
        "category": "Macrame",
        "subcategory": "Wall Hangings",
        "brand": "NB BEADS STUDIO Home",
        "mrp": 350.00,
        "sale_price": 280.00,
        "stock": 40,
        "description": "Artisan woven cotton macrame wall hanging with wooden rod.",
        "short_description": "Boho chic handcrafted macrame art.",
        "tags": "macrame, boho, wall decor, home",
        "color": "Ivory",
        "size": "Medium",
        "thumbnail_url": "https://images.unsplash.com/photo-1632393121391-3c40fcfafe1a?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080",
        "gallery_image_urls": "",
        "status": "active",
        "featured": "FALSE",
        "trending": "TRUE",
        "best_seller": "FALSE",
        "meta_title": "Handcrafted Macrame Wall Hanging",
        "meta_description": "Bring bohemian elegance into your space with macrame."
    },
    {
        "name": "Matching Couple Pendant Set",
        "sku": "CP-MPS-303",
        "category": "Couple Things",
        "subcategory": "Pendants",
        "brand": "NB BEADS STUDIO Bond",
        "mrp": 199.00,
        "sale_price": 149.00,
        "stock": 50,
        "description": "Magnetic interlocking heart pendant necklaces for couples.",
        "short_description": "Interlocking couple pendant set in silver.",
        "tags": "couple, gift, love, pendant",
        "color": "Silver / Black",
        "size": "Adjustable",
        "thumbnail_url": "https://images.unsplash.com/photo-1517037126752-acf49bfda61a?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080",
        "gallery_image_urls": "",
        "status": "active",
        "featured": "TRUE",
        "trending": "TRUE",
        "best_seller": "TRUE",
        "meta_title": "Matching Couple Pendant Set - NB BEADS STUDIO",
        "meta_description": "Celebrate your love with romantic matching couple pendants."
    }
]

def generate_csv_template() -> bytes:
    """Generates a UTF-8 CSV template with sample data."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    headers = [col["key"] for col in TEMPLATE_COLUMNS]
    writer.writerow(headers)
    
    # Sample rows
    for sample in SAMPLE_ROWS:
        row = [sample.get(col["key"], "") for col in TEMPLATE_COLUMNS]
        writer.writerow(row)
        
    return output.getvalue().encode("utf-8-sig")


def generate_excel_template() -> bytes:
    """Generates a formatted Excel (.xlsx) template with styles and instructions."""
    wb = openpyxl.Workbook()
    
    # Sheet 1: Products Template
    ws = wb.active
    ws.title = "Products Template"
    
    # Header styling
    header_fill = PatternFill(start_color="1F2937", end_color="1F2937", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    required_font = Font(name="Calibri", size=11, bold=True, color="FBBF24")
    border_side = Side(border_style="thin", color="D1D5DB")
    cell_border = Border(left=border_side, right=border_side, top=border_side, bottom=border_side)
    
    # Write header row
    for col_idx, col in enumerate(TEMPLATE_COLUMNS, 1):
        cell = ws.cell(row=1, column=col_idx, value=col["key"])
        cell.fill = header_fill
        cell.font = required_font if col["required"] else header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = cell_border
        
    # Write sample rows
    for row_idx, sample in enumerate(SAMPLE_ROWS, 2):
        for col_idx, col in enumerate(TEMPLATE_COLUMNS, 1):
            val = sample.get(col["key"], "")
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.border = cell_border
            cell.alignment = Alignment(vertical="center")
            
    # Auto-adjust column widths
    for col_idx, col in enumerate(TEMPLATE_COLUMNS, 1):
        max_len = max(len(col["key"]), 12)
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 15)
        
    ws.row_dimensions[1].height = 28
    
    # Sheet 2: Field Descriptions & Instructions
    ws_info = wb.create_sheet(title="Instructions")
    ws_info.column_dimensions["A"].width = 25
    ws_info.column_dimensions["B"].width = 15
    ws_info.column_dimensions["C"].width = 15
    ws_info.column_dimensions["D"].width = 60
    
    info_headers = ["Field Name", "Required?", "Data Type", "Description & Guidelines"]
    for c_idx, h in enumerate(info_headers, 1):
        cell = ws_info.cell(row=1, column=c_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        
    instructions = [
        ("name", "YES", "Text", "The full display title of the product (e.g., 'Diamond Solitaire Ring')."),
        ("sku", "YES", "Text", "Stock Keeping Unit. Must be unique per product (e.g., 'JW-DSR-101')."),
        ("category", "YES", "Text", "Category name (e.g., 'Jewellery', 'Couple Things', 'Macrame', 'Fashion')."),
        ("subcategory", "NO", "Text", "Optional subcategory name (e.g., 'Rings', 'Necklaces', 'Wall Hangings')."),
        ("brand", "NO", "Text", "Brand or collection label."),
        ("mrp", "YES", "Number", "Original price / Maximum Retail Price. Must be >= sale_price and >= 0."),
        ("sale_price", "YES", "Number", "Actual selling price. Must be >= 0."),
        ("stock", "YES", "Integer", "Available quantity in inventory. Must be >= 0."),
        ("description", "NO", "Text", "Full product description supporting details and dimensions."),
        ("short_description", "NO", "Text", "Brief summary displayed in product previews."),
        ("tags", "NO", "Comma separated", "List of tags (e.g. 'diamond, gold, trending')."),
        ("color", "NO", "Text", "Primary color or shade."),
        ("size", "NO", "Text", "Size specifications (e.g., 'Small', '7', 'Adjustable')."),
        ("thumbnail_url", "NO", "URL", "Direct public image URL. If Cloudinary upload is enabled, it is automatically migrated."),
        ("gallery_image_urls", "NO", "URLs", "Comma-separated list of secondary product images."),
        ("status", "NO", "active/inactive/archived", "Defaults to 'active'."),
        ("featured", "NO", "TRUE/FALSE", "Mark TRUE to highlight on homepage."),
        ("trending", "NO", "TRUE/FALSE", "Mark TRUE for trending section."),
        ("best_seller", "NO", "TRUE/FALSE", "Mark TRUE for best-seller badge."),
        ("meta_title", "NO", "Text", "SEO title tag for search engine optimization."),
        ("meta_description", "NO", "Text", "SEO meta description snippet.")
    ]
    
    for r_idx, (fname, req, dtype, desc) in enumerate(instructions, 2):
        ws_info.cell(row=r_idx, column=1, value=fname).font = Font(bold=True)
        ws_info.cell(row=r_idx, column=2, value=req).font = Font(color="DC2626" if req == "YES" else "4B5563", bold=req=="YES")
        ws_info.cell(row=r_idx, column=3, value=dtype)
        ws_info.cell(row=r_idx, column=4, value=desc)
        
    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


def parse_raw_file(file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
    """Parses raw CSV or Excel bytes into a list of normalized row dictionaries."""
    filename_lower = filename.lower()
    rows: List[Dict[str, Any]] = []
    
    if filename_lower.endswith(".csv"):
        # Try UTF-8 with BOM or plain UTF-8
        try:
            text = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1")
            
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            # Clean up keys (strip whitespace, convert to lowercase)
            cleaned_row = {
                k.strip().lower().replace(" ", "_").replace("*", ""): (v.strip() if isinstance(v, str) else v)
                for k, v in row.items() if k
            }
            if any(cleaned_row.values()): # Ignore blank rows
                rows.append(cleaned_row)
                
    elif filename_lower.endswith((".xlsx", ".xls")):
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        ws = wb.active
        
        headers = []
        for cell in ws[1]:
            val = str(cell.value or "").strip().lower().replace(" ", "_").replace("*", "")
            headers.append(val)
            
        for row_cells in ws.iter_rows(min_row=2, values_only=True):
            if not any(row_cells):
                continue
            row_dict = {}
            for col_idx, cell_value in enumerate(row_cells):
                if col_idx < len(headers) and headers[col_idx]:
                    val = cell_value
                    if isinstance(val, str):
                        val = val.strip()
                    row_dict[headers[col_idx]] = val
            if any(row_dict.values()):
                rows.append(row_dict)
    else:
        raise ValueError("Unsupported file format. Please upload a .csv or .xlsx file.")
        
    return rows


async def validate_bulk_file(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Validates every row of the bulk import file against required rules, data types,
    and database state (existing SKUs).
    """
    raw_rows = parse_raw_file(file_bytes, filename)
    
    if not raw_rows:
        return {
            "total_rows": 0,
            "valid_count": 0,
            "warning_count": 0,
            "error_count": 0,
            "existing_sku_count": 0,
            "rows": [],
            "error_summary": ["Uploaded file is empty or contains no data rows."]
        }
        
    validated_rows = []
    seen_skus = {}
    valid_count = 0
    warning_count = 0
    error_count = 0
    existing_sku_count = 0
    
    # Pre-fetch existing categories for validation
    categories = await Category.find_all().to_list()
    category_names = {c.name.lower(): c.name for c in categories}
    
    # Pre-fetch existing SKUs in MongoDB
    db_products = await Product.find_all().to_list()
    db_skus = {p.sku.upper(): p.name for p in db_products}
    
    for idx, raw in enumerate(raw_rows, 1):
        row_errors = []
        row_warnings = []
        
        # 1. Product Name
        name = str(raw.get("name") or raw.get("product_name") or "").strip()
        if not name:
            row_errors.append("Product name is required.")
            
        # 2. SKU
        sku = str(raw.get("sku") or "").strip().upper()
        is_duplicate_db = False
        if not sku:
            row_errors.append("SKU is required.")
        else:
            if sku in seen_skus:
                row_errors.append(f"Duplicate SKU '{sku}' inside the uploaded file (already in row {seen_skus[sku]}).")
            else:
                seen_skus[sku] = idx
                
            if sku in db_skus:
                is_duplicate_db = True
                existing_sku_count += 1
                row_warnings.append(f"SKU '{sku}' already exists in store database ('{db_skus[sku]}').")
                
        # 3. Category
        cat = str(raw.get("category") or "").strip()
        if not cat:
            row_errors.append("Category is required.")
        elif cat.lower() not in category_names:
            row_warnings.append(f"Category '{cat}' is not currently in database (it will be created automatically).")
            
        # 4. MRP & Sale Price
        mrp_raw = raw.get("mrp") or raw.get("mrp_(original_price)")
        sale_price_raw = raw.get("sale_price")
        
        mrp = 0.0
        try:
            mrp = float(mrp_raw)
            if mrp < 0:
                row_errors.append("MRP cannot be negative.")
        except (ValueError, TypeError):
            row_errors.append("MRP must be a valid positive number.")
            
        sale_price = 0.0
        try:
            sale_price = float(sale_price_raw)
            if sale_price < 0:
                row_errors.append("Sale price cannot be negative.")
        except (ValueError, TypeError):
            row_errors.append("Sale price must be a valid positive number.")
            
        if mrp > 0 and sale_price > 0 and sale_price > mrp:
            row_warnings.append(f"Sale price (${sale_price}) is greater than MRP (${mrp}).")
            
        # 5. Stock
        stock_raw = raw.get("stock") or raw.get("stock_quantity")
        stock = 0
        try:
            stock = int(float(stock_raw))
            if stock < 0:
                row_errors.append("Stock quantity cannot be negative.")
        except (ValueError, TypeError):
            row_errors.append("Stock quantity must be a valid whole number.")
            
        # 6. Status
        status_val = str(raw.get("status") or "active").strip().lower()
        if status_val not in ["active", "inactive", "archived"]:
            status_val = "active"
            
        # 7. Flags
        def parse_bool(val: Any) -> bool:
            if isinstance(val, bool):
                return val
            s = str(val or "").strip().lower()
            return s in ["true", "1", "yes", "y"]
            
        featured = parse_bool(raw.get("featured"))
        trending = parse_bool(raw.get("trending"))
        best_seller = parse_bool(raw.get("best_seller"))
        
        # 8. Tags
        tags_raw = raw.get("tags") or ""
        tags = [t.strip() for t in str(tags_raw).split(",") if t.strip()]
        
        # 9. Gallery Images
        gallery_raw = raw.get("gallery_image_urls") or ""
        gallery_images = [img.strip() for img in str(gallery_raw).split(",") if img.strip()]
        
        # Row status determination
        if row_errors:
            row_status = "error"
            error_count += 1
        elif row_warnings:
            row_status = "warning"
            warning_count += 1
        else:
            row_status = "valid"
            valid_count += 1
            
        validated_rows.append({
            "row_index": idx,
            "status": row_status,
            "errors": row_errors,
            "warnings": row_warnings,
            "is_duplicate_db": is_duplicate_db,
            "data": {
                "name": name,
                "sku": sku,
                "category": cat,
                "subcategory": str(raw.get("subcategory") or "").strip() or None,
                "brand": str(raw.get("brand") or "").strip() or None,
                "mrp": mrp,
                "sale_price": sale_price,
                "stock": stock,
                "description": str(raw.get("description") or "").strip(),
                "short_description": str(raw.get("short_description") or "").strip() or None,
                "tags": tags,
                "color": str(raw.get("color") or "").strip() or None,
                "size": str(raw.get("size") or "").strip() or None,
                "thumbnail_url": str(raw.get("thumbnail_url") or "").strip() or None,
                "gallery_image_urls": gallery_images,
                "status": status_val,
                "featured": featured,
                "trending": trending,
                "best_seller": best_seller,
                "meta_title": str(raw.get("meta_title") or "").strip() or None,
                "meta_description": str(raw.get("meta_description") or "").strip() or None
            }
        })
        
    return {
        "total_rows": len(raw_rows),
        "valid_count": valid_count,
        "warning_count": warning_count,
        "error_count": error_count,
        "existing_sku_count": existing_sku_count,
        "rows": validated_rows
    }


async def execute_bulk_import(
    rows: List[Dict[str, Any]],
    duplicate_action: str = "skip", # "skip", "update", "reject"
    upload_images_to_cloudinary: bool = False
) -> Dict[str, Any]:
    """
    Executes the bulk import process given validated row items.
    Handles duplicate SKUs according to duplicate_action,
    and optionally uploads remote image URLs to Cloudinary.
    """
    imported_count = 0
    updated_count = 0
    skipped_count = 0
    failed_count = 0
    error_logs = []
    
    # Check if reject mode is requested and any duplicate exists
    if duplicate_action == "reject":
        for item in rows:
            data = item.get("data", item)
            sku = data.get("sku", "").upper()
            existing = await Product.find_one(Product.sku == sku)
            if existing:
                return {
                    "success": False,
                    "message": f"Bulk import rejected: SKU '{sku}' already exists in database.",
                    "imported_count": 0,
                    "updated_count": 0,
                    "skipped_count": 0,
                    "failed_count": len(rows),
                    "error_logs": [{"row_index": item.get("row_index", 0), "sku": sku, "reason": "Duplicate SKU detected in reject mode"}]
                }
                
    for item in rows:
        data = item.get("data", item)
        sku = (data.get("sku") or "").strip().upper()
        row_idx = item.get("row_index", 0)
        
        if not sku or not data.get("name"):
            failed_count += 1
            error_logs.append({
                "row_index": row_idx,
                "sku": sku,
                "name": data.get("name", "Unknown"),
                "reason": "Missing required SKU or name"
            })
            continue
            
        try:
            # Handle image uploads to Cloudinary if requested
            thumbnail = data.get("thumbnail_url")
            gallery = data.get("gallery_image_urls") or []
            
            if upload_images_to_cloudinary:
                if thumbnail and thumbnail.startswith("http"):
                    upload_res = await upload_image_from_url(thumbnail)
                    thumbnail = upload_res.get("url", thumbnail)
                    
                new_gallery = []
                for g_url in gallery:
                    if g_url and g_url.startswith("http"):
                        g_res = await upload_image_from_url(g_url)
                        new_gallery.append(g_res.get("url", g_url))
                    else:
                        new_gallery.append(g_url)
                gallery = new_gallery
                
            # Category assurance: Ensure category exists in DB
            cat_name = data.get("category", "General").strip()
            existing_cat = await Category.find_one(Category.name == cat_name)
            if not existing_cat:
                slug_cat = cat_name.lower().replace(" ", "-")
                new_cat = Category(
                    name=cat_name,
                    slug=slug_cat,
                    status="active"
                )
                await new_cat.insert()
                
            # Check for existing product by SKU
            existing_product = await Product.find_one(Product.sku == sku)
            
            if existing_product:
                if duplicate_action == "skip":
                    skipped_count += 1
                    continue
                elif duplicate_action == "update":
                    # Update fields
                    existing_product.name = data.get("name", existing_product.name)
                    existing_product.category = cat_name
                    existing_product.subcategory = data.get("subcategory")
                    existing_product.brand = data.get("brand")
                    existing_product.mrp = float(data.get("mrp", existing_product.mrp))
                    existing_product.sale_price = float(data.get("sale_price", existing_product.sale_price))
                    existing_product.stock = int(data.get("stock", existing_product.stock))
                    existing_product.description = data.get("description", existing_product.description)
                    existing_product.short_description = data.get("short_description")
                    existing_product.tags = data.get("tags") or existing_product.tags
                    existing_product.color = data.get("color")
                    existing_product.size = data.get("size")
                    if thumbnail:
                        existing_product.thumbnail = thumbnail
                    if gallery:
                        existing_product.gallery_images = gallery
                    existing_product.status = data.get("status", existing_product.status)
                    existing_product.featured = data.get("featured", existing_product.featured)
                    existing_product.trending = data.get("trending", existing_product.trending)
                    existing_product.best_seller = data.get("best_seller", existing_product.best_seller)
                    
                    # SEO
                    if data.get("meta_title") or data.get("meta_description"):
                        existing_product.seo = {
                            "meta_title": data.get("meta_title") or existing_product.name,
                            "meta_description": data.get("meta_description") or "",
                            "meta_keywords": data.get("tags") or []
                        }
                    existing_product.updated_at = datetime.utcnow()
                    existing_product.calculate_discount()
                    await existing_product.save()
                    updated_count += 1
                    continue
                    
            # Insert new product
            slug = re.sub(r'[^a-zA-Z0-9\-]', '', data["name"].lower().replace(" ", "-"))
            existing_slug = await Product.find_one(Product.slug == slug)
            if existing_slug:
                slug = f"{slug}-{int(datetime.utcnow().timestamp())}"
                
            seo_dict = None
            if data.get("meta_title") or data.get("meta_description"):
                seo_dict = {
                    "meta_title": data.get("meta_title") or data["name"],
                    "meta_description": data.get("meta_description") or "",
                    "meta_keywords": data.get("tags") or []
                }
                
            product = Product(
                name=data["name"],
                slug=slug,
                sku=sku,
                category=cat_name,
                subcategory=data.get("subcategory"),
                brand=data.get("brand"),
                mrp=float(data.get("mrp", 0)),
                sale_price=float(data.get("sale_price", 0)),
                stock=int(data.get("stock", 0)),
                description=data.get("description", ""),
                short_description=data.get("short_description"),
                tags=data.get("tags") or [],
                color=data.get("color"),
                size=data.get("size"),
                thumbnail=thumbnail,
                gallery_images=gallery,
                status=data.get("status", "active"),
                featured=data.get("featured", False),
                trending=data.get("trending", False),
                best_seller=data.get("best_seller", False),
                seo=seo_dict
            )
            product.calculate_discount()
            await product.insert()
            imported_count += 1
            
        except Exception as e:
            failed_count += 1
            error_logs.append({
                "row_index": row_idx,
                "sku": sku,
                "name": data.get("name", "Unknown"),
                "reason": str(e)
            })
            
    return {
        "success": True,
        "message": f"Bulk import complete: {imported_count} imported, {updated_count} updated, {skipped_count} skipped, {failed_count} failed.",
        "imported_count": imported_count,
        "updated_count": updated_count,
        "skipped_count": skipped_count,
        "failed_count": failed_count,
        "error_logs": error_logs
    }
