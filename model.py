import logging
from dataclasses import dataclass
from typing import Optional
from enum import Enum
from transformers import pipeline

# Configure logging
logging.basicConfig(
    filename='complaint_processing.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load NLP models
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

class ComplaintStatus(Enum):
    PENDING = "pending"
    REJECTED = "rejected"
    ACCEPTED = "accepted"
    OUT_OF_SCOPE = "out_of_scope"
    REQUIRES_IMAGE = "requires_image"

@dataclass
class ComplaintVerificationResult:
    status: ComplaintStatus
    confidence: float
    message: str
    department: Optional[str] = None
    sub_category: Optional[str] = None
    is_urgent: bool = False
    requires_image: bool = False

class ComplaintProcessor:
    def __init__(self, text_confidence_threshold: float = 0.3):
        self.text_confidence_threshold = text_confidence_threshold
        
        # Departments and categories
        self.departments = {
            "Electricity Department": ["Power Outage", "Streetlight Issue", "Faulty Meter", "Billing Issue"],
            "Water Supply Department": ["No Water", "Water Leakage", "Polluted Water", "Sewage Issue"],
            "Road & Transport": ["Potholes", "Traffic Signal Malfunction", "Public Transport Issue"],
            "Waste Management": ["Garbage Collection Delay", "Illegal Dumping", "Recycling Issue"],
            "Public Safety": ["Crime Report", "Harassment", "Fire Incident", "Accident Report"],
            "Health & Sanitation": ["Hospital Complaint", "Emergency Medical Assistance", "Sanitation Issue"],
            "Education": ["School Infrastructure Issue", "Teacher Misconduct", "Lack of Study Materials"]
        }

        self.image_required_categories = {
            "Waste Management": ["Garbage Collection Delay", "Illegal Dumping"],
            "Road & Transport": ["Potholes", "Traffic Signal Malfunction"],
            "Water Supply Department": ["Water Leakage", "Sewage Issue"],
            "Public Safety": ["Fire Incident", "Accident Report"]
        }

        self.urgent_keywords = ["fire", "accident", "emergency", "life-threatening", "collapse", "urgent", "critical", "immediate"]

    def requires_image(self, category: str, sub_category: str) -> bool:
        """Check if a complaint requires an image for verification"""
        return category in self.image_required_categories and sub_category in self.image_required_categories[category]

    def process_complaint(self, complaint_text: str) -> ComplaintVerificationResult:
        """
        Process a complaint through the complete workflow
        """
        # Text classification
        main_categories = list(self.departments.keys())
        classification = classifier(complaint_text, candidate_labels=main_categories)

        # Check if complaint is valid
        if classification["scores"][0] < self.text_confidence_threshold:
            return ComplaintVerificationResult(
                status=ComplaintStatus.OUT_OF_SCOPE,
                confidence=classification["scores"][0],
                message="Complaint does not match any government category."
            )

        main_department = classification["labels"][0]
        sub_categories = self.departments[main_department]
        sub_classification = classifier(complaint_text, candidate_labels=sub_categories)
        sub_department = sub_classification["labels"][0]

        print(f"Assigned Department: {main_department}")
        print(f"Assigned Sub-Category: {sub_department}")

        needs_image = self.requires_image(main_department, sub_department)

        if needs_image:
            return ComplaintVerificationResult(
                status=ComplaintStatus.REQUIRES_IMAGE,
                confidence=classification["scores"][0],
                message="Please provide an image to support your complaint.",
                department=main_department,
                sub_category=sub_department,
                requires_image=True
            )

        is_urgent = any(word in complaint_text.lower() for word in self.urgent_keywords)

        return ComplaintVerificationResult(
            status=ComplaintStatus.ACCEPTED,
            confidence=classification["scores"][0],
            message="Complaint accepted and will be processed.",
            department=main_department,
            sub_category=sub_department,
            is_urgent=is_urgent
        )
