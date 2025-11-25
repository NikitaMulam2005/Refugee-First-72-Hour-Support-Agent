
# Refugee First – 72-Hour Support Agent

A multilingual WhatsApp and web-based AI assistant that provides critical survival information to refugees during their first 72 hours in a new city.

## Project Description

Refugee First is a humanitarian AI system specifically designed to address the urgent needs of refugees and displaced persons during the most critical period—the first 72 hours after arrival in an unfamiliar city. The system provides immediate access to life-saving information including emergency shelter locations, food and water distribution points, medical facilities, safety guidelines, and local navigation assistance in multiple languages.

## Technologies Used

- **Frontend**: React, TypeScript, Tailwind CSS
- **Backend**: FastAPI, Python
- **AI/ML**: LangGraph, Vertex AI Embeddings, Groq API
- **Database**: MongoDB
- **Messaging**: WhatsApp Cloud API
- **Translation**: Google Translate API
- **Languages Supported**: Arabic, Farsi, Hindi, Urdu, English, French, Ukrainian, Tamil, Marathi

## How It Works

1. **User Input**: Refugees send messages via WhatsApp or web chat in their native language
2. **Language Processing**: System detects and translates language automatically
3. **AI Analysis**: LangGraph agent analyzes urgency and needs
4. **Resource Retrieval**: RAG system finds nearby shelters, food banks, medical centers
5. **72-Hour Plan**: AI generates customized survival plan
6. **Multilingual Delivery**: Response delivered in user's preferred language

## Installation

```bash
# Backend setup
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend setup  
cd frontend
npm install
npm start
```

## Usage Examples

## Food and Water Request (Hindi):

👤 User: "भूख लगी है, खाना चाहिए"

🤖 Refugee First: "नमस्ते! आपके निकटतम भोजन वितरण केंद्र:

🍞 अन्नक्षेत्र भोजनालय - 0.5 किमी (अभी खुला)
🍎 सामुदायिक रसोई - 1.2 किमी
💧 पेयजल स्टेशन - 0.3 किमी

तत्काल सहायता:
1. पहले पानी लें
2. निकटतम भोजन केंद्र पर जाएं
3. यदि अस्वस्थ हैं तो चिकित्सक से मिलें

क्या आप विशिष्ट दिशा-निर्देश चाहते हैं?"


## File Structure

```
refugee-first/
├── backend/           # FastAPI server with AI agents
├── frontend/          # React web interface  
├── database/          # MongoDB schemas and data
└── docs/             # Project documentation
```

## Demo

**Video Demo**: [https://drive.google.com/file/d/1EvefO1SAihRdXT55CqyduXXM3emgixbw/view]

## Humanitarian Mission

This project provides information only—no legal advice or government process automation. Strictly for humanitarian support of refugees and displaced persons.

