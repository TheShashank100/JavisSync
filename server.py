import re
import os
import json
import requests
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
from transformers import GPT2LMHeadModel, GPT2Tokenizer
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from youtubesearchpython import VideosSearch

# Initialize environment
load_dotenv()

# Create required directories
os.makedirs('music_data', exist_ok=True)
os.makedirs('uploads', exist_ok=True)

# Initialize AI components with error handling
try:
    # Check required environment variables
    if not os.getenv("DEEPSEEK_API_KEY"):
        raise ValueError("DEEPSEEK_API_KEY environment variable is required")

    tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
    model = GPT2LMHeadModel.from_pretrained("gpt2")
    
    # Add special tokens for song structure
    special_tokens = {'additional_special_tokens': ['[Verse]', '[Chorus]', '[Bridge]', '[Intro]', '[Outro]']}
    num_added_toks = tokenizer.add_special_tokens(special_tokens)
    model.resize_token_embeddings(len(tokenizer))
    
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
    if embedding_model is None:
        raise ValueError("Failed to initialize embedding model")
except Exception as e:
    print(f"Error loading AI models: {str(e)}")
    tokenizer = None
    model = None
    embedding_model = None

# Initialize Flask
app = Flask(__name__)
CORS(app, resources={
    r"/chat": {"origins": "*", "methods": ["POST"]},
    r"/music/*": {"origins": "*", "methods": ["GET"]},
    r"/": {"origins": "*", "methods": ["GET"]}
})

# DeepSeek API configuration
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# Lyrics database with embeddings
lyrics_db = [
    "I'm in love with the shape of you, we push and pull like a magnet do",
    "Hello, it's me, I was wondering if after all these years you'd like to meet",
    "Don't stop believin', hold on to that feelin'",
    "Just a small town girl, living in a lonely world",
    "Sweet dreams are made of this, who am I to disagree?",
    "I will survive, oh as long as I know how to love, I know I'll stay alive"
]
lyrics_db_embeddings = None
if embedding_model is not None:
    lyrics_db_embeddings = embedding_model.encode(lyrics_db)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

def find_similar_lyrics(prompt):
    """Find most similar lyrics using cosine similarity"""
    if embedding_model is None or lyrics_db_embeddings is None:
        return lyrics_db[0]  # Return first lyric as fallback
        
    prompt_embedding = embedding_model.encode(prompt, normalize_embeddings=True)
    prompt_embedding = np.array(prompt_embedding).reshape(1, -1)
    similarities = cosine_similarity(prompt_embedding, lyrics_db_embeddings)
    most_similar_index = np.argmax(similarities)
    return lyrics_db[most_similar_index]

def detect_mood(text):
    """Analyze lyrics to detect mood using keywords"""
    mood_keywords = {
        'happy': ['love', 'happy', 'joy', 'sun', 'smile'],
        'sad': ['sad', 'cry', 'tears', 'lonely', 'pain'],
        'angry': ['angry', 'hate', 'fight', 'rage', 'war'],
        'chill': ['calm', 'peace', 'relax', 'cool', 'easy']
    }
    
    text_lower = text.lower()
    mood_scores = {mood: 0 for mood in mood_keywords}
    
    for mood, keywords in mood_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                mood_scores[mood] += 1
                
    dominant_mood = max(mood_scores.items(), key=lambda x: x[1])[0]
    return dominant_mood if mood_scores[dominant_mood] > 0 else 'neutral'

