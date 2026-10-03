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
    payload = {
        "sub": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


async def require_admin(
    creds: HTTPAuthorizationCredentials = Depends(security)
):
    if not creds:
        raise HTTPException(401, "Missing token")

    try:
        payload = jwt.decode(
            creds.credentials,
            JWT_SECRET,
            algorithms=["HS256"]
        )
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

    if not user or not verify_pwd(
        body.password,
        user["password_hash"]
    ):
        raise HTTPException(401, "Invalid credentials")

    return {
        "token": make_token(user["email"]),
        "email": user["email"]
    }


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
    phones: List[str] = [
        "+91 172 4641656",
        "+91 172 2791656"
    ]

    email: str = "info@sipndine.co.in"

    address: str = (
        "SCO 16A, Sector 7C, Madhya Marg, "
        "Chandigarh 160019 (India)"
    )

    hours: List[Dict[str, str]] = []

    social: Dict[str, str] = {}

    logo_url: str = ""

    map_embed_url: str = (
        "https://www.google.com/maps/embed?pb="
        "!1m18!1m12!1m3!1d3428.1!2d76.7794!3d30.7333"
        "!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1"
        "!3m3!1m2!1s0x0%3A0x0!2sSip%20n%20Dine%20Chandigarh"
        "!5e0!3m2!1sen!2sin!4v1700000000000"
    )


@api.get("/settings")
async def get_settings():
    s = await db.settings.find_one({"_id": "global"})

    if not s:
        return Settings().model_dump()

    s.pop("_id", None)

    return s


@api.put("/settings")
async def update_settings(
    body: Settings,
    user=Depends(require_admin)
):
    await db.settings.update_one(
        {"_id": "global"},
        {"$set": body.model_dump()},
        upsert=True
    )

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
async def upsert_content(
    slug: str,
    body: PageContent,
    user=Depends(require_admin)
):
    body.slug = slug

    await db.content.update_one(
        {"slug": slug},
        {"$set": body.model_dump()},
        upsert=True
    )

    return body.model_dump()


# ---------- menu ----------
class MenuItem(BaseModel):
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )

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
    items = await db.menu.find({}).sort(
        "order",
        1
    ).to_list(500)

    return [clean(i) for i in items]


@api.post("/admin/menu")
async def create_menu_item(
    body: MenuItem,
    user=Depends(require_admin)
):
    doc = body.model_dump()

    await db.menu.insert_one(doc)

    return clean(doc)


@api.put("/admin/menu/{item_id}")
async def update_menu_item(
    item_id: str,
    body: MenuItem,
    user=Depends(require_admin)
):
    body.id = item_id

    await db.menu.update_one(
        {"id": item_id},
        {"$set": body.model_dump()},
        upsert=True
    )

    return body.model_dump()


@api.delete("/admin/menu/{item_id}")
async def delete_menu_item(
    item_id: str,
    user=Depends(require_admin)
):
    await db.menu.delete_one({"id": item_id})

    return {"ok": True}


class ImageGenBody(BaseModel):
    prompt: str
    item_id: Optional[str] = None


async def _generate_food_image(
    prompt: str
) -> Optional[str]:

    """Generate an image via Gemini Nano Banana and return served URL."""

    if not EMERGENT_LLM_KEY:
        return None

    try:
        from emergentintegrations.llm.chat import (
            LlmChat,
            UserMessage
        )

        chat = (
            LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"img-{uuid.uuid4()}",
                system_message=(
                    "You are a professional food photographer."
                ),
            )
            .with_model(
                "gemini",
                "gemini-3.1-flash-image-preview"
            )
            .with_params(
                modalities=["image", "text"]
            )
        )

        full_prompt = (
            f"Ultra-realistic overhead food photography of {prompt}. "
            "Indian fine-dining plating on dark rustic wooden table, "
            "warm amber restaurant lighting, "
            "shallow depth of field, garnish, steam, "
            "cinematic magazine style, no text, no watermark."
        )

        _, images = await chat.send_message_multimodal_response(
            UserMessage(text=full_prompt)
        )

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
async def generate_image(
    body: ImageGenBody,
    user=Depends(require_admin)
):
    url = await _generate_food_image(body.prompt)

    if not url:
        raise HTTPException(
            500,
            "Image generation failed"
        )

    if body.item_id:
        await db.menu.update_one(
            {"id": body.item_id},
            {"$set": {"image_url": url}}
        )

    return {"image_url": url}


# ---------- gallery ----------
class GalleryImage(BaseModel):
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )

    url: str
    caption: str = ""
    order: int = 0


@api.get("/gallery")
async def list_gallery():
    items = await db.gallery.find({}).sort(
        "order",
        1
    ).to_list(200)

    return [clean(i) for i in items]


@api.post("/admin/gallery")
async def add_gallery(
    body: GalleryImage,
    user=Depends(require_admin)
):
    await db.gallery.insert_one(
        body.model_dump()
    )

    return body.model_dump()


@api.put("/admin/gallery/{gid}")
async def upd_gallery(
    gid: str,
    body: GalleryImage,
    user=Depends(require_admin)
):
    body.id = gid

    await db.gallery.update_one(
        {"id": gid},
        {"$set": body.model_dump()},
        upsert=True
    )

    return body.model_dump()


@api.delete("/admin/gallery/{gid}")
async def del_gallery(
    gid: str,
    user=Depends(require_admin)
):
    await db.gallery.delete_one({"id": gid})

    return {"ok": True}


# ---------- recognition ----------
class Recognition(BaseModel):
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )

    platform: str
    rating: str = ""
    quote: str = ""
    icon: str = ""
    order: int = 0


@api.get("/recognition")
async def list_recognition():
    return [
        clean(i)
        for i in await db.recognition.find({}).sort(
            "order",
            1
        ).to_list(50)
    ]


@api.post("/admin/recognition")
async def add_rec(
    body: Recognition,
    user=Depends(require_admin)
):
    await db.recognition.insert_one(
        body.model_dump()
    )

    return body.model_dump()


@api.put("/admin/recognition/{rid}")
async def upd_rec(
    rid: str,
    body: Recognition,
    user=Depends(require_admin)
):
    body.id = rid

    await db.recognition.update_one(
        {"id": rid},
        {"$set": body.model_dump()},
        upsert=True
    )

    return body.model_dump()


@api.delete("/admin/recognition/{rid}")
async def del_rec(
    rid: str,
    user=Depends(require_admin)
):
    await db.recognition.delete_one({"id": rid})

    return {"ok": True}


# ---------- offers ----------
class Offer(BaseModel):
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )

    title: str
    subtitle: str = ""
    description: str = ""
    valid_till: str = ""
    image_url: str = ""
    active: bool = True
    order: int = 0


@api.get("/offers")
async def list_offers():
    return [
        clean(i)
        for i in await db.offers.find({}).sort(
            "order",
            1
        ).to_list(100)
    ]


@api.post("/admin/offers")
async def add_offer(
    body: Offer,
    user=Depends(require_admin)
):
    await db.offers.insert_one(
        body.model_dump()
    )

    return body.model_dump()


@api.put("/admin/offers/{oid}")
async def upd_offer(
    oid: str,
    body: Offer,
    user=Depends(require_admin)
):
    body.id = oid

    await db.offers.update_one(
        {"id": oid},
        {"$set": body.model_dump()},
        upsert=True
    )

    return body.model_dump()


@api.delete("/admin/offers/{oid}")
async def del_offer(
    oid: str,
    user=Depends(require_admin)
):
    await db.offers.delete_one({"id": oid})

    return {"ok": True}


# ---------- membership tiers ----------
class Tier(BaseModel):
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )

    name: str
    price: str = ""
    tagline: str = ""
    benefits: List[str] = []
    highlighted: bool = False
    order: int = 0


@api.get("/membership")
async def list_tiers():
    return [
        clean(i)
        for i in await db.membership.find({}).sort(
            "order",
            1
        ).to_list(50)
    ]


@api.post("/admin/membership")
async def add_tier(
    body: Tier,
    user=Depends(require_admin)
):
    await db.membership.insert_one(
        body.model_dump()
    )

    return body.model_dump()


