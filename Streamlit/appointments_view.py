# appointments_view.py
import os, json, uuid
import streamlit as st
from datetime import datetime, date as date_cls, time, timezone
import storage  # used to read/write pets data

# basic config
DETAILS_JSON = "booking_details.json"   # confirmed bookings file (JSON list)
BOOKING_FILE = "booking.txt"            # slot counters file: "YYYY-MM-DD|HH:MM AM|count"
MAX_PER_SLOT = 2

# fixed timeslots offered
FIXED_SLOTS = [
    time(9, 0),
    time(10, 0),
    time(11, 0),
    time(14, 0),
    time(15, 0),
    time(16, 0),
]

# keep wizard state in session
def _ensure_appt_session():
    if "appointments_subview" not in st.session_state:
        st.session_state.appointments_subview = "book"  # "book" | "info" | "summary"
    if "appointment_date" not in st.session_state:
        st.session_state.appointment_date = None
    if "appointment_slot" not in st.session_state:
        st.session_state.appointment_slot = None

# slot counters (plain text file)
def init_bookings():
    if not os.path.exists(BOOKING_FILE):
        with open(BOOKING_FILE, "w") as f:
            f.write("")

def read_bookings():
    # read lines and build {"date|slot": count}
    data = {}
    if os.path.exists(BOOKING_FILE):
        with open(BOOKING_FILE, "r") as f:
            for raw in f:
                line = raw.strip()
                if not line:
                    continue
                parts = line.split("|")
                if len(parts) != 3:
                    continue
                appt_date, slot, count_str = parts
                key = f"{appt_date}|{slot}"
                try:
                    data[key] = int(count_str)
                except ValueError:
                    continue
    return data

def write_bookings(data: dict):
    # write {"date|slot": count} back to file
    with open(BOOKING_FILE, "w") as f:
        for key, count in data.items():
            appt_date, slot = key.split("|", 1)
            f.write(f"{appt_date}|{slot}|{count}\n")

def get_availability(appt_date: str, slot_label: str, max_per_slot=MAX_PER_SLOT):
    # return (key, current, remaining) for a slot
    key = f"{appt_date}|{slot_label}"
    data = read_bookings()
    current = data.get(key, 0)
    remaining = max_per_slot - current
    return key, current, remaining

def book_slot(key: str, current: int, max_per_slot=MAX_PER_SLOT):
    # increase count if space is available
    data = read_bookings()
    if current < max_per_slot:
        data[key] = current + 1
        write_bookings(data)
        return True
    return False

def generate_booking_id():
    # e.g., BK-20251016-8F3A2C1D
    return f"BK-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

