from flask import Flask, request, jsonify, render_template, send_from_directory
import json
import google.generativeai as genai
from difflib import get_close_matches
from gtts import gTTS
import os
import uuid
import re

app = Flask(__name__)

# Configure Gemini API
GEN_API_KEY = 'AIzaSyCamQ6JU2YzlUdlGitTys6rP6E4gA_rKCg'  # Replace with your actual Gemini API key
genai.configure(api_key=GEN_API_KEY)

# Load the dataset
with open("data.json", "r", encoding="utf-8") as file:
    dataset = json.load(file)

# Function to search local JSON data
def search_answers(user_input):
    for topic in dataset['topics']:
        for qa_pair in topic['questions_answers']:
            for question in qa_pair['questions']:
                if user_input in question or user_input in get_close_matches(user_input, qa_pair['questions']):
                    return qa_pair['answers'][0]
    return None

# Function to get a response from Gemini API with error handling
def generate_gemini_response(user_input):
    model = genai.GenerativeModel('gemini-pro')
    try:
        response = model.generate_content(user_input)
        if response and response.candidates:
            valid_candidates = [c for c in response.candidates if not c.safety_ratings or all(r.blocked == False for r in c.safety_ratings)]
            if valid_candidates and valid_candidates[0].content.parts:
                return valid_candidates[0].content.parts[0].text
            else:
                return "மன்னிக்கவும், உங்கள் கேள்விக்கு பதில் வழங்க முடியவில்லை."
        else:
            return "மன்னிக்கவும், சரியான பதிலை தர இயலவில்லை."
    except Exception as e:
        return f"மன்னிக்கவும், பிழை ஏற்பட்டது: {str(e)}"

@app.route("/")
def index():
    return render_template("index.html")



@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message", "")
    if not user_input:
        return jsonify({"error": "Message is required"}), 400

    # Step 1: Search in local JSON data
    local_answer = search_answers(user_input)
    if local_answer:
        response = local_answer
    else:
        # Step 2: Fallback to Gemini API
        response = generate_gemini_response(user_input)

    response_words = response.split()
    limited_response = ' '.join(response_words[:20])

    allowed_characters = [
        *"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"  # Letters and numbers
        , *" \s.,!?'"  # Spaces and punctuation
        , *"".join(chr(i) for i in range(0x0B80, 0x0BFF+1))  # Tamil characters
    ]

    # Filter the response to only contain allowed characters
    cleaned_response = ''.join([char for char in limited_response if char in allowed_characters])

    # Generate audio from the cleaned response using gTTS
    tts = gTTS(cleaned_response, lang='ta')
    unique_filename = f"response_{uuid.uuid4()}.mp3"
    audio_path = os.path.join('static', 'audio', unique_filename)
    tts.save(audio_path)

    # Return the cleaned response and the audio file URL
    return jsonify({"reply": cleaned_response, "audio_url": f"/static/audio/{unique_filename}"})


@app.route("/static/audio/<filename>")
def get_audio(filename):
    return send_from_directory('static/audio', filename, mimetype="audio/mpeg")

if __name__ == "__main__":
    if not os.path.exists('static/audio'):
        os.makedirs('static/audio')
    app.run(debug=True)
