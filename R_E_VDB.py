import os
import json
import pandas as pd
import PyPDF2
import docx
import mysql.connector
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

# Initialize FastAPI
app = FastAPI()

# Load Sentence Transformer Model
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Connect to MySQL
db_conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Sushma@3420",
    database="db"
)
db_cursor = db_conn.cursor()

def read_file(file_path):
    """Read content from various file types."""
    _, file_extension = os.path.splitext(file_path)
    try:
        if file_extension == ".txt":
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read()
        elif file_extension == ".csv":
            df = pd.read_csv(file_path)
            return df.to_string()
        elif file_extension == ".json":
            with open(file_path, "r", encoding="utf-8") as file:
                return json.dumps(json.load(file), indent=4)
        elif file_extension in [".xls", ".xlsx"]:
            df = pd.read_excel(file_path)
            return df.to_string()
        elif file_extension == ".pdf":
            content = []
            with open(file_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    content.append(page.extract_text())
            return "\n".join(content)
        elif file_extension == ".docx":
            doc = docx.Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        else:
            return "Unsupported file format."
    except Exception as e:
        return f"Error reading file: {e}"

def save_to_txt(content, output_filename="output.txt"):
    """Save extracted content to a .txt file."""
    with open(output_filename, "w", encoding="utf-8") as file:
        file.write(content)
    print(f"Content saved to {output_filename}")

# API Models
class CaptionRequest(BaseModel):
    video_url: str
    languages: list[str] = None

def get_youtube_video_id(url: str) -> str:
    """Extract video ID from YouTube URL."""
    if "youtube.com/watch?v=" in url:
        return url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        return url.split("/")[-1]
    raise ValueError("Invalid YouTube URL format")

def get_youtube_video_captions(url: str, languages: list = None) -> str:
    """Fetch captions from a YouTube video."""
    try:
        video_id = get_youtube_video_id(url)
        kwargs = {"languages": languages} if languages else {}
        try:
            captions = YouTubeTranscriptApi.get_transcript(video_id, **kwargs)
        except NoTranscriptFound:
            captions = YouTubeTranscriptApi.get_transcript(video_id, languages=["auto"])
        return " ".join(line["text"] for line in captions) if captions else "No captions available"
    except (TranscriptsDisabled, NoTranscriptFound):
        return "No transcript available."
    except Exception as e:
        return f"Error fetching captions: {str(e)}"

def store_caption_embedding(video_id, captions):
    """Generate and store video captions and embeddings in MySQL."""
    embedding = model.encode(captions).tolist()
    db_cursor.execute(
        "INSERT INTO video_captions (video_id, captions, embedding) VALUES (%s, %s, %s) "
        "ON DUPLICATE KEY UPDATE captions=%s, embedding=%s",
        (video_id, captions, json.dumps(embedding), captions, json.dumps(embedding))
    )
    db_conn.commit()

def cosine_similarity(vec1, vec2):
    """Compute cosine similarity between two vectors."""
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def search_similar_captions(query):
    """Search for similar video captions using vector similarity."""
    query_embedding = model.encode(query).tolist()
    db_cursor.execute("SELECT video_id, captions, embedding FROM video_captions")
    results = db_cursor.fetchall()
    similarities = [
        (video_id, captions, cosine_similarity(query_embedding, json.loads(embedding)))
        for video_id, captions, embedding in results
    ]
    similarities.sort(key=lambda x: x[2], reverse=True)
    return similarities[:5]

@app.post("/write-captions")
async def write_captions(request: CaptionRequest):
    """FastAPI endpoint to extract, store captions, and generate embeddings."""
    video_id = get_youtube_video_id(request.video_url)
    captions = get_youtube_video_captions(request.video_url, request.languages)
    if captions.startswith("No") or captions.startswith("Error"):
        raise HTTPException(status_code=400, detail=captions)
    store_caption_embedding(video_id, captions)
    return {"status": "success", "message": f"Captions stored for video {video_id}"}

@app.get("/search")
async def search(query: str):
    """FastAPI endpoint to find similar video captions."""
    results = search_similar_captions(query)
    return {"status": "success", "matches": [
        {"video_id": video_id, "captions": captions, "similarity": similarity}
        for video_id, captions, similarity in results
    ]}
