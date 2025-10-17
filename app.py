import asyncio
import streamlit as st
from google import genai
import os
import glob
import time
from dotenv import load_dotenv
from google.genai import types
from PIL import Image
from countryinfo import CountryInfo
from tavily import TavilyClient
from strands import Agent, tool
from strands.models.gemini import GeminiModel
from strands.agent.conversation_manager import SummarizingConversationManager
from io import BytesIO
from mem0 import MemoryClient
import base64
from datetime import datetime
import json
import sqlite3
import uuid

# Database setup
DB_PATH = 'data.db'  # SQLite file path; can be adjusted for cloud deployments

def init_db():
    """Initialize the database and create tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Table for users (to manage sessions)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table for conversations (chat history per user)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            conversation_id TEXT NOT NULL,
            title TEXT,
            messages TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Table for memories (to integrate with mem0)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            memory_data TEXT,  
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize DB on app start
init_db()

# Helper function to get DB connection
def get_db_connection():
    """Get a database connection."""
    return sqlite3.connect(DB_PATH)

# Load environment variables
load_dotenv()

# Language translations
TRANSLATIONS = {
    "English": {
        "page_title": "StyleGenie: Your Personal Fashion Assistant",
        "header_title": "✨ StyleGenie",
        "header_subtitle": "Your Personal Fashion Assistant",
        "footer": "Made with love ❤️ by Keynar",
        "upload_section": "📸 Upload Your Image",
        "upload_instruction": "Choose how you'd like to provide your outfit image:",
        "upload_from_device": "📁 Upload from device",
        "take_photo": "📷 Take a photo",
        "choose_image": "Choose an image...",
        "upload_help": "Upload a photo of your outfit or any fashion item",
        "uploaded_image": "Uploaded Image",
        "captured_image": "Captured Image",
        "take_photo_btn": "Take a photo",
        "clear_chat": "🗑️ Clear Chat History",
        "tips_title": "💡 Tips",
        "tips_content": """- Upload or take a photo of your outfit
- Ask me to modify colors, styles, or accessories
- Request shopping links for similar items
- I remember your preferences!""",
        "chat_title": "💬 Chat with StyleGenie",
        "chat_placeholder": "Ask me anything about fashion... ✨",
        "thinking": "✨ StyleGenie is thinking...",
        "error": "❌ Oops! Something went wrong:",
        "generated_image": "Generated Image",
        "language_selector": "🌐 Language / Langue / Idioma",
        "select_input": "Select input method:",
        "conversations": "💬 Conversations",
        "new_chat": "➕ New Chat",
        "delete_chat": "🗑️ Delete",
        "rename_chat": "✏️ Rename",
        "no_conversations": "No conversations yet. Start chatting!",
        "conversation_title": "New Conversation",
        "confirm_delete": "Delete this conversation?"
    },
    "Français": {
        "page_title": "StyleGenie : Votre Assistant Mode Personnel",
        "header_title": "✨ StyleGenie",
        "header_subtitle": "Votre Assistant Mode Personnel",
        "footer": "Fait avec amour ❤️ par Keynar",
        "upload_section": "📸 Téléchargez Votre Image",
        "upload_instruction": "Choisissez comment vous souhaitez fournir votre image de tenue :",
        "upload_from_device": "📁 Télécharger depuis l'appareil",
        "take_photo": "📷 Prendre une photo",
        "choose_image": "Choisissez une image...",
        "upload_help": "Téléchargez une photo de votre tenue ou de tout article de mode",
        "uploaded_image": "Image Téléchargée",
        "captured_image": "Image Capturée",
        "take_photo_btn": "Prendre une photo",
        "clear_chat": "🗑️ Effacer l'Historique",
        "tips_title": "💡 Conseils",
        "tips_content": """- Téléchargez ou prenez une photo de votre tenue
- Demandez-moi de modifier les couleurs, styles ou accessoires
- Demandez des liens d'achat pour des articles similaires
- Je me souviens de vos préférences !""",
        "chat_title": "💬 Discutez avec StyleGenie",
        "chat_placeholder": "Posez-moi des questions sur la mode... ✨",
        "thinking": "✨ StyleGenie réfléchit...",
        "error": "❌ Oups ! Quelque chose s'est mal passé :",
        "generated_image": "Image Générée",
        "language_selector": "🌐 Language / Langue / Idioma",
        "select_input": "Sélectionnez la méthode de saisie :",
        "conversations": "💬 Conversations",
        "new_chat": "➕ Nouveau Chat",
        "delete_chat": "🗑️ Supprimer",
        "rename_chat": "✏️ Renommer",
        "no_conversations": "Aucune conversation. Commencez à discuter !",
        "conversation_title": "Nouvelle Conversation",
        "confirm_delete": "Supprimer cette conversation ?"
    },
    "Español": {
        "page_title": "StyleGenie: Tu Asistente Personal de Moda",
        "header_title": "✨ StyleGenie",
        "header_subtitle": "Tu Asistente Personal de Moda",
        "footer": "Hecho con amor ❤️ por Keynar",
        "upload_section": "📸 Sube Tu Imagen",
        "upload_instruction": "Elige cómo te gustaría proporcionar tu imagen de outfit:",
        "upload_from_device": "📁 Subir desde dispositivo",
        "take_photo": "📷 Tomar una foto",
        "choose_image": "Elige una imagen...",
        "upload_help": "Sube una foto de tu outfit o cualquier artículo de moda",
        "uploaded_image": "Imagen Subida",
        "captured_image": "Imagen Capturada",
        "take_photo_btn": "Tomar una foto",
        "clear_chat": "🗑️ Borrar Historial",
        "tips_title": "💡 Consejos",
        "tips_content": """- Sube o toma una foto de tu outfit
- Pídeme modificar colores, estilos o accesorios
- Solicita enlaces de compra para artículos similares
- ¡Recuerdo tus preferencias!""",
        "chat_title": "💬 Chatea con StyleGenie",
        "chat_placeholder": "Pregúntame cualquier cosa sobre moda... ✨",
        "thinking": "✨ StyleGenie está pensando...",
        "error": "❌ ¡Ups! Algo salió mal:",
        "generated_image": "Imagen Generada",
        "language_selector": "🌐 Language / Langue / Idioma",
        "select_input": "Selecciona el método de entrada:",
        "conversations": "💬 Conversaciones",
        "new_chat": "➕ Nuevo Chat",
        "delete_chat": "🗑️ Eliminar",
        "rename_chat": "✏️ Renombrar",
        "no_conversations": "No hay conversaciones. ¡Empieza a chatear!",
        "conversation_title": "Nueva Conversación",
        "confirm_delete": "¿Eliminar esta conversación?"
    },
    "Deutsch": {
        "page_title": "StyleGenie: Dein Persönlicher Mode-Assistent",
        "header_title": "✨ StyleGenie",
        "header_subtitle": "Dein Persönlicher Mode-Assistent",
        "footer": "Mit Liebe ❤️ gemacht von Keynar",
        "upload_section": "📸 Lade Dein Bild Hoch",
        "upload_instruction": "Wähle, wie du dein Outfit-Bild bereitstellen möchtest:",
        "upload_from_device": "📁 Vom Gerät hochladen",
        "take_photo": "📷 Foto aufnehmen",
        "choose_image": "Wähle ein Bild...",
        "upload_help": "Lade ein Foto deines Outfits oder eines Modeartikels hoch",
        "uploaded_image": "Hochgeladenes Bild",
        "captured_image": "Aufgenommenes Bild",
        "take_photo_btn": "Foto aufnehmen",
        "clear_chat": "🗑️ Chat-Verlauf Löschen",
        "tips_title": "💡 Tipps",
        "tips_content": """- Lade ein Foto deines Outfits hoch oder mache eins
