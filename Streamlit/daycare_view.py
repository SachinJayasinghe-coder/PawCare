# daycare_view.py
import streamlit as st
from datetime import datetime, timedelta, time, date as date_cls, timezone
import storage

# --- pricing constants ---
PRICE_HALF_DAY = 700      # LKR
PRICE_FULL_DAY = 1200     # LKR
PRICE_OVERNIGHT = 2200    # LKR per 24h

PACKAGES = ["Half Day", "Full Day", "Overnight Stay"]
OPENING_TIME = time(8, 0)  # Daycare opens at 08:00

# ----------------- helpers -----------------
def _ensure_daycare_in_session():
    """Initialize daycare store + UI subview + temp buffer for 2-step flow."""
    if "daycare" not in st.session_state:
        st.session_state.daycare = storage.load_daycare([])
    if "daycare_subview" not in st.session_state:
        st.session_state.daycare_subview = "book"  # "book" | "info" | "list"
    if "daycare_temp" not in st.session_state:
        st.session_state.daycare_temp = None       # holds step-1 data until confirm

def _next_reservation_id(items):
    return (max([i.get("reservation_id", 0) for i in items]) + 1) if items else 1

def _compute_price(package: str, days: int) -> int:
    if package == "Half Day":
        return PRICE_HALF_DAY
    if package == "Full Day":
        return PRICE_FULL_DAY
    return PRICE_OVERNIGHT * max(1, days)

def _dt_on_dummy(t: time) -> datetime:
    return datetime.combine(datetime.today().date(), t)

def _fmt_time(t: time | None) -> str:
    return t.strftime("%H:%M") if t else "--:--"

def _validate_same_day_window(dropoff_t: time, pickup_t: time, max_hours: int) -> str | None:
    """Half/Full day rule: same day, pickup after dropoff, within 4/8 hours, open from 08:00."""
    if dropoff_t is None or pickup_t is None:
        return "Please choose both drop-off and pick-up times."
    if dropoff_t < OPENING_TIME:
        return "Daycare opens at 08:00. Choose a drop-off time of 08:00 or later."

    d0 = _dt_on_dummy(dropoff_t)
    d1 = _dt_on_dummy(pickup_t)

    if d1 < d0:
        return "Pick-up time must be after the drop-off time."
    if (d1 - d0) > timedelta(hours=max_hours):
        return f"Pick-up must be within {max_hours} hours of drop-off."
    if d1.date() != d0.date():
        return "Pick-up must be on the same day for this package."
    return None

def _ensure_pets_in_session():
    if "pets" not in st.session_state:
        st.session_state.pets = storage.load_pets([])

def _next_pet_id(pets):
    return (max([p.get("pet_id", 0) for p in pets]) + 1) if pets else 1

# ----------------- Step 1: booking form -----------------
def _render_booking_form(username: str):
    st.header("🏡 Daycare Booking")

    # top-right buttons
    c1, c2 = st.columns([1, 0.35])
    with c2:
        if st.button("📋 My Reservations →"):
            st.session_state.daycare_subview = "list"
            st.rerun()

    # --- inputs ---
    pet_name = st.text_input("Pet Name")
    package = st.selectbox("Package", PACKAGES, help="Half Day (≤4h), Full Day (≤8h), Overnight (24h×days)")

    days = 1
    if package == "Overnight Stay":
        days = st.number_input("Number of Days", min_value=1, step=1, value=1)

    # only allow today or future
    today = date_cls.today()
    when_date = st.date_input("Date", min_value=today, value=today)

    dropoff_time = None
    pickup_time = None
    hint_text = ""
    validation = None

    if package == "Half Day":
        col1, col2 = st.columns(2)
        with col1:
            dropoff_time = st.time_input("Drop-off Time", value=OPENING_TIME)
        with col2:
            pickup_time = st.time_input("Pick-up Time", value=None)
        latest_allowed = (_dt_on_dummy(dropoff_time) + timedelta(hours=4)).time() if dropoff_time else None
        hint_text = f"Allowed pick-up window: {_fmt_time(dropoff_time)}–{_fmt_time(latest_allowed)} (≤ 4 hours, same day)."
        validation = _validate_same_day_window(dropoff_time, pickup_time, 4)

    elif package == "Full Day":
        col1, col2 = st.columns(2)
        with col1:
            dropoff_time = st.time_input("Drop-off Time", value=OPENING_TIME)
        with col2:
            pickup_time = st.time_input("Pick-up Time", value=None)
        latest_allowed = (_dt_on_dummy(dropoff_time) + timedelta(hours=8)).time() if dropoff_time else None
        hint_text = f"Allowed pick-up window: {_fmt_time(dropoff_time)}–{_fmt_time(latest_allowed)} (≤ 8 hours, same day)."
        validation = _validate_same_day_window(dropoff_time, pickup_time, 8)

    else:
        # Overnight: flexible
        st.caption("Overnight Stay: flexible times; price is 24h × Number of Days.")
        col1, col2 = st.columns(2)
        with col1:
            dropoff_time = st.time_input("Drop-off Time", value=OPENING_TIME, help="Arrival time")
        with col2:
            pickup_time = st.time_input("Pick-up Time", value=None, help="Return time")

    if hint_text:
        st.caption(hint_text)
    if validation:
        st.warning(validation)

    notes = st.text_area("Notes (optional)")

    # --- live price ---
    total_price = _compute_price(package, days)
    st.markdown(f"**💰 Total Price: Rs {total_price}**")

    # --- continue to step 2 (info) ---
    if st.button("Book"):
        if not pet_name.strip():
            st.warning("Please enter the pet name.")
            return
        if not when_date:
            st.warning("Please select a date.")
            return
        if package in ("Half Day", "Full Day") and validation:
            st.error(validation)
            return

        # Save step-1 data to temp and go to info page
        st.session_state.daycare_temp = {
            "username": username,
            "pet_name": pet_name.strip(),
            "package": package,
            "days": int(days),
            "date": when_date,  # keep date object; convert later
            "dropoff_time": dropoff_time,
            "pickup_time": pickup_time,
            "notes": notes.strip(),
            "price": int(total_price),
        }
        st.session_state.daycare_subview = "info"
        st.rerun()

