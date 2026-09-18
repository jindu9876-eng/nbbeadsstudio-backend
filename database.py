import logging
from backend.config import settings
from backend.pg_engine import init_pg, Document
from backend.models.admin import Admin
from backend.models.user import User
from backend.models.product import Product
from backend.models.category import Category
from backend.models.order import Order
from backend.models.wishlist import Wishlist
from backend.models.cart import Cart
from backend.models.banner import Banner
from backend.models.setting import SystemSetting, get_or_create_settings
from backend.utils.security import get_password_hash

logger = logging.getLogger(__name__)

async def init_db():
    logger.info(f"Initializing PostgreSQL database '{settings.DB_NAME}' at {settings.DB_HOST}:{settings.DB_PORT}...")
    success = await init_pg(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        dbname=settings.DB_NAME
    )
    if success:
        logger.info(f"PostgreSQL connection and tables initialized successfully for database '{settings.DB_NAME}'.")
    else:
        logger.warning(f"PostgreSQL could not authenticate. Running in fallback mode until DB_PASSWORD is provided.")

    # Initialize settings and default data
    await get_or_create_settings()
    await seed_data()

async def seed_data():
    # Check if admin collection is empty
    admin_count = await Admin.count()
    if admin_count == 0:
        logger.info("Database is empty. Seeding default data...")
        
        # Create Admin
        admin = Admin(
            username="admin",
            email="admin@NB BEADS STUDIO.com",
            password_hash=get_password_hash("admin123"),
            status="active"
        )
        await admin.insert()
        
        # Create Categories
        categories_data = [
            {
                "name": "Jewellery",
                "slug": "jewellery",
                "description": "Timeless elegance in every piece",
                "image": "https://images.unsplash.com/photo-1758995115560-59c10d6cc28f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080",
                "icon": "gem"
            },
            {
                "name": "Couple Things",
                "slug": "couple-things",
                "description": "Celebrate love together",
                "image": "https://images.unsplash.com/photo-1517037126752-acf49bfda61a?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080",
                "icon": "heart"
            },
            {
                "name": "Macrame",
                "slug": "macrame",
                "description": "Handcrafted bohemian beauty",
                "image": "https://images.unsplash.com/photo-1632393121391-3c40fcfafe1a?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080",
                "icon": "scissors"
            },
            {
                "name": "Fashion",
                "slug": "fashion",
                "description": "Curated style essentials",
                "image": "https://images.unsplash.com/photo-1704775986777-b903cf6b9802?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080",
                "icon": "shirt"
            },
            {
                "name": "Gifts",
                "slug": "gifts",
                "description": "Beautiful gifts for your loved ones",
                "image": "https://images.unsplash.com/photo-1764267703999-372dddcb665a?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080",
                "icon": "gift"
            }
        ]
        
        for cat in categories_data:
            category = Category(
                name=cat["name"],
                slug=cat["slug"],
                image=cat["image"],
                icon=cat["icon"],
                status="active"
            )
            await category.insert()
            
        # Create Users
        for i in range(1, 11):
            user = User(
                name=f"User {i}",
                email=f"user{i}@NB BEADS STUDIO.com",
                password_hash=get_password_hash("user123"),
                phone=f"+123456789{i}",
                address=f"{100*i} NB BEADS STUDIO Street, Suite {i}, ShopCity",
                status="active"
            )
            await user.insert()
            
        # Create Banners
        banners_data = [
            {
                "title": "New Collection 2026",
                "subtitle": "Discover Luxury - Curated collections for the discerning individual",
                "button_text": "Explore Collection",
                "button_link": "/jewellery",
                "image": "https://images.unsplash.com/photo-1758995115560-59c10d6cc28f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080",
                "sort_order": 1
            },
            {
                "title": "Handcrafted Macrame",
                "subtitle": "Bring boho aesthetics into your cozy space",
                "button_text": "Shop Now",
                "button_link": "/macrame",
                "image": "https://images.unsplash.com/photo-1632393121391-3c40fcfafe1a?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080",
                "sort_order": 2
            },
            {
                "title": "Matching Couple Items",
                "subtitle": "Celebrate your bond with special bracelets and mugs",
                "button_text": "View All",
                "button_link": "/couple-things",
                "image": "https://images.unsplash.com/photo-1517037126752-acf49bfda61a?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080",
                "sort_order": 3
            },
            {
                "title": "Summer Fashion 2026",
                "subtitle": "Elegant dresses and statement designer accessories",
                "button_text": "View Collection",
                "button_link": "/fashion",
                "image": "https://images.unsplash.com/photo-1704775986777-b903cf6b9802?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080",
                "sort_order": 4
            },
            {
                "title": "Exclusive Sale",
                "subtitle": "Up to 50% off on featured jewellery items",
                "button_text": "Shop Sale",
                "button_link": "/jewellery",
                "image": "https://images.unsplash.com/photo-1739591414031-edd27896c8bf?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080",
                "sort_order": 5
            }
        ]
        
        for idx, ban in enumerate(banners_data):
            banner = Banner(
                title=ban["title"],
                subtitle=ban["subtitle"],
                button_text=ban["button_text"],
                button_link=ban["button_link"],
                image=ban["image"],
                sort_order=ban["sort_order"],
                status="active"
            )
            await banner.insert()
            
        # Create 20+ products spread over categories
        products_data = [
            # Jewellery
            {"name": "Gold Layered Necklace", "price": 899, "category": "Jewellery", "image": "https://images.unsplash.com/photo-1758995115560-59c10d6cc28f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", "sku": "JW-GLN-001"},
            {"name": "Diamond Solitaire Ring", "price": 1299, "category": "Jewellery", "image": "https://images.unsplash.com/photo-1739591414031-edd27896c8bf?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", "sku": "JW-DSR-002"},
            {"name": "Pearl Drop Earrings", "price": 459, "category": "Jewellery", "image": "https://images.unsplash.com/photo-1767210338407-54b9264c326b?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", "sku": "JW-PDE-003"},
            {"name": "Rose Gold Bracelet", "price": 679, "category": "Jewellery", "image": "https://images.unsplash.com/photo-1758995115560-59c10d6cc28f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", "sku": "JW-RGB-004"},
            {"name": "Sapphire Pendant", "price": 1899, "category": "Jewellery", "image": "https://images.unsplash.com/photo-1739591414031-edd27896c8bf?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", "sku": "JW-SP-005"},
            {"name": "Emerald Stud Earrings", "price": 729, "category": "Jewellery", "image": "https://images.unsplash.com/photo-1767210338407-54b9264c326b?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", "sku": "JW-ESE-006"},
            
            # Couple Things
            {"name": "Matching Bracelets Set", "price": 149, "category": "Couple Things", "image": "https://images.unsplash.com/photo-1517037126752-acf49bfda61a?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", "sku": "CP-MBS-001"},
            {"name": "Personalized Gift Box", "price": 199, "category": "Couple Things", "image": "https://images.unsplash.com/photo-1764267703999-372dddcb665a?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", "sku": "CP-PGB-002"},
            {"name": "Couple Mugs Set", "price": 45, "category": "Couple Things", "image": "https://images.unsplash.com/photo-1758524944375-7d61202cc481?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", "sku": "CP-CMS-003"},
            {"name": "Engraved Photo Frame", "price": 79, "category": "Couple Things", "image": "https://images.unsplash.com/photo-1764267703999-372dddcb665a?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", "sku": "CP-EPF-004"},
            {"name": "Couple Keychains", "price": 35, "category": "Couple Things", "image": "https://images.unsplash.com/photo-1517037126752-acf49bfda61a?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", "sku": "CP-CK-005"},
            
            # Macrame
            {"name": "Boho Wall Hanging", "price": 89, "category": "Macrame", "image": "https://images.unsplash.com/photo-1632393121391-3c40fcfafe1a?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", "sku": "MC-BWH-001"},
            {"name": "Plant Hanger Set", "price": 65, "category": "Macrame", "image": "https://images.unsplash.com/photo-1645129603960-f1ba77dbd198?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", "sku": "MC-PHS-002"},
            {"name": "Natural Decor Piece", "price": 75, "category": "Macrame", "image": "https://images.unsplash.com/photo-1632393121391-3c40fcfafe1a?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", "sku": "MC-NDP-003"},
            {"name": "Hanging Dream Catcher", "price": 45, "category": "Macrame", "image": "https://images.unsplash.com/photo-1645129603960-f1ba77dbd198?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", "sku": "MC-HDC-004"},
            
            # Fashion
            {"name": "Elegant Dress", "price": 299, "category": "Fashion", "image": "https://images.unsplash.com/photo-1704775986777-b903cf6b9802?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", "sku": "FS-ED-001"},
            {"name": "Designer Handbag", "price": 2499, "category": "Fashion", "image": "https://images.unsplash.com/photo-1758171692659-024183c2c272?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", "sku": "FS-DH-002"},
            {"name": "Premium Accessories", "price": 399, "category": "Fashion", "image": "https://images.unsplash.com/photo-1769116416641-e714b71851e8?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", "sku": "FS-PA-003"},
            {"name": "Silk Scarf", "price": 189, "category": "Fashion", "image": "https://images.unsplash.com/photo-1704775986777-b903cf6b9802?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", "sku": "FS-SS-004"},
            {"name": "Leather Tote", "price": 899, "category": "Fashion", "image": "https://images.unsplash.com/photo-1758171692659-024183c2c272?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", "sku": "FS-LT-005"},
            {"name": "Statement Sunglasses", "price": 249, "category": "Fashion", "image": "https://images.unsplash.com/photo-1769116416641-e714b71851e8?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", "sku": "FS-SSG-006"}
        ]
        
        for prod in products_data:
            slug = prod["name"].lower().replace(" ", "-").replace("&", "and")
            product = Product(
                name=prod["name"],
                slug=slug,
                description=f"This elegant {prod['name']} is crafted from premium materials. Ideal for enhancing your everyday collections or gifting on special occasions.",
                short_description=f"Premium quality {prod['name']}.",
                category=prod["category"],
                brand="NB BEADS STUDIO Premium",
                mrp=prod["price"] * 1.25,
                sale_price=prod["price"],
                stock=50,
                sku=prod["sku"],
                tags=[prod["category"].lower(), "premium", "new-arrival"],
                featured=(prod["sku"].endswith("-001") or prod["sku"].endswith("-002")),
                trending=(prod["sku"].endswith("-003") or prod["sku"].endswith("-004")),
                best_seller=(prod["sku"].endswith("-005") or prod["sku"].endswith("-006")),
                status="active",
                thumbnail=prod["image"],
                gallery_images=[prod["image"]]
            )
            product.calculate_discount()
            await product.insert()
            
        logger.info("Default seed data populated successfully.")
