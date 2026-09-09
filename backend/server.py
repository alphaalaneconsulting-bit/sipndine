"""Sip 'n' Dine — Restaurant + Admin CMS backend."""
from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from pathlib import Path
import os, uuid, base64, logging, asyncio, jwt, bcrypt

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")
UPLOADS_DIR = ROOT / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@sipndine.co.in")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme")
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title="Sip 'n' Dine API")
api = APIRouter(prefix="/api")
security = HTTPBearer(auto_error=False)
log = logging.getLogger("sipndine")
logging.basicConfig(level=logging.INFO)


# ---------- auth ----------
def hash_pwd(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def verify_pwd(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except Exception:
        return False


def make_token(email: str) -> str:
    payload = {"sub": email, "exp": datetime.now(timezone.utc) + timedelta(days=7)}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


async def require_admin(creds: HTTPAuthorizationCredentials = Depends(security)):
    if not creds:
        raise HTTPException(401, "Missing token")
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=["HS256"])
        email = payload.get("sub")
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid token")
    user = await db.admins.find_one({"email": email})
    if not user:
        raise HTTPException(401, "Not authorised")
    return user


class LoginBody(BaseModel):
    email: EmailStr
    password: str


@api.post("/auth/login")
async def login(body: LoginBody):
    user = await db.admins.find_one({"email": body.email.lower()})
    if not user or not verify_pwd(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    return {"token": make_token(user["email"]), "email": user["email"]}


@api.get("/auth/me")
async def me(user=Depends(require_admin)):
    return {"email": user["email"]}


# ---------- helpers ----------
def clean(doc: Optional[dict]) -> Optional[dict]:
    if not doc:
        return doc
    doc.pop("_id", None)
    return doc


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- settings (global) ----------
class Settings(BaseModel):
    phones: List[str] = ["+91 172 4641656", "+91 172 2791656"]
    email: str = "info@sipndine.co.in"
    address: str = "SCO 16A, Sector 7C, Madhya Marg, Chandigarh 160019 (India)"
    hours: List[Dict[str, str]] = []
    social: Dict[str, str] = {}
    logo_url: str = ""
    map_embed_url: str = "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3428.1!2d76.7794!3d30.7333!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x0%3A0x0!2sSip%20n%20Dine%20Chandigarh!5e0!3m2!1sen!2sin!4v1700000000000"


@api.get("/settings")
async def get_settings():
    s = await db.settings.find_one({"_id": "global"})
    if not s:
        return Settings().model_dump()
    s.pop("_id", None)
    return s


@api.put("/settings")
async def update_settings(body: Settings, user=Depends(require_admin)):
    await db.settings.update_one({"_id": "global"}, {"$set": body.model_dump()}, upsert=True)
    return body.model_dump()


# ---------- page content ----------
class PageContent(BaseModel):
    slug: str
    title: str = ""
    eyebrow: str = ""
    hero_image: str = ""
    intro: str = ""
    body_html: str = ""
    extras: Dict[str, Any] = {}


@api.get("/content/{slug}")
async def get_content(slug: str):
    doc = await db.content.find_one({"slug": slug})
    if not doc:
        return PageContent(slug=slug).model_dump()
    return clean(doc)


@api.get("/content")
async def list_content():
    docs = await db.content.find({}).to_list(200)
    return [clean(d) for d in docs]


@api.put("/content/{slug}")
async def upsert_content(slug: str, body: PageContent, user=Depends(require_admin)):
    body.slug = slug
    await db.content.update_one({"slug": slug}, {"$set": body.model_dump()}, upsert=True)
    return body.model_dump()


# ---------- menu ----------
class MenuItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: str
    description: str = ""
    price: Optional[float] = None
    veg: bool = True
    signature: bool = False
    image_url: str = ""
    order: int = 0


@api.get("/menu")
async def list_menu():
    items = await db.menu.find({}).sort("order", 1).to_list(500)
    return [clean(i) for i in items]


@api.post("/admin/menu")
async def create_menu_item(body: MenuItem, user=Depends(require_admin)):
    doc = body.model_dump()
    await db.menu.insert_one(doc)
    return clean(doc)


@api.put("/admin/menu/{item_id}")
async def update_menu_item(item_id: str, body: MenuItem, user=Depends(require_admin)):
    body.id = item_id
    await db.menu.update_one({"id": item_id}, {"$set": body.model_dump()}, upsert=True)
    return body.model_dump()


@api.delete("/admin/menu/{item_id}")
async def delete_menu_item(item_id: str, user=Depends(require_admin)):
    await db.menu.delete_one({"id": item_id})
    return {"ok": True}


class ImageGenBody(BaseModel):
    prompt: str
    item_id: Optional[str] = None


async def _generate_food_image(prompt: str) -> Optional[str]:
    """Generate an image via Gemini Nano Banana and return served URL."""
    if not EMERGENT_LLM_KEY:
        return None
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"img-{uuid.uuid4()}",
            system_message="You are a professional food photographer.",
        ).with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])
        full_prompt = (
            f"Ultra-realistic overhead food photography of {prompt}. "
            "Indian fine-dining plating on dark rustic wooden table, warm amber restaurant lighting, "
            "shallow depth of field, garnish, steam, cinematic magazine style, no text, no watermark."
        )
        _, images = await chat.send_message_multimodal_response(UserMessage(text=full_prompt))
        if not images:
            return None
        img = images[0]
        raw = base64.b64decode(img["data"])
        fname = f"{uuid.uuid4()}.png"
        (UPLOADS_DIR / fname).write_bytes(raw)
        return f"/api/uploads/{fname}"
    except Exception as e:
        log.exception("image gen failed: %s", e)
        return None