# ----------------- Step 2: info + confirm -----------------
def _render_info_form(username: str):
    st.header("📝 Your Details")

    temp = st.session_state.daycare_temp
    if not temp:
        st.info("No booking data found. Please start from the booking page.")
        if st.button("← Back to Booking"):
            st.session_state.daycare_subview = "book"
            st.rerun()
        return

    # Summary box
    st.subheader("Booking Summary")
    st.markdown(
        f"""
- **Package:** {temp['package']}
- **Date:** {temp['date'].isoformat()}
- **Drop-off:** {_fmt_time(temp['dropoff_time'])}  
- **Pick-up:** {_fmt_time(temp['pickup_time'])}  
- **Price:** Rs {temp['price']}
- **Pet Name:** {temp['pet_name']}
        """.strip()
    )

    st.divider()

    # Contact + pet details
    default_full_name = st.session_state.logged_user.get("full_name", "")
    full_name = st.text_input("Full Name", value=default_full_name)
    nic = st.text_input("NIC (required)")
    email = st.text_input("Email (optional)", placeholder="e.g., name@example.com")
    phone = st.text_input("Phone (required)", placeholder="e.g., 0712345678", help="Must start with 0 and be exactly 10 digits (e.g., 0712345678)")

    pet_type = st.selectbox("Pet Type", ["Dog", "Cat", "Other"])
    other_type = ""
    if pet_type == "Other":
        other_type = st.text_input("If Other, type here")
    breed = st.text_input("Pet Breed (optional)")

    # Actions
    colA, colB = st.columns([0.4, 0.6])
    with colA:
        if st.button("← Back to Booking"):
            st.session_state.daycare_subview = "book"
            st.rerun()
    with colB:
        if st.button("Confirm Reservation ✅"):
            # Basic required field checks
            if not full_name.strip():
                st.error("Full Name is required.")
                return
            if not nic.strip():
                st.error("NIC is required.")
                return
            if not phone.strip():
                st.error("Phone is required.")
                return
            if pet_type == "Other" and not other_type.strip():
                st.error("Please specify the pet type.")
                return

            # ---- Simple phone & email checks (no regex) ----
            phone_clean = phone.strip().replace(" ", "")
            if not (phone_clean.startswith("0") and len(phone_clean) == 10 and phone_clean.isdigit()):
                st.error("Phone must start with 0 and be exactly 10 digits (e.g., 0712345678).")
                return

            email_clean = email.strip()
            if email_clean and "@" not in email_clean:
                st.error("Please enter a valid email address that includes '@' (e.g., name@example.com).")
                return
            # -----------------------------------------------

            # Save daycare booking
            items = st.session_state.daycare
            now_iso = datetime.now(timezone.utc).isoformat()

            record = {
                "reservation_id": _next_reservation_id(items),
                "username": username,
                "full_name": full_name.strip(),
                "nic": nic.strip(),
                "email": email_clean,
                "phone": phone_clean,
                "pet_type": (other_type.strip() if pet_type == "Other" else pet_type),
                "pet_breed": breed.strip(),
                "pet_name": temp["pet_name"],
                "package": temp["package"],
                "days": temp["days"],
                "date": temp["date"].isoformat(),
                "dropoff_time": _fmt_time(temp["dropoff_time"]),
                "pickup_time": _fmt_time(temp["pickup_time"]),
                "notes": temp["notes"],
                "price": temp["price"],
                "created_at": now_iso,
            }
            items.append(record)
            storage.save_daycare(items)

            # --- upsert into pets.json ---
            if "pets" not in st.session_state:
                st.session_state.pets = storage.load_pets([])
            pets = st.session_state.pets
            key_owner = username.strip().lower()
            key_pet = temp["pet_name"].strip().lower()

            existing = next(
                (p for p in pets
                 if p.get("owner_username", "").strip().lower() == key_owner
                 and p.get("pet_name", "").strip().lower() == key_pet),
                None
            )

            pet_type_value = other_type.strip() if pet_type == "Other" else pet_type

            if existing:
                existing["visit_count"] = int(existing.get("visit_count", 0)) + 1
                existing["last_updated"] = now_iso
                if pet_type_value and not existing.get("pet_type"):
                    existing["pet_type"] = pet_type_value
                if breed.strip() and not existing.get("pet_breed"):
                    existing["pet_breed"] = breed.strip()
            else:
                new_id = (max([p.get("pet_id", 0) for p in pets]) + 1) if pets else 1
                pets.append({
                    "pet_id": new_id,
                    "pet_name": temp["pet_name"],
                    "pet_type": pet_type_value,
                    "pet_breed": breed.strip(),
                    "owner_username": username,
                    "notes": "",
                    "created_at": now_iso,
                    "last_updated": now_iso,
                    "visit_count": 1
                })
            storage.save_pets(pets)

            # Finish
            st.session_state.daycare_temp = None
            st.session_state.daycare_subview = "list"
            st.success("Reservation confirmed! 🎉")
            st.rerun()


