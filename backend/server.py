from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
import bcrypt
from bson import ObjectId

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security
SECRET_KEY = "tech_haven_secret_key_2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

app = FastAPI(title="Tech Haven API")
api_router = APIRouter(prefix="/api")

# Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    is_admin: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    brand: str
    category: str
    price: float
    original_price: Optional[float] = None
    description: str
    specifications: Dict[str, Any]
    images: List[str]
    stock: int = 0
    rating: float = 0.0
    review_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    featured: bool = False

class ProductCreate(BaseModel):
    name: str
    brand: str
    category: str
    price: float
    original_price: Optional[float] = None
    description: str
    specifications: Dict[str, Any]
    images: List[str]
    stock: int = 0
    featured: bool = False

class CartItem(BaseModel):
    product_id: str
    quantity: int

class Cart(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    items: List[CartItem] = []
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class OrderItem(BaseModel):
    product_id: str
    product_name: str
    price: float
    quantity: int

class Order(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    items: List[OrderItem]
    total_amount: float
    status: str = "pending"  # pending, processing, shipped, delivered, cancelled
    shipping_address: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class OrderCreate(BaseModel):
    shipping_address: Dict[str, Any]

class Review(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    user_id: str
    user_name: str
    rating: int
    comment: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ReviewCreate(BaseModel):
    product_id: str
    rating: int
    comment: str

# Helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await db.users.find_one({"email": email})
    if user is None:
        raise credentials_exception
    return User(**user)

# Auth endpoints
@api_router.post("/register", response_model=dict)
async def register(user: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    hashed_password = get_password_hash(user.password)
    user_dict = user.dict()
    del user_dict["password"]
    user_obj = User(**user_dict)
    user_data = user_obj.dict()
    user_data["hashed_password"] = hashed_password
    
    await db.users.insert_one(user_data)
    return {"message": "User registered successfully"}

@api_router.post("/login", response_model=Token)
async def login(user_login: UserLogin):
    user = await db.users.find_one({"email": user_login.email})
    if not user or not verify_password(user_login.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@api_router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# Products endpoints
@api_router.get("/products", response_model=List[Product])
async def get_products(
    category: Optional[str] = None,
    brand: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    search: Optional[str] = None,
    featured: Optional[bool] = None,
    limit: int = 50
):
    query = {}
    if category:
        query["category"] = category
    if brand:
        query["brand"] = brand
    if min_price is not None or max_price is not None:
        query["price"] = {}
        if min_price is not None:
            query["price"]["$gte"] = min_price
        if max_price is not None:
            query["price"]["$lte"] = max_price
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"brand": {"$regex": search, "$options": "i"}}
        ]
    if featured is not None:
        query["featured"] = featured

    products = await db.products.find(query).limit(limit).to_list(limit)
    return [Product(**product) for product in products]

@api_router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: str):
    product = await db.products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return Product(**product)

@api_router.post("/products", response_model=Product)
async def create_product(product: ProductCreate, current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    product_obj = Product(**product.dict())
    await db.products.insert_one(product_obj.dict())
    return product_obj

@api_router.get("/categories")
async def get_categories():
    categories = await db.products.distinct("category")
    brands = await db.products.distinct("brand")
    return {"categories": categories, "brands": brands}

# Cart endpoints
@api_router.get("/cart", response_model=Cart)
async def get_cart(current_user: User = Depends(get_current_user)):
    cart = await db.carts.find_one({"user_id": current_user.id})
    if not cart:
        cart = Cart(user_id=current_user.id)
        await db.carts.insert_one(cart.dict())
    else:
        cart = Cart(**cart)
    return cart

@api_router.post("/cart/add")
async def add_to_cart(item: CartItem, current_user: User = Depends(get_current_user)):
    cart = await db.carts.find_one({"user_id": current_user.id})
    if not cart:
        cart = Cart(user_id=current_user.id)
        cart.items = [item]
    else:
        cart = Cart(**cart)
        # Check if item exists
        existing_item = None
        for i, cart_item in enumerate(cart.items):
            if cart_item.product_id == item.product_id:
                existing_item = i
                break
        
        if existing_item is not None:
            cart.items[existing_item].quantity += item.quantity
        else:
            cart.items.append(item)
    
    cart.updated_at = datetime.utcnow()
    await db.carts.replace_one({"user_id": current_user.id}, cart.dict(), upsert=True)
    return {"message": "Item added to cart"}

@api_router.put("/cart/update")
async def update_cart_item(item: CartItem, current_user: User = Depends(get_current_user)):
    cart = await db.carts.find_one({"user_id": current_user.id})
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    cart = Cart(**cart)
    for i, cart_item in enumerate(cart.items):
        if cart_item.product_id == item.product_id:
            if item.quantity <= 0:
                cart.items.pop(i)
            else:
                cart.items[i].quantity = item.quantity
            break
    
    cart.updated_at = datetime.utcnow()
    await db.carts.replace_one({"user_id": current_user.id}, cart.dict())
    return {"message": "Cart updated"}

@api_router.delete("/cart/remove/{product_id}")
async def remove_from_cart(product_id: str, current_user: User = Depends(get_current_user)):
    cart = await db.carts.find_one({"user_id": current_user.id})
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    cart = Cart(**cart)
    cart.items = [item for item in cart.items if item.product_id != product_id]
    cart.updated_at = datetime.utcnow()
    await db.carts.replace_one({"user_id": current_user.id}, cart.dict())
    return {"message": "Item removed from cart"}

# Orders endpoints
@api_router.post("/orders", response_model=Order)
async def create_order(order_create: OrderCreate, current_user: User = Depends(get_current_user)):
    cart = await db.carts.find_one({"user_id": current_user.id})
    if not cart or not cart.get("items"):
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    cart = Cart(**cart)
    order_items = []
    total_amount = 0
    
    for cart_item in cart.items:
        product = await db.products.find_one({"id": cart_item.product_id})
        if not product:
            continue
        
        order_item = OrderItem(
            product_id=cart_item.product_id,
            product_name=product["name"],
            price=product["price"],
            quantity=cart_item.quantity
        )
        order_items.append(order_item)
        total_amount += product["price"] * cart_item.quantity
    
    order = Order(
        user_id=current_user.id,
        items=order_items,
        total_amount=total_amount,
        shipping_address=order_create.shipping_address
    )
    
    await db.orders.insert_one(order.dict())
    
    # Clear cart
    cart.items = []
    cart.updated_at = datetime.utcnow()
    await db.carts.replace_one({"user_id": current_user.id}, cart.dict())
    
    return order

@api_router.get("/orders", response_model=List[Order])
async def get_orders(current_user: User = Depends(get_current_user)):
    query = {"user_id": current_user.id} if not current_user.is_admin else {}
    orders = await db.orders.find(query).sort("created_at", -1).to_list(100)
    return [Order(**order) for order in orders]

@api_router.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: str, current_user: User = Depends(get_current_user)):
    order = await db.orders.find_one({"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order = Order(**order)
    if not current_user.is_admin and order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return order

# Reviews endpoints
@api_router.get("/products/{product_id}/reviews", response_model=List[Review])
async def get_product_reviews(product_id: str):
    reviews = await db.reviews.find({"product_id": product_id}).sort("created_at", -1).to_list(100)
    return [Review(**review) for review in reviews]

@api_router.post("/reviews", response_model=Review)
async def create_review(review: ReviewCreate, current_user: User = Depends(get_current_user)):
    # Check if product exists
    product = await db.products.find_one({"id": review.product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if user already reviewed this product
    existing_review = await db.reviews.find_one({
        "product_id": review.product_id,
        "user_id": current_user.id
    })
    if existing_review:
        raise HTTPException(status_code=400, detail="You have already reviewed this product")
    
    review_obj = Review(
        product_id=review.product_id,
        user_id=current_user.id,
        user_name=current_user.full_name,
        rating=review.rating,
        comment=review.comment
    )
    
    await db.reviews.insert_one(review_obj.dict())
    
    # Update product rating
    reviews = await db.reviews.find({"product_id": review.product_id}).to_list(1000)
    avg_rating = sum(r["rating"] for r in reviews) / len(reviews)
    await db.products.update_one(
        {"id": review.product_id},
        {"$set": {"rating": round(avg_rating, 1), "review_count": len(reviews)}}
    )
    
    return review_obj

# Initialize sample data
@api_router.post("/init-data")
async def init_sample_data():
    # Check if data already exists
    product_count = await db.products.count_documents({})
    if product_count > 0:
        return {"message": "Sample data already exists"}
    
    # Sample products
    sample_products = [
        {
            "name": "MacBook Pro M3",
            "brand": "Apple",
            "category": "Professional",
            "price": 2499.00,
            "original_price": 2699.00,
            "description": "The ultimate pro laptop with M3 chip for unparalleled performance and efficiency.",
            "specifications": {
                "processor": "Apple M3 Pro",
                "memory": "18GB Unified Memory",
                "storage": "1TB SSD",
                "display": "14.2-inch Liquid Retina XDR",
                "graphics": "Integrated 18-core GPU",
                "battery": "Up to 18 hours",
                "weight": "3.5 lbs"
            },
            "images": [
                "https://lh3.googleusercontent.com/aida-public/AB6AXuCo80kMNEBUnRe3Z9mOP2JJUVhmQVE6EfdHIg_hlPTRIwJCp6rhXLbrVdT-QeBe6uVT57DGjmn8bndDQ6yLR-tE4y85rtOEVea-4H03ywvJZRP2HvWrivlc9yLzTkpquTTX4NmJbzHkMIwgHqE6hzszEPRG8hUE9M_AcRsIMrjSDB7gmIJ9XnicRcWD5AJhKHnCRyEdSY924voR1S02LPGv5xQSW4QwWXibao0lld67EMBzL3OrXNajf-zr5BrEq5rE6MQI1Dcot6w"
            ],
            "stock": 15,
            "rating": 4.8,
            "review_count": 124,
            "featured": True
        },
        {
            "name": "Dell XPS 13",
            "brand": "Dell",
            "category": "Ultrabook",
            "price": 1299.00,
            "original_price": 1499.00,
            "description": "The perfect blend of performance and design in an ultraportable form factor.",
            "specifications": {
                "processor": "Intel Core i7-13700H",
                "memory": "16GB LPDDR5",
                "storage": "512GB PCIe NVMe SSD",
                "display": "13.4-inch FHD+ InfinityEdge",
                "graphics": "Intel Iris Xe",
                "battery": "Up to 12 hours",
                "weight": "2.8 lbs"
            },
            "images": [
                "https://lh3.googleusercontent.com/aida-public/AB6AXuDjrES9-HLv3xxFES7gQ6fSgv7fSekv9fJFYA68wUDVLAXxo2VT87NeyjgypHK_s7Eg6lIGuYhID3uYKhqO6I1qPx1fYU710TCcSUCke_rVSjc0uZDUw58i-zVO4V6Vdsw8buVv5KZI_Ocu1wu1Kp8UKm0U2rY9vo3RFruow2y-Kr3R0PjunHSqNJmxufHpPhn_b3S-nE0lRhhnDqByxxjnwotCmwPISFVjp2Q8jMQhwDpS62OkPmge068tjpWzOCvQ5Rd41Crtckc"
            ],
            "stock": 22,
            "rating": 4.6,
            "review_count": 89,
            "featured": True
        },
        {
            "name": "Gaming Laptop X500",
            "brand": "ASUS",
            "category": "Gaming",
            "price": 2199.00,
            "description": "High-performance gaming laptop designed for enthusiasts and competitive gamers.",
            "specifications": {
                "processor": "Intel Core i9-12900HX",
                "memory": "32GB DDR5 4800MHz",
                "storage": "1TB PCIe Gen4 NVMe SSD",
                "display": "17.3\" QHD (2560x1440) 240Hz IPS",
                "graphics": "NVIDIA GeForce RTX 3080 Ti 16GB GDDR6",
                "battery": "Up to 6 hours",
                "weight": "5.7 lbs"
            },
            "images": [
                "https://lh3.googleusercontent.com/aida-public/AB6AXuBvCqw1pC_kz5JyDXFuvMv71m4GsuIeqa_xjl-EyXu7PNBleCmca4DNqmilBS3BeRbQfX13NbWLH5tn0TC3FfJS1n2LF_gUFBjbuedPGyMYEmorUuC6qRlIBfZIxArcb-cI5clJAdYoXnTFL0pVxqfFI_SVAabxZk9wJa1Vg1iXQHka1526ydNg5yL7zQrtr1773FKMO0_YEdaXGM-t6LAZz0Yd_ggBnCKPF6ejTPSGFp5aferAFUMUnZUxq-BXvZBwpBQhQj8vFEI"
            ],
            "stock": 8,
            "rating": 4.7,
            "review_count": 156,
            "featured": True
        },
        {
            "name": "Lenovo X1 Carbon",
            "brand": "Lenovo",
            "category": "Business",
            "price": 1899.00,
            "description": "Lightweight and powerful laptop designed for business professionals.",
            "specifications": {
                "processor": "Intel Core i7-13700U",
                "memory": "16GB LPDDR5",
                "storage": "1TB PCIe SSD",
                "display": "14\" WUXGA (1920x1200) IPS",
                "graphics": "Intel Iris Xe",
                "battery": "Up to 15 hours",
                "weight": "2.48 lbs"
            },
            "images": [
                "https://lh3.googleusercontent.com/aida-public/AB6AXuBKpOHaTQt7dAAsbM2w7cfOSOio5JRupyvaWp6jUdTFJGpXdfMolG7X9nw19Z66gDQaD99DY-Cfxv43HgKtbl9ACuplWwvpDDB0xdB_HZwYjup2hQuNETBOhM9_I6DSfytRBCH-sPDDEvlidGkb4xAxmG7QxsWKVuZaQ7UafX-aUaOlF-kEDE1e7F08JNDp2QiGa8h-h9d9_7bbNFzSUquKcnZwn7cIDl9ugNj0Be6aVaClCLrxur_Uc2hklU9_-IIFwi21LZzD2UI"
            ],
            "stock": 18,
            "rating": 4.5,
            "review_count": 67,
            "featured": False
        },
        {
            "name": "HP Pavilion Gaming",
            "brand": "HP",
            "category": "Gaming",
            "price": 899.00,
            "original_price": 1099.00,
            "description": "Affordable gaming laptop perfect for casual gamers and students.",
            "specifications": {
                "processor": "AMD Ryzen 7 5800H",
                "memory": "16GB DDR4",
                "storage": "512GB PCIe NVMe SSD",
                "display": "15.6\" FHD (1920x1080) 144Hz",
                "graphics": "NVIDIA GeForce GTX 1660 Ti",
                "battery": "Up to 8 hours",
                "weight": "5.4 lbs"
            },
            "images": [
                "https://lh3.googleusercontent.com/aida-public/AB6AXuBvCqw1pC_kz5JyDXFuvMv71m4GsuIeqa_xjl-EyXu7PNBleCmca4DNqmilBS3BeRbQfX13NbWLH5tn0TC3FfJS1n2LF_gUFBjbuedPGyMYEmorUuC6qRlIBfZIxArcb-cI5clJAdYoXnTFL0pVxqfFI_SVAabxZk9wJa1Vg1iXQHka1526ydNg5yL7zQrtr1773FKMO0_YEdaXGM-t6LAZz0Yd_ggBnCKPF6ejTPSGFp5aferAFUMUnZUxq-BXvZBwpBQhQj8vFEI"
            ],
            "stock": 25,
            "rating": 4.2,
            "review_count": 43,
            "featured": False
        }
    ]
    
    # Add IDs to products
    for product in sample_products:
        product["id"] = str(uuid.uuid4())
        product["created_at"] = datetime.utcnow()
    
    await db.products.insert_many(sample_products)
    
    # Create admin user
    admin_user = {
        "id": str(uuid.uuid4()),
        "email": "admin@techhaven.com",
        "full_name": "Admin User",
        "phone": "+1234567890",
        "is_admin": True,
        "created_at": datetime.utcnow(),
        "hashed_password": get_password_hash("admin123")
    }
    await db.users.insert_one(admin_user)
    
    return {"message": "Sample data initialized successfully"}

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()