@api.post("/admin/generate-image")
async def generate_image(body: ImageGenBody, user=Depends(require_admin)):
    url = await _generate_food_image(body.prompt)
    if not url:
        raise HTTPException(500, "Image generation failed")
    if body.item_id:
        await db.menu.update_one({"id": body.item_id}, {"$set": {"image_url": url}})
    return {"image_url": url}


# ---------- gallery ----------
class GalleryImage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str
    caption: str = ""
    order: int = 0


@api.get("/gallery")
async def list_gallery():
    items = await db.gallery.find({}).sort("order", 1).to_list(200)
    return [clean(i) for i in items]


@api.post("/admin/gallery")
async def add_gallery(body: GalleryImage, user=Depends(require_admin)):
    await db.gallery.insert_one(body.model_dump())
    return body.model_dump()


@api.put("/admin/gallery/{gid}")
async def upd_gallery(gid: str, body: GalleryImage, user=Depends(require_admin)):
    body.id = gid
    await db.gallery.update_one({"id": gid}, {"$set": body.model_dump()}, upsert=True)
    return body.model_dump()


@api.delete("/admin/gallery/{gid}")
async def del_gallery(gid: str, user=Depends(require_admin)):
    await db.gallery.delete_one({"id": gid})
    return {"ok": True}


