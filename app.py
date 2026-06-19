import json
import os
import re
import uuid
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash
from authlib.integrations.flask_client import OAuth
from supabase import create_client

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "pakshield-local-secret-key")


# -------------------------------------------------
# Environment / Config
# -------------------------------------------------

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
POSTEX_WEBHOOK_SECRET = os.getenv("POSTEX_WEBHOOK_SECRET", "")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("WARNING: SUPABASE_URL or SUPABASE_KEY is missing in .env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# -------------------------------------------------
# OAuth
# -------------------------------------------------

oauth = OAuth(app)

google = oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


# -------------------------------------------------
# Supabase Helpers
# -------------------------------------------------

TABLE_MAP = {
    "Users": "users",
    "Sheet1": "bad_customers",
    "Courier Reviews": "courier_reviews",
    "Search Logs": "search_logs",
    "PostEx Webhook Logs": "postex_webhook_logs",
    "Alert Logs": "alert_logs",
}

COLUMN_MAP = {
    "Email": "email",
    "Name": "name",
    "Role": "role",
    "Plan": "plan",
    "Date Added": "date_added",

    "Tracking ID": "tracking_id",
    "Phone Number": "phone_number",
    "Customer Name": "customer_name",
    "City": "city",
    "Reason": "reason",
    "Reported By": "reported_by",
    "Date": "date",
    "Phone Normalized": "phone_normalized",
    "Verification Status": "verification_status",

    "Courier Name": "courier_name",
    "Rating": "rating",
    "Review": "review",

    "Log ID": "log_id",
    "User Email": "user_email",
    "Phone Normalize": "phone_normalized",
    "Result Found": "result_found",
    "Searched At": "searched_at",

    "Webhook ID": "webhook_id",
    "Received At": "received_at",
    "Header Secret Valid": "header_secret_valid",
    "Tracking Number": "tracking_number",
    "Status": "status",
    "Raw Payload": "raw_payload",

    "Alert ID": "alert_id",
    "Created At": "created_at",
    "Customer Phone": "customer_phone",
    "Old Status": "old_status",
    "New Status": "new_status",
    "Alert Type": "alert_type",
    "Message": "message",
    "Alert Status": "alert_status",
}

REVERSE_COLUMN_MAP = {v: k for k, v in COLUMN_MAP.items()}


def to_db_row(row_data):
    db_row = {}
    for key, value in row_data.items():
        db_key = COLUMN_MAP.get(key, key)
        db_row[db_key] = value
    return db_row


def from_db_row(row):
    clean_row = {}
    for key, value in row.items():
        if key == "id":
            continue
        sheet_key = REVERSE_COLUMN_MAP.get(key, key)
        clean_row[sheet_key] = value if value is not None else ""
    return clean_row


def get_records(sheet_name, headers=None):
    table = TABLE_MAP.get(sheet_name)
    if not table:
        return []

    try:
        res = supabase.table(table).select("*").execute()
        return [from_db_row(row) for row in (res.data or [])]
    except Exception as e:
        print(f"Supabase get_records error for {table}: {e}")
        return []


def get_recent_records(sheet_name, order_column="id", limit=10, desc=True):
    table = TABLE_MAP.get(sheet_name)
    if not table:
        return []

    try:
        res = (
            supabase.table(table)
            .select("*")
            .order(order_column, desc=desc)
            .limit(limit)
            .execute()
        )
        return [from_db_row(row) for row in (res.data or [])]
    except Exception as e:
        print(f"Supabase get_recent_records error for {table}: {e}")
        return get_records(sheet_name)[:limit]


def append_dict_row(sheet_name, row_data, headers=None):
    table = TABLE_MAP.get(sheet_name)
    if not table:
        return None

    db_row = to_db_row(row_data)

    try:
        return supabase.table(table).insert(db_row).execute()
    except Exception as e:
        print(f"Supabase insert error for {table}: {e}")
        raise


def find_row_by_value(sheet_name, header_name, value, headers=None):
    table = TABLE_MAP.get(sheet_name)
    column = COLUMN_MAP.get(header_name, header_name)

    if not table:
        return None, None

    try:
        res = supabase.table(table).select("id").eq(column, value).limit(1).execute()
        if not res.data:
            return None, None
        return table, res.data[0]["id"]
    except Exception as e:
        print(f"Supabase find error for {table}: {e}")
        return None, None


def update_row_value(table, row_id, header_name, new_value):
    column = COLUMN_MAP.get(header_name, header_name)

    try:
        return supabase.table(table).update({column: new_value}).eq("id", row_id).execute()
    except Exception as e:
        print(f"Supabase update error for {table}: {e}")
        raise


def delete_row(table, row_id):
    try:
        return supabase.table(table).delete().eq("id", row_id).execute()
    except Exception as e:
        print(f"Supabase delete error for {table}: {e}")
        raise


# -------------------------------------------------
# Utility Helpers
# -------------------------------------------------

def normalize_phone(phone):
    if not phone:
        return ""

    digits = re.sub(r"\D", "", str(phone))

    if digits.startswith("00"):
        digits = digits[2:]

    if digits.startswith("92") and len(digits) == 12:
        return digits

    if digits.startswith("0") and len(digits) == 11:
        return "92" + digits[1:]

    if digits.startswith("3") and len(digits) == 10:
        return "92" + digits

    return digits


def today_date():
    return datetime.now().strftime("%Y-%m-%d")


def current_datetime():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def find_value_in_payload(payload, possible_keys):
    if payload is None:
        return ""

    possible_keys_lower = [str(k).lower() for k in possible_keys]

    if isinstance(payload, dict):
        for key, value in payload.items():
            if str(key).lower() in possible_keys_lower:
                return value

        for value in payload.values():
            found = find_value_in_payload(value, possible_keys)
            if found:
                return found

    if isinstance(payload, list):
        for item in payload:
            found = find_value_in_payload(item, possible_keys)
            if found:
                return found

    return ""


def normalize_status_text(status):
    return str(status or "").strip().lower()


def is_risky_postex_status(status):
    normalized = normalize_status_text(status)

    risky_keywords = [
        "attempted",
        "attempt made",
        "returned",
        "out for return",
        "delivery under review",
        "expired",
    ]

    return any(keyword in normalized for keyword in risky_keywords)


def alert_already_exists(tracking_number, new_status):
    if not tracking_number:
        return False

    try:
        res = (
            supabase.table("alert_logs")
            .select("id")
            .eq("tracking_number", str(tracking_number).strip())
            .eq("new_status", str(new_status).strip())
            .limit(1)
            .execute()
        )
        return bool(res.data)
    except Exception as e:
        print(f"alert_already_exists error: {e}")
        return False


def create_postex_alert(payload, tracking_number, new_status):
    if not tracking_number:
        return False

    if alert_already_exists(tracking_number, new_status):
        return False

    customer_name = find_value_in_payload(
        payload,
        ["customerName", "customer_name", "name", "customer"],
    )

    customer_phone = find_value_in_payload(
        payload,
        ["customerPhone", "customer_phone", "phone", "phoneNumber", "mobile", "customerMobile"],
    )

    old_status = find_value_in_payload(
        payload,
        ["previousStatus", "oldStatus", "previous_status", "lastStatus"],
    )

    message = (
        f"Parcel {tracking_number} status is now {new_status}. "
        "Contact the customer immediately to save this delivery."
    )

    append_dict_row(
        "Alert Logs",
        {
            "Alert ID": str(uuid.uuid4())[:8].upper(),
            "Created At": current_datetime(),
            "Tracking Number": str(tracking_number),
            "Customer Name": str(customer_name),
            "Customer Phone": str(customer_phone),
            "Old Status": str(old_status),
            "New Status": str(new_status),
            "Alert Type": "Parcel Risk Alert",
            "Message": message,
            "Alert Status": "New",
        },
    )

    return True


def generate_tracking_id():
    return str(uuid.uuid4())[:8].upper()


def get_report_status(record):
    status = str(record.get("Verification Status", "")).strip()

    if not status:
        return "Approved"

    return status


def is_report_approved(record):
    return get_report_status(record).lower() == "approved"


def calculate_risk_level(records):
    count = len(records)

    if count >= 3:
        return "High Risk"

    if count == 2:
        return "Medium Risk"

    if count == 1:
        return "Low Risk"

    return "No Issue Found"


def get_user(email):
    email = str(email).lower().strip()

    try:
        res = (
            supabase.table("users")
            .select("*")
            .eq("email", email)
            .limit(1)
            .execute()
        )

        if not res.data:
            return None

        user = res.data[0]
        return {
            "email": user.get("email", ""),
            "name": user.get("name", ""),
            "role": str(user.get("role", "user")).lower().strip(),
            "plan": str(user.get("plan", "free")).lower().strip(),
            "date_added": user.get("date_added", ""),
        }
    except Exception as e:
        print(f"get_user error: {e}")
        return None


def log_search(phone, phone_normalized, result_found):
    user_email = session.get("user", {}).get("email", "")

    append_dict_row(
        "Search Logs",
        {
            "User Email": user_email,
            "Phone Number": phone,
            "Phone Normalize": phone_normalized,
            "Result Found": "Yes" if result_found else "No",
            "Searched At": current_datetime(),
        },
    )


# -------------------------------------------------
# Auth Decorators
# -------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))

        if session["user"].get("role") != "admin":
            flash("Admin access required.")
            return redirect(url_for("dashboard"))

        return f(*args, **kwargs)

    return decorated


def user_or_admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))

        if session["user"].get("role") not in ["admin", "user"]:
            flash("Access denied.")
            return redirect(url_for("dashboard"))

        return f(*args, **kwargs)

    return decorated


