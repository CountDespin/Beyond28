
import streamlit as st
from google import genai

# Set up the page
st.set_page_config(page_title="Gemini Chatbot")
st.title("My Gemini Chatbot")

# Connect to Google Gemini
client = genai.Client(
    api_key=st.secrets["GEMINI_API_KEY"]
)

# Create a chat session if one doesn't already exist
if "chat" not in st.session_state:
    st.session_state.chat = client.chats.create(
        model="gemini-flash-latest"
    )

# Create a list to store conversation messages
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept a new message from the user
if prompt := st.chat_input("Ask me anything..."):

    # Display the user's message
    with st.chat_message("user"):
        st.markdown(prompt)

    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    # Ask Gemini to generate a response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = st.session_state.chat.send_message(prompt)
            answer = response.text
            st.markdown(answer)

    # Save Gemini's response
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })
