# pets_view.py
import streamlit as st
from datetime import datetime, timezone
import storage

# ---------------- helpers ----------------
def _ensure_pets_in_session():
    if "pets" not in st.session_state:
        st.session_state.pets = storage.load_pets([])
    if "pets_subview" not in st.session_state:
        st.session_state.pets_subview = "list"   # "list" | "add" | "edit"
    if "pets_edit_id" not in st.session_state:
        st.session_state.pets_edit_id = None


def _next_pet_id(pets):
    return (max([p.get("pet_id", 0) for p in pets]) + 1) if pets else 1


# ---------------- list view ----------------
def _render_pet_list():
    _ensure_pets_in_session()
    pets = st.session_state.pets

    st.header("🐾 Pet Database (Owner)")
    st.caption(f"Total pets: {len(pets)}")

    if st.button("➕ Add Pet"):
        st.session_state.pets_subview = "add"
        st.rerun()

    if not pets:
        st.info("No pet records yet. Pets will appear here after confirmed bookings or manual additions.")
        return

    # Display the table
    st.dataframe(
        [
            {k: p.get(k, "") for k in [
                "pet_id", "pet_name", "pet_type", "pet_breed",
                "owner_username", "visit_count", "last_updated", "notes"
            ]}
            for p in pets
        ],
        use_container_width=True
    )

    # Select a pet to edit
    st.subheader("✏️ Edit Pet Info")
    pet_ids = [p["pet_id"] for p in pets]
    if pet_ids:
        selected_id = st.selectbox("Select Pet ID to Edit", pet_ids, index=0)
        if st.button("Edit Selected Pet"):
            st.session_state.pets_edit_id = selected_id
            st.session_state.pets_subview = "edit"
            st.rerun()


# ---------------- add pet form ----------------
def _render_add_pet():
    st.header("➕ Add New Pet")

    st.caption("Fill the details below to add a new pet record.")

    pet_name = st.text_input("Pet Name *")
    pet_type = st.selectbox("Pet Type *", ["Dog", "Cat", "Other"])
    pet_breed = st.text_input("Pet Breed (optional)")
    owner_username = st.text_input("Owner Username *")
    notes = st.text_area("Notes (optional)")

    if st.button("Save Pet Record"):
        if not pet_name.strip() or not owner_username.strip():
            st.warning("Please fill in the required fields (Pet Name, Owner Username).")
            return

        pets = st.session_state.pets
        now_iso = datetime.now(timezone.utc).isoformat()

        new_pet = {
            "pet_id": _next_pet_id(pets),
            "pet_name": pet_name.strip(),
            "pet_type": pet_type.strip(),
            "pet_breed": pet_breed.strip(),
            "owner_username": owner_username.strip(),
            "notes": notes.strip(),
            "created_at": now_iso,
            "last_updated": now_iso,
            "visit_count": 0
        }

        pets.append(new_pet)
        storage.save_pets(pets)

        st.success("✅ New pet record added successfully!")
        st.session_state.pets_subview = "list"
        st.rerun()

    if st.button("← Back to List"):
        st.session_state.pets_subview = "list"
        st.rerun()


# ---------------- edit pet info form ----------------
def _render_edit_pet():
    st.header("✏️ Edit Pet Info")

    pets = st.session_state.pets
    pet_id = st.session_state.pets_edit_id
    if pet_id is None:
        st.warning("No pet selected.")
        st.session_state.pets_subview = "list"
        st.rerun()
        return

    # find the selected pet
    pet = next((p for p in pets if p.get("pet_id") == pet_id), None)
    if not pet:
        st.error("Pet not found.")
        st.session_state.pets_subview = "list"
        st.rerun()
        return

    st.markdown(f"**Editing:** {pet['pet_name']} (Owner: {pet['owner_username']})")

    pet_breed = st.text_input("Pet Breed (optional)", value=pet.get("pet_breed", ""))
    notes = st.text_area("Notes", value=pet.get("notes", ""))

    if st.button("💾 Save Changes"):
        pet["pet_breed"] = pet_breed.strip()
        pet["notes"] = notes.strip()
        pet["last_updated"] = datetime.now(timezone.utc).isoformat()
        storage.save_pets(pets)
        st.success("Changes saved successfully!")
        st.session_state.pets_subview = "list"
        st.rerun()

    if st.button("← Cancel"):
        st.session_state.pets_subview = "list"
        st.rerun()


# ---------------- main entry ----------------
def show_owner_pets():
    """Owner: Pet Database with Add/Edit capability."""
    _ensure_pets_in_session()
    view = st.session_state.pets_subview

    if view == "add":
        _render_add_pet()
    elif view == "edit":
        _render_edit_pet()
    else:
        _render_pet_list()