def process_lyrics(text):
    """Extract musical structure, clean lyrics and detect mood"""
    mood = detect_mood(text)
    
    musical_data = {
        'sections': [],
        'beats': [],
        'tempo': 120 if mood == 'happy' else 90 if mood == 'chill' else 140 if mood == 'angry' else 70,
        'key': 'C major' if mood in ['happy', 'chill'] else 'C minor',
        'instruments': ['piano', 'drums', 'bass'],
        'mood': mood,
        'timestamp': datetime.now().isoformat()
    }
    
    beat_counter = 0
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    for line in lines:
        # Detect section headers
        if line.startswith('['):
            section_match = re.match(r'\[(Verse|Chorus|Bridge|Intro|Outro)\s*(\d*)\]', line)
            if section_match:
                musical_data['sections'].append({
                    'type': section_match.group(1),
                    'number': section_match.group(2) or '1',
                    'start_beat': beat_counter,
                    'lyrics': []
                })
            continue
        
        # Extract beats and lyrics
        words = line.split()
        current_section = musical_data['sections'][-1] if musical_data['sections'] else None
        line_beats = []
        
        for word in words:
            if '𝅘𝅥𝅯' in word:
                clean_word = word.replace('𝅘𝅥𝅯', '').strip()
                musical_data['beats'].append({
                    'time': beat_counter,
                    'word': clean_word,
                    'duration': 0.5,  # Quarter note
                    'pitch': 'C4' if beat_counter % 2 == 0 else 'Eb4'
                })
                line_beats.append(clean_word)
                beat_counter += 1
        
        if current_section:
            current_section['lyrics'].append(' '.join(line_beats))
    
    # Clean lyrics output (remove musical annotations)
    clean_lyrics = '\n'.join([
        re.sub(r'𝅘𝅥𝅯|✨|yo!|know what I\'m sayin\?', '', line)
        for line in lines
    ])
    
    return {
        'clean_lyrics': clean_lyrics,
        'musical_data': musical_data
    }

@app.route("/chat", methods=["POST"])
def chat():
    try:
        # Validate request
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
            
        data = request.get_json()
        user_message = data.get("prompt", "").strip()
        
        if not user_message:
            return jsonify({"error": "Empty prompt"}), 400

        # Find similar lyrics for context
        similar_lyric = find_similar_lyrics(user_message)
        
        # Prepare DeepSeek API request
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": f"""You are a professional songwriter. Create complete song lyrics with:
                    - Clear [Verse], [Chorus], [Bridge] sections
                    - Beat markers (𝅘𝅥𝅯) on stressed syllables
                    - Inspired by: {similar_lyric}
                    - About: {user_message}
                    Return ONLY the lyrics with structure annotations."""
                },
                {
                    "role": "user",
                    "content": f"Write a song about: {user_message}"
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1000,
            "top_p": 0.9
        }

        # Call DeepSeek API
        response = requests.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        
        # Process response
        response_data = response.json()
        if not response_data.get("choices"):
            return jsonify({"error": "Empty API response"}), 500
            
        raw_lyrics = response_data["choices"][0]["message"]["content"]
        processed = process_lyrics(raw_lyrics)
        
        # Store musical data with proper path
        session_id = datetime.now().strftime("%Y%m%d%H%M%S")
        music_file = os.path.join('music_data', f'music_{session_id}.json')
        with open(music_file, 'w') as f:
            json.dump(processed['musical_data'], f)
        
        return jsonify({
            "lyrics": processed['clean_lyrics'],
            "session_id": session_id
        })

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"API request failed: {str(e)}"}), 502
    except Exception as e:
        return jsonify({"error": f"Processing error: {str(e)}"}), 500

@app.route("/music/<session_id>", methods=["GET"])
def get_music_data(session_id):
    try:
        music_file = os.path.join('music_data', f'music_{session_id}.json')
        with open(music_file, 'r') as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify({"error": "Music data not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/youtube/search", methods=["POST"])
def youtube_search():
    try:
        data = request.get_json()
        query = data.get("query", "").strip()
        if not query:
            return jsonify({"error": "Empty query"}), 400

        search = VideosSearch(query, limit=3)
        results = search.result()
        videos = []
        for item in results['result']:
            videos.append({
                "id": item['id'],
                "title": item['title'],
                "channel": item['channel']['name'],
                "duration": item['duration'],
                "thumbnail": item['thumbnails'][0]['url']
            })
        return jsonify({"videos": videos})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