# ---------- recognition (why chandigarh loves us) ----------
class Recognition(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    platform: str
    rating: str = ""
    quote: str = ""
    icon: str = ""
    order: int = 0


@api.get("/recognition")
async def list_recognition():
    return [clean(i) for i in await db.recognition.find({}).sort("order", 1).to_list(50)]


@api.post("/admin/recognition")
async def add_rec(body: Recognition, user=Depends(require_admin)):
    await db.recognition.insert_one(body.model_dump())
    return body.model_dump()


@api.put("/admin/recognition/{rid}")
async def upd_rec(rid: str, body: Recognition, user=Depends(require_admin)):
    body.id = rid
    await db.recognition.update_one({"id": rid}, {"$set": body.model_dump()}, upsert=True)
    return body.model_dump()


@api.delete("/admin/recognition/{rid}")
async def del_rec(rid: str, user=Depends(require_admin)):
    await db.recognition.delete_one({"id": rid})
    return {"ok": True}


# ---------- offers ----------
class Offer(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    subtitle: str = ""
    description: str = ""
    valid_till: str = ""
    image_url: str = ""
    active: bool = True
    order: int = 0


@api.get("/offers")
async def list_offers():
    return [clean(i) for i in await db.offers.find({}).sort("order", 1).to_list(100)]


@api.post("/admin/offers")
async def add_offer(body: Offer, user=Depends(require_admin)):
    await db.offers.insert_one(body.model_dump())
    return body.model_dump()


@api.put("/admin/offers/{oid}")
async def upd_offer(oid: str, body: Offer, user=Depends(require_admin)):
    body.id = oid
    await db.offers.update_one({"id": oid}, {"$set": body.model_dump()}, upsert=True)
    return body.model_dump()


@api.delete("/admin/offers/{oid}")
async def del_offer(oid: str, user=Depends(require_admin)):
    await db.offers.delete_one({"id": oid})
    return {"ok": True}


# ---------- membership tiers ----------
class Tier(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    price: str = ""
    tagline: str = ""
    benefits: List[str] = []
    highlighted: bool = False
    order: int = 0


@api.get("/membership")
async def list_tiers():
    return [clean(i) for i in await db.membership.find({}).sort("order", 1).to_list(50)]


@api.post("/admin/membership")
async def add_tier(body: Tier, user=Depends(require_admin)):
    await db.membership.insert_one(body.model_dump())
    return body.model_dump()


@api.put("/admin/membership/{tid}")
async def upd_tier(tid: str, body: Tier, user=Depends(require_admin)):
    body.id = tid
    await db.membership.update_one({"id": tid}, {"$set": body.model_dump()}, upsert=True)
    return body.model_dump()


@api.delete("/admin/membership/{tid}")
async def del_tier(tid: str, user=Depends(require_admin)):
    await db.membership.delete_one({"id": tid})
    return {"ok": True}


class WaitlistEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    created_at: str = Field(default_factory=now_iso)


@api.post("/membership/waitlist")
async def join_waitlist(body: WaitlistEntry):
    await db.waitlist.insert_one(body.model_dump())
    return {"ok": True}


@api.get("/admin/waitlist")
async def get_waitlist(user=Depends(require_admin)):
    return [clean(i) for i in await db.waitlist.find({}).sort("created_at", -1).to_list(1000)]


# ---------- bookings ----------
class BookingCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = ""
    date: str
    time: str
    party_size: int
    occasion: Optional[str] = ""
    notes: Optional[str] = ""


class Booking(BookingCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "pending"  # pending | confirmed | cancelled
    created_at: str = Field(default_factory=now_iso)


@api.post("/bookings")
async def create_booking(body: BookingCreate):
    obj = Booking(**body.model_dump())
    await db.bookings.insert_one(obj.model_dump())
    return {"ok": True, "id": obj.id}


@api.get("/admin/bookings")
async def list_bookings(user=Depends(require_admin)):
    return [clean(i) for i in await db.bookings.find({}).sort("created_at", -1).to_list(1000)]


class BookingStatus(BaseModel):
    status: str


@api.put("/admin/bookings/{bid}")
async def update_booking(bid: str, body: BookingStatus, user=Depends(require_admin)):
    await db.bookings.update_one({"id": bid}, {"$set": {"status": body.status}})
    return {"ok": True}


@api.delete("/admin/bookings/{bid}")
async def delete_booking(bid: str, user=Depends(require_admin)):
    await db.bookings.delete_one({"id": bid})
    return {"ok": True}


# ---------- enquiries (banqueting / catering / contact) ----------
class EnquiryCreate(BaseModel):
    kind: str  # banqueting | catering | contact
    name: str
    phone: str
    email: Optional[str] = ""
    date: Optional[str] = ""
    guests: Optional[int] = None
    message: Optional[str] = ""


class Enquiry(EnquiryCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=now_iso)
    status: str = "new"


@api.post("/enquiries")
async def create_enquiry(body: EnquiryCreate):
    obj = Enquiry(**body.model_dump())
    await db.enquiries.insert_one(obj.model_dump())
    return {"ok": True, "id": obj.id}


@api.get("/admin/enquiries")
async def list_enquiries(user=Depends(require_admin)):
    return [clean(i) for i in await db.enquiries.find({}).sort("created_at", -1).to_list(1000)]


@api.put("/admin/enquiries/{eid}")
async def upd_enquiry(eid: str, body: BookingStatus, user=Depends(require_admin)):
    await db.enquiries.update_one({"id": eid}, {"$set": {"status": body.status}})
    return {"ok": True}


@api.delete("/admin/enquiries/{eid}")
async def del_enquiry(eid: str, user=Depends(require_admin)):
    await db.enquiries.delete_one({"id": eid})
    return {"ok": True}


# ---------- root ----------
@api.get("/")
async def root():
    return {"service": "sip-n-dine", "ok": True}


app.include_router(api)
app.mount("/api/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- seed on startup ----------
SEED_MENU = [
    ("Dahi Ke Kebab", "Starters", "Spiced hung yogurt kebabs, crisp outside, silken within", 425, True, True),
    ("Tandoori Broccoli", "Starters", "Charred florets with hung curd and cheddar glaze", 445, True, False),
    ("Galouti Kebab", "Starters", "Silken minced lamb pattie with saffron & warak", 545, False, True),
    ("Murgh Malai Tikka", "Tandoor", "Cream & cheese marinated chicken, mildly spiced", 495, False, True),
    ("Sikandari Raan", "Tandoor", "Slow-cooked whole lamb leg with royal spices", 1250, False, True),
    ("Tandoori Prawns", "Tandoor", "Jumbo prawns in ajwain-cardamom marinade", 795, False, False),
    ("Paneer Butter Masala", "Mains", "Cottage cheese in silken tomato-fenugreek gravy", 465, True, True),
    ("Dal Sip 'n' Dine", "Mains", "Signature black lentils, 24-hour slow-simmered", 425, True, True),
    ("Butter Chicken", "Mains", "Classic Delhi-style, tomato-cashew, kissed with kasuri methi", 545, False, True),
    ("Laal Maas", "Mains", "Rajasthani fiery lamb curry with mathania chillies", 675, False, False),
    ("Awadhi Mutton Biryani", "Biryani", "Dum-cooked long-grain rice, saffron & rose", 595, False, True),
    ("Hyderabadi Chicken Biryani", "Biryani", "Kacchi style dum, mint & fried onions", 545, False, False),
    ("Vegetable Dum Biryani", "Biryani", "Aromatic seasonal veg biryani, dum-sealed", 445, True, False),
    ("Truffle Naan", "Breads", "Butter naan with black truffle shavings", 245, True, False),
    ("Garlic Kulcha", "Breads", "Punjabi kulcha, roasted garlic & coriander", 145, True, False),
    ("Laccha Paratha", "Breads", "Multi-layered whole wheat paratha", 125, True, False),
    ("Rasmalai Tres Leches", "Desserts", "Fusion cardamom milk cake with pistachio", 325, True, True),
    ("Gulab Jamun Cheesecake", "Desserts", "Baked cheesecake with saffron gulab jamun", 345, True, False),
    ("Masala Chai Old Fashioned", "Drinks", "Chai-infused bourbon, orange bitters (non-alc)", 395, True, False),
    ("Rose Falooda", "Drinks", "Classic rose milk with basil seeds & ice cream", 245, True, False),
]

SEED_RECOGNITION = [
    ("Google Reviews", "4.6 ★", "\"An old-Chandigarh institution — warm service and food that lingers.\"", "google", 0),
    ("Zomato", "4.5 ★", "\"A benchmark for Awadhi & Punjabi fine dining in the tricity.\"", "zomato", 1),
    ("JustDial", "5.0 ★", "\"Consistently rated top Indian fine dining in Sector 7.\"", "star", 2),
    ("Rotary Chandigarh Shivalik", "Award", "Honoured for hospitality excellence and community.", "award", 3),
    ("Owners Also Eat Here", "House Pride", "The wall sign that says everything about our kitchen.", "heart", 4),
]

SEED_OFFERS = [
    ("Weekday Lunch Escape", "Mon – Fri, 12:30 – 3:30 PM", "Two-course fine-dining thali for two at ₹1,299. Includes a signature dessert.", "Till 31 Mar 2026"),
    ("Family Sunday Brunch", "Every Sunday", "Live counters, unlimited buffet, chef's kebab platter — ₹1,599 per adult.", "Ongoing"),
    ("Anniversary Table", "Celebrations", "A candle-lit table, complimentary cake and a house cocktail on the night.", "By reservation"),
]

SEED_TIERS = [
    ("Silver", "Coming Soon", "For our regulars", ["10% off à la carte", "Priority reservations", "Birthday dessert on the house"], False, 0),
    ("Gold", "Coming Soon", "For those who dine often", ["20% off à la carte & buffet", "Guaranteed table on weekends", "Complimentary house cocktail once a month", "Early access to chef's tasting nights"], True, 1),
    ("Platinum", "Coming Soon", "Our most treasured guests", ["30% off everything", "Private nook access", "Chef's table experience twice a year", "Personal concierge for events"], False, 2),
]

SEED_CONTENT = {
    "home": {
        "title": "An unhurried table in Sector 7",
        "eyebrow": "Chandigarh, since a long time",
        "hero_image": "/restaurant/image1.jpeg",
        "intro": "Sip 'n' Dine is a quiet corner of Madhya Marg where warm wood, hand-plated Awadhi and Punjabi classics, and a familiar hello have kept the same guests coming back for years.",
    },
    "our-story": {
        "title": "Our Story",
        "eyebrow": "Since 2005 · Sector 7C",
        "hero_image": "/restaurant/image5.jpeg",
        "intro": "A family table that grew into a neighbourhood institution.",
        "body_html": "<p>Sip 'n' Dine began the way most good restaurants do — around a family table, with recipes older than the room, and a stubborn belief that a meal in Chandigarh could feel like a meal in a home in old Lucknow. Two decades later, the plaque on our wall still reads <em>\"Owners also eat here\"</em>, and it is not a marketing line.</p><p>Our kitchen is Awadhi at heart and Punjabi by neighbourhood — dum biryanis rested overnight, dal simmered for a full day, kebabs shaped by hand, breads pulled from a live tandoor. Our dining room is warm wood, soft brass light, floral corners for the private conversations, and a communal table for the ones you want to remember.</p><p>Whether you're stopping in for a Sunday lunch, hosting an intimate anniversary, planning a wedding rehearsal, or feeding a marching band — we're a small, family-run house, and we still like to plate the first course ourselves.</p>",
    },
    "menu": {
        "title": "The Menu",
        "eyebrow": "Awadhi · Punjabi · Signature",
        "hero_image": "/restaurant/image7.jpeg",
        "intro": "Photos are AI-suggested until our new food photography arrives — flavours, however, are entirely ours.",
    },
    "buffet": {
        "title": "The Restaurant Buffet",
        "eyebrow": "Lunch & Dinner",
        "hero_image": "/restaurant/image3.jpeg",
        "intro": "A rotating spread of house classics — soups, salads, chaat station, live tandoor, five mains, three biryanis, and a full Indian dessert counter.",
        "body_html": "<p><strong>Weekday Lunch:</strong> 12:30 – 3:30 PM · ₹899 per adult</p><p><strong>Weekend Lunch:</strong> 12:30 – 3:45 PM · ₹1,199 per adult</p><p><strong>Dinner Buffet:</strong> 7:30 – 11:00 PM · ₹1,299 per adult</p><p>Children under 8 dine at half. Reservations recommended on weekends.</p>",
    },
    "gallery": {"title": "Inside Sip 'n' Dine", "eyebrow": "Room by room", "hero_image": "/restaurant/image6.jpeg", "intro": "A quick walk through our dining rooms, private nooks, and the wall we're most proud of."},
    "banqueting": {
        "title": "Banqueting & Events",
        "eyebrow": "Private Dining",
        "hero_image": "/restaurant/image5.jpeg",
        "intro": "A private nook for twelve, a communal table for eighteen, and the whole room for a hundred and forty.",
        "body_html": "<p>From rehearsal dinners and intimate anniversaries to milestone birthdays and cocktail receptions — our team plans it, our chef curates it, and our sommelier pairs it. Ask us for the private nook if you want the floral wall in your photographs.</p>",
    },
    "catering": {
        "title": "Catering",
        "eyebrow": "Off-premise",
        "hero_image": "/restaurant/image4.jpeg",
        "intro": "The Sip 'n' Dine table, at your address.",
        "body_html": "<p>Live tandoors, chaat counters, seven-course pre-plated menus, and dessert stations — set up on your lawn, in your farmhouse, or at your office. We cater from 30 guests to 3,000 across Chandigarh, Panchkula and Mohali.</p>",
    },
    "offers": {"title": "Offers & Specials", "eyebrow": "This Season", "hero_image": "/restaurant/image7.jpeg", "intro": "Everyday reasons to book the table."},
    "membership": {"title": "Privilege Membership", "eyebrow": "Coming soon", "hero_image": "/restaurant/image4.jpeg", "intro": "A quieter kind of loyalty — for guests who make this their table."},
    "book-table": {"title": "Book a Table", "eyebrow": "Reservations", "hero_image": "/restaurant/image1.jpeg", "intro": "Tell us when — we'll keep the light on."},
    "contact": {"title": "Find Us", "eyebrow": "Sector 7C · Chandigarh", "hero_image": "/restaurant/image2.jpeg", "intro": "SCO 16A, Madhya Marg — the green sign next door to Fluid."},
}


async def _seed_ai_images():
    """Background task — replace Unsplash fallbacks with AI-generated food images."""
    items = await db.menu.find({"image_url": {"$regex": "^https://images.unsplash"}}).to_list(500)
    for it in items:
        url = await _generate_food_image(f"{it['name']} — {it.get('description', '')}")
        if url:
            await db.menu.update_one({"id": it["id"]}, {"$set": {"image_url": url}})
            log.info("Generated AI image for %s", it["name"])
        await asyncio.sleep(1.5)


UNSPLASH_BY_CATEGORY = {
    "Starters": "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=800&q=80",
    "Tandoor": "https://images.unsplash.com/photo-1599487488170-d11ec9c172f0?auto=format&fit=crop&w=800&q=80",
    "Mains": "https://images.unsplash.com/photo-1588166524941-3bf61a9c41db?auto=format&fit=crop&w=800&q=80",
    "Biryani": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=800&q=80",
    "Breads": "https://images.unsplash.com/photo-1626074353765-517a681e40be?auto=format&fit=crop&w=800&q=80",
    "Desserts": "https://images.unsplash.com/photo-1587736908148-6e6da4e4c8b8?auto=format&fit=crop&w=800&q=80",
    "Drinks": "https://images.unsplash.com/photo-1544145945-f90425340c7e?auto=format&fit=crop&w=800&q=80",
}


@app.on_event("startup")
async def startup():
    # admin
    if not await db.admins.find_one({"email": ADMIN_EMAIL.lower()}):
        await db.admins.insert_one({
            "email": ADMIN_EMAIL.lower(),
            "password_hash": hash_pwd(ADMIN_PASSWORD),
            "created_at": now_iso(),
        })
        log.info("Seeded admin %s", ADMIN_EMAIL)
    # settings
    if not await db.settings.find_one({"_id": "global"}):
        s = Settings().model_dump()
        s["hours"] = [
            {"day": "Monday – Thursday", "hours": "12:30 PM – 3:30 PM · 7:30 PM – 11:00 PM"},
            {"day": "Friday – Saturday", "hours": "12:30 PM – 3:45 PM · 7:30 PM – 11:30 PM"},
            {"day": "Sunday", "hours": "12:30 PM – 3:45 PM · 7:30 PM – 11:00 PM"},
        ]
        s["social"] = {"instagram": "https://instagram.com/sipndine", "facebook": "https://facebook.com/sipndine"}
        s["logo_url"] = ""
        await db.settings.update_one({"_id": "global"}, {"$set": s}, upsert=True)
    # content
    for slug, data in SEED_CONTENT.items():
        if not await db.content.find_one({"slug": slug}):
            doc = PageContent(slug=slug, **data).model_dump()
            await db.content.insert_one(doc)
    # menu
    if await db.menu.count_documents({}) == 0:
        for i, (name, cat, desc, price, veg, sig) in enumerate(SEED_MENU):
            doc = MenuItem(
                name=name, category=cat, description=desc, price=float(price),
                veg=veg, signature=sig, order=i,
                image_url=UNSPLASH_BY_CATEGORY.get(cat, ""),
            ).model_dump()
            await db.menu.insert_one(doc)
        log.info("Seeded %d menu items", len(SEED_MENU))
    # recognition
    if await db.recognition.count_documents({}) == 0:
        for platform, rating, quote, icon, order in SEED_RECOGNITION:
            await db.recognition.insert_one(Recognition(
                platform=platform, rating=rating, quote=quote, icon=icon, order=order
            ).model_dump())
    # offers
    if await db.offers.count_documents({}) == 0:
        for i, (title, sub, desc, till) in enumerate(SEED_OFFERS):
            await db.offers.insert_one(Offer(
                title=title, subtitle=sub, description=desc, valid_till=till, order=i,
                image_url=f"/restaurant/image{(i % 5) + 3}.jpeg",
            ).model_dump())
    # tiers
    if await db.membership.count_documents({}) == 0:
        for i, (name, price, tag, benefits, hl, order) in enumerate(SEED_TIERS):
            await db.membership.insert_one(Tier(
                name=name, price=price, tagline=tag, benefits=benefits, highlighted=hl, order=order
            ).model_dump())
    # gallery
    if await db.gallery.count_documents({}) == 0:
        for i in range(1, 8):
            await db.gallery.insert_one(GalleryImage(
                url=f"/restaurant/image{i}.jpeg",
                caption="",
                order=i,
            ).model_dump())
    # background AI image regen (fire-and-forget)
    if os.environ.get("SKIP_AI_SEED") != "1":
        asyncio.create_task(_seed_ai_images())


@app.on_event("shutdown")
async def shutdown():
    client.close()
