#!/usr/bin/env python3
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from time import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = DATA_DIR / "orders.sqlite3"
IS_PRODUCTION = os.environ.get("SCIADE_ENV", "development").lower() == "production"
DEFAULT_ADMIN_EMAIL = "lv.desideri@gmail.com"
DEFAULT_ADMIN_PASSWORD = "change-this-local-password"
ADMIN_PASSWORD = os.environ.get("SCIADE_ADMIN_PASSWORD")
ADMIN_EMAIL = os.environ.get("SCIADE_ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL).lower()
SESSION_COOKIE = "sciade_session"
SESSIONS = {}
SESSION_LIFETIME_SECONDS = 7 * 24 * 60 * 60
ADMIN_LOGIN_ATTEMPTS = {}
ADMIN_LOGIN_LIMIT = 5
ADMIN_LOGIN_LOCK_SECONDS = 10 * 60
UPLOAD_DIR = FRONTEND_DIR / "assets" / "uploads"
MAX_JSON_BYTES = 256 * 1024
MAX_CART_ITEMS = 30
MAX_ITEM_QUANTITY = 20
HOST = os.environ.get("SCIADE_HOST") or ("0.0.0.0" if IS_PRODUCTION else "localhost")
PORT = int(os.environ.get("PORT") or os.environ.get("SCIADE_PORT", "4176"))
COOKIE_SECURE = (
    os.environ.get("SCIADE_COOKIE_SECURE", "1" if IS_PRODUCTION else "0").lower()
    in ["1", "true", "yes"]
)

if IS_PRODUCTION and not ADMIN_PASSWORD:
    raise RuntimeError("SCIADE_ADMIN_PASSWORD is required when SCIADE_ENV=production")

if IS_PRODUCTION and ADMIN_EMAIL == DEFAULT_ADMIN_EMAIL and not os.environ.get("SCIADE_ADMIN_EMAIL"):
    raise RuntimeError("SCIADE_ADMIN_EMAIL is required when SCIADE_ENV=production")

if ADMIN_PASSWORD is None:
    ADMIN_PASSWORD = DEFAULT_ADMIN_PASSWORD

INITIAL_PRODUCTS = [
    {
        "id": "purse-rosa",
        "category": "purses",
        "name": "Borsa Rosa Weekend",
        "price": 68,
        "image": "assets/purse-rosa.svg",
        "position": "center",
        "description": "Borsa morbida e strutturata con patta corallo, manico intrecciato e corpo effetto lino.",
    },
    {
        "id": "purse-luna",
        "category": "purses",
        "name": "Borsa Luna a tracolla",
        "price": 54,
        "image": "assets/purse-luna.svg",
        "position": "center",
        "description": "Borsa compatta da tutti i giorni con dettagli color petrolio, chiusura dorata e tracolla regolabile.",
    },
    {
        "id": "necklace-pearl",
        "category": "necklaces",
        "name": "Collana lunga di perle",
        "price": 35,
        "image": "assets/pearl-lariat-necklace.jpg",
        "position": "center 36%",
        "description": "Filo lungo di perle con dettaglio dorato, fotografato su busto argentato.",
    },
    {
        "id": "necklace-crystal-collar",
        "category": "necklaces",
        "name": "Collana collarino cristalli",
        "price": 35,
        "image": "assets/crystal-collar-necklace.jpg",
        "position": "center 78%",
        "description": "Collana statement con dettagli luminosi in cristallo e texture intrecciata fatta a mano.",
    },
    {
        "id": "necklace-link-chain",
        "category": "necklaces",
        "name": "Collana catena bicolore",
        "price": 35,
        "image": "assets/link-chain-necklace.jpg",
        "position": "center center",
        "description": "Collana morbida a maglie dorate con anelli decorativi rosa e argento.",
    },
    {
        "id": "necklace-layered-gold",
        "category": "necklaces",
        "name": "Collana dorata a strati",
        "price": 35,
        "image": "assets/layered-gold-necklace.jpg",
        "position": "center 76%",
        "description": "Collana a strati con dettagli effetto collarino, cristalli e catenina delicata.",
    },
    {
        "id": "ring-amber-crystal",
        "category": "rings",
        "name": "Anello cristallo ambra",
        "price": 25,
        "image": "assets/amber-crystal-ring.jpg",
        "position": "center center",
        "description": "Anello con grande cristallo color ambra avvolto da una fascia artigianale rosata.",
    },
    {
        "id": "ring-rose",
        "category": "rings",
        "name": "Anello rosa intrecciata",
        "price": 25,
        "image": "assets/rose-ring.jpg",
        "position": "center center",
        "description": "Anello scultoreo a forma di rosa con finitura calda in filo metallico.",
    },
    {
        "id": "bracelet-teal-lace",
        "category": "bracelets",
        "name": "Bracciale pizzo blu",
        "price": 25,
        "image": "assets/teal-lace-ring.jpg",
        "position": "center 68%",
        "description": "Bracciale blu fatto a mano con trama intrecciata e piccolo charm dorato a forma di foglia.",
    },
]


def connect():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    DATA_DIR.mkdir(exist_ok=True)
    UPLOAD_DIR.mkdir(exist_ok=True)
    with connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              created_at TEXT NOT NULL,
              customer_name TEXT NOT NULL,
              customer_email TEXT NOT NULL,
              customer_phone TEXT,
              customer_address TEXT NOT NULL,
              delivery TEXT NOT NULL,
              payment TEXT NOT NULL,
              timing TEXT NOT NULL,
              notes TEXT,
              total REAL NOT NULL,
              items_json TEXT NOT NULL,
              raw_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
              id TEXT PRIMARY KEY,
              category TEXT NOT NULL,
              name TEXT NOT NULL,
              price REAL NOT NULL,
              image TEXT NOT NULL,
              position TEXT,
              description TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              email TEXT NOT NULL UNIQUE,
              password_hash TEXT NOT NULL,
              salt TEXT NOT NULL,
              role TEXT NOT NULL DEFAULT 'customer',
              first_name TEXT,
              last_name TEXT,
              birthdate TEXT,
              updated_at TEXT,
              created_at TEXT NOT NULL
            )
            """
        )
        ensure_user_columns(connection)

        existing_count = connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if existing_count == 0:
            now = datetime.now(timezone.utc).isoformat()
            connection.executemany(
                """
                INSERT INTO products (
                  id, category, name, price, image, position, description, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        product["id"],
                        product["category"],
                        product["name"],
                        product["price"],
                        product["image"],
                        product.get("position") or "center",
                        product["description"],
                        now,
                        now,
                    )
                    for product in INITIAL_PRODUCTS
                ],
            )

        admin = connection.execute("SELECT id FROM users WHERE email = ?", (ADMIN_EMAIL,)).fetchone()
        salt, password_hash = hash_password(ADMIN_PASSWORD)
        if admin is None:
            connection.execute(
                """
                INSERT INTO users (
                  email, password_hash, salt, role, first_name, last_name,
                  birthdate, updated_at, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ADMIN_EMAIL,
                    password_hash,
                    salt,
                    "admin",
                    "Luca",
                    "Desideri",
                    "",
                    datetime.now(timezone.utc).isoformat(),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        else:
            connection.execute(
                """
                UPDATE users
                SET password_hash = ?, salt = ?, role = ?, updated_at = ?
                WHERE email = ?
                """,
                (password_hash, salt, "admin", datetime.now(timezone.utc).isoformat(), ADMIN_EMAIL),
            )


def ensure_user_columns(connection):
    columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(users)").fetchall()
    }
    migrations = {
        "first_name": "ALTER TABLE users ADD COLUMN first_name TEXT",
        "last_name": "ALTER TABLE users ADD COLUMN last_name TEXT",
        "birthdate": "ALTER TABLE users ADD COLUMN birthdate TEXT",
        "updated_at": "ALTER TABLE users ADD COLUMN updated_at TEXT",
    }
    for column, statement in migrations.items():
        if column not in columns:
            connection.execute(statement)


def public_order(row):
    return {
        "id": row["id"],
        "createdAt": row["created_at"],
        "customer": {
            "name": row["customer_name"],
            "email": row["customer_email"],
            "phone": row["customer_phone"],
            "address": row["customer_address"],
        },
        "preferences": {
            "delivery": row["delivery"],
            "payment": row["payment"],
            "timing": row["timing"],
            "notes": row["notes"],
        },
        "items": json.loads(row["items_json"]),
        "total": row["total"],
    }


def public_product(row):
    return {
        "id": row["id"],
        "category": row["category"],
        "name": row["name"],
        "price": row["price"],
        "image": row["image"],
        "position": row["position"] or "center",
        "description": row["description"],
    }


def public_user(row):
    return {
        "email": row["email"],
        "role": row["role"],
        "firstName": row["first_name"] or "",
        "lastName": row["last_name"] or "",
        "birthdate": row["birthdate"] or "",
    }


def create_session(user):
    session_token = secrets.token_urlsafe(32)
    SESSIONS[session_token] = {
        "role": user["role"],
        "email": user["email"],
        "expires_at": time() + SESSION_LIFETIME_SECONDS,
    }
    return session_token


def read_session(session_token):
    session = SESSIONS.get(session_token)
    if not session:
        return None

    if session.get("expires_at", 0) <= time():
        SESSIONS.pop(session_token, None)
        return None

    return session


def session_cookie_header(session_token, max_age=SESSION_LIFETIME_SECONDS):
    parts = [
        f"{SESSION_COOKIE}={session_token}",
        "HttpOnly",
        "SameSite=Lax",
        "Path=/",
        f"Max-Age={max_age}",
    ]
    if COOKIE_SECURE:
        parts.append("Secure")
    return "; ".join(parts)


def clear_session_cookie_header():
    parts = [
        f"{SESSION_COOKIE}=",
        "Max-Age=0",
        "HttpOnly",
        "SameSite=Lax",
        "Path=/",
    ]
    if COOKIE_SECURE:
        parts.append("Secure")
    return "; ".join(parts)


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        str(password).encode("utf-8"),
        salt.encode("utf-8"),
        120_000,
    ).hex()
    return salt, digest


def verify_password(password, salt, expected_hash):
    _, digest = hash_password(password, salt)
    return hmac.compare_digest(digest, expected_hash)


def normalize_email(email):
    email = str(email or "").strip().lower()
    if "@" not in email or "." not in email:
        raise ValueError("Inserisci un'email valida")
    return email


def validate_password(password):
    password = str(password or "")
    if len(password) < 8:
        raise ValueError("La password deve avere almeno 8 caratteri")
    return password


def validate_profile(payload):
    first_name = str(payload.get("firstName") or "").strip()
    last_name = str(payload.get("lastName") or "").strip()
    birthdate = str(payload.get("birthdate") or "").strip()

    if not first_name:
        raise ValueError("Il nome è obbligatorio")
    if not last_name:
        raise ValueError("Il cognome è obbligatorio")
    if not birthdate:
        raise ValueError("La data di nascita è obbligatoria")

    try:
        datetime.strptime(birthdate, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("La data di nascita non è valida") from exc

    return {
        "firstName": first_name,
        "lastName": last_name,
        "birthdate": birthdate,
    }


def require_text(payload, field, label, max_length):
    value = str(payload.get(field) or "").strip()
    if not value:
        raise ValueError(f"{label} è obbligatorio")
    if len(value) > max_length:
        raise ValueError(f"{label} è troppo lungo")
    return value


def validate_order_payload(payload):
    customer = payload.get("customer") or {}
    preferences = payload.get("preferences") or {}
    raw_items = payload.get("items")

    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("L'ordine deve contenere almeno un prodotto")
    if len(raw_items) > MAX_CART_ITEMS:
        raise ValueError("L'ordine contiene troppi prodotti")

    customer_email = normalize_email(customer.get("email"))
    customer_name = require_text(customer, "name", "Nome e cognome", 120)
    customer_address = require_text(customer, "address", "Indirizzo", 500)
    customer_phone = str(customer.get("phone") or "").strip()
    if len(customer_phone) > 40:
        raise ValueError("Telefono troppo lungo")

    delivery = require_text(preferences, "delivery", "Metodo di consegna", 80)
    payment = require_text(preferences, "payment", "Metodo di pagamento", 80)
    timing = require_text(preferences, "timing", "Tempistiche", 80)
    notes = str(preferences.get("notes") or "").strip()
    if len(notes) > 1000:
        raise ValueError("Note troppo lunghe")

    product_ids = []
    quantities = {}
    for item in raw_items:
        product_id = str((item or {}).get("id") or "").strip()
        if not product_id:
            raise ValueError("Prodotto non valido")
        quantity = int((item or {}).get("quantity") or 0)
        if quantity < 1 or quantity > MAX_ITEM_QUANTITY:
            raise ValueError("Quantità prodotto non valida")
        product_ids.append(product_id)
        quantities[product_id] = quantities.get(product_id, 0) + quantity

    unique_product_ids = tuple(set(product_ids))
    placeholders = ",".join(["?"] * len(unique_product_ids))
    with connect() as connection:
        rows = connection.execute(
            f"SELECT * FROM products WHERE id IN ({placeholders})",
            unique_product_ids,
        ).fetchall()

    products = {row["id"]: row for row in rows}
    if len(products) != len(unique_product_ids):
        raise ValueError("Uno o più prodotti non sono più disponibili")

    items = []
    total = 0.0
    for product_id, quantity in quantities.items():
        product = products[product_id]
        price = float(product["price"])
        line_total = round(price * quantity, 2)
        total = round(total + line_total, 2)
        items.append(
            {
                "id": product_id,
                "name": product["name"],
                "category": product["category"],
                "price": price,
                "quantity": quantity,
                "lineTotal": line_total,
            }
        )

    return {
        "customer": {
            "name": customer_name,
            "email": customer_email,
            "phone": customer_phone,
            "address": customer_address,
        },
        "preferences": {
            "delivery": delivery,
            "payment": payment,
            "timing": timing,
            "notes": notes,
        },
        "items": items,
        "total": total,
    }


def admin_attempt_key(handler, email):
    forwarded_for = handler.headers.get("X-Forwarded-For", "")
    client_ip = forwarded_for.split(",", 1)[0].strip()
    if not client_ip and handler.client_address:
        client_ip = handler.client_address[0]
    return f"{email}:{client_ip}"


def admin_lock_status(key):
    attempt = ADMIN_LOGIN_ATTEMPTS.get(key)
    if not attempt:
        return None

    locked_until = attempt.get("locked_until", 0)
    if locked_until > time():
        return int(locked_until - time()) + 1

    if locked_until:
        ADMIN_LOGIN_ATTEMPTS.pop(key, None)
    return None


def record_admin_login_failure(key):
    attempt = ADMIN_LOGIN_ATTEMPTS.get(key, {"count": 0, "locked_until": 0})
    attempt["count"] += 1
    if attempt["count"] >= ADMIN_LOGIN_LIMIT:
        attempt["locked_until"] = time() + ADMIN_LOGIN_LOCK_SECONDS
    ADMIN_LOGIN_ATTEMPTS[key] = attempt


def clear_admin_login_failures(key):
    ADMIN_LOGIN_ATTEMPTS.pop(key, None)


def slugify(value):
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or secrets.token_hex(4)


def save_product_image(product_id, image_data):
    if not image_data:
        return None

    match = re.match(r"data:image/(png|jpeg|jpg|webp);base64,(.+)", image_data)
    if not match:
        raise ValueError("Image must be a PNG, JPEG, or WebP file")

    extension = "jpg" if match.group(1) in ["jpeg", "jpg"] else match.group(1)
    raw = base64.b64decode(match.group(2), validate=True)

    if len(raw) > 6 * 1024 * 1024:
        raise ValueError("Image is too large")

    UPLOAD_DIR.mkdir(exist_ok=True)
    filename = f"{slugify(product_id)}-{secrets.token_hex(4)}.{extension}"
    path = UPLOAD_DIR / filename
    path.write_bytes(raw)
    return f"assets/uploads/{filename}"


def read_json(handler):
    length = int(handler.headers.get("Content-Length", "0"))
    if length > MAX_JSON_BYTES:
        raise ValueError("Richiesta troppo grande")
    return json.loads(handler.rfile.read(length))


def validate_product_payload(payload, existing_image=None):
    name = str(payload.get("name", "")).strip()
    category = str(payload.get("category", "")).strip()
    description = str(payload.get("description", "")).strip()
    product_id = str(payload.get("id") or slugify(name)).strip()

    if not name:
        raise ValueError("Il nome prodotto è obbligatorio")
    if category not in ["purses", "necklaces", "rings", "bracelets"]:
        raise ValueError("Categoria prodotto non valida")
    if not description:
        raise ValueError("La descrizione prodotto è obbligatoria")

    price = float(payload.get("price"))
    if price < 0:
        raise ValueError("Il prezzo non può essere negativo")

    uploaded_image = save_product_image(product_id, payload.get("imageData"))
    image = uploaded_image or str(payload.get("image") or existing_image or "").strip()
    if not image:
        raise ValueError("L'immagine prodotto è obbligatoria")

    return {
        "id": product_id,
        "category": category,
        "name": name,
        "price": price,
        "image": image,
        "position": str(payload.get("position") or "center").strip(),
        "description": description,
    }


class SciadeHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'",
        )
        super().end_headers()

    def current_user(self):
        return read_session(self.session_token())

    def session_token(self):
        cookie_header = self.headers.get("Cookie", "")
        cookies = {}
        for part in cookie_header.split(";"):
            if "=" in part:
                key, value = part.strip().split("=", 1)
                cookies[key] = value
        return cookies.get(SESSION_COOKIE, "")

    def is_admin(self):
        user = self.current_user()
        return bool(user and user.get("role") == "admin")

    def require_user(self):
        user = self.current_user()
        if user:
            return user

        self.send_json(401, {"ok": False, "error": "Accesso richiesto"})
        return None

    def require_admin(self):
        if self.is_admin():
            return True

        self.send_json(401, {"ok": False, "error": "Accesso admin richiesto"})
        return False

    def redirect(self, location):
        self.send_response(302)
        self.send_header("Location", location)
        self.end_headers()

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/admin.html" and not self.is_admin():
            self.redirect("/login.html")
            return

        if path == "/account.html" and not self.current_user():
            self.redirect("/login.html")
            return

        if path == "/api/session":
            user = self.current_user()
            self.send_json(
                200,
                {
                    "authenticated": bool(user),
                    "role": user.get("role") if user else "guest",
                    "email": user.get("email") if user else "",
                },
            )
            return

        if path == "/api/account":
            session_user = self.require_user()
            if not session_user:
                return

            with connect() as connection:
                user = connection.execute(
                    "SELECT * FROM users WHERE email = ?", (session_user["email"],)
                ).fetchone()

            if user is None:
                self.send_json(401, {"ok": False, "error": "Accesso richiesto"})
                return

            self.send_json(200, {"ok": True, "user": public_user(user)})
            return

        if path == "/api/orders":
            if not self.require_admin():
                return
            with connect() as connection:
                rows = connection.execute(
                    "SELECT * FROM orders ORDER BY id DESC"
                ).fetchall()
            self.send_json(200, {"orders": [public_order(row) for row in rows]})
            return

        if path == "/api/products":
            with connect() as connection:
                rows = connection.execute(
                    "SELECT * FROM products ORDER BY category, created_at, name"
                ).fetchall()
            self.send_json(200, {"products": [public_product(row) for row in rows]})
            return

        super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/api/login":
            try:
                payload = read_json(self)
                email = normalize_email(payload.get("email"))
                password = str(payload.get("password", ""))
            except (ValueError, json.JSONDecodeError) as error:
                self.send_json(400, {"ok": False, "error": str(error)})
                return

            with connect() as connection:
                user = connection.execute(
                    "SELECT * FROM users WHERE email = ?", (email,)
                ).fetchone()

            if user is None:
                self.send_json(404, {"ok": False, "error": "Non esiste un account associato a questa email."})
                return

            is_admin_login = user["role"] == "admin"
            admin_key = admin_attempt_key(self, email) if is_admin_login else None

            if is_admin_login:
                wait_seconds = admin_lock_status(admin_key)
                if wait_seconds:
                    self.send_json(
                        429,
                        {
                            "ok": False,
                            "error": f"Troppi tentativi admin. Riprova tra {(wait_seconds + 59) // 60} minuti.",
                        },
                    )
                    return

            if not verify_password(password, user["salt"], user["password_hash"]):
                if is_admin_login:
                    record_admin_login_failure(admin_key)
                self.send_json(401, {"ok": False, "error": "Password sbagliata."})
                return

            if is_admin_login:
                clear_admin_login_failures(admin_key)

            session_token = create_session(user)
            redirect_to = "/admin.html" if user["role"] == "admin" else "/account.html"
            body = json.dumps(
                {"ok": True, "role": user["role"], "email": user["email"], "redirectTo": redirect_to}
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Set-Cookie", session_cookie_header(session_token))
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/api/signup":
            try:
                payload = read_json(self)
                email = normalize_email(payload.get("email"))
                password = validate_password(payload.get("password"))
                profile = validate_profile(payload)
            except (ValueError, json.JSONDecodeError) as error:
                self.send_json(400, {"ok": False, "error": str(error)})
                return

            salt, password_hash = hash_password(password)
            try:
                with connect() as connection:
                    connection.execute(
                        """
                        INSERT INTO users (
                          email, password_hash, salt, role, first_name, last_name,
                          birthdate, updated_at, created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            email,
                            password_hash,
                            salt,
                            "customer",
                            profile["firstName"],
                            profile["lastName"],
                            profile["birthdate"],
                            datetime.now(timezone.utc).isoformat(),
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )
            except sqlite3.IntegrityError:
                self.send_json(409, {"ok": False, "error": "Esiste già un account con questa email"})
                return

            session_token = create_session({"role": "customer", "email": email})
            body = json.dumps(
                {"ok": True, "role": "customer", "email": email, "redirectTo": "/account.html"}
            ).encode("utf-8")
            self.send_response(201)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Set-Cookie", session_cookie_header(session_token))
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/api/logout":
            SESSIONS.pop(self.session_token(), None)
            body = json.dumps({"ok": True}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Set-Cookie", clear_session_cookie_header())
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/api/products":
            if not self.require_admin():
                return
            try:
                payload = read_json(self)
                product = validate_product_payload(payload)
                now = datetime.now(timezone.utc).isoformat()
                with connect() as connection:
                    connection.execute(
                        """
                        INSERT INTO products (
                          id, category, name, price, image, position, description, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            product["id"],
                            product["category"],
                            product["name"],
                            product["price"],
                            product["image"],
                            product["position"],
                            product["description"],
                            now,
                            now,
                        ),
                    )
                self.send_json(201, {"ok": True, "product": product})
            except sqlite3.IntegrityError:
                self.send_json(409, {"ok": False, "error": "A product with this id already exists"})
            except (KeyError, ValueError, json.JSONDecodeError) as error:
                self.send_json(400, {"ok": False, "error": str(error)})
            return

        if path != "/api/orders":
            self.send_error(404)
            return

        try:
            payload = read_json(self)
            order = validate_order_payload(payload)
            customer = order["customer"]
            preferences = order["preferences"]
            items = order["items"]
            total = order["total"]

            created_at = datetime.now(timezone.utc).isoformat()
            with connect() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO orders (
                      created_at,
                      customer_name,
                      customer_email,
                      customer_phone,
                      customer_address,
                      delivery,
                      payment,
                      timing,
                      notes,
                      total,
                      items_json,
                      raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        created_at,
                        customer["name"],
                        customer["email"],
                        customer.get("phone") or "",
                        customer["address"],
                        preferences["delivery"],
                        preferences["payment"],
                        preferences["timing"],
                        preferences.get("notes") or "",
                        total,
                        json.dumps(items),
                        json.dumps(order),
                    ),
                )

            self.send_json(201, {"ok": True, "orderId": cursor.lastrowid})
        except (KeyError, ValueError, json.JSONDecodeError) as error:
            self.send_json(400, {"ok": False, "error": str(error)})

    def do_PUT(self):
        path = urlparse(self.path).path
        parts = path.strip("/").split("/")

        if path == "/api/account":
            session_user = self.require_user()
            if not session_user:
                return

            try:
                payload = read_json(self)
                profile = validate_profile(payload)
            except (ValueError, json.JSONDecodeError) as error:
                self.send_json(400, {"ok": False, "error": str(error)})
                return

            with connect() as connection:
                connection.execute(
                    """
                    UPDATE users
                    SET first_name = ?, last_name = ?, birthdate = ?, updated_at = ?
                    WHERE email = ?
                    """,
                    (
                        profile["firstName"],
                        profile["lastName"],
                        profile["birthdate"],
                        datetime.now(timezone.utc).isoformat(),
                        session_user["email"],
                    ),
                )
                user = connection.execute(
                    "SELECT * FROM users WHERE email = ?", (session_user["email"],)
                ).fetchone()

            self.send_json(200, {"ok": True, "user": public_user(user)})
            return

        if path == "/api/account/password":
            session_user = self.require_user()
            if not session_user:
                return

            try:
                payload = read_json(self)
                current_password = str(payload.get("currentPassword") or "")
                new_password = validate_password(payload.get("newPassword"))
            except (ValueError, json.JSONDecodeError) as error:
                self.send_json(400, {"ok": False, "error": str(error)})
                return

            with connect() as connection:
                user = connection.execute(
                    "SELECT * FROM users WHERE email = ?", (session_user["email"],)
                ).fetchone()

                if user is None:
                    self.send_json(401, {"ok": False, "error": "Accesso richiesto"})
                    return

                if not verify_password(current_password, user["salt"], user["password_hash"]):
                    self.send_json(401, {"ok": False, "error": "La password attuale è sbagliata"})
                    return

                salt, password_hash = hash_password(new_password)
                connection.execute(
                    """
                    UPDATE users
                    SET password_hash = ?, salt = ?, updated_at = ?
                    WHERE email = ?
                    """,
                    (
                        password_hash,
                        salt,
                        datetime.now(timezone.utc).isoformat(),
                        session_user["email"],
                    ),
                )

            self.send_json(200, {"ok": True})
            return

        if len(parts) != 3 or parts[:2] != ["api", "products"]:
            self.send_error(404)
            return

        if not self.require_admin():
            return

        product_id = parts[2]

        try:
            payload = read_json(self)
            with connect() as connection:
                existing = connection.execute(
                    "SELECT * FROM products WHERE id = ?", (product_id,)
                ).fetchone()

                if existing is None:
                    self.send_json(404, {"ok": False, "error": "Prodotto non trovato"})
                    return

                payload["id"] = product_id
                product = validate_product_payload(payload, existing_image=existing["image"])
                now = datetime.now(timezone.utc).isoformat()
                connection.execute(
                    """
                    UPDATE products
                    SET category = ?, name = ?, price = ?, image = ?, position = ?,
                        description = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        product["category"],
                        product["name"],
                        product["price"],
                        product["image"],
                        product["position"],
                        product["description"],
                        now,
                        product_id,
                    ),
                )
            self.send_json(200, {"ok": True, "product": product})
        except (KeyError, ValueError, json.JSONDecodeError) as error:
            self.send_json(400, {"ok": False, "error": str(error)})

    def do_DELETE(self):
        path = urlparse(self.path).path
        parts = path.strip("/").split("/")

        if len(parts) == 3 and parts[:2] == ["api", "products"]:
            if not self.require_admin():
                return

            product_id = parts[2]
            with connect() as connection:
                cursor = connection.execute("DELETE FROM products WHERE id = ?", (product_id,))

            if cursor.rowcount == 0:
                self.send_json(404, {"ok": False, "error": "Prodotto non trovato"})
                return

            self.send_json(200, {"ok": True, "productId": product_id})
            return

        if len(parts) != 3 or parts[:2] != ["api", "orders"]:
            self.send_error(404)
            return

        if not self.require_admin():
            return

        try:
            order_id = int(parts[2])
        except ValueError:
            self.send_json(400, {"ok": False, "error": "Invalid order id"})
            return

        with connect() as connection:
            cursor = connection.execute("DELETE FROM orders WHERE id = ?", (order_id,))

        if cursor.rowcount == 0:
            self.send_json(404, {"ok": False, "error": "Ordine non trovato"})
            return

        self.send_json(200, {"ok": True, "orderId": order_id})


if __name__ == "__main__":
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), SciadeHandler)
    print(f"Sciadè server running at http://{HOST}:{PORT}")
    print(f"Frontend directory: {FRONTEND_DIR}")
    print(f"Orders database: {DB_PATH}")
    server.serve_forever()