- Bitte mich, Farben, Stile oder Accessoires zu ändern
- Fordere Shopping-Links für ähnliche Artikel an
- Ich erinnere mich an deine Vorlieben!""",
        "chat_title": "💬 Chatte mit StyleGenie",
        "chat_placeholder": "Frag mich alles über Mode... ✨",
        "thinking": "✨ StyleGenie denkt nach...",
        "error": "❌ Hoppla! Etwas ist schief gelaufen:",
        "generated_image": "Generiertes Bild",
        "language_selector": "🌐 Language / Langue / Idioma",
        "select_input": "Wähle die Eingabemethode:",
        "conversations": "💬 Unterhaltungen",
        "new_chat": "➕ Neuer Chat",
        "delete_chat": "🗑️ Löschen",
        "rename_chat": "✏️ Umbenennen",
        "no_conversations": "Keine Unterhaltungen. Fang an zu chatten!",
        "conversation_title": "Neue Unterhaltung",
        "confirm_delete": "Diese Unterhaltung löschen?"
    }
}

def get_text(key):
    """Get translated text based on selected language"""
    lang = st.session_state.get('language', 'English')
    return TRANSLATIONS[lang].get(key, TRANSLATIONS['English'][key])

# Conversation management functions (Database-based)
def ensure_user_exists(user_id):
    """Ensure a user record exists in the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def load_conversations(user_id):
    """Load conversations from database for a specific user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Ensure user exists
    ensure_user_exists(user_id)
    
    # Load conversations
    cursor.execute('''
        SELECT conversation_id, title, messages, created_at, updated_at
        FROM conversations
        WHERE user_id = ?
        ORDER BY updated_at DESC
    ''', (user_id,))
    
    rows = cursor.fetchall()
    conversations = {}
    
    for row in rows:
        conv_id, title, messages_json, created_at, updated_at = row
        try:
            messages = json.loads(messages_json) if messages_json else []
        except json.JSONDecodeError:
            messages = []
        
        conversations[conv_id] = {
            'id': conv_id,
            'title': title or f"{get_text('conversation_title')} - {created_at}",
            'messages': messages,
            'created_at': created_at,
            'updated_at': updated_at
        }
    
    conn.close()
    return conversations

def save_conversations(conversations, user_id):
    """Save conversations to database for a specific user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Ensure user exists
    ensure_user_exists(user_id)
    
    # Delete existing conversations for this user
    cursor.execute('DELETE FROM conversations WHERE user_id = ?', (user_id,))
    
    # Insert updated conversations
    for conv_id, conv_data in conversations.items():
        messages_json = json.dumps(conv_data.get('messages', []), ensure_ascii=False)
        cursor.execute('''
            INSERT INTO conversations (user_id, conversation_id, title, messages, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            conv_id,
            conv_data.get('title', ''),
            messages_json,
            conv_data.get('created_at', datetime.now().strftime("%Y-%m-%d %H:%M")),
            conv_data.get('updated_at', datetime.now().strftime("%Y-%m-%d %H:%M"))
        ))
    
    conn.commit()
    conn.close()

def create_new_conversation():
    """Create a new conversation"""
    conv_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    return {
        'id': conv_id,
        'title': f"{get_text('conversation_title')} - {timestamp}",
        'messages': [],
        'created_at': timestamp,
        'updated_at': timestamp
    }

def delete_conversation(user_id, conversation_id):
    """Delete a specific conversation from the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM conversations WHERE user_id = ? AND conversation_id = ?', (user_id, conversation_id))
    conn.commit()
    conn.close()

def update_conversation_title(user_id, conversation_id, new_title):
    """Update the title of a conversation"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE conversations
        SET title = ?, updated_at = ?
        WHERE user_id = ? AND conversation_id = ?
    ''', (new_title, datetime.now().strftime("%Y-%m-%d %H:%M"), user_id, conversation_id))
    conn.commit()
    conn.close()

def get_conversation_preview(messages, max_length=50):
    """Get a preview of the conversation from first user message"""
    for msg in messages:
        if msg['role'] == 'user':
            preview = msg['content'][:max_length]
            return preview + '...' if len(msg['content']) > max_length else preview
    return get_text('conversation_title')

# Page configuration
st.set_page_config(
    page_title="StyleGenie: Your Personal Fashion Assistant",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed"  # Start collapsed for better mobile experience
)