@api.put("/admin/membership/{tid}")
async def upd_tier(
    tid: str,
    body: Tier,
    user=Depends(require_admin)
):
    body.id = tid

    await db.membership.update_one(
        {"id": tid},
        {"$set": body.model_dump()},
        upsert=True
    )

    return body.model_dump()


@api.delete("/admin/membership/{tid}")
async def del_tier(
    tid: str,
    user=Depends(require_admin)
):
    await db.membership.delete_one({"id": tid})

    return {"ok": True}


class WaitlistEntry(BaseModel):
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )

    email: EmailStr
    created_at: str = Field(
        default_factory=now_iso
    )


@api.post("/membership/waitlist")
async def join_waitlist(body: WaitlistEntry):
    await db.waitlist.insert_one(
        body.model_dump()
    )

    return {"ok": True}


@api.get("/admin/waitlist")
async def get_waitlist(
    user=Depends(require_admin)
):
    return [
        clean(i)
        for i in await db.waitlist.find({}).sort(
            "created_at",
            -1
        ).to_list(1000)
    ]


# =========================================================
# BOOKINGS
# =========================================================

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
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )

    status: str = "pending"
    created_at: str = Field(
        default_factory=now_iso
    )


@api.post("/bookings")
async def create_booking(
    body: BookingCreate
):
    obj = Booking(
        **body.model_dump()
    )

    await db.bookings.insert_one(
        obj.model_dump()
    )

    return {
        "ok": True,
        "id": obj.id
    }


@api.get("/admin/bookings")
async def list_bookings(
    user=Depends(require_admin)
):
    return [
        clean(i)
        for i in await db.bookings.find({}).sort(
            "created_at",
            -1
        ).to_list(1000)
    ]


class BookingStatus(BaseModel):
    status: str


@api.put("/admin/bookings/{bid}")
async def update_booking(
    bid: str,
    body: BookingStatus,
    user=Depends(require_admin)
):
    await db.bookings.update_one(
        {"id": bid},
        {"$set": {"status": body.status}}
    )

    return {"ok": True}


@api.delete("/admin/bookings/{bid}")
async def delete_booking(
    bid: str,
    user=Depends(require_admin)
):
    await db.bookings.delete_one(
        {"id": bid}
    )

    return {"ok": True}


# =========================================================
# BOOKING SLOT AVAILABILITY
# =========================================================

class BookingSlot(BaseModel):
    date: str
    time: str
    full: bool = True


@api.get("/booking-slots")
async def get_booking_slots(
    date: str
):
    """
    Public endpoint.

    Returns the slots that the admin has manually
    marked as FULL for a specific date.
    """

    slots = await db.booking_slots.find(
        {
            "date": date,
            "full": True
        }
    ).to_list(100)

    return [
        {
            "date": slot["date"],
            "time": slot["time"],
            "full": slot.get("full", True)
        }
        for slot in slots
    ]


@api.get("/admin/booking-slots")
async def admin_get_booking_slots(
    date: str,
    user=Depends(require_admin)
):
    """
    Admin endpoint.

    Returns the manually blocked/full slots
    for the selected date.
    """

    slots = await db.booking_slots.find(
        {
            "date": date
        }
    ).sort(
        "time",
        1
    ).to_list(100)

    return [
        clean(slot)
        for slot in slots
    ]


@api.put("/admin/booking-slots")
async def update_booking_slot(
    body: BookingSlot,
    user=Depends(require_admin)
):
    """
    Mark a specific date/time as FULL or AVAILABLE.
    """

    if body.full:

        await db.booking_slots.update_one(
            {
                "date": body.date,
                "time": body.time
            },
            {
                "$set": {
                    "date": body.date,
                    "time": body.time,
                    "full": True
                }
            },
            upsert=True
        )

    else:

        await db.booking_slots.delete_one(
            {
                "date": body.date,
                "time": body.time
            }
        )

    return {
        "ok": True,
        "date": body.date,
        "time": body.time,
        "full": body.full
    }


# ---------- enquiries ----------
class EnquiryCreate(BaseModel):
    kind: str
    name: str
    phone: str
    email: Optional[str] = ""
    date: Optional[str] = ""
    guests: Optional[int] = None
    message: Optional[str] = ""


class Enquiry(EnquiryCreate):
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )

    created_at: str = Field(
        default_factory=now_iso
    )

    status: str = "new"


@api.post("/enquiries")
async def create_enquiry(
    body: EnquiryCreate
):
    obj = Enquiry(
        **body.model_dump()
    )

    await db.enquiries.insert_one(
        obj.model_dump()
    )

    return {
        "ok": True,
        "id": obj.id
    }


@api.get("/admin/enquiries")
async def list_enquiries(
    user=Depends(require_admin)
):
    return [
        clean(i)
        for i in await db.enquiries.find({}).sort(
            "created_at",
            -1
        ).to_list(1000)
    ]


@api.put("/admin/enquiries/{eid}")
async def upd_enquiry(
    eid: str,
    body: BookingStatus,
    user=Depends(require_admin)
):
    await db.enquiries.update_one(
        {"id": eid},
        {"$set": {"status": body.status}}
    )

    return {"ok": True}


@api.delete("/admin/enquiries/{eid}")
async def del_enquiry(
    eid: str,
    user=Depends(require_admin)
):
    await db.enquiries.delete_one(
        {"id": eid}
    )

    return {"ok": True}


# ---------- root ----------
@api.get("/")
async def root():
    return {
        "service": "sip-n-dine",
        "ok": True
    }


app.include_router(api)