# -------------------------------------------------
# Routes: Auth
# -------------------------------------------------

@app.route("/")
def home():
    if "user" in session:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


@app.route("/login")
def login():
    oauth_ready = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
    return render_template("login.html", oauth_ready=oauth_ready)


@app.route("/google-login")
def google_login():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        flash("Google OAuth credentials are not configured.")
        return redirect(url_for("login"))

    redirect_uri = url_for("google_callback", _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route("/google-callback")
def google_callback():
    token = google.authorize_access_token()
    user_info = token.get("userinfo")

    if not user_info:
        try:
            user_info = google.parse_id_token(token)
        except Exception:
            user_info = {}

    email = str(user_info.get("email", "")).lower().strip()
    name = str(user_info.get("name", "")).strip()

    if not email:
        flash("Google login failed. Please try again.")
        return redirect(url_for("login"))

    allowed_user = get_user(email)

    if not allowed_user:
        flash("Access denied. Your email is not approved.")
        return redirect(url_for("login"))

    session["user"] = {
        "email": email,
        "name": allowed_user.get("name") or name or email.split("@")[0],
        "role": allowed_user.get("role", "user"),
        "plan": allowed_user.get("plan", "free"),
    }

    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# -------------------------------------------------
# Routes: Dashboard
# -------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    role = session["user"].get("role", "user")

    reports = get_records("Sheet1")
    reviews = get_records("Courier Reviews")
    users = get_records("Users")
    searches = get_records("Search Logs")
    alerts = list(reversed(get_records("Alert Logs")))[:10]

    if role == "admin":
        approved_reports = [r for r in reports if is_report_approved(r)]
        pending_reports = [
            r for r in reports
            if str(r.get("Verification Status", "")).lower().strip() == "pending"
        ]

        recent_reports = list(reversed(reports))[:10]

        stats = {
            "total_reports": len(reports),
            "approved_reports": len(approved_reports),
            "pending_reports": len(pending_reports),
            "total_users": len(users),
            "total_reviews": len(reviews),
            "total_searches": len(searches),
        }

        return render_template(
            "dashboard.html",
            user=session["user"],
            stats=stats,
            recent_reports=recent_reports,
            is_admin=True,
            alerts=alerts,
        )

    user_email = session["user"].get("email", "")

    user_searches = [
        s for s in searches
        if str(s.get("User Email", "")).lower().strip() == user_email.lower()
    ]

    user_stats = {
        "my_searches": len(user_searches),
        "courier_reviews": len(reviews),
    }

    return render_template(
        "dashboard.html",
        user=session["user"],
        stats=user_stats,
        recent_reports=[],
        is_admin=False,
        alerts=[],
    )


# -------------------------------------------------
# Routes: Risk Check
# -------------------------------------------------

@app.route("/search", methods=["GET", "POST"])
@user_or_admin_required
def search():
    results = []
    searched = False
    search_phone = ""
    risk_level = "No Issue Found"

    if request.method == "POST":
        phone = request.form.get("phone", "").strip()
        search_phone = phone
        searched = True

        phone_normalized = normalize_phone(phone)

        if phone_normalized:
            all_reports = get_records("Sheet1")
            matched_reports = []

            for record in all_reports:
                record_phone = str(record.get("Phone Number", "")).strip()
                record_normalized = str(record.get("Phone Normalized", "")).strip()

                if not record_normalized:
                    record_normalized = normalize_phone(record_phone)

                if record_normalized == phone_normalized and is_report_approved(record):
                    matched_reports.append(record)

            results = matched_reports
            risk_level = calculate_risk_level(results)
            log_search(phone, phone_normalized, len(results) > 0)

    return render_template(
    "index.html",
    results=results,
    searched=searched,
    search_phone=search_phone,
    risk_level=risk_level,
    risk=risk_level,
    user=session["user"],
    )


# -------------------------------------------------
# Routes: Submit Delivery Issue
# -------------------------------------------------

@app.route("/add", methods=["GET", "POST"])
@user_or_admin_required
def add():
    success = False

    if request.method == "POST":
        phone = request.form.get("phone", "").strip()
        customer_name = request.form.get("name", "").strip()
        city = request.form.get("city", "").strip()
        reason = request.form.get("reason", "").strip()

        issue_type = (
            request.form.get("issue_type", "").strip()
            or request.form.get("status", "").strip()
            or reason
        )

        reported_by = (
            request.form.get("reported_by", "").strip()
            or session["user"].get("name", "")
            or session["user"].get("email", "")
        )

        phone_normalized = normalize_phone(phone)

        if not phone_normalized:
            flash("Please enter a valid phone number.")
            return render_template("add.html", success=False, user=session["user"])

        row = {
            "Tracking ID": generate_tracking_id(),
            "Phone Number": phone,
            "Customer Name": customer_name,
            "City": city,
            "Reason": issue_type or reason,
            "Reported By": reported_by,
            "Date": today_date(),
            "Phone Normalized": phone_normalized,
            "Verification Status": "Approved",
        }

        append_dict_row("Sheet1", row)
        success = True
        flash("Delivery issue submitted successfully.")

    return render_template("add.html", success=success, user=session["user"])


# -------------------------------------------------
# Routes: Courier Reviews
# -------------------------------------------------

@app.route("/courier-reviews", methods=["GET", "POST"])
@user_or_admin_required
def courier_reviews():
    success = False

    if request.method == "POST":
        courier = request.form.get("courier", "").strip()
        city = request.form.get("city", "").strip()
        rating = request.form.get("rating", "").strip()
        review = request.form.get("review", "").strip()

        row = {
            "Courier Name": courier,
            "City": city,
            "Rating": rating,
            "Review": review,
            "Reported By": session["user"].get("email", ""),
            "Date": today_date(),
        }

        append_dict_row("Courier Reviews", row)
        success = True
        flash("Courier review submitted successfully.")

    reviews = list(reversed(get_records("Courier Reviews")))

    return render_template(
        "courier_reviews.html",
        reviews=reviews,
        success=success,
        user=session["user"],
    )


# -------------------------------------------------
# Routes: Webhook
# -------------------------------------------------

@app.route("/webhooks/postex/status", methods=["POST"])
def postex_status_webhook():
    received_secret = request.headers.get("X-PakShield-Webhook-Secret", "").strip()
    expected_secret = POSTEX_WEBHOOK_SECRET.strip()

    if expected_secret:
        header_valid = received_secret == expected_secret
    else:
        header_valid = True

    payload = request.get_json(silent=True)

    if payload is None:
        form_data = request.form.to_dict()
        if form_data:
            payload = form_data
        else:
            payload = {"raw_body": request.get_data(as_text=True)}

    tracking_number = find_value_in_payload(
        payload,
        [
            "trackingNumber",
            "tracking_number",
            "trackingNo",
            "tracking_no",
            "consignmentNumber",
            "cn",
            "orderTrackingNumber",
        ],
    )

    status = find_value_in_payload(
        payload,
        [
            "transactionStatus",
            "orderStatus",
            "status",
            "statusName",
            "currentStatus",
            "transactionStatusMessage",
            "orderStatusName",
        ],
    )

    raw_payload = json.dumps(payload, ensure_ascii=False)

    append_dict_row(
        "PostEx Webhook Logs",
        {
            "Webhook ID": str(uuid.uuid4())[:8].upper(),
            "Received At": current_datetime(),
            "Header Secret Valid": "Yes" if header_valid else "No",
            "Tracking Number": str(tracking_number),
            "Status": str(status),
            "Raw Payload": raw_payload[:45000],
        },
    )

    alert_created = False

    if header_valid and is_risky_postex_status(status):
        alert_created = create_postex_alert(payload, tracking_number, status)

    if not header_valid:
        return {"ok": False, "message": "Invalid webhook secret"}, 401

    return {
        "ok": True,
        "message": "Webhook received",
        "trackingNumber": str(tracking_number),
        "status": str(status),
        "alertCreated": alert_created,
    }, 200


# -------------------------------------------------
# Routes: Admin
# -------------------------------------------------

@app.route("/admin")
@admin_required
def admin():
    users = get_records("Users")
    reports = get_records("Sheet1")

    pending_reports = [
        r for r in reports
        if str(r.get("Verification Status", "")).lower().strip() == "pending"
    ]

    approved_reports = [r for r in reports if is_report_approved(r)]

    stats = {
        "total_reports": len(reports),
        "approved_reports": len(approved_reports),
        "pending_reports": len(pending_reports),
        "total_users": len(users),
    }

    return render_template(
        "admin.html",
        users=users,
        pending_reports=pending_reports,
        total_bad=len(reports),
        approved_reports=len(approved_reports),
        pending_count=len(pending_reports),
        stats=stats,
        user=session["user"],
    )


@app.route("/admin/add-user", methods=["POST"])
@admin_required
def add_user():
    email = request.form.get("email", "").lower().strip()
    name = request.form.get("name", "").strip()
    role = request.form.get("role", "user").lower().strip()
    plan = request.form.get("plan", "free").lower().strip()

    if role not in ["admin", "user"]:
        role = "user"

    existing_user = get_user(email)

    if existing_user:
        flash("User already exists.")
        return redirect(url_for("admin"))

    row = {
        "Email": email,
        "Name": name,
        "Role": role,
        "Plan": plan,
        "Date Added": today_date(),
    }

    append_dict_row("Users", row)

    flash("User added successfully.")
    return redirect(url_for("admin"))


@app.route("/admin/report/<tracking_id>/approve", methods=["POST"])
@admin_required
def approve_report(tracking_id):
    table, row_id = find_row_by_value("Sheet1", "Tracking ID", tracking_id)

    if not table:
        flash("Report not found.")
        return redirect(url_for("admin"))

    update_row_value(table, row_id, "Verification Status", "Approved")

    flash("Report approved successfully.")
    return redirect(url_for("admin"))


@app.route("/admin/report/<tracking_id>/reject", methods=["POST"])
@admin_required
def reject_report(tracking_id):
    table, row_id = find_row_by_value("Sheet1", "Tracking ID", tracking_id)

    if not table:
        flash("Report not found.")
        return redirect(url_for("admin"))

    update_row_value(table, row_id, "Verification Status", "Rejected")

    flash("Report rejected successfully.")
    return redirect(url_for("admin"))


@app.route("/admin/report/<tracking_id>/delete", methods=["POST"])
@admin_required
def delete_report(tracking_id):
    table, row_id = find_row_by_value("Sheet1", "Tracking ID", tracking_id)

    if not table:
        flash("Report not found.")
        return redirect(url_for("admin"))

    delete_row(table, row_id)

    flash("Report deleted successfully.")
    return redirect(url_for("admin"))


# -------------------------------------------------
# Error Handlers
# -------------------------------------------------

@app.errorhandler(404)
def not_found(error):
    return "Page not found.", 404


@app.errorhandler(500)
def server_error(error):
    print(error)
    return "Server error. Please check the terminal logs.", 500


if __name__ == "__main__":
    app.run(debug=True)