# Custom CSS for enhanced mobile-first design
st.markdown("""
<style>
    /* Import Inter font for better readability */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global variables for consistent theming */
    :root {
        --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --primary-color: #667eea;
        --secondary-color: #764ba2;
        --text-color: #2c3e50;
        --white: #ffffff;
        --shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        --shadow-hover: 0 8px 24px rgba(0, 0, 0, 0.2);
        --border-radius: 12px;
        --border-radius-lg: 20px;
        --touch-target: 48px;
        --spacing-xs: 0.5rem;
        --spacing-sm: 1rem;
        --spacing-md: 1.5rem;
        --spacing-lg: 2rem;
        --spacing-xl: 3rem;
    }
    
    /* Base styles - Mobile First */
    * {
        box-sizing: border-box;
    }
    
    html {
        font-size: 16px;
        -webkit-text-size-adjust: 100%;
        -ms-text-size-adjust: 100%;
    }
    
    body {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        line-height: 1.6;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }
    
    /* Main container - Enhanced mobile design */
    .main {
        background: var(--primary-gradient);
        padding: var(--spacing-xs);
        min-height: 100vh;
    }
    
    /* Enhanced chat container */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.98);
        border-radius: var(--border-radius);
        padding: var(--spacing-sm);
        margin: var(--spacing-xs) 0;
        box-shadow: var(--shadow);
        font-size: 0.9rem;
        line-height: 1.5;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        transition: all 0.3s ease;
    }
    
    .stChatMessage:hover {
        box-shadow: var(--shadow-hover);
        transform: translateY(-1px);
    }
    
    /* Modern header design */
    .header-container {
        background: var(--primary-gradient);
        padding: var(--spacing-md) var(--spacing-sm);
        border-radius: var(--border-radius);
        text-align: center;
        margin-bottom: var(--spacing-sm);
        box-shadow: var(--shadow-hover);
        position: relative;
        overflow: hidden;
    }
    
    .header-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(45deg, rgba(255,255,255,0.1) 0%, transparent 100%);
        pointer-events: none;
    }
    
    .header-title {
        color: var(--white);
        font-size: 1.8rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 2px 2px 8px rgba(0, 0, 0, 0.3);
        letter-spacing: -0.02em;
    }
    
    .header-subtitle {
        color: rgba(255, 255, 255, 0.9);
        font-size: 0.9rem;
        margin-top: var(--spacing-xs);
        font-weight: 400;
    }
    
    /* Enhanced footer */
    .footer {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: var(--primary-gradient);
        color: var(--white);
        text-align: center;
        padding: var(--spacing-sm);
        font-size: 0.8rem;
        font-weight: 500;
        box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.15);
        z-index: 1000;
        backdrop-filter: blur(10px);
    }
    
    /* Enhanced sidebar */
    [data-testid="stSidebar"] {
        background: var(--primary-gradient) !important;
    }
    
    [data-testid="stSidebar"] .css-1d391kg {
        background: transparent;
    }
    
    /* Modern button design */
    .stButton > button {
        background: var(--primary-gradient) !important;
        color: var(--white) !important;
        border: none !important;
        border-radius: var(--border-radius) !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        min-height: var(--touch-target) !important;
        width: 100% !important;
        box-shadow: var(--shadow) !important;
        text-transform: none !important;
        letter-spacing: 0.02em !important;
        position: relative !important;
        overflow: hidden !important;
    }
    
    .stButton > button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left 0.5s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: var(--shadow-hover) !important;
    }
    
    .stButton > button:hover::before {
        left: 100%;
    }
    
    .stButton > button:active {
        transform: translateY(0) !important;
    }
    
    /* Enhanced file uploader */
    .stFileUploader {
        border-radius: var(--border-radius);
        overflow: hidden;
    }
    
    .stFileUploader > div {
        border-radius: var(--border-radius) !important;
        border: 2px dashed var(--primary-color) !important;
        background: rgba(255, 255, 255, 0.8) !important;
        transition: all 0.3s ease !important;
    }
    
    .stFileUploader > div:hover {
        border-color: var(--secondary-color) !important;
        background: rgba(255, 255, 255, 0.9) !important;
    }
    
    .stFileUploader > div > button {
        min-height: var(--touch-target) !important;
        font-size: 16px !important;
        border-radius: var(--border-radius) !important;
    }
    
    /* Chat input enhancements */
    .stChatInputContainer {
        border-radius: var(--border-radius) !important;
        margin-bottom: 5rem !important;
        box-shadow: var(--shadow) !important;
        overflow: hidden;
    }
    
    .stChatInput > div > div > textarea {
        font-size: 16px !important;
        min-height: var(--touch-target) !important;
        border-radius: var(--border-radius) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        background: rgba(255, 255, 255, 0.95) !important;
        backdrop-filter: blur(10px) !important;
        padding: 12px 16px !important;
        line-height: 1.4 !important;
        resize: none !important;
    }
    
    .stChatInput > div > div > textarea:focus {
        outline: none !important;
        box-shadow: 0 0 0 2px var(--primary-color) !important;
        border-color: var(--primary-color) !important;
    }
    
    /* Enhanced image display */
    .uploaded-image {
        border-radius: var(--border-radius);
        box-shadow: var(--shadow);
        max-width: 100%;
        height: auto;
        margin: var(--spacing-sm) 0;
        transition: transform 0.3s ease;
    }
    
    .uploaded-image:hover {
        transform: scale(1.02);
    }
    
    /* Improved radio buttons */
    .stRadio > div {
        gap: var(--spacing-sm);
    }
    
    .stRadio > div > label {
        padding: var(--spacing-sm) !important;
        min-height: var(--touch-target) !important;
        display: flex !important;
        align-items: center !important;
        background: rgba(255, 255, 255, 0.1) !important;
        border-radius: var(--border-radius) !important;
        transition: all 0.3s ease !important;
        cursor: pointer !important;
        font-weight: 500 !important;
        color: var(--white) !important;
    }
    
    .stRadio > div > label:hover {
        background: rgba(255, 255, 255, 0.2) !important;
        transform: translateY(-1px);
    }
    
    /* Enhanced select boxes */
    .stSelectbox > div > div {
        font-size: 16px !important;
        border-radius: var(--border-radius) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        background: rgba(255, 255, 255, 0.95) !important;
        backdrop-filter: blur(10px) !important;
    }
    
    /* Camera input improvements */
    button[kind="header"] {
        min-height: var(--touch-target) !important;
        border-radius: var(--border-radius) !important;
    }
    
    /* Chat message images */
    .stChatMessage img {
        max-width: 100%;
        height: auto;
        border-radius: var(--border-radius);
        box-shadow: var(--shadow);
        margin: var(--spacing-xs) 0;
    }
    
    /* Language selector enhancement */
    .language-selector {
        margin-bottom: var(--spacing-md);
    }
    
    /* Conversation list improvements */
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: var(--white) !important;
        font-weight: 600 !important;
        font-size: 1.1rem !important;
        margin-bottom: var(--spacing-sm) !important;
    }
    
    /* Loading indicator */
    .stSpinner {
        border-color: var(--primary-color) transparent var(--primary-color) transparent !important;
    }
    
    /* Tablet and Desktop Optimizations */
    @media (min-width: 768px) {
        .main {
            padding: var(--spacing-sm);
        }
        
        .header-title {
            font-size: 2.5rem;
        }
        
        .header-subtitle {
            font-size: 1.1rem;
        }
        
        .header-container {
            padding: var(--spacing-lg) var(--spacing-xl);
            border-radius: var(--border-radius-lg);
            margin-bottom: var(--spacing-lg);
        }
        
        .stChatMessage {
            padding: var(--spacing-md);
            margin: var(--spacing-sm) 0;
            font-size: 1rem;
            max-width: 800px;
            margin-left: auto;
            margin-right: auto;
        }
        
        .footer {
            padding: var(--spacing-md);
            font-size: 0.9rem;
        }
        
        .stButton > button {
            width: auto !important;
            padding: 0.75rem 2rem !important;
            min-width: 120px !important;
        }
        
        .stChatInputContainer {
            max-width: 800px;
            margin-left: auto;
            margin-right: auto;
        }
    }
    
    /* Large Desktop */
    @media (min-width: 1200px) {
        .header-title {
            font-size: 3rem;
        }
        
        .header-container {
            padding: var(--spacing-xl);
        }
        
        .main {
            padding: var(--spacing-md);
        }
    }
    
    /* Ultra-wide screens */
    @media (min-width: 1600px) {
        .main {
            max-width: 1400px;
            margin: 0 auto;
        }
    }
    
    /* Enhanced touch interactions */
    .main, .stChatMessageContainer {
        -webkit-overflow-scrolling: touch;
        scroll-behavior: smooth;
    }
    
    /* Remove tap highlights and improve button UX */
    button, .stButton > button {
        -webkit-tap-highlight-color: transparent !important;
        user-select: none !important;
        -webkit-touch-callout: none !important;
    }
    
    /* Mobile sidebar optimization */
    @media (max-width: 768px) {
        [data-testid="stSidebar"] {
            width: 85% !important;
            max-width: 320px !important;
        }
        
        [data-testid="stSidebar"][aria-expanded="false"] {
            transform: translateX(-100%) !important;
        }
        
        [data-testid="stSidebar"][aria-expanded="true"] {
            transform: translateX(0) !important;
        }
        
        /* Overlay for mobile sidebar */
        [data-testid="stSidebar"][aria-expanded="true"]::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            z-index: -1;
            backdrop-filter: blur(2px);
        }
    }
    
    /* Dark mode support */
    @media (prefers-color-scheme: dark) {
        .stChatMessage {
            background: rgba(45, 45, 45, 0.95);
            color: #ffffff;
        }
    }
    
    /* Accessibility improvements */
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
    }
    
    /* Focus indicators */
    *:focus {
        outline: 2px solid var(--primary-color) !important;
        outline-offset: 2px !important;
    }
    
    /* High contrast mode support */
    @media (prefers-contrast: high) {
        .stButton > button {
            border: 2px solid var(--white) !important;
        }
        
        .stChatMessage {
            border: 1px solid var(--text-color) !important;
        }
    }
    
    /* Additional mobile-specific enhancements */
    .sidebar-header h3 {
        color: var(--white) !important;
        font-weight: 600 !important;
        font-size: 1.1rem !important;
        margin: 0 !important;
        padding: var(--spacing-xs) 0 !important;
    }
    
    .sidebar-section h3 {
        color: var(--white) !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        margin: 0 !important;
        padding: var(--spacing-xs) 0 !important;
    }
    
    .sidebar-divider {
        height: 1px;
        background: rgba(255, 255, 255, 0.2);
        margin: var(--spacing-sm) 0;
        border-radius: 1px;
    }
    
    .upload-instruction {
        color: rgba(255, 255, 255, 0.9) !important;
        font-size: 0.85rem !important;
        margin: var(--spacing-xs) 0 !important;
        line-height: 1.4 !important;
    }
    
    .conversation-spacer {
        height: var(--spacing-xs);
    }
    
    .image-container {
        margin: var(--spacing-sm) 0;
        border-radius: var(--border-radius);
        overflow: hidden;
        box-shadow: var(--shadow);
    }
    
    .image-container img {
        border-radius: var(--border-radius) !important;
        transition: transform 0.3s ease !important;
    }
    
    .image-container:hover img {
        transform: scale(1.02);
    }
    
    .tips-content {
        color: rgba(255, 255, 255, 0.9) !important;
        font-size: 0.85rem !important;
        line-height: 1.5 !important;
        white-space: pre-line;
    }
    
    /* Enhanced expander styling */
    .streamlit-expanderHeader {
        background: rgba(255, 255, 255, 0.1) !important;
        border-radius: var(--border-radius) !important;
        padding: var(--spacing-sm) !important;
        font-weight: 600 !important;
        color: var(--white) !important;
    }
    
    .streamlit-expanderContent {
        background: rgba(255, 255, 255, 0.05) !important;
        border-radius: 0 0 var(--border-radius) var(--border-radius) !important;
        padding: var(--spacing-sm) !important;
    }
    
    /* Mobile chat optimization */
    @media (max-width: 768px) {
        .stChatInputContainer {
            position: fixed !important;
            bottom: 0 !important;
            left: 0 !important;
            right: 0 !important;
            z-index: 999 !important;
            background: rgba(255, 255, 255, 0.95) !important;
            backdrop-filter: blur(10px) !important;
            padding: var(--spacing-sm) !important;
            margin: 0 !important;
            border-radius: 0 !important;
            box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.15) !important;
        }
        
        .main .block-container {
            padding-bottom: 6rem !important;
        }
        
        .footer {
            display: none;
        }
        
        .language-selector {
            margin-bottom: var(--spacing-sm);
        }
        
        .header-container {
            margin-bottom: var(--spacing-sm);
            border-radius: var(--border-radius);
        }
    }
    
    /* Improved mobile scrolling */
    @media (max-width: 768px) {
        [data-testid="stSidebar"] .element-container {
            margin-bottom: var(--spacing-xs);
        }
        
        .main {
            padding-bottom: 0;
        }
        
        .stChatMessage {
            margin: var(--spacing-xs) var(--spacing-xs);
            font-size: 0.9rem;
        }
    }
    
    /* Tablet optimizations */
    @media (min-width: 769px) and (max-width: 1024px) {
        .header-title {
            font-size: 2.2rem;
        }
        
        .stChatMessage {
            max-width: 90%;
            margin-left: auto;
            margin-right: auto;
        }
    }
</style>
""", unsafe_allow_html=True)

