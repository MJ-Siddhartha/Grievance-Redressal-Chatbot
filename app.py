import streamlit as st
from model import ComplaintProcessor, ComplaintStatus

# Streamlit UI
st.title("Complaint Processing System")
st.write("Enter a complaint and check its status.")

# Initialize processor
processor = ComplaintProcessor()

# Session state to store complaint status
if "complaint_status" not in st.session_state:
    st.session_state.complaint_status = "No complaint submitted yet."
if "last_result" not in st.session_state:
    st.session_state.last_result = None  # Store last complaint result
if "image_required" not in st.session_state:
    st.session_state.image_required = False  # Flag to track if image is needed

# User Input
complaint_text = st.text_input("Enter Complaint Text:")
submit_button = st.button("Submit Complaint")

# Process Complaint
if submit_button and complaint_text:
    result = processor.process_complaint(complaint_text)
    st.session_state.last_result = result  # Store the latest complaint result
    st.session_state.image_required = result.requires_image  # Store if image is required

    # Set complaint status
    if result.status == ComplaintStatus.REQUIRES_IMAGE:
        st.session_state.complaint_status = "Complaint Pending: Image Required"
    elif result.status == ComplaintStatus.ACCEPTED:
        st.session_state.complaint_status = "Complaint Submitted: Processing"
    else:
        st.session_state.complaint_status = "Complaint Submitted: Pending"

    # Display complaint processing details
    st.subheader("Complaint Processing Result")
    st.write(f"**Status:** {result.status.value.capitalize()}")
    st.write(f"**Department:** {result.department or 'N/A'}")
    st.write(f"**Sub-Category:** {result.sub_category or 'N/A'}")
    st.write(f"**Urgent:** {'Yes' if result.is_urgent else 'No'}")
    st.write(f"**Message:** {result.message}")

# If image is required, ask user to upload it
if st.session_state.image_required:
    uploaded_file = st.file_uploader("Upload an Image (Required for this complaint)", type=["jpg", "png", "jpeg"])
    if uploaded_file:
        st.success("Image uploaded successfully! Your complaint is now being processed.")

# Check Status Button
if st.button("Check Status"):
    st.subheader("Complaint Status")
    st.write(f"### {st.session_state.complaint_status}")

    if st.session_state.last_result:  # Show last complaint details if available
        result = st.session_state.last_result
        st.write(f"**Status:** {result.status.value.capitalize()}")
        st.write(f"**Department:** {result.department or 'N/A'}")
        st.write(f"**Sub-Category:** {result.sub_category or 'N/A'}")
        st.write(f"**Urgent:** {'Yes' if result.is_urgent else 'No'}")
        st.write(f"**Message:** {result.message}")