# ----------------- My Reservations -----------------
def _render_my_reservations(username: str):
    st.header("📋 My Reservations")

    # back to booking
    if st.button("← Back to Booking"):
        st.session_state.daycare_subview = "book"
        st.rerun()

    # all my records
    items = [r for r in st.session_state.daycare if r.get("username") == username]

    today = date_cls.today()

    def _rec_date(r):
        # r["date"] is stored as "YYYY-MM-DD"
        try:
            return datetime.fromisoformat(r.get("date", "")).date()
        except Exception:
            return today  # treat bad/missing as today to avoid crashes

    # sort: oldest first (by reservation ID)
    items.sort(key=lambda r: r.get("reservation_id", 0))

    if not items:
        st.info("No reservations to show.")
        return

    # card-style list (expanders), similar to Appointments "My Bookings"
    for r in items:
        d = _rec_date(r)
        status = "Past" if d < today else "Upcoming"
        # removed the "#<id>" part here
        title = f"📋 {r.get('pet_name','')} • {r.get('package','')} • {r.get('date','')}"
        with st.expander(title, expanded=False):
            st.caption(f"Status: **{status}**")
            col1, col2 = st.columns([1, 1])
            with col1:
                st.write(f"**Date:** {r.get('date','')}")
                st.write(f"**Drop-off:** {r.get('dropoff_time','')}")
                st.write(f"**Pick-up:** {r.get('pickup_time','')}")
            with col2:
                st.write(f"**Package:** {r.get('package','')} (days: {r.get('days',1)})")
                st.write(f"**Price:** Rs {r.get('price',0)}")

            notes = (r.get("notes") or "").strip() or "-"
            st.write(f"**Notes:** {notes}")


# ----------------- public entry points -----------------
def show_user_daycare():
    """User: Daycare module with 3 subviews: booking → info → list."""
    _ensure_daycare_in_session()
    username = st.session_state.logged_user["username"]
    subview = st.session_state.daycare_subview
    if subview == "info":
        _render_info_form(username)
    elif subview == "list":
        _render_my_reservations(username)
    else:
        _render_booking_form(username)

def show_owner_daycare():
    """Owner: view all daycare reservations with simple date filters."""
    _ensure_daycare_in_session()
    st.header("🗂 Daycare Management (All Reservations)")

    items = st.session_state.daycare

    # ---- filter control ----
    filter_choice = st.selectbox("Show", ["All", "Current / Upcoming", "Past"], index=0)

    if not items:
        st.info("No reservations yet.")
        return

    # ---- apply filter ----
    today = date_cls.today()

    def _rec_date(r):
        # r["date"] is stored as "YYYY-MM-DD"
        try:
            return datetime.fromisoformat(r.get("date", "")).date()
        except Exception:
            # if bad/missing date in data, treat as today so it still shows up
            return today

    if filter_choice == "Current / Upcoming":
        show_items = [r for r in items if _rec_date(r) >= today]
    elif filter_choice == "Past":
        show_items = [r for r in items if _rec_date(r) < today]
    else:
        show_items = items

    st.caption(f"Showing {len(show_items)} reservation(s)")

    if show_items:
        st.dataframe(
            [
                {k: r.get(k, "") for k in [
                    "reservation_id","username","full_name","nic","email","phone",
                    "pet_name","pet_type","pet_breed","package","days","date",
                    "dropoff_time","pickup_time","price","created_at","notes"
                ]}
                for r in show_items
            ],
            use_container_width=True
        )
    else:
        st.info("No reservations for this filter.")