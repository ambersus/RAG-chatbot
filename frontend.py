import streamlit as st
import requests

st.title("AI Chatbot: File & Video Processor")

# Sidebar navigation
menu = st.sidebar.radio("Select Mode", ["Process File", "Process YouTube Video"])

if menu == "Process File":
    st.header("Upload and Extract Content from Files")
    uploaded_file = st.file_uploader("Upload a file", type=["txt", "csv", "json", "xls", "xlsx", "pdf", "docx"])
    
    if uploaded_file:
        files = {"file": uploaded_file.getvalue()}
        try:
            response = requests.post("http://localhost:8000/process-file", files=files)
            if response.status_code == 200:
                st.success("File processed successfully!")
                st.text_area("Extracted Content", response.json()["content"], height=300)
            else:
                st.error(f"Error processing file: {response.text}")
        except Exception as e:
            st.error(f"Error calling API: {str(e)}")

elif menu == "Process YouTube Video":
    st.header("Process YouTube Video and Extract Captions")
    video_url = st.text_input("Enter YouTube Video URL:")

    if video_url:
        try:
            video_id = video_url.split("v=")[1].split("&")[0] if "youtube.com" in video_url else video_url.split(".be/")[1]
            st.video(f"https://www.youtube.com/embed/{video_id}")
            
            response = requests.post("http://localhost:8000/write-captions", json={"video_url": video_url})
            if response.status_code == 200:
                st.success("Captions processed successfully!")
            else:
                st.error(f"Error processing captions: {response.text}")
        except Exception as e:
            st.error(f"Error processing the URL: {e}")

# Chatbot Interface
st.header("Chatbot: Ask Anything")
question = st.text_input("Ask a question:")
if question:
    try:
        response = requests.post("http://localhost:8000/ask", json={"question": question})
        if response.status_code == 200:
            st.write("Answer:", response.json()["answer"])
        else:
            st.error(f"Error getting answer: {response.text}")
    except Exception as e:
        st.error(f"Error making API request: {str(e)}")