# System prompt
style_genie_system_prompt = """<system_prompt>

🧥 **STYLE GENIE — MULTILINGUAL AI FASHION DESIGNER, PERSONAL STYLIST & SHOPPING EXPERT**

YOU ARE **STYLE GENIE**, THE WORLD’S MOST ADVANCED MULTILINGUAL AI FASHION ADVISOR.  
YOUR MISSION IS TO **ASSIST USERS IN ANALYZING, STYLING, ENHANCING, AND SOURCING OUTFITS** WHILE MAINTAINING THEIR UNIQUE IDENTITY AND PERSONAL STYLE.

---

### 🌟 TONE & PERSONA

- YOU SPEAK AS A **FRIENDLY, PROFESSIONAL, AND ENTHUSIASTIC STYLIST** — confident but never arrogant.  
- YOUR VOICE IS **CONVERSATIONAL, POSITIVE, AND CREATIVE**, blending expertise with encouragement.  
- USE contractions naturally (e.g., “I’ll”, “you’re”, “that’s”).  
- KEEP messages concise but insightful — aim for clarity, warmth, and excitement.

---

### 🧠 MEMORY SYSTEM INTEGRATION

YOU HAVE ACCESS TO THREE MEMORY TOOLS:

- **`add_memories(prompt, user_id)`** → STORE new user information (preferences, brands, colors, etc.)  
- **`search_memories(prompt, user_id)`** → RECALL previously discussed topics  
- **`get_all_memories(prompt, user_id)`** → RETRIEVE all stored user data for personalization  

#### RULES FOR MEMORY BEHAVIOR
1. **CALL `get_all_memories()` ON FIRST MESSAGE** in a new session to check if data exists.  
2. **ASK POLITELY FOR USER’S NAME** only if no memory exists. Example:  
   > “To personalize your experience, could you please tell me your name?”  
3. **ONCE NAME IS GIVEN**, immediately store it using `add_memories("User's name is [name]", "{USER_ID}")`.  
4. **NEVER ASK AGAIN** for name or data already known in the current session.  
5. **WHEN USER REFERS TO PAST DISCUSSIONS**, use `search_memories()` to recall context.  
6. **SUMMARIZE STORED DATA NATURALLY**, never print raw memory content.  
7. **ONLY STORE FACTUAL USER-APPROVED INFORMATION**, not assumptions or inferred data.  

---

### 🪪 USER IDENTITY MANAGEMENT

- Each session uses a persistent `"{USER_ID}"`.  
- All memory operations MUST use this same identifier.  
- If a user refuses to share their name, reply courteously:  
  > “No problem! I’ll continue without saving your preferences this time.”  
- Do not attempt to infer the user’s name or private information.

---

### 🧭 CORE CAPABILITIES

1. **STYLE ANALYSIS** — Analyze uploaded outfits and describe key elements (fit, color, aesthetic).  
2. **OUTFIT MODIFICATION** — Use `generate_image(prompt)` to apply style changes while **preserving the user’s identity**.  
3. **SHOPPING ASSISTANCE** — Find product links or alternatives using `web_search()`.  
4. **CULTURAL CONTEXTUALIZATION** — When asked, adapt style advice to local weather, traditions, or trends using `user_country()`.  
5. **MEMORY-AWARE PERSONALIZATION** — Integrate user history into every response.  
6. **MULTILINGUAL DIALOGUE** — Respond fluently and consistently in the user’s active language.  

---

### 🌐 MULTILINGUAL BEHAVIOR RULES

- **DETECT** the language of the latest user message.  
- **RESPOND** in that exact language unless explicitly told otherwise.  
- **MAINTAIN CONSISTENCY** in tone across languages — friendly, refined, confident.  
- If detection fails, default to English and add:  
  > “I’ll respond in English for now — feel free to switch languages anytime!”

---

### 🖼️ IMAGE GENERATION PROTOCOL

- When modifying outfits, call **`generate_image(detailed_prompt)`**.  
- ENSURE:
  - Only requested changes are made (e.g., jacket → leather, color → white).  
  - Face, body, and background remain untouched.  
  - Output looks **photorealistic and natural**.  
- If no image is uploaded, reply politely:  
  > “Please upload an image so I can visualize your outfit adjustments.”

---

### ⚙️ WORKFLOW SUMMARY

| **User Intent** | **Action Sequence** |
|------------------|--------------------|
| First message | `get_all_memories("user info", "{USER_ID}")` → check if name exists |
| No name stored | Ask politely → save name with `add_memories()` |
| Style change request | `generate_image(prompt)` → show result → describe creative reasoning |
| Shopping request | Ask for missing info (country/budget) → use `user_country()` + `web_search()` |
| Feedback or opinion | Use `search_memories()` if relevant → provide insight and new suggestion |
| New preference shared | Save via `add_memories()` immediately |

---

### 🧩 CHAIN OF THOUGHT PROCESS

FOLLOW THIS INTERNAL REASONING SEQUENCE (DO NOT DISPLAY TO USER):

1. **UNDERSTAND** → Identify what the user wants (e.g., advice, image edit, outfit match).  
2. **CHECK SESSION CONTEXT** → Determine if it’s a new chat or continuation.  
3. **BASICS** → Identify garments, colors, and goals in the message.  
4. **ANALYZE** → Search or recall past preferences via memory tools if needed.  
5. **EXECUTE** → Perform the primary action (style advice, search, or image generation).  
6. **EVALUATE** → Verify if the result fulfills the user’s intent; refine if needed.  
7. **FINAL ANSWER** → Present response in the user’s language, with enthusiasm and clear formatting.

---

### 🧷 RESPONSE FORMATTING GUIDELINES

- ALWAYS combine **visual description + reasoning + suggestion**.  
- Structure with clear paragraph breaks.  
- When applicable, end with a **friendly CTA (call to action)** such as:  
  > “Would you like me to create a visual version of that?” or  
  > “Want me to find some shopping links for this look?”

---

### 🚫 WHAT NOT TO DO

- ❌ NEVER show or reveal raw memory data or database content.  
- ❌ NEVER ask for the user’s name or data more than once per session.  
- ❌ NEVER modify a person’s face, body, or pose during image generation.  
- ❌ NEVER switch languages unless explicitly requested.  
- ❌ NEVER provide brand links without verifying via `web_search()`.  
- ❌ NEVER produce generic fashion advice without personalization or reasoning.  
- ❌ NEVER repeat tool outputs verbatim — always explain results conversationally.

---

### ✅ EXAMPLES (FEW-SHOT)

**User:** “Change my jacket to white leather.”  
**Assistant:**  
> “Got it! I’ll transform your jacket into a white leather style while keeping everything else identical — including your pose and lighting. Let’s see the result!”  
→ *(Calls `generate_image()`)*

---

**User:** “I love minimalist tones.”  
**Assistant:**  
> “Perfect — I’ll remember that. You seem drawn to clean lines and neutral shades. Want me to find similar outfits online?”  
→ *(Calls `add_memories()` and optionally `web_search()`)*

---

**User:** “Find me summer outfits for Italy.”  
**Assistant:**  
> “Excellent choice! Let’s tailor your look for the Italian summer vibe — light fabrics, Mediterranean colors. Checking current trends...”  
→ *(Calls `user_country("Italy")` + `web_search("Italian summer fashion")`)*

---

</system_prompt>


"""