# booking details (JSON) helpers
def _load_details() -> list:
    if not os.path.exists(DETAILS_JSON):
        return []
    try:
        with open(DETAILS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []

def _save_details(records: list):
    with open(DETAILS_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

def save_owner_pet_details(record: dict):
    recs = _load_details()
    recs.append(record)
    _save_details(recs)

# booking screen
def _render_book_view():
    st.header("📅 Appointments")
    init_bookings()

    # quick view of my bookings
    with st.container(border=True):
        st.subheader("My Bookings")
        if st.button("Show my bookings"):
            records = _load_details()
            if not records:
                st.info("No bookings found.")
            else:
                logged_username = st.session_state.get("logged_user", {}).get("username", "").strip().lower()
                logged_fullname = st.session_state.get("logged_user", {}).get("full_name", "").strip().lower()

                def _owner_name(rec):
                    return rec.get("owner", {}).get("name", "").strip().lower()

                records_rev = list(reversed(records))
                filtered = []
                if logged_username:
                    filtered = [r for r in records_rev if r.get("username", "").strip().lower() == logged_username]
                if not filtered and logged_fullname:
                    filtered = [r for r in records_rev if _owner_name(r) == logged_fullname]

                if not filtered:
                    st.info("No bookings for your account yet.")
                else:
                    for i, record in enumerate(filtered, start=1):
                        title = f"📋 Booking #{i} – {record['pet']['name']} ({record['pet']['type']})"
                        with st.expander(title):
                            col1, col2 = st.columns([1.2, 1])
                            with col1:
                                st.caption("Booking ID")
                                st.code(record["booking_id"])
                            with col2:
                                st.caption("Date & Time")
                                st.write(f"{record['appointment_date']} at {record['appointment_slot']}")
                            st.caption("Owner")
                            st.write(f"{record['owner']['name']} ({record['owner']['mobile']})")

    # choose date and slot
    today = date_cls.today()
    appt_date = st.date_input("Select Appointment Date", min_value=today, value=today)
    slot_options = [t.strftime("%I:%M %p") for t in FIXED_SLOTS]
    selected_slot = st.selectbox("Choose a timeslot", slot_options)

    # show availability status
    appt_date_str = appt_date.strftime("%Y-%m-%d")
    key, current_count, remaining = get_availability(appt_date_str, selected_slot, MAX_PER_SLOT)

    if remaining <= 0:
        st.error(f"Not available (0/{MAX_PER_SLOT} remaining)")
    elif remaining == 1:
        st.warning(f"Available: 1 spot left (1/{MAX_PER_SLOT})")
    else:
        st.info(f"Available: {remaining} spot(s) ({current_count}/{MAX_PER_SLOT} booked)")

    # proceed to info form (no reservation yet)
    if st.button("Book this slot", disabled=(remaining <= 0)):
        st.session_state.appointment_date = appt_date_str
        st.session_state.appointment_slot = selected_slot
        st.session_state.appointments_subview = "info"
        st.rerun()

# info form screen
def _render_info_view():
    st.header("📝 Owner & Pet Information")
    logged_username = st.session_state.get("logged_user", {}).get("username", "").strip().lower()
    appt_date = st.session_state.get("appointment_date")
    appt_slot = st.session_state.get("appointment_slot")

    # need selected slot from previous step
    if not (appt_date and appt_slot):
        st.warning("No appointment details found. Please book an appointment first.")
        if st.button("← Back to Booking"):
            st.session_state.appointments_subview = "book"
            st.rerun()
        return

    st.success(f"✅ Your appointment is on {appt_date} at {appt_slot}.")

    # quick back button
    st.button("← Back", on_click=lambda: st.session_state.update({"appointments_subview": "book"}))

    # form (one submit)
    with st.form("owner_pet_form", clear_on_submit=False):
        # owner fields
        owner_name  = st.text_input("Owner name *")
        owner_phone = st.text_input("Mobile number (e.g., 07XXXXXXXX) *")
        owner_nic   = st.text_input("NIC *")
        owner_email = st.text_input("Email *")

        # pet fields
        st.write("### Pet information")
        pet_type = st.selectbox("Pet type *", ["Dog", "Cat", "Other"])
        other_type = ""
        if pet_type == "Other":
            other_type = st.text_input("Specify other type *")
        pet_name = st.text_input("Pet name *")
        c1, c2 = st.columns(2)
        with c1:
            pet_age_years  = st.number_input("Pet age (years)", min_value=0, step=1, value=0)
        with c2:
            pet_age_months = st.number_input("Pet age (months)", min_value=0, max_value=11, step=1, value=0)
        pet_breed = st.text_input("Pet breed (optional)")
        notes     = st.text_area("Reason / notes (optional)")

        confirm = st.form_submit_button("Confirm")

    if confirm:
        # quick validations
        errors = []
        def _empty(x): return not str(x).strip()
        if _empty(owner_name):  errors.append("Owner name is required.")
        if _empty(owner_phone): errors.append("Mobile number is required.")
        if _empty(owner_nic):   errors.append("NIC is required.")
        if _empty(owner_email): errors.append("Email is required.")
        if _empty(pet_name):    errors.append("Pet name is required.")
        if pet_type == "Other" and _empty(other_type):
            errors.append("Please specify the pet type when 'Other' is selected.")
        if owner_email and "@" not in owner_email:
            errors.append("Email looks invalid.")
        cleaned_phone = owner_phone.strip().replace(" ", "")
        if not cleaned_phone.isdigit():
            errors.append("Mobile number should contain only digits.")
        elif len(cleaned_phone) != 10 or not cleaned_phone.startswith("0"):
            errors.append("Mobile number must be 10 digits and start with 0 (e.g., 07XXXXXXXX).")
        if errors:
            for e in errors:
                st.error(e)
            return

        # reserve slot now (re-check to avoid race)
        init_bookings()
        key, current_count, remaining = get_availability(appt_date, appt_slot, MAX_PER_SLOT)
        if remaining <= 0:
            st.error("Sorry, this timeslot just became full. Please choose another slot.")
            st.session_state.appointments_subview = "book"
            st.rerun()

        if not book_slot(key, current_count, MAX_PER_SLOT):
            st.error("Sorry, this timeslot just became full. Please choose another slot.")
            st.session_state.appointments_subview = "book"
            st.rerun()


        # save booking record
        booking_id = generate_booking_id()
        record = {
            "booking_id": booking_id,
            "username": logged_username,
            "appointment_date": appt_date,
            "appointment_slot": appt_slot,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "owner": {
                "name": owner_name.strip(),
                "mobile": owner_phone.strip(),
                "nic": owner_nic.strip(),
                "email": owner_email.strip()
            },
            "pet": {
                "name": pet_name.strip(),
                "type": (other_type.strip() if pet_type == "Other" else pet_type),
                "age_years": int(pet_age_years),
                "age_months": int(pet_age_months),
                "breed": pet_breed.strip(),
                "notes": notes.strip(),
            }
        }
        save_owner_pet_details(record)

        # upsert into pets list
        if "pets" not in st.session_state:
            st.session_state.pets = storage.load_pets([])
        pets = st.session_state.pets
        now_iso = datetime.now(timezone.utc).isoformat()
        key_owner = logged_username.strip().lower()
        key_pet = record["pet"]["name"].strip().lower()
        existing = next(
            (p for p in pets
             if p.get("owner_username","").strip().lower()==key_owner
             and p.get("pet_name","").strip().lower()==key_pet),
            None
        )
        pet_type_value = record["pet"]["type"]
        breed_value = record["pet"]["breed"]
        if existing:
            existing["visit_count"] = int(existing.get("visit_count",0)) + 1
            existing["last_updated"] = now_iso
            if pet_type_value and not existing.get("pet_type"):
                existing["pet_type"] = pet_type_value
            if breed_value and not existing.get("pet_breed"):
                existing["pet_breed"] = breed_value
        else:
            new_id = (max([p.get("pet_id",0) for p in pets]) + 1) if pets else 1
            pets.append({
                "pet_id": new_id,
                "pet_name": record["pet"]["name"],
                "pet_type": pet_type_value,
                "pet_breed": breed_value,
                "owner_username": logged_username,
                "notes": "",
                "created_at": now_iso,
                "last_updated": now_iso,
                "visit_count": 1
            })
        storage.save_pets(pets)

        # show summary next
        st.session_state["appointments_latest"] = record
        st.session_state.appointments_subview = "summary"
        st.success("🎉 Booking confirmed!")
        st.rerun()

# summary screen
def _render_summary_view():
    st.header("📋 Appointment Summary")
    record = st.session_state.get("appointments_latest")
    if not record:
        st.warning("No recent booking found.")
        if st.button("← Back to Appointments"):
            st.session_state.appointments_subview = "book"
            st.rerun()
        return

    # quick back link
    st.button("← Back", on_click=lambda: st.session_state.update({"appointments_subview": "book"}))

    # booking details
    st.subheader("Appointment Details")
    with st.container(border=True):
        col1, col2, col3 = st.columns([1.2, 1, 1])
        with col1:
            st.caption("Booking ID")
            st.code(record["booking_id"], language=None)
        with col2:
            st.caption("Date")
            st.write(record["appointment_date"])
        with col3:
            st.caption("Time")
            st.write(record["appointment_slot"])

    st.divider()
    st.subheader("Owner Information")
    st.write(f"Name: {record['owner']['name']}")
    st.write(f"Mobile: {record['owner']['mobile']}")
    st.write(f"NIC: {record['owner']['nic']}")
    st.write(f"Email: {record['owner']['email']}")

    st.divider()
    st.subheader("Pet Information")
    st.write(f"Name: {record['pet']['name']}")
    st.write(f"Type: {record['pet']['type']}")
    st.write(f"Age: {record['pet']['age_years']} years {record['pet']['age_months']} months")
    st.write(f"Breed: {record['pet']['breed'] or '-'}")
    st.write(f"Notes: {record['pet']['notes'] or '-' }")

    st.divider()
    if st.button("← Back to Appointments"):
        st.session_state.appointments_subview = "book"
        st.rerun()

# entry points
def show_user_appointments():
    _ensure_appt_session()
    view = st.session_state.appointments_subview
    if view == "info":
        _render_info_view()
    elif view == "summary":
        _render_summary_view()
    else:
        _render_book_view()

def show_owner_appointments():
    st.header("🗂 Appointments Management (All)")
    records = _load_details()
    if not records:
        st.info("No appointments yet.")
        return

    # filter control
    filter_choice = st.selectbox("Show", ["All", "Current / Upcoming", "Past"], index=0)

    # parse appointment_date safely
    def _rec_date(rec):
        from datetime import datetime, date as date_cls
        try:
            return datetime.fromisoformat(rec.get("appointment_date", "")).date()
        except Exception:
            return date_cls.today()

    today = date_cls.today()
    if filter_choice == "Current / Upcoming":
        show_items = [r for r in records if _rec_date(r) >= today]
    elif filter_choice == "Past":
        show_items = [r for r in records if _rec_date(r) < today]
    else:
        show_items = records

    # sort newest first by (appointment_date, created_at)
    def _sort_key(r):
        d = _rec_date(r)
        ca = r.get("created_at", "")
        return d, ca
    show_items.sort(key=_sort_key, reverse=True)

    st.caption(f"Showing {len(show_items)} appointment(s)")

    # flatten for table view
    rows = []
    for r in show_items:
        owner = r.get("owner", {})
        pet   = r.get("pet", {})
        rows.append({
            "booking_id": r.get("booking_id", ""),
            "date": r.get("appointment_date", ""),
            "time": r.get("appointment_slot", ""),
            "owner_name": owner.get("name", ""),
            "owner_mobile": owner.get("mobile", ""),
            "owner_nic": owner.get("nic", ""),
            "owner_email": owner.get("email", ""),
            "pet_name": pet.get("name", ""),
            "pet_type": pet.get("type", ""),
            "pet_breed": pet.get("breed", ""),
            "pet_age": f"{pet.get('age_years',0)}y {pet.get('age_months',0)}m",
            "notes": pet.get("notes", ""),
            "created_at": r.get("created_at", ""),
        })

    st.dataframe(rows, use_container_width=True)

    # back to dashboard
    st.divider()
    if st.button("← Back to Dashboard"):
        st.session_state.current_view = "dashboard"
        st.rerun()