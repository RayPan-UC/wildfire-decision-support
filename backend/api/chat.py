from flask import Blueprint, request, jsonify
import time

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/', methods=['POST'])
def ask_assistant():
    # Get the text 
    data = request.get_json()
    user_message = data.get('message', '')

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    print(f"User asked: {user_message}")

    # think for 1 second
    time.sleep(1)

    # Testing a mock AI response
    ai_response = f"This is a test response to: '{user_message}'. Highway 63 North is currently the safest evacuation route."

    # text back to the frontend
    return jsonify({"response": ai_response}), 200