# Initialize genai client (cached to avoid recreation)
@st.cache_resource
def get_genai_client():
    # Try to get API key from Streamlit secrets first, then fall back to environment variable
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY", os.environ.get("GOOGLE_API_KEY"))
    except:
        api_key = os.environ.get("GOOGLE_API_KEY")
    
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in secrets or environment variables")
    
    try:
        client = genai.Client(api_key=api_key)
        return client
    except Exception as e:
        st.error(f"Failed to initialize genai client: {e}")
        raise

# Tool definitions
@tool
async def generate_image(prompt: str) -> str:
    """" 
    This function allows you to generate an image based on the user's query.
    It modifies the current image that the user uploaded while preserving their identity.

    Args :

    prompt : the user's modification request (e.g., "change the jacket to white leather")

    Returns :

    Status message indicating success or failure
    
    """
    global current_image_bytes
    
    if current_image_bytes is None:
        return "Error: No image available to modify. Please upload an image first."

    system_prompt = """You are an AI image editor specializing in outfit modifications. 
When modifying clothing in images, you must:
- Change ONLY the requested clothing items, colors, or accessories
- Preserve the person's face, body, pose, hairstyle, and background exactly as they are
- Keep all other elements of the image unchanged
- Generate realistic and natural-looking results
- The input image shows the person whose outfit you need to modify"""
    
    try:
        api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY"))
    except:
        api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        return "Error: GEMINI_API_KEY not found in environment variables or secrets."
    
    try:
        client = genai.Client(api_key=api_key)
        
        # Get image bytes from global variable
        image_bytes = current_image_bytes
        
        # Create the image part from bytes
        image_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type="image/jpeg"
        )
        
        # Send both the original image and the modification prompt
        response = client.models.generate_content(
            model="gemini-2.5-flash-image-preview",
            contents=[image_part, prompt],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_modalities=['Text', 'Image']
            )
        )

        # Process response
        full_response = ""
        generated_image = None
        
        try:
            for part in response.candidates[0].content.parts:
                if part.text is not None:
                    full_response += part.text
                elif part.inline_data is not None:
                    try:
                        generated_image = Image.open(BytesIO(part.inline_data.data))

                        # Validate image dimensions
                        if generated_image.size[0] <= 0 or generated_image.size[1] <= 0:
                            print(f"Invalid image dimensions: {generated_image.size}")
                            full_response = "Error: Generated image has invalid dimensions. Please try again."
                            generated_image = None
                            continue

                        # Convert image to bytes for display in chat
                        img_byte_arr = BytesIO()
                        generated_image.save(img_byte_arr, format='PNG')
                        image_bytes = img_byte_arr.getvalue()

                        # Store image bytes in global variable and session state
                        update_generated_image(image_bytes)

                        try:
                            if hasattr(st, 'session_state'):
                                if 'generated_images' not in st.session_state:
                                    st.session_state.generated_images = []
                                st.session_state.generated_images.append(image_bytes)
                                st.session_state.latest_generated_image = image_bytes
                                print(f"Image stored in session state: {len(image_bytes)} bytes")
                            else:
                                print("No session state available in tool context")
                        except Exception as e:
                            print(f"Error storing image in session state: {e}")
                            pass

                        print("Image generated successfully and stored in memory")
                    except Exception as img_error:
                        print(f"Error processing generated image: {img_error}")
                        full_response = f"Error processing generated image: {str(img_error)}. Please try again."
                        generated_image = None
        except Exception as ex:
            full_response = f"ERROR in image generation: {str(ex)}"
            generated_image = None
        
        if generated_image is not None:
            return "Image successfully modified and saved. The person's identity and pose have been preserved."
        else:
            return full_response if full_response else "Image modification completed but no image was generated in the response."
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in generate_image: {error_details}")
        return f"Error generating image: {str(e)}"


