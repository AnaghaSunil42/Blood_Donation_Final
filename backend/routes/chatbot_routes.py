from flask import Blueprint, request, jsonify, current_app, session
import math

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 # km
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2) * math.sin(dLat/2) + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(dLon/2) * math.sin(dLon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c
import google.generativeai as genai
import os

chatbot_bp = Blueprint('chatbot', __name__)

system_instruction = """
You are a helpful AI assistant for 'Lifeline', a Blood Donation Management System.
Your job is to:
- Explain blood donation eligibility (e.g., minimum age 18, weight > 50kg, no recent tattoos).
- Guide users on how to donate via the website.
- Help users find blood groups and understand map features.
- Answer FAQs about blood donation.
Your responses should be brief, friendly, and related ONLY to blood donation and this system.
Keep formatting simple (plain text or very light markdown).
"""

@chatbot_bp.route('/ask', methods=['POST'])
def ask_chatbot():
    data = request.get_json()
    user_message = data.get('message', '')

    if not user_message:
        return jsonify({"reply": "Please ask a question."})
        
    text = user_message.lower()
    
    # Emergency Proximity Feature
    if any(kw in text for kw in ['nearby', 'near', '1 km', '1km', 'emergency', 'available']):
        user_id = session.get('user_id')
        user_type = session.get('user_type')
        
        if not user_id:
            return jsonify({"reply": "Please **log in** first so I can check your registered location for nearby blood availability!"})
            
        if user_type != 'donor':
            return jsonify({"reply": "The 1km Emergency Scan command is built for registered **Donors** who have exact GPS coordinates on file. For recipients, please navigate to the **Find Local Donors** map to search for available blood nearby!"})
            
        from backend.app import get_db_connection
        conn = get_db_connection()
        if not conn:
            return jsonify({"reply": "System offline. Cannot check nearby donors."})
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT latitude, longitude FROM donors WHERE id = %s", (user_id,))
        user_loc = cursor.fetchone()
        
        if not user_loc or not user_loc.get('latitude') or not user_loc.get('longitude'):
            cursor.close()
            conn.close()
            return jsonify({"reply": "I couldn't find your exact location coordinates. Please update your profile with your location to use this emergency 1km feature."})
            
        # Get all available donors
        cursor.execute("SELECT blood_group, latitude, longitude FROM donors WHERE availability_status = 'Available' AND id != %s", (user_id,))
        all_donors = cursor.fetchall()
        cursor.close()
        conn.close()
        
        nearby_counts = {}
        for d in all_donors:
            try:
                lat, lon = float(d['latitude']), float(d['longitude'])
                dist = haversine(float(user_loc['latitude']), float(user_loc['longitude']), lat, lon)
                if dist <= 1.0: # within 1 km radius
                    bg = d['blood_group']
                    nearby_counts[bg] = nearby_counts.get(bg, 0) + 1
            except (TypeError, ValueError):
                continue
                    
        if not nearby_counts:
            reply = "I checked within a **1 km radius** of your registered location, but currently there are no active donors available."
        else:
            reply = "Here is the available blood within **1 km** of your location:<br>"
            for bg, count in nearby_counts.items():
                reply += f"- **{bg}**: {count} donor(s) nearby<br>"
            reply += "<br>Please navigate to the *Find Local Donors* map to request blood from them immediately."
            
        return jsonify({"reply": reply})

    api_key = current_app.config.get('GEMINI_API_KEY')
    
    if not api_key or api_key == 'YOUR_GEMINI_API_KEY_HERE':
        # Fallback rule-based chatbot for when Gemini isn't configured
        text = user_message.lower()
        if 'age' in text or 'old' in text:
            reply = "To donate blood, you must be between 18 and 65 years old."
        elif 'weight' in text:
            reply = "You must weigh at least 50 kg (110 lbs) to donate blood safely."
        elif 'how' in text and ('donate' in text or 'process' in text):
            reply = "You can register as a donor on our platform, keep your availability updated, and hospitals or recipients will be securely matched with you when there is an emergency."
        elif 'tattoo' in text or 'piercing' in text:
            reply = "If you recently got a tattoo or piercing, medical guidelines state that you must wait at least 6 months before donating blood."
        elif 'often' in text or 'how many times' in text or 'when' in text:
            reply = "Men can safely donate whole blood every 3 months, and women every 4 months (or 90-120 days)."
        elif 'safe' in text or 'hurt' in text:
            reply = "Yes, blood donation is very safe! Only sterile, single-use equipment is used, and it generally feels like a quick pinch."
        elif 'hi ' in text or text.startswith('hi') or 'hello' in text or 'hey' in text:
            reply = "Hello! I am the Lifeline AI Assistant. Ask me anything about blood donation."
        elif 'thank' in text:
            reply = "You're very welcome! Let me know if you need anything else."
        else:
            reply = "That's a great question! For specific medical advice, please consult your doctor. Can I help you with any basic eligibility rules like age, weight, or how often you can donate?"
            
        return jsonify({"reply": reply})

    try:
        genai.configure(api_key=api_key)
        # Using gemini-1.5-flash which is standard for fast text
        model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=system_instruction)
        
        # We perform a stateless generation here for simplicity,
        # but in a real app, passing chat history is better.
        response = model.generate_content(user_message)
        
        return jsonify({"reply": response.text})
    except Exception as e:
        return jsonify({"reply": f"Sorry, I encountered an error: {str(e)}"})