app.mount(
    "/api/uploads",
    StaticFiles(directory=str(UPLOADS_DIR)),
    name="uploads"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get(
        "CORS_ORIGINS",
        "*"
    ).split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- seed on startup ----------
SEED_MENU = [

    # =====================================================
    # SIZZLERS
    # =====================================================

    (
        "Vegetable Steak",
        "Sizzlers",
        "Assorted vegetables served with sauce and vegetables.",
        704,
        True,
        False
    ),
    (
        "Paneer Shashlik",
        "Sizzlers",
        "Paneer cooked in a spicy red sauce served with baked vegetables.",
        749,
        True,
        False
    ),
    (
        "Chicken Shashlik",
        "Sizzlers",
        "Chicken steak served with vegetables.",
        828,
        False,
        False
    ),
    (
        "Sizzling Chicken Chunks",
        "Sizzlers",
        "Chicken chunks with vegetables served sizzling.",
        828,
        False,
        False
    ),


    # =====================================================
    # SANDWICHES
    # =====================================================

    (
        "Chicken S/W",
        "Sandwiches",
        "",
        429,
        False,
        False
    ),
    (
        "Vegetable S/W",
        "Sandwiches",
        "",
        379,
        True,
        False
    ),
    (
        "Cheese S/W",
        "Sandwiches",
        "",
        379,
        True,
        False
    ),
    (
        "Egg S/W",
        "Sandwiches",
        "",
        379,
        False,
        False
    ),
    (
        "Plain Garlic Bread",
        "Sandwiches",
        "",
        219,
        True,
        False
    ),
    (
        "Garlic Bread with Cheese",
        "Sandwiches",
        "",
        249,
        True,
        False
    ),


    # =====================================================
    # PASTAS
    # =====================================================

    (
        "Vegetarian Pasta",
        "Pastas",
        "Arrabita Sauce / Tomato",
        436,
        True,
        False
    ),
    (
        "Mushroom Pasta",
        "Pastas",
        "Arrabita Sauce / Tomato",
        480,
        True,
        False
    ),
    (
        "Chicken Pasta",
        "Pastas",
        "Arrabita Sauce / Tomato",
        589,
        False,
        False
    ),


    # =====================================================
    # CUTLETS
    # =====================================================

    (
        "Pepper Cutlets",
        "Cutlets",
        "",
        599,
        False,
        False
    ),
    (
        "Vegetable Cutlets",
        "Cutlets",
        "",
        391,
        True,
        False
    ),
    (
        "Mutton Cutlets",
        "Cutlets",
        "",
        727,
        False,
        False
    ),
    (
        "Chicken Cutlets",
        "Cutlets",
        "",
        682,
        False,
        False
    ),


    # =====================================================
    # CHINESE — NON-VEGETARIAN
    # =====================================================

    (
        "Chicken Schezwan",
        "Chinese - Non-Vegetarian",
        "",
        794,
        False,
        False
    ),
    (
        "Chicken in Black Pepper Sauce",
        "Chinese - Non-Vegetarian",
        "",
        794,
        False,
        False
    ),
    (
        "Lemon Chicken",
        "Chinese - Non-Vegetarian",
        "",
        794,
        False,
        False
    ),
    (
        "Garlic Chicken",
        "Chinese - Non-Vegetarian",
        "",
        794,
        False,
        False
    ),
    (
        "Honey Ginger Chicken",
        "Chinese - Non-Vegetarian",
        "",
        794,
        False,
        False
    ),
    (
        "Chicken Manchurian in Gravy",
        "Chinese - Non-Vegetarian",
        "",
        794,
        False,
        False
    ),
    (
        "Chicken Chilly in Dry",
        "Chinese - Non-Vegetarian",
        "",
        794,
        False,
        False
    ),
    (
        "Chicken Chilly in Gravy",
        "Chinese - Non-Vegetarian",
        "",
        794,
        False,
        False
    ),
    (
        "Chicken Sweet & Sour",
        "Chinese - Non-Vegetarian",
        "",
        794,
        False,
        False
    ),
    (
        "Kung Pao Chicken",
        "Chinese - Non-Vegetarian",
        "",
        794,
        False,
        False
    ),


    # =====================================================
    # CHINESE — VEGETARIAN
    # =====================================================

    (
        "Boiled Vegetable",
        "Chinese - Vegetarian",
        "",
        525,
        True,
        False
    ),
    (
        "Baked Vegetable",
        "Chinese - Vegetarian",
        "",
        525,
        True,
        False
    ),
    (
        "Almond Vegetable",
        "Chinese - Vegetarian",
        "",
        525,
        True,
        False
    ),
    (
        "Vegetable Manchurian in Gravy",
        "Chinese - Vegetarian",
        "",
        648,
        True,
        False
    ),
    (
        "Chilly Mushroom in Gravy",
        "Chinese - Vegetarian",
        "",
        648,
        True,
        False
    ),
    (
        "Cheese Chilly in Gravy",
        "Chinese - Vegetarian",
        "",
        648,
        True,
        False
    ),
    (
        "Vegetable Sweet & Sour",
        "Chinese - Vegetarian",
        "",
        525,
        True,
        False
    ),
    (
        "Vegetables in Schezwan Sauce",
        "Chinese - Vegetarian",
        "",
        525,
        True,
        False
    ),


    # =====================================================
    # CHINESE — CHOPSEY
    # =====================================================

    (
        "Vegetable Chopsuey",
        "Chinese - Chopsey",
        "",
        548,
        True,
        False
    ),
    (
        "Chicken Chopsuey",
        "Chinese - Chopsey",
        "",
        749,
        False,
        False
    ),
    (
        "American Chopsuey",
        "Chinese - Chopsey",
        "",
        749,
        False,
        False
    ),


    # =====================================================
    # CHINESE — NOODLES
    # =====================================================

    (
        "Chicken Hakka Noodles",
        "Chinese - Noodles",
        "",
        525,
        False,
        False
    ),
    (
        "Vegetable Hakka Noodles",
        "Chinese - Noodles",
        "",
        436,
        True,
        False
    ),
    (
        "Chicken Chow Mein",
        "Chinese - Noodles",
        "",
        525,
        False,
        False
    ),
    (
        "Vegetable Chow Mein",
        "Chinese - Noodles",
        "",
        436,
        True,
        False
    ),
    (
        "Chilly Garlic Noodles",
        "Chinese - Noodles",
        "",
        436,
        True,
        False
    ),


    # =====================================================
    # CHINESE — RICE
    # =====================================================

    (
        "Chicken Fried Rice",
        "Chinese - Rice",
        "",
        459,
        False,
        False
    ),
    (
        "Golden Chicken Rice",
        "Chinese - Rice",
        "",
        459,
        False,
        False
    ),
    (
        "Fish Fried Rice",
        "Chinese - Rice",
        "",
        519,
        False,
        False
    ),
    (
        "Prawn Fried Rice",
        "Chinese - Rice",
        "",
        869,
        False,
        False
    ),
    (
        "Egg Fried Rice",
        "Chinese - Rice",
        "",
        389,
        False,
        False
    ),
    (
        "Vegetable Fried Rice",
        "Chinese - Rice",
        "",
        319,
        True,
        False
    ),


    # =====================================================
    # STARTERS — MEAT & POULTRY
    # =====================================================

    (
        "Chilly Chicken (With Bone)",
        "Starters - Meat & Poultry",
        "Pieces of fried chicken cooked in capsicum, onions and Chinese herbs.",
        760,
        False,
        False
    ),
    (
        "Chilly Chicken (Boneless)",
        "Starters - Meat & Poultry",
        "Boneless pieces of fried chicken cooked in capsicum and onions.",
        783,
        False,
        False
    ),
    (
        "Chicken Tandoori",
        "Starters - Meat & Poultry",
        "Tender chicken marinated in yoghurt and spices, grilled in the tandoor.",
        727,
        False,
        True
    ),
    (
        "Chicken Tangri Kabab",
        "Starters - Meat & Poultry",
        "Chicken drumsticks marinated in yoghurt and spices, grilled in the tandoor.",
        794,
        False,
        False
    ),
    (
        "Chicken Kalmi Kabab",
        "Starters - Meat & Poultry",
        "Chicken drumsticks delicately marinated with traditional Indian spices and broiled.",
        760,
        False,
        False
    ),
    (
        "Chicken Tikka",
        "Starters - Meat & Poultry",
        "Chicken nuggets marinated in tandoori masala and grilled in the tandoor.",
        783,
        False,
        True
    ),
    (
        "Murg Malai Tikka",
        "Starters - Meat & Poultry",
        "Chicken nuggets marinated in tandoori masala and grilled in the tandoor.",
        783,
        False,
        True
    ),
    (
        "Chicken Chakori Kabab",
        "Starters - Meat & Poultry",
        "A true delight where minced chicken is coated with a blend of spices.",
        861,
        False,
        False
    ),
    (
        "Chicken Seekh Kabab",
        "Starters - Meat & Poultry",
        "Finely minced chicken enhanced with fresh coriander and spices.",
        760,
        False,
        False
    ),
    (
        "Chicken Spring Roll",
        "Starters - Meat & Poultry",
        "Rolls consisting of a savoury mixture of chicken and vegetables rolled in a thin pancake and fried.",
        760,
        False,
        False
    ),
    (
        "Chicken Kurkib",
        "Starters - Meat & Poultry",
        "",
        760,
        False,
        False
    ),
    (
        "Non-Veg Platter",
        "Starters - Meat & Poultry",
        "",
        1376,
        False,
        True
    ),
    (
        "Chicken Manchurian",
        "Starters - Meat & Poultry",
        "Finely chopped minced chicken bound with some corn flour and served in a sauce.",
        760,
        False,
        False
    ),
    (
        "Chicken Lolly Pop",
        "Starters - Meat & Poultry",
        "Chicken wings shaped into lollipops, delicately spiced and fried crisp.",
        760,
        False,
        False
    ),
    (
        "Mutton Seekh Kabab",
        "Starters - Meat & Poultry",
        "Finely minced lamb enhanced with fresh coriander and spices.",
        783,
        False,
        False
    ),
    (
        "Honey Fried Chicken Wings",
        "Starters - Meat & Poultry",
        "Chicken wings flavoured in honey and barbecue sauce.",
        760,
        False,
        False
    ),
    (
        "Chicken Pakora",
        "Starters - Meat & Poultry",
        "Succulent chunks of chicken marinated in spices and deep fried.",
        760,
        False,
        False
    ),
    (
        "Chicken Salt & Pepper",
        "Starters - Meat & Poultry",
        "Chicken coated with light cornflour batter and sauteed in onions, green pepper, garlic, chilli and herbs.",
        760,
        False,
        False
    ),
    (
        "Lemon Chicken",
        "Starters - Meat & Poultry",
        "",
        760,
        False,
        False
    ),
    (
        "Afgani Chicken",
        "Starters - Meat & Poultry",
        "",
        839,
        False,
        False
    ),
    (
        "Egg Bhurjee",
        "Starters - Meat & Poultry",
        "",
        279,
        False,
        False
    ),
    (
        "Omelette",
        "Starters - Meat & Poultry",
        "",
        279,
        False,
        False
    ),
    (
        "Boiled Egg (Three Pcs)",
        "Starters - Meat & Poultry",
        "",
        279,
        False,
        False
    ),


    # =====================================================
    # STARTERS — VEGETARIAN
    # =====================================================

    (
        "Paneer Tikka",
        "Starters - Vegetarian",
        "",
        615,
        True,
        True
    ),
    (
        "Paneer Haryali Tikka",
        "Starters - Vegetarian",
        "",
        615,
        True,
        False
    ),
    (
        "Paneer Achari Tikka",
        "Starters - Vegetarian",
        "",
        615,
        True,
        False
    ),
    (
        "Paneer Bahari Tikka",
        "Starters - Vegetarian",
        "",
        615,
        True,
        False
    ),
    (
        "Paneer Papadi",
        "Starters - Vegetarian",
        "",
        615,
        True,
        False
    ),
    (
        "Cheese Finger",
        "Starters - Vegetarian",
        "",
        615,
        True,
        False
    ),
    (
        "Paneer Pakora",
        "Starters - Vegetarian",
        "",
        615,
        True,
        False
    ),
    (
        "Paneer Roll",
        "Starters - Vegetarian",
        "",
        615,
        True,
        False
    ),
    (
        "Cheese Chilly Dry",
        "Starters - Vegetarian",
        "",
        615,
        True,
        False
    ),
    (
        "Tandoori Broccoli",
        "Starters - Vegetarian",
        "",
        604,
        True,
        False
    ),
    (
        "Soya Malai Champ",
        "Starters - Vegetarian",
        "",
        660,
        True,
        False
    ),
    (
        "Soya Mint Champ",
        "Starters - Vegetarian",
        "",
        660,
        True,
        False
    ),
    (
        "Hara Bhara Kabab",
        "Starters - Vegetarian",
        "",
        492,
        True,
        False
    ),
    (
        "Veg. Platter",
        "Starters - Vegetarian",
        "",
        1040,
        True,
        True
    ),
    (
        "Honey Chilly Cauliflower",
        "Starters - Vegetarian",
        "",
        368,
        True,
        False
    ),
    (
        "Peanut Masala / Plain",
        "Starters - Vegetarian",
        "",
        245,
        True,
        False
    ),
    (
        "Crispy Corn",
        "Starters - Vegetarian",
        "",
        413,
        True,
        False
    ),
    (
        "Vegetable Cocktail Kabab",
        "Starters - Vegetarian",
        "",
        447,
        True,
        False
    ),
    (
        "Punjabi Papad",
        "Starters - Vegetarian",
        "",
        100,
        True,
        False
    ),
    (
        "Fried Papad",
        "Starters - Vegetarian",
        "",
        100,
        True,
        False
    ),
    (
        "Masala Papad",
        "Starters - Vegetarian",
        "",
        133,
        True,
        False
    ),
    (
        "Potato Chips",
        "Starters - Vegetarian",
        "",
        245,
        True,
        False
    ),
    (
        "Mixed Pakora",
        "Starters - Vegetarian",
        "",
        357,
        True,
        False
    ),
    (
        "Peanut Plain",
        "Starters - Vegetarian",
        "",
        245,
        True,
        False
    ),
    (
        "Cheese Kabab",
        "Starters - Vegetarian",
        "",
        615,
        True,
        False
    ),
    (
        "Kurkuri Kabab",
        "Starters - Vegetarian",
        "",
        447,
        True,
        False
    ),
    (
        "Vegetable Seekh Kabab",
        "Starters - Vegetarian",
        "",
        536,
        True,
        False
    ),
    (
        "Stuffed Potato",
        "Starters - Vegetarian",
        "",
        536,
        True,
        False
    ),
    (
        "Mushroom Tikka",
        "Starters - Vegetarian",
        "",
        615,
        True,
        False
    ),
    (
        "Mushroom Achari Tikka",
        "Starters - Vegetarian",
        "",
        615,
        True,
        False
    ),
    (
        "Stuffed Mushroom",
        "Starters - Vegetarian",
        "",
        660,
        True,
        False
    ),
    (
        "Mushroom Chilly",
        "Starters - Vegetarian",
        "",
        660,
        True,
        False
    ),
    (
        "Vegetable Salt & Pepper",
        "Starters - Vegetarian",
        "",
        447,
        True,
        False
    ),
    (
        "Vegetable Manchurian",
        "Starters - Vegetarian",
        "",
        447,
        True,
        False
    ),
    (
        "Golden Fried Baby Corn",
        "Starters - Vegetarian",
        "",
        615,
        True,
        False
    ),
    (
        "Spinach & Cheese Spring Roll",
        "Starters - Vegetarian",
        "",
        559,
        True,
        False
    ),
    (
        "Vegetable Spring Roll",
        "Starters - Vegetarian",
        "",
        536,
        True,
        False
    ),
    (
        "Honey Potato",
        "Starters - Vegetarian",
        "",
        368,
        True,
        False
    ),
    (
        "Aloo Chana Chat",
        "Starters - Vegetarian",
        "",
        391,
        True,
        False
    ),
    (
        "Chana Chat",
        "Starters - Vegetarian",
        "",
        447,
        True,
        False
    ),
    (
        "Fried Aloo Chat",
        "Starters - Vegetarian",
        "",
        301,
        True,
        False
    ),
    (
        "Fruit Chat",
        "Starters - Vegetarian",
        "",
        346,
        True,
        False
    ),
    (
        "Corn Salad",
        "Starters - Vegetarian",
        "",
        413,
        True,
        False
    ),
    (
        "Bhalla Chat Papdi",
        "Starters - Vegetarian",
        "",
        447,
        True,
        False
    ),
    (
        "BharwaGolGappa",
        "Starters - Vegetarian",
        "",
        301,
        True,
        False
    ),
    (
        "Corn Chat",
        "Starters - Vegetarian",
        "",
        413,
        True,
        False
    ),


    # =====================================================
    # SEAFOOD STARTERS
    # =====================================================

    (
        "Fish Tikka",
        "Starters - Seafood",
        "",
        940,
        False,
        False
    ),
    (
        "Fish Finger",
        "Starters - Seafood",
        "",
        940,
        False,
        False
    ),
    (
        "Lemon Fish",
        "Starters - Seafood",
        "",
        940,
        False,
        False
    ),
    (
        "Fish Chilly",
        "Starters - Seafood",
        "",
        940,
        False,
        False
    ),
    (
        "Golden Frien Fish",
        "Starters - Seafood",
        "",
        940,
        False,
        False
    ),
    (
        "Afgani Fish",
        "Starters - Seafood",
        "",
        940,
        False,
        False
    ),
    (
        "Fish Fry",
        "Starters - Seafood",
        "",
        940,
        False,
        False
    ),
    (
        "Fish Amritsari",
        "Starters - Seafood",
        "",
        940,
        False,
        False
    ),
    (
        "Golden Fried Prawns",
        "Starters - Seafood",
        "",
        1679,
        False,
        False
    ),
    (
        "Tandoori Prawns",
        "Starters - Seafood",
        "",
        1679,
        False,
        False
    ),
    (
        "Tandoori Pomfret",
        "Starters - Seafood",
        "",
        996,
        False,
        False
    ),


    # =====================================================
    # INDIAN NON-VEGETARIAN — CHICKEN
    # =====================================================

    (
        "Karahi Chicken (Full/Half)",
        "Indian Non-Vegetarian - Chicken",
        "",
        1220.00,
        False,
        True
    ),
    (
        "Butter Chicken (Full/Half)",
        "Indian Non-Vegetarian - Chicken",
        "",
        1220.00,
        False,
        True
    ),
    (
        "Butter Chicken (Boneless)",
        "Indian Non-Vegetarian - Chicken",
        "",
        1220.00,
        False,
        False
    ),
    (
        "Chicken Musalam (Full/Half)",
        "Indian Non-Vegetarian - Chicken",
        "",
        1220.00,
        False,
        False
    ),
    (
        "Chicken Tikka Tak (Full/Half)",
        "Indian Non-Vegetarian - Chicken",
        "",
        1220.00,
        False,
        False
    ),
    (
        "Chicken Shahi",
        "Indian Non-Vegetarian - Chicken",
        "",
        805,
        False,
        False
    ),
    (
        "Chicken Tikka Lababdar",
        "Indian Non-Vegetarian - Chicken",
        "",
        805,
        False,
        False
    ),
    (
        "Achari Chicken",
        "Indian Non-Vegetarian - Chicken",
        "",
        805,
        False,
        False
    ),
    (
        "Chicken Dahiwala",
        "Indian Non-Vegetarian - Chicken",
        "",
        805,
        False,
        False
    ),
    (
        "Chicken Curry",
        "Indian Non-Vegetarian - Chicken",
        "",
        805,
        False,
        False
    ),
    (
        "Chicken Rahra",
        "Indian Non-Vegetarian - Chicken",
        "",
        805,
        False,
        False
    ),
    (
        "Chicken in Palak",
        "Indian Non-Vegetarian - Chicken",
        "",
        805,
        False,
        False
    ),
    (
        "Chicken Methi Malai",
        "Indian Non-Vegetarian - Chicken",
        "",
        805,
        False,
        False
    ),
    (
        "Afgani Chicken",
        "Indian Non-Vegetarian - Chicken",
        "",
        805,
        False,
        False
    ),
    (
        "Chicken Masala",
        "Indian Non-Vegetarian - Chicken",
        "",
        805,
        False,
        False
    ),


    # =====================================================
    # INDIAN NON-VEGETARIAN — MUTTON
    # =====================================================

    (
        "Handi Meat",
        "Indian Non-Vegetarian - Mutton",
        "",
        850,
        False,
        False
    ),
    (
        "Mutton Curry",
        "Indian Non-Vegetarian - Mutton",
        "",
        850,
        False,
        False
    ),
    (
        "Mutton Rogan Josh",
        "Indian Non-Vegetarian - Mutton",
        "",
        850,
        False,
        True
    ),
    (
        "Mirchi Korma",
        "Indian Non-Vegetarian - Mutton",
        "",
        850,
        False,
        False
    ),
    (
        "Saag Meat",
        "Indian Non-Vegetarian - Mutton",
        "",
        850,
        False,
        False
    ),
    (
        "Rarha Meat",
        "Indian Non-Vegetarian - Mutton",
        "",
        850,
        False,
        False
    ),
    (
        "Mutton Yakhni",
        "Indian Non-Vegetarian - Mutton",
        "",
        850,
        False,
        False
    ),


    # =====================================================
    # INDIAN NON-VEGETARIAN — FISH
    # =====================================================

    (
        "Fish Tomato",
        "Indian Non-Vegetarian - Fish",
        "",
        940,
        False,
        False
    ),
    (
        "Fish Curry",
        "Indian Non-Vegetarian - Fish",
        "",
        940,
        False,
        False
    ),
    (
        "Fish Goan Curry",
        "Indian Non-Vegetarian - Fish",
        "",
        940,
        False,
        False
    ),
    (
        "Banarsi Fish",
        "Indian Non-Vegetarian - Fish",
        "",
        940,
        False,
        False
    ),
    (
        "Egg Curry",
        "Indian Non-Vegetarian - Fish",
        "",
        514,
        False,
        False
    ),


    # =====================================================
    # INDIAN VEGETARIAN — CLEAR ITEMS
    # =====================================================

    (
        "Paneer Do Pyaza",
        "Indian Vegetarian",
        "",
        660,
        True,
        False
    ),
    (
        "Paneer Butter Masala",
        "Indian Vegetarian",
        "",
        660,
        True,
        True
    ),
    (
        "Achari Paneer",
        "Indian Vegetarian",
        "",
        660,
        True,
        False
    ),
    (
        "Paneer Pasanda",
        "Indian Vegetarian",
        "",
        660,
        True,
        False
    ),
    (
        "Paneer Tikka Masala",
        "Indian Vegetarian",
        "",
        660,
        True,
        False
    ),
    (
        "Paneer Bhurji",
        "Indian Vegetarian",
        "",
        660,
        True,
        False
    ),
    (
        "Dal Paneer",
        "Indian Vegetarian",
        "",
        660,
        True,
        False
    ),
    (
        "Cheese Tomato",
        "Indian Vegetarian",
        "",
        660,
        True,
        False
    ),
    (
        "Shahi Paneer",
        "Indian Vegetarian",
        "",
        660,
        True,
        False
    ),
    (
        "Palak Paneer",
        "Indian Vegetarian",
        "",
        660,
        True,
        False
    ),
    (
        "Mutter Paneer",
        "Indian Vegetarian",
        "",
        660,
        True,
        False
    ),
    (
        "Khumb Do Pyaza",
        "Indian Vegetarian",
        "",
        660,
        True,
        False
    ),
    (
        "Mushroom Mutter",
        "Indian Vegetarian",
        "",
        660,
        True,
        False
    ),
    (
        "Mushroom Lazziz",
        "Indian Vegetarian",
        "",
        660,
        True,
        False
    ),
    (
        "Mushroom Capsicum Achari",
        "Indian Vegetarian",
        "",
        660,
        True,
        False
    ),
    (
        "Navratan Korma",
        "Indian Vegetarian",
        "",
        682,
        True,
        False
    ),
    (
        "Asparagus Korma",
        "Indian Vegetarian",
        "",
        682,
        True,
        False
    ),
    (
        "Malai Kofta",
        "Indian Vegetarian",
        "",
        682,
        True,
        False
    ),
    (
        "Paneer Kofta in Cashewnut Gravy",
        "Indian Vegetarian",
        "",
        682,
        True,
        False
    ),
    (
        "Mutter Methi",
        "Indian Vegetarian",
        "",
        682,
        True,
        False
    ),
    (
        "Palak Kofta",
        "Indian Vegetarian",
        "",
        637,
        True,
        False
    ),
    (
        "Palak Corn",
        "Indian Vegetarian",
        "",
        637,
        True,
        False
    ),
    (
        "Kulfi Bhindi",
        "Indian Vegetarian",
        "",
        525,
        True,
        False
    ),


    # =====================================================
    # INDIAN VEGETARIAN — RIGHT COLUMN
    # =====================================================

    (
        "Dum Aloo Kashmiri",
        "Indian Vegetarian",
        "",
        525,
        True,
        False
    ),
    (
        "Dum Aloo Rajasthani",
        "Indian Vegetarian",
        "",
        525,
        True,
        False
    ),
    (
        "Chana Masala",
        "Indian Vegetarian",
        "",
        536,
        True,
        False
    ),
    (
        "Channa Peshawari",
        "Indian Vegetarian",
        "",
        536,
        True,
        False
    ),
    (
        "Dal Makhni",
        "Indian Vegetarian",
        "",
        536,
        True,
        True
    ),
    (
        "Dal Tadka",
        "Indian Vegetarian",
        "",
        525,
        True,
        False
    ),
    (
        "Mixed Vegetables",
        "Indian Vegetarian",
        "",
        525,
        True,
        False
    ),
    (
        "Vegetable Jalfrezi",
        "Indian Vegetarian",
        "",
        525,
        True,
        False
    ),
    (
        "Zeera Aloo",
        "Indian Vegetarian",
        "",
        525,
        True,
        False
    ),
    (
        "Gobi Mutter",
        "Indian Vegetarian",
        "",
        525,
        True,
        False
    ),
    (
        "Seasonal Vegetable",
        "Indian Vegetarian",
        "",
        525,
        True,
        False
    ),
    (
        "Exotic Veg Mix",
        "Indian Vegetarian",
        "",
        525,
        True,
        False
    ),
    (
        "Corn Capsicum Masala",
        "Indian Vegetarian",
        "",
        525,
        True,
        False
    ),
    (
        "Dum Aloo Chutney Wala",
        "Indian Vegetarian",
        "",
        525,
        True,
        False
    ),
    (
        "Chura Pyao",
        "Indian Vegetarian",
        "",
        525,
        True,
        False
    ),
    (
        "Soya Keema Mutter",
        "Indian Vegetarian",
        "",
        525,
        True,
        False
    ),
    (
        "Virkha Palak",
        "Indian Vegetarian",
        "",
        525,
        True,
        False
    ),
    (
        "Baby Corn Jalfrezi",
        "Indian Vegetarian",
        "",
        536,
        True,
        False
    ),
    (
        "Achari Aloo",
        "Indian Vegetarian",
        "",
        525,
        True,
        False
    ),
    (
        "Boiled Vegetable",
        "Indian Vegetarian",
        "",
        525,
        True,
        False
    ),
    (
        "Gobi Masala / Gobi Mutter",
        "Indian Vegetarian",
        "",
        525,
        True,
        False
    ),
    (
        "Bhindi Masala",
        "Indian Vegetarian",
        "",
        525,
        True,
        False
    ),
    (
        "Vegetable Kofta",
        "Indian Vegetarian",
        "",
        525,
        True,
        False
    ),


    # =====================================================
    # SALADS
    # =====================================================

    (
        "Green Salad",
        "Salads",
        "",
        200,
        True,
        False
    ),
    (
        "Crispy Salad",
        "Salads",
        "",
        200,
        True,
        False
    ),
    (
        "Kachumber Salad",
        "Salads",
        "",
        200,
        True,
        False
    ),
    (
        "Russian Salad",
        "Salads",
        "",
        324,
        True,
        False
    ),
    (
        "Fruit Salad",
        "Salads",
        "",
        368,
        True,
        False
    ),
    (
        "Onion Salad",
        "Salads",
        "",
        156,
        True,
        False
    ),
    (
        "Chicken Pineapple Salad",
        "Salads",
        "",
        405,
        False,
        False
    ),


    # =====================================================
    # RAITA
    # =====================================================

    (
        "Pineapple Mint Raita",
        "Raita",
        "",
        256,
        True,
        False
    ),
    (
        "Dahi Raita",
        "Raita",
        "",
        162,
        True,
        False
    ),
    (
        "Boondi Raita",
        "Raita",
        "",
        162,
        True,
        False
    ),
    (
        "Aloo Mint Raita",
        "Raita",
        "",
        162,
        True,
        False
    ),
    (
        "Mix Raita",
        "Raita",
        "",
        162,
        True,
        False
    ),
    (
        "Plain Raita",
        "Raita",
        "",
        144,
        True,
        False
    ),


    # =====================================================
    # NAAN / ROTI
    # =====================================================

    (
        "Roti",
        "Naan / Roti",
        "",
        66,
        True,
        False
    ),
    (
        "Butter Roti",
        "Naan / Roti",
        "",
        78,
        True,
        False
    ),
    (
        "Laccha Paratha",
        "Naan / Roti",
        "",
        95,
        True,
        False
    ),
    (
        "Butter Naan",
        "Naan / Roti",
        "",
        111,
        True,
        False
    ),
    (
        "Garlic Naan",
        "Naan / Roti",
        "",
        144,
        True,
        False
    ),
    (
        "Roomali Roti",
        "Naan / Roti",
        "",
        144,
        True,
        False
    ),
    (
        "Missi Roti",
        "Naan / Roti",
        "",
        111,
        True,
        False
    ),
    (
        "Pudina Paratha",
        "Naan / Roti",
        "",
        111,
        True,
        False
    ),
    (
        "Onion Kulcha",
        "Naan / Roti",
        "",
        161,
        True,
        False
    ),
    (
        "Vegetable Paratha",
        "Naan / Roti",
        "",
        161,
        True,
        False
    ),
    (
        "Mutton Keema Naan with Gravy",
        "Naan / Roti",
        "",
        458,
        False,
        False
    ),
    (
        "Chicken Keema Naan with Gravy",
        "Naan / Roti",
        "",
        458,
        False,
        False
    ),
    (
        "Paneer Naan with Gravy",
        "Naan / Roti",
        "",
        357,
        True,
        False
    ),
    (
        "Ajwain Paratha",
        "Naan / Roti",
        "",
        100,
        True,
        False
    ),
    (
        "Lal Mirch Paratha",
        "Naan / Roti",
        "",
        100,
        True,
        False
    ),
    (
        "Green Mirch Paratha",
        "Naan / Roti",
        "",
        100,
        True,
        False
    ),
    (
        "Onion Mix",
        "Naan / Roti",
        "",
        100,
        True,
        False
    ),


    # =====================================================
    # BIRYANI / PULAO
    # =====================================================

    (
        "Chicken Biryani (Full/Half)",
        "Biryani / Pulao",
        "",
        749,
        False,
        True
    ),
    (
        "Mutton Biryani (Full/Half)",
        "Biryani / Pulao",
        "",
        749,
        False,
        True
    ),
    (
        "Vegetable Biryani (Half/Full)",
        "Biryani / Pulao",
        "",
        660,
        True,
        False
    ),
    (
        "Kashmiri Pulao",
        "Biryani / Pulao",
        "",
        413,
        True,
        False
    ),
    (
        "Peas Pulao",
        "Biryani / Pulao",
        "",
        346,
        True,
        False
    ),
    (
        "Vegetable Pulao",
        "Biryani / Pulao",
        "",
        365,
        True,
        False
    ),
    (
        "Jeera Rice",
        "Biryani / Pulao",
        "",
        290,
        True,
        False
    ),
    (
        "Plain Rice",
        "Biryani / Pulao",
        "",
        290,
        True,
        False
    ),


    # =====================================================
    # SOUPS — CHINESE
    # =====================================================

    (
        "Sweet Corn Soup - Chicken",
        "Soups - Chinese",
        "",
        312,
        False,
        False
    ),
    (
        "Sweet Corn Soup - Vegetable",
        "Soups - Chinese",
        "",
        290,
        True,
        False
    ),
    (
        "Talumein Soup - Chicken",
        "Soups - Chinese",
        "",
        312,
        False,
        False
    ),
    (
        "Talumein Soup - Vegetable",
        "Soups - Chinese",
        "",
        290,
        True,
        False
    ),
    (
        "Hot & Sour Soup - Chicken",
        "Soups - Chinese",
        "",
        312,
        False,
        False
    ),
    (
        "Hot & Sour Soup - Vegetable",
        "Soups - Chinese",
        "",
        290,
        True,
        False
    ),
    (
        "Clear Soup - Chicken",
        "Soups - Chinese",
        "",
        312,
        False,
        False
    ),
    (
        "Clear Soup - Vegetable",
        "Soups - Chinese",
        "",
        290,
        True,
        False
    ),
    (
        "Munchow Soup - Chicken",
        "Soups - Chinese",
        "",
        312,
        False,
        False
    ),
    (
        "Munchow Soup - Vegetable",
        "Soups - Chinese",
        "",
        290,
        True,
        False
    ),


    # =====================================================
    # SOUPS — INDIAN
    # =====================================================

    (
        "Badam Shorba",
        "Soups - Indian",
        "",
        312,
        True,
        False
    ),
    (
        "Tomato Shorba",
        "Soups - Indian",
        "",
        290,
        True,
        False
    ),
    (
        "Murg Yakhni Shorba",
        "Soups - Indian",
        "",
        290,
        False,
        False
    ),
    (
        "Mushroom Shorba",
        "Soups - Indian",
        "",
        290,
        True,
        False
    ),
    (
        "Sip 'n' Dine Special Shorba",
        "Soups - Indian",
        "",
        312,
        False,
        True
    ),
    (
        "Cream of Mushroom",
        "Soups - Indian",
        "",
        290,
        True,
        False
    ),
    (
        "Cream of Tomato",
        "Soups - Indian",
        "",
        290,
        True,
        False
    ),
    (
        "Lemon Coriander",
        "Soups - Indian",
        "",
        290,
        True,
        False
    ),


    # =====================================================
    # DESSERTS & ICE CREAMS
    # =====================================================

    (
        "Tutti Fruity",
        "Desserts & Ice Creams",
        "",
        234,
        True,
        False
    ),
    (
        "Hot Chocolate Fudge with Brownie",
        "Desserts & Ice Creams",
        "",
        402,
        True,
        False
    ),
    (
        "Sizzling Brownie",
        "Desserts & Ice Creams",
        "",
        402,
        True,
        True
    ),
    (
        "Ice Cream Boat",
        "Desserts & Ice Creams",
        "",
        346,
        True,
        False
    ),
    (
        "Fruit Cream",
        "Desserts & Ice Creams",
        "",
        346,
        True,
        False
    ),
    (
        "Gulab Jamun (3 pcs)",
        "Desserts & Ice Creams",
        "",
        156,
        True,
        False
    ),
    (
        "Rasmalai (2 pcs)",
        "Desserts & Ice Creams",
        "",
        212,
        True,
        False
    ),
    (
        "Cold Kheer",
        "Desserts & Ice Creams",
        "",
        156,
        True,
        False
    ),
    (
        "Dakka Kulfi (as per availability)",
        "Desserts & Ice Creams",
        "",
        125,
        True,
        False
    ),
    (
        "Moong Dal Halwa",
        "Desserts & Ice Creams",
        "",
        234,
        True,
        False
    ),
    (
        "Gajer Halwa (as per availability)",
        "Desserts & Ice Creams",
        "",
        200,
        True,
        False
    ),
    (
        "Jalebi (as per availability)",
        "Desserts & Ice Creams",
        "",
        200,
        True,
        False
    ),
    (
        "Chocolate Ice Cream",
        "Desserts & Ice Creams",
        "",
        212,
        True,
        False
    ),
    (
        "Vanilla Ice Cream",
        "Desserts & Ice Creams",
        "",
        189,
        True,
        False
    ),
    (
        "Strawberry Ice Cream",
        "Desserts & Ice Creams",
        "",
        189,
        True,
        False
    ),
    (
        "Mango Ice Cream",
        "Desserts & Ice Creams",
        "",
        189,
        True,
        False
    ),
    (
        "Black Current Ice Cream",
        "Desserts & Ice Creams",
        "",
        189,
        True,
        False
    ),
    (
        "Butter Scotch Ice Cream",
        "Desserts & Ice Creams",
        "",
        189,
        True,
        False
    ),
    (
        "Kesar Pista Ice Cream",
        "Desserts & Ice Creams",
        "",
        189,
        True,
        False
    ),
]
SEED_RECOGNITION = [
    (
        "Google Reviews",
        "4.6 ★",
        "\"An old-Chandigarh institution — warm service and food that lingers.\"",
        "google",
        0
    ),
    (
        "Zomato",
        "4.5 ★",
        "\"A benchmark for Awadhi & Punjabi fine dining in the tricity.\"",
        "zomato",
        1
    ),
    (
        "JustDial",
        "5.0 ★",
        "\"Consistently rated top Indian fine dining in Sector 7.\"",
        "star",
        2
    ),
    (
        "Rotary Chandigarh Shivalik",
        "Award",
        "Honoured for hospitality excellence and community.",
        "award",
        3
    ),
    (
        "Owners Also Eat Here",
        "House Pride",
        "The wall sign that says everything about our kitchen.",
        "heart",
        4
    ),
]

SEED_OFFERS = [
    (
        "Weekday Lunch Escape",
        "Mon – Fri, 12:30 – 3:30 PM",
        "Two-course fine-dining thali for two at ₹1,299. Includes a signature dessert.",
        "Till 31 Mar 2026"
    ),
    (
        "Family Sunday Brunch",
        "Every Sunday",
        "Live counters, unlimited buffet, chef's kebab platter — ₹1,599 per adult.",
        "Ongoing"
    ),
    (
        "Anniversary Table",
        "Celebrations",
        "A candle-lit table, complimentary cake and a house cocktail on the night.",
        "By reservation"
    ),
]

SEED_TIERS = [
    (
        "Silver",
        "Coming Soon",
        "For our regulars",
        [
            "10% off à la carte",
            "Priority reservations",
            "Birthday dessert on the house"
        ],
        False,
        0
    ),
    (
        "Gold",
        "Coming Soon",
        "For those who dine often",
        [
            "20% off à la carte & buffet",
            "Guaranteed table on weekends",
            "Complimentary house cocktail once a month",
            "Early access to chef's tasting nights"
        ],
        True,
        1
    ),
    (
        "Platinum",
        "Coming Soon",
        "Our most treasured guests",
        [
            "30% off everything",
            "Private nook access",
            "Chef's table experience twice a year",
            "Personal concierge for events"
        ],
        False,
        2
    ),
]

SEED_CONTENT = {
    "home": {
        "title": "An unhurried table in Sector 7",
        "eyebrow": "Chandigarh, since a long time",
        "hero_image": "/restaurant/image1.jpeg",
        "intro": (
            "Sip 'n' Dine is a quiet corner of Madhya Marg where "
            "warm wood, hand-plated Awadhi and Punjabi classics, "
            "and a familiar hello have kept the same guests "
            "coming back for years."
        ),
    },

    "our-story": {
        "title": "Our Story",
        "eyebrow": "Since 2005 · Sector 7C",
        "hero_image": "/restaurant/image5.jpeg",
        "intro": (
            "A family table that grew into a neighbourhood institution."
        ),
        "body_html": (
            "<p>Sip 'n' Dine began the way most good restaurants do — "
            "around a family table, with recipes older than the room, "
            "and a stubborn belief that a meal in Chandigarh could "
            "feel like a meal in a home in old Lucknow. Two decades "
            "later, the plaque on our wall still reads "
            "<em>\"Owners also eat here\"</em>, and it is not a "
            "marketing line.</p>"
            "<p>Our kitchen is Awadhi at heart and Punjabi by "
            "neighbourhood — dum biryanis rested overnight, dal "
            "simmered for a full day, kebabs shaped by hand, breads "
            "pulled from a live tandoor. Our dining room is warm "
            "wood, soft brass light, floral corners for the private "
            "conversations, and a communal table for the ones you "
            "want to remember.</p>"
            "<p>Whether you're stopping in for a Sunday lunch, "
            "hosting an intimate anniversary, planning a wedding "
            "rehearsal, or feeding a marching band — we're a small, "
            "family-run house, and we still like to plate the first "
            "course ourselves.</p>"
        ),
    },

    "menu": {
        "title": "The Menu",
        "eyebrow": "Awadhi · Punjabi · Signature",
        "hero_image": "/restaurant/image7.jpeg",
        "intro": (
            "Photos are AI-suggested until our new food photography "
            "arrives — flavours, however, are entirely ours."
        ),
    },

    "buffet": {
        "title": "The Restaurant Buffet",
        "eyebrow": "Lunch & Dinner",
        "hero_image": "/restaurant/image3.jpeg",
        "intro": (
            "A rotating spread of house classics — soups, salads, "
            "chaat station, live tandoor, five mains, three biryanis, "
            "and a full Indian dessert counter."
        ),
        "body_html": (
            "<p><strong>Weekday Lunch:</strong> 12:30 – 3:30 PM · "
            "₹899 per adult</p>"
            "<p><strong>Weekend Lunch:</strong> 12:30 – 3:45 PM · "
            "₹1,199 per adult</p>"
            "<p><strong>Dinner Buffet:</strong> 7:30 – 11:00 PM · "
            "₹1,299 per adult</p>"
            "<p>Children under 8 dine at half. Reservations "
            "recommended on weekends.</p>"
        ),
    },

    "gallery": {
        "title": "Inside Sip 'n' Dine",
        "eyebrow": "Room by room",
        "hero_image": "/restaurant/image6.jpeg",
        "intro": (
            "A quick walk through our dining rooms, private nooks, "
            "and the wall we're most proud of."
        ),
    },

    "banqueting": {
        "title": "Banqueting & Events",
        "eyebrow": "Private Dining",
        "hero_image": "/restaurant/image5.jpeg",
        "intro": (
            "A private nook for twelve, a communal table for "
            "eighteen, and the whole room for a hundred and forty."
        ),
        "body_html": (
            "<p>From rehearsal dinners and intimate anniversaries "
            "to milestone birthdays and cocktail receptions — our "
            "team plans it, our chef curates it, and our sommelier "
            "pairs it. Ask us for the private nook if you want the "
            "floral wall in your photographs.</p>"
        ),
    },

    "catering": {
        "title": "Catering",
        "eyebrow": "Off-premise",
        "hero_image": "/restaurant/image4.jpeg",
        "intro": (
            "The Sip 'n' Dine table, at your address."
        ),
        "body_html": (
            "<p>Live tandoors, chaat counters, seven-course "
            "pre-plated menus, and dessert stations — set up on "
            "your lawn, in your farmhouse, or at your office. We "
            "cater from 30 guests to 3,000 across Chandigarh, "
            "Panchkula and Mohali.</p>"
        ),
    },

    "offers": {
        "title": "Offers & Specials",
        "eyebrow": "This Season",
        "hero_image": "/restaurant/image7.jpeg",
        "intro": "Everyday reasons to book the table."
    },

    "membership": {
        "title": "Privilege Membership",
        "eyebrow": "Coming soon",
        "hero_image": "/restaurant/image4.jpeg",
        "intro": (
            "A quieter kind of loyalty — for guests who make "
            "this their table."
        )
    },

    "book-table": {
        "title": "Book a Table",
        "eyebrow": "Reservations",
        "hero_image": "/restaurant/image1.jpeg",
        "intro": "Tell us when — we'll keep the light on."
    },

    "contact": {
        "title": "Find Us",
        "eyebrow": "Sector 7C · Chandigarh",
        "hero_image": "/restaurant/image2.jpeg",
        "intro": (
            "SCO 16A, Madhya Marg — the green sign next to Fluid."
        )
    },
}


async def _seed_ai_images():
    """Background task — replace Unsplash fallbacks with AI-generated food images."""

    items = await db.menu.find(
        {
            "image_url": {
                "$regex": "^https://images.unsplash"
            }
        }
    ).to_list(500)

    for it in items:

        url = await _generate_food_image(
            f"{it['name']} — {it.get('description', '')}"
        )

        if url:
            await db.menu.update_one(
                {"id": it["id"]},
                {"$set": {"image_url": url}}
            )

            log.info(
                "Generated AI image for %s",
                it["name"]
            )

        await asyncio.sleep(1.5)


UNSPLASH_BY_CATEGORY = {
    "Starters": (
        "https://images.unsplash.com/"
        "photo-1631452180519-c014fe946bc7"
        "?auto=format&fit=crop&w=800&q=80"
    ),

    "Tandoor": (
        "https://images.unsplash.com/"
        "photo-1599487488170-d11ec9c172f0"
        "?auto=format&fit=crop&w=800&q=80"
    ),

    "Mains": (
        "https://images.unsplash.com/"
        "photo-1588166524941-3bf61a9c41db"
        "?auto=format&fit=crop&w=800&q=80"
    ),

    "Biryani": (
        "https://images.unsplash.com/"
        "photo-1563379091339-03b21ab4a4f8"
        "?auto=format&fit=crop&w=800&q=80"
    ),

    "Breads": (
        "https://images.unsplash.com/"
        "photo-1626074353765-517a681e40be"
        "?auto=format&fit=crop&w=800&q=80"
    ),

    "Desserts": (
        "https://images.unsplash.com/"
        "photo-1587736908148-6e6da4e4c8b8"
        "?auto=format&fit=crop&w=800&q=80"
    ),

    "Drinks": (
        "https://images.unsplash.com/"
        "photo-1544145945-f90425340c7e"
        "?auto=format&fit=crop&w=800&q=80"
    ),
}


@app.on_event("startup")
async def startup():

    # admin
    if not await db.admins.find_one(
        {"email": ADMIN_EMAIL.lower()}
    ):

        await db.admins.insert_one(
            {
                "email": ADMIN_EMAIL.lower(),
                "password_hash": hash_pwd(
                    ADMIN_PASSWORD
                ),
                "created_at": now_iso(),
            }
        )

        log.info(
            "Seeded admin %s",
            ADMIN_EMAIL
        )

    # settings
    if not await db.settings.find_one(
        {"_id": "global"}
    ):

        s = Settings().model_dump()

        s["hours"] = [
            {
                "day": "Monday – Thursday",
                "hours": (
                    "12:30 PM – 3:30 PM · "
                    "7:30 PM – 11:00 PM"
                )
            },
            {
                "day": "Friday – Saturday",
                "hours": (
                    "12:30 PM – 3:45 PM · "
                    "7:30 PM – 11:30 PM"
                )
            },
            {
                "day": "Sunday",
                "hours": (
                    "12:30 PM – 3:45 PM · "
                    "7:30 PM – 11:00 PM"
                )
            },
        ]

        s["social"] = {
            "instagram": "https://instagram.com/sipndine",
            "facebook": "https://facebook.com/sipndine"
        }

        s["logo_url"] = ""

        await db.settings.update_one(
            {"_id": "global"},
            {"$set": s},
            upsert=True
        )

    # content
    for slug, data in SEED_CONTENT.items():

        if not await db.content.find_one(
            {"slug": slug}
        ):

            doc = PageContent(
                slug=slug,
                **data
            ).model_dump()

            await db.content.insert_one(doc)

    # menu
    if await db.menu.count_documents({}) == 0:

        for i, (
            name,
            cat,
            desc,
            price,
            veg,
            sig
        ) in enumerate(SEED_MENU):

            doc = MenuItem(
                name=name,
                category=cat,
                description=desc,
                price=float(price),
                veg=veg,
                signature=sig,
                order=i,
                image_url=UNSPLASH_BY_CATEGORY.get(
                    cat,
                    ""
                ),
            ).model_dump()

            await db.menu.insert_one(doc)

        log.info(
            "Seeded %d menu items",
            len(SEED_MENU)
        )

    # recognition
    if await db.recognition.count_documents({}) == 0:

        for (
            platform,
            rating,
            quote,
            icon,
            order
        ) in SEED_RECOGNITION:

            await db.recognition.insert_one(
                Recognition(
                    platform=platform,
                    rating=rating,
                    quote=quote,
                    icon=icon,
                    order=order
                ).model_dump()
            )

    # offers
    if await db.offers.count_documents({}) == 0:

        for i, (
            title,
            sub,
            desc,
            till
        ) in enumerate(SEED_OFFERS):

            await db.offers.insert_one(
                Offer(
                    title=title,
                    subtitle=sub,
                    description=desc,
                    valid_till=till,
                    order=i,
                    image_url=(
                        f"/restaurant/image{(i % 5) + 3}.jpeg"
                    ),
                ).model_dump()
            )

    # tiers
    if await db.membership.count_documents({}) == 0:

        for i, (
            name,
            price,
            tag,
            benefits,
            hl,
            order
        ) in enumerate(SEED_TIERS):

            await db.membership.insert_one(
                Tier(
                    name=name,
                    price=price,
                    tagline=tag,
                    benefits=benefits,
                    highlighted=hl,
                    order=order
                ).model_dump()
            )

    # gallery
    if await db.gallery.count_documents({}) == 0:

        for i in range(1, 8):

            await db.gallery.insert_one(
                GalleryImage(
                    url=f"/restaurant/image{i}.jpeg",
                    caption="",
                    order=i,
                ).model_dump()
            )

    # background AI image regen
    if os.environ.get("SKIP_AI_SEED") != "1":
        asyncio.create_task(
            _seed_ai_images()
        )


@app.on_event("shutdown")
async def shutdown():
    client.close()