@tool
async def web_search(search: str) -> dict:
    """
    This function allows the model to make searches online based on a subject given by the user.
    
    Args:
        search: the user's query
    
    Returns:
        Dictionary with search results including titles, URLs, and content snippets
    """
    try:
        api_key = st.secrets.get("TAVILY_API_KEY", os.environ.get("TAVILY_API_KEY"))
    except:
        api_key = os.environ.get("TAVILY_API_KEY")
    
    tavily_client = TavilyClient(api_key=api_key)
    
    # Use basic search for faster results
    response = tavily_client.search(
        search,
        search_depth="advanced",
        max_results=5
    )
    
    if 'results' in response:
        formatted_results = []
        for result in response['results']:
            formatted_results.append({
                'title': result.get('title', 'No title'),
                'url': result.get('url', 'No URL'),
                'content': result.get('content', 'No description'),
                'score': result.get('score', 0)
            })
        return {
            'results': formatted_results,
            'total_results': len(formatted_results)
        }
    
    return {'results': [], 'total_results': 0}


@tool
async def user_country(name: str) -> dict:
    """
    This function allows you to find information about the user's country.
    """
    try:
        country = CountryInfo(name)
        country_infos = {
            'capital': country.capital(),
            'currencies': country.currencies(),
            'languages': country.languages(),
            'borders': country.borders(),
            'area': country.area(),
            'calling_codes': country.calling_codes(),
            'timezones': country.timezones(),
            'population': country.population()
        }
        return country_infos
    except Exception as e:
        return {'error': str(e)}


@tool
async def add_memories(prompt: str, user_id: str) -> dict:
    """
    This function tool allows you to save the user's message.
    
    Args:
        prompt: the user's query
        user_id: the user's id
    
    Returns:
        The status of the function tool usage
    """
    try:
        memory_api_key = st.secrets.get('MEM0_API_KEY', os.environ.get('MEM0_API_KEY'))
    except:
        memory_api_key = os.environ.get('MEM0_API_KEY')
    
    if not memory_api_key:
        print("ERROR: MEM0_API_KEY not found in environment variables or secrets")
        return {"status": "error", "message": "MEM0_API_KEY not found"}
    
    client = MemoryClient(memory_api_key)
    
    message = {
        "role": "user",
        "content": prompt
    }
    
    try:
        client.add([message], user_id=user_id)
        print(f"Memory added successfully for user: {user_id}")
        return {"status": "success"}
    except Exception as e:
        print(f"Error adding memory for user {user_id}: {str(e)}")
        return {"status": "error", "message": str(e)}


@tool
async def search_memories(prompt: str, user_id: str) -> dict:
    """
    This function tool allows you to search for relevant memories.
    
    Args:
        prompt: the search query
        user_id: the user's id
    
    Returns:
        The status of the function tool usage
    """
    try:
        memory_api_key = st.secrets.get('MEM0_API_KEY', os.environ.get('MEM0_API_KEY'))
    except:
        memory_api_key = os.environ.get('MEM0_API_KEY')
    
    client = MemoryClient(memory_api_key)
    
    filters = {
        "AND": [
            {
                "user_id": user_id
            }
        ]
    }
    
    try:
        results = client.search(prompt, version="v2", filters=filters)
        num_results = len(results) if results else 0
        print(f"Memory search successful for user: {user_id}, found {num_results} results")
        return {"status": "success", "results": results}
    except Exception as e:
        print(f"Error searching memories for user {user_id}: {str(e)}")
        return {"status": "error", "message": str(e)}


@tool
async def get_all_memories(prompt: str, user_id: str) -> dict:
    """
    This function allows you to retrieve all memories of a user.
    
    Args:
        prompt: the user's query
        user_id: the user's id
    
    Returns:
        The status of the function tool usage
    """
    try:
        memory_api_key = st.secrets.get('MEM0_API_KEY', os.environ.get('MEM0_API_KEY'))
    except:
        memory_api_key = os.environ.get('MEM0_API_KEY')
    
    client = MemoryClient(memory_api_key)
    
    filters = {
        "AND": [
            {
                "user_id": user_id
            }
        ]
    }
    
    try:
        all_memories = client.get_all(version="v2", filters=filters, page=1, page_size=50)
        print(f"Retrieved {len(all_memories) if all_memories else 0} memories for user: {user_id}")
        return {"status": "success", "memories": all_memories}
    except Exception as e:
        print(f"Error getting all memories for user {user_id}: {str(e)}")
        return {"status": "error", "message": str(e)}


# Initialize the agent (removed caching to allow tools to access current session state)
def initialize_agent(user_id):
    """Initialize agent with user-specific system prompt"""
    api_key = os.environ.get("GEMINI_API_KEY")
    
    # Inject the actual user_id into the system prompt
    personalized_prompt = style_genie_system_prompt.replace("{USER_ID}", user_id)
    
    model = GeminiModel(
        client_args={
            'api_key': api_key,
        },
        model_id="gemini-2.5-flash",
    )
    
    agent = Agent(
        model=model,
        tools=[generate_image, user_country, web_search, get_all_memories, search_memories, add_memories],
        system_prompt=personalized_prompt,
        conversation_manager=SummarizingConversationManager(),
        
    )
    
    return agent


# Global variables to store images
current_image_bytes = None
latest_generated_image_bytes = None

def update_current_image(image_bytes):
    """Updates the global current_image_bytes variable."""
    global current_image_bytes
    current_image_bytes = image_bytes

def update_generated_image(image_bytes):
    """Updates the global latest_generated_image_bytes variable."""
    global latest_generated_image_bytes
    latest_generated_image_bytes = image_bytes

# Initialize session state
# Generate unique user ID for this session to isolate memories per user
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
    print(f"New user session created with ID: {st.session_state.user_id}")

if "conversations" not in st.session_state:
    st.session_state.conversations = load_conversations(st.session_state.user_id)

if "current_conversation_id" not in st.session_state:
    # Create first conversation if none exist
    if not st.session_state.conversations:
        new_conv = create_new_conversation()
        st.session_state.conversations[new_conv['id']] = new_conv
        st.session_state.current_conversation_id = new_conv['id']
        save_conversations(st.session_state.conversations, st.session_state.user_id)
    else:
        # Load the most recent conversation
        st.session_state.current_conversation_id = list(st.session_state.conversations.keys())[-1]

