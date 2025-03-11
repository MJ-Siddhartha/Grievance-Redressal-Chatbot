import random
import string
from datetime import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate


# For basic NLP tasks: summarization and tokenization.
# In a production system, use a more advanced NLP library or API.
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

# Download NLTK resources if not already available.
nltk.download('punkt')
nltk.download('stopwords')

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Siddu87@localhost/complaints_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# In-memory storage (for demonstration only)
complaints_db = {}    # complaint_id -> complaint details
otp_sessions = {}     # phone -> OTP details
chat_sessions = {}    # session_id -> list of chat messages

# --- Helper Functions ---

def generate_complaint_id():
    """Generate a random complaint ID."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def generate_otp():
    """Generate a 6-digit OTP."""
    return str(random.randint(100000, 999999))

def summarize_text(text):
    """
    A simple summarization: tokenizes the text, removes stop words,
    counts word frequency, and returns top 5 frequent words as a summary.
    """
    tokens = word_tokenize(text)
    tokens = [t.lower() for t in tokens if t.isalpha()]
    stop_words = set(stopwords.words('english'))
    filtered_tokens = [w for w in tokens if w not in stop_words]
    freq = {}
    for word in filtered_tokens:
        freq[word] = freq.get(word, 0) + 1
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    summary = ' '.join([word for word, count in sorted_words[:5]])
    return summary

def classify_complaint(text):
    """
    Simple keyword-based classifier. Maps complaint text to a category
    based on presence of keywords.
    """
    categories = {
        'electricity': ['power', 'electric', 'light', 'voltage'],
        'water': ['water', 'leak', 'pipe', 'drain', 'faucet'],
        'transport': ['bus', 'train', 'metro', 'commute'],
        'infrastructure': ['road', 'pothole', 'bridge', 'construction'],
        'health': ['hospital', 'clinic', 'health', 'disease', 'medicine']
    }
    text_lower = text.lower()
    for category, keywords in categories.items():
        for kw in keywords:
            if kw in text_lower:
                return category
    return 'general'




def check_priority(text):
    """Mark complaint as high priority if it contains urgent keywords."""
    urgent_keywords = ['urgent', 'immediate', 'asap', 'emergency', 'critical']
    text_lower = text.lower()
    for kw in urgent_keywords:
        if kw in text_lower:
            return 'high'
    return 'normal'

def merge_similar_complaints(new_text):
    """
    Checks existing complaints for similarity using summarized keywords.
    Returns an existing complaint ID if a similar complaint is found.
    """
    new_summary = set(summarize_text(new_text).split())
    for cid, complaint in complaints_db.items():
        existing_summary = set(complaint.get('summary', '').split())
        if len(new_summary & existing_summary) >= 3:
            return cid
    return None


# Define Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

class OTP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(15), nullable=False)
    otp = db.Column(db.String(6), nullable=False)
    verified = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.String(10), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    complaint_text = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    priority = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), default='submitted')
    summary = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class ChatSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(10), unique=True, nullable=False)
    messages = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Create tables
with app.app_context():
    db.create_all()


# --- Routes / Endpoints ---

@app.route('/submit_complaint', methods=['POST'])
def submit_complaint():
    """
    Endpoint to submit a complaint.
    Expects JSON with: name, phone, email, complaint_text.
    Optional: voice_input, image_input, otp_verified.
    """
    data = request.json
    name = data.get('name')
    phone = data.get('phone')
    email = data.get('email')
    text = data.get('complaint_text')
    voice = data.get('voice_input', None)   # In practice, process voice file appropriately.
    image = data.get('image_input', None)   # In practice, decode/process image data.

    if not (name and phone and email and text):
        return jsonify({'error': 'Missing required fields (name, phone, email, complaint_text)'}), 400

    # OTP Verification Check
    otp_entry = OTP.query.filter_by(phone=phone, verified=True).first()
    if not otp_entry:
        return jsonify({'error': 'OTP verification required'}), 403

    # Check if user exists, if not, create user
    user = User.query.filter_by(phone=phone).first()
    if not user:
        user = User(name=name, phone=phone, email=email)
        db.session.add(user)
        db.session.commit()

    # Check for duplicate complaint (merge logic)
    existing_complaint = Complaint.query.filter_by(complaint_text=text).first()
    if existing_complaint:
        return jsonify({
            'message': f'Complaint merged with existing complaint {existing_complaint.complaint_id}',
            'complaint_id': existing_complaint.complaint_id
        }), 200

    # Generate Complaint Details
    complaint_id = generate_complaint_id()
    summary = summarize_text(text)
    category = classify_complaint(text)
    priority = check_priority(text)

    # Save Complaint
    new_complaint = Complaint(
        complaint_id=complaint_id,
        user_id=user.id,
        complaint_text=text,
        summary=summary,
        category=category,
        priority=priority,
        status="forwarded",
        timestamp=datetime.utcnow()
    )

    db.session.add(new_complaint)
    db.session.commit()

    return jsonify({
        'message': 'Complaint submitted successfully',
        'complaint_id': complaint_id,
        'summary': summary,
        'category': category,
        'priority': priority
    }), 200

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    """
    Endpoint to verify OTP.
    Expects JSON with: phone, otp.
    """
    data = request.json
    phone = data.get('phone')
    otp_input = data.get('otp')

    if not phone or not otp_input:
        return jsonify({'error': 'Phone number and OTP are required'}), 400

    # Fetch OTP from database
    otp_entry = OTP.query.filter_by(phone=phone, otp=otp_input, verified=False).first()

    if not otp_entry:
        return jsonify({'error': 'Invalid or expired OTP'}), 400

    # Mark OTP as verified
    otp_entry.verified = True
    db.session.commit()

    return jsonify({'message': 'OTP verified successfully'}), 200

@app.route('/status/<complaint_id>', methods=['GET'])
def complaint_status(complaint_id):
    """
    Endpoint to check the status and alerts for a given complaint.
    """
    complaint = Complaint.query.get(complaint_id)

    if not complaint:
        return jsonify({'error': 'Complaint ID not found.'}), 404

    return jsonify({
        'complaint_id': complaint.id,
        'status': complaint.status,
        'alerts': complaint.alerts  # Assuming alerts is a serialized JSON field in the model
    }), 200

@app.route('/live_chat', methods=['POST'])
def live_chat():
    """
    Live chat endpoint.
    Expects JSON with: session_id (optional) and message.
    If session_id is not provided, a new session is created.
    """
    data = request.json
    session_id = data.get('session_id')
    message = data.get('message')

    if not message:
        return jsonify({'error': 'Message cannot be empty.'}), 400

    # If no session_id, create a new chat session
    if not session_id:
        session_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        new_session = ChatSession(id=session_id, created_at=datetime.datetime.now())
        db.session.add(new_session)
        db.session.commit()

    # Store the user message in the database
    user_message = ChatMessage(session_id=session_id, sender='user', message=message, timestamp=datetime.datetime.now())
    db.session.add(user_message)
    db.session.commit()

    # Simulated AI response
    response_text = f"Received your message: '{message}'. How can I help further?"
    bot_message = ChatMessage(session_id=session_id, sender='bot', message=response_text, timestamp=datetime.datetime.now())
    db.session.add(bot_message)
    db.session.commit()

    # Retrieve full chat history
    chat_history = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.timestamp).all()
    chat_data = [{'sender': msg.sender, 'message': msg.message, 'timestamp': msg.timestamp.isoformat()} for msg in chat_history]

    return jsonify({
        'session_id': session_id,
        'response': response_text,
        'chat_history': chat_data
    }), 200

@app.route('/feedback', methods=['POST'])
def feedback():
    """
    Endpoint to submit feedback on the complaint resolution.
    Expects JSON with: complaint_id and feedback.
    """
    data = request.json
    complaint_id = data.get('complaint_id')
    user_feedback = data.get('feedback')

    # Validate input
    if not complaint_id or not user_feedback:
        return jsonify({'error': 'Missing complaint_id or feedback.'}), 400

    # Fetch complaint from the database
    complaint = Complaint.query.get(complaint_id)
    if not complaint:
        return jsonify({'error': 'Complaint ID not found.'}), 404

    # Update feedback in the database
    complaint.feedback = user_feedback
    db.session.commit()

    return jsonify({'message': 'Feedback submitted. Thank you!'}), 200

@app.route('/official_report/<int:complaint_id>', methods=['GET'])
def official_report(complaint_id):
    """
    Generates a simple official report of the complaint.
    """
    # Fetch complaint from the database
    complaint = Complaint.query.get(complaint_id)
    if not complaint:
        return jsonify({'error': 'Complaint ID not found.'}), 404

    # Prepare report
    report = {
        'Complaint ID': complaint.id,
        'Name': complaint.name,
        'Email': complaint.email,
        'Category': complaint.category,
        'Priority': complaint.priority,
        'Status': complaint.status,
        'Summary': complaint.summary,
        'Timestamp': complaint.timestamp
    }

    return jsonify({'report': report}), 200

# --- Run the Flask app ---
if __name__ == '__main__':
    app.run(debug=True)