if "messages" not in st.session_state:
    # Load messages from current conversation
    current_conv = st.session_state.conversations.get(st.session_state.current_conversation_id, {})
    st.session_state.messages = current_conv.get('messages', [])

if "uploaded_image" not in st.session_state:
    st.session_state.uploaded_image = None

if "generated_image" not in st.session_state:
    st.session_state.generated_image = None

if "generated_images" not in st.session_state:
    st.session_state.generated_images = []

if "latest_generated_image" not in st.session_state:
    st.session_state.latest_generated_image = None

# Initialize agent fresh each time to ensure tools have access to current session state
st.session_state.agent = initialize_agent(st.session_state.user_id)

if "language" not in st.session_state:
    st.session_state.language = "English"

if "current_image_bytes" not in st.session_state:
    st.session_state.current_image_bytes = None


# Language selector at the top with better mobile layout
with st.container():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="language-selector">', unsafe_allow_html=True)
        selected_language = st.selectbox(
            get_text("language_selector"),
            ["English", "Français", "Español", "Deutsch"],
            index=["English", "Français", "Español", "Deutsch"].index(st.session_state.language),
            key="language_select",
            label_visibility="visible"
        )
        st.markdown('</div>', unsafe_allow_html=True)
        if selected_language != st.session_state.language:
            st.session_state.language = selected_language
            st.rerun()

# Header
st.markdown(f"""
<div class="header-container">
    <h1 class="header-title">{get_text("header_title")}</h1>
    <p class="header-subtitle">{get_text("header_subtitle")}</p>
</div>
""", unsafe_allow_html=True)

# Enhanced Sidebar with mobile-optimized layout
with st.sidebar:
    # Mobile-friendly header
    st.markdown(f'<div class="sidebar-header"><h3>{get_text("conversations")}</h3></div>', unsafe_allow_html=True)
    
    # New chat button with better mobile styling
    if st.button(get_text('new_chat'), width="stretch", type="primary"):
        new_conv = create_new_conversation()
        st.session_state.conversations[new_conv['id']] = new_conv
        st.session_state.current_conversation_id = new_conv['id']
        st.session_state.messages = []
        st.session_state.uploaded_image = None
        st.session_state.generated_images = []
        save_conversations(st.session_state.conversations, st.session_state.user_id)
        st.rerun()
    
    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
    
    # Display conversations list
    if st.session_state.conversations:
        # Sort conversations by updated_at (most recent first)
        sorted_convs = sorted(
            st.session_state.conversations.items(),
            key=lambda x: x[1].get('updated_at', ''),
            reverse=True
        )
        
        for conv_id, conv in sorted_convs:
            # Mobile-optimized conversation item
            with st.container():
                col1, col2 = st.columns([5, 1], gap="small")
                
                with col1:
                    # Get conversation preview
                    preview = get_conversation_preview(conv.get('messages', []))
                    
                    # Highlight current conversation
                    is_current = conv_id == st.session_state.current_conversation_id
                    
                    # Better mobile button styling
                    button_style = "primary" if is_current else "secondary"
                    button_label = f"{'🔵 ' if is_current else '💬 '}{preview}"
                    
                    if st.button(
                        button_label,
                        key=f"conv_{conv_id}",
                        width="stretch",
                        disabled=is_current,
                        type=button_style
                    ):
                        # Switch to this conversation
                        st.session_state.current_conversation_id = conv_id
                        st.session_state.messages = conv.get('messages', [])
                        st.rerun()
                
                with col2:
                    # Mobile-friendly delete button
                    if st.button("🗑️", key=f"del_{conv_id}", help=get_text('delete_chat'), width="stretch"):
                        if len(st.session_state.conversations) > 1:
                            del st.session_state.conversations[conv_id]
                            save_conversations(st.session_state.conversations, st.session_state.user_id)
                            
                            # Switch to another conversation if current was deleted
                            if conv_id == st.session_state.current_conversation_id:
                                new_current = list(st.session_state.conversations.keys())[0]
                                st.session_state.current_conversation_id = new_current
                                st.session_state.messages = st.session_state.conversations[new_current].get('messages', [])
                            
                            st.rerun()
                        else:
                            st.warning("Cannot delete the last conversation!")
                
                # Add spacing between conversations for better mobile UX
                st.markdown('<div class="conversation-spacer"></div>', unsafe_allow_html=True)
    else:
        st.info(get_text('no_conversations'))
    
    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
    
    # Enhanced upload section with better mobile styling
    with st.container():
        st.markdown(f'<div class="sidebar-section"><h3>{get_text("upload_section")}</h3></div>', unsafe_allow_html=True)
        st.markdown(f'<p class="upload-instruction">{get_text("upload_instruction")}</p>', unsafe_allow_html=True)
        
        # Image upload options with better mobile layout
        upload_option = st.radio(
            get_text('select_input'),
            [get_text('upload_from_device'), get_text('take_photo')],
            label_visibility="collapsed",
            horizontal=False
        )
    
    if upload_option == get_text('upload_from_device'):
        uploaded_file = st.file_uploader(
            get_text('choose_image'),
            type=["jpg", "jpeg", "png"],
            help=get_text('upload_help')
        )
        
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.session_state.uploaded_image = image
            with st.container():
                st.markdown('<div class="image-container">', unsafe_allow_html=True)
                st.image(image, caption=get_text('uploaded_image'), width="stretch")
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Save the image temporarily and store bytes
            image.save("temp_uploaded_image.jpg")
            
            # Convert image to bytes for the agent
            img_byte_arr = BytesIO()
            image.save(img_byte_arr, format='JPEG')
            image_bytes = img_byte_arr.getvalue()
            st.session_state.current_image_bytes = image_bytes
            
            # Update global variable for the tool
            update_current_image(image_bytes)
    
    else:  # Camera input
        camera_photo = st.camera_input(get_text('take_photo_btn'))
        
        if camera_photo is not None:
            image = Image.open(camera_photo)
            st.session_state.uploaded_image = image
            with st.container():
                st.markdown('<div class="image-container">', unsafe_allow_html=True)
                st.image(image, caption=get_text('captured_image'), width="stretch")
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Save the image temporarily and store bytes
            image.save("temp_uploaded_image.jpg")
            
            # Convert image to bytes for the agent
            img_byte_arr = BytesIO()
            image.save(img_byte_arr, format='JPEG')
            image_bytes = img_byte_arr.getvalue()
            st.session_state.current_image_bytes = image_bytes
            
            # Update global variable for the tool
            update_current_image(image_bytes)
    
    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
    
    # Enhanced clear chat button
    if st.button(get_text('clear_chat'), width="stretch", type="secondary"):
        # Clear messages in current conversation
        if st.session_state.current_conversation_id in st.session_state.conversations:
            st.session_state.conversations[st.session_state.current_conversation_id]['messages'] = []
            st.session_state.conversations[st.session_state.current_conversation_id]['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M")
            save_conversations(st.session_state.conversations, st.session_state.user_id)
        
        st.session_state.messages = []
        st.session_state.uploaded_image = None
        st.session_state.generated_image = None
        st.rerun()
    
    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
    
    # Enhanced tips section
    with st.expander(get_text('tips_title'), expanded=False):
        st.markdown(f'<div class="tips-content">{get_text("tips_content")}</div>', unsafe_allow_html=True)

# Main chat interface
st.markdown(f"### {get_text('chat_title')}")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Display images if present
        if "image" in message and message["image"]:
            # Handle both base64 encoded images and image bytes
            if isinstance(message["image"], str):
                # Base64 encoded image from saved conversation
                import base64
                try:
                    image_bytes = base64.b64decode(message["image"])
                    # Validate image before displaying
                    temp_image = Image.open(BytesIO(image_bytes))
                    if temp_image.size[0] > 0 and temp_image.size[1] > 0:
                        st.image(image_bytes, caption=get_text('generated_image'), width=True)
                    else:
                        st.error("Error: Invalid image dimensions in saved conversation")
                except Exception as e:
                    st.error(f"Error displaying saved image: {str(e)}")
            elif isinstance(message["image"], bytes):
                # Direct image bytes
                try:
                    # Validate image before displaying
                    temp_image = Image.open(BytesIO(message["image"]))
                    if temp_image.size[0] > 0 and temp_image.size[1] > 0:
                        st.image(message["image"], caption=get_text('generated_image'), width=True)
                    else:
                        st.error("Error: Invalid image dimensions")
                except Exception as e:
                    st.error(f"Error displaying image: {str(e)}")

# Chat input
if prompt := st.chat_input(get_text('chat_placeholder')):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate response
    with st.chat_message("assistant"):
        # Create placeholder for streaming response
        response_placeholder = st.empty()
        
        try:
            # Prepare the input for the agent
            # Build a full conversation history so the agent has access to prior user and assistant messages
            # Each entry can include text and, when available, image bytes (decoded from base64 or raw bytes)
            history_input = []
            for m in st.session_state.messages:
                entry = {}
                role = m.get("role", "user")
                content = m.get("content", "")
                if content:
                    entry["text"] = str(content)
                entry["role"] = role
                # Include images from saved conversation entries if present
                if "image" in m and m["image"]:
                    image_bytes = None
                    try:
                        # If image was saved as base64 string in conversations, decode it
                        if isinstance(m["image"], str):
                            image_bytes = base64.b64decode(m["image"])
                            # Validate image before including in history
                            temp_image = Image.open(BytesIO(image_bytes))
                            if temp_image.size[0] <= 0 or temp_image.size[1] <= 0:
                                image_bytes = None
                        elif isinstance(m["image"], (bytes, bytearray)):
                            image_bytes = bytes(m["image"])
                            # Validate image before including in history
                            temp_image = Image.open(BytesIO(image_bytes))
                            if temp_image.size[0] <= 0 or temp_image.size[1] <= 0:
                                image_bytes = None
                    except Exception:
                        image_bytes = None

                    if image_bytes:
                        entry["image"] = {
                            "format": "jpeg",
                            "source": {"bytes": image_bytes},
                        }

                history_input.append(entry)

            # Append the new user prompt as the latest message
            history_input.append({"text": prompt, "role": "user"})

            # Start agent_input with the assembled history
            agent_input = history_input

            # Also attach the currently uploaded image (if any) as an explicit image part
            # This mirrors the previous behavior but now the agent will also receive past images from history
            if st.session_state.uploaded_image is not None:
                try:
                    img_byte_arr = BytesIO()
                    st.session_state.uploaded_image.save(img_byte_arr, format='JPEG')
                    image_bytes = img_byte_arr.getvalue()
                    
                    # Validate uploaded image before sending to agent
                    temp_image = Image.open(BytesIO(image_bytes))
                    if temp_image.size[0] > 0 and temp_image.size[1] > 0:
                        agent_input.append({
                            "image": {
                                "format": "jpeg",
                                "source": {"bytes": image_bytes},
                            },
                        })
                except Exception as e:
                    print(f"Error processing uploaded image for agent: {e}")
                    st.error(f"Error processing uploaded image: {str(e)}")
            
            # Show loading indicator
            with response_placeholder:
                st.markdown(f"_{get_text('thinking')}_")
            
            # Clear previous generated image flag and record timestamp
            st.session_state.latest_generated_image = None
            request_start_time = time.time()
            
            # Get response from agent (optimized)
            agent_response = asyncio.run(st.session_state.agent(agent_input))
            
            # Convert AgentResult to string if needed
            if hasattr(agent_response, 'content'):
                response = str(agent_response.content)
            elif hasattr(agent_response, 'text'):
                response = str(agent_response.text)
            else:
                response = str(agent_response)
            
            # Display response immediately
            response_placeholder.markdown(response)
            
            # Check if a new image was generated and display it
            # Try global variable first, then session state
            generated_image_bytes = latest_generated_image_bytes or st.session_state.get('latest_generated_image', None)
            
            if generated_image_bytes and isinstance(generated_image_bytes, bytes):
                try:
                    # Validate image before displaying
                    temp_image = Image.open(BytesIO(generated_image_bytes))
                    if temp_image.size[0] > 0 and temp_image.size[1] > 0:
                        print(f"Displaying generated image: {len(generated_image_bytes)} bytes")
                        st.image(generated_image_bytes, caption=get_text('generated_image'), width="stretch")
                    else:
                        print("Generated image has invalid dimensions")
                        st.error("Error: Generated image has invalid dimensions")
                except Exception as e:
                    print(f"Error displaying generated image: {e}")
                    st.error(f"Error displaying generated image: {str(e)}")
            else:
                print(f"No image to display. Global: {latest_generated_image_bytes is not None}, Session: {st.session_state.get('latest_generated_image', None) is not None}")
            
            # Add assistant message to chat (ensure serializable)
            message_to_save = {
                "role": "assistant",
                "content": response,
                "image": generated_image_bytes if generated_image_bytes and isinstance(generated_image_bytes, bytes) else None
            }
            st.session_state.messages.append(message_to_save)
            
            # Save conversation with serializable data only
            if st.session_state.current_conversation_id in st.session_state.conversations:
                # Create a clean copy of messages for JSON serialization
                serializable_messages = []
                for msg in st.session_state.messages:
                    clean_msg = {
                        "role": msg.get("role", "user"),
                        "content": str(msg.get("content", "")),
                    }
                    if "image" in msg and msg["image"]:
                        # Convert image bytes to base64 for JSON serialization
                        if isinstance(msg["image"], bytes):
                            import base64
                            clean_msg["image"] = base64.b64encode(msg["image"]).decode('utf-8')
                        else:
                            clean_msg["image"] = str(msg["image"])
                    serializable_messages.append(clean_msg)
                
                st.session_state.conversations[st.session_state.current_conversation_id]['messages'] = serializable_messages
                st.session_state.conversations[st.session_state.current_conversation_id]['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                save_conversations(st.session_state.conversations, st.session_state.user_id)
            
        except Exception as e:
            error_message = f"{get_text('error')} {str(e)}"
            response_placeholder.error(error_message)
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_message
            })

# Footer
st.markdown(f"""
<div class="footer">
    {get_text('footer')}
</div>
""", unsafe_allow_html=True)

# Add some spacing at the bottom to account for the footer
st.markdown("<br><br><br>", unsafe_allow_html=True)
