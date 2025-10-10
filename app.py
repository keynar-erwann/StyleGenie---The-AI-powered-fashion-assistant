import streamlit as st
from google import genai
import os
from dotenv import load_dotenv
from google.genai import types
from PIL import Image
from countryinfo import CountryInfo
from tavily import TavilyClient
from strands import Agent, tool
from strands.models.gemini import GeminiModel
from io import BytesIO
from mem0 import MemoryClient
import base64
from datetime import datetime
import json
import uuid
import warnings

# Load environment variables
load_dotenv()

# Suppress the AttributeError warning from google.genai.Client.__del__
# This is a known issue with google-genai in Python 3.13
warnings.filterwarnings('ignore', message=".*'Client' object has no attribute '_api_client'.*")

# Global variable to store latest generated image path (workaround for thread context issues)
_latest_generated_image_path = None

# Monkey patch to fix the genai.Client.__del__ issue
original_client_del = genai.Client.__del__

def safe_client_del(self):
    """Safe destructor that handles missing _api_client attribute"""
    try:
        if hasattr(self, '_api_client'):
            original_client_del(self)
    except AttributeError:
        # Silently ignore the AttributeError
        pass
    except Exception:
        # Ignore other exceptions during cleanup
        pass

genai.Client.__del__ = safe_client_del

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

# Conversation management functions
def load_conversations():
    """Load conversations from JSON file"""
    if os.path.exists('conversations.json'):
        try:
            with open('conversations.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_conversations(conversations):
    """Save conversations to JSON file"""
    try:
        with open('conversations.json', 'w', encoding='utf-8') as f:
            json.dump(conversations, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Error saving conversations: {e}")

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
    initial_sidebar_state="auto"  # Auto-collapse on mobile
)

# Custom CSS for beautiful UI with mobile-first design
st.markdown("""
<style>
    /* Mobile-first: Base styles for mobile */
    
    /* Main container styling */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 0.5rem;
    }
    
    /* Chat container - optimized for mobile */
    .stChatMessage {
        background-color: rgba(255, 255, 255, 0.95);
        border-radius: 15px;
        padding: 12px;
        margin: 8px 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        font-size: 0.95rem;
    }
    
    /* Header styling - mobile optimized */
    .header-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem 1rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 1rem;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
    }
    
    .header-title {
        color: white;
        font-size: 2rem;
        font-weight: bold;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
    }
    
    .header-subtitle {
        color: rgba(255, 255, 255, 0.9);
        font-size: 0.95rem;
        margin-top: 0.5rem;
    }
    
    /* Footer styling - mobile optimized */
    .footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        text-align: center;
        padding: 0.75rem;
        font-size: 0.85rem;
        box-shadow: 0 -4px 6px rgba(0, 0, 0, 0.1);
        z-index: 999;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Button styling - larger touch targets for mobile */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 1.5rem;
        font-weight: bold;
        transition: all 0.3s ease;
        min-height: 44px; /* iOS recommended touch target */
        width: 100%;
        font-size: 1rem;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.2);
    }
    
    .stButton>button:active {
        transform: translateY(0);
    }
    
    /* File uploader styling - mobile friendly */
    .uploadedFile {
        border-radius: 10px;
        border: 2px dashed #667eea;
    }
    
    /* Chat input styling - mobile optimized */
    .stChatInputContainer {
        border-radius: 15px;
        margin-bottom: 4rem;
    }
    
    .stChatInput>div>div>textarea {
        font-size: 16px !important; /* Prevents zoom on iOS */
        min-height: 44px;
    }
    
    /* Image display styling - responsive */
    .uploaded-image {
        border-radius: 15px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        max-width: 100%;
        height: auto;
        margin: 1rem 0;
    }
    
    /* Radio buttons - larger touch targets */
    .stRadio > div {
        gap: 0.75rem;
    }
    
    .stRadio > div > label {
        padding: 0.75rem;
        min-height: 44px;
        display: flex;
        align-items: center;
    }
    
    /* Select box - mobile friendly */
    .stSelectbox > div > div {
        font-size: 16px !important; /* Prevents zoom on iOS */
    }
    
    /* File uploader - larger touch area */
    .stFileUploader > div > button {
        min-height: 44px;
        font-size: 16px;
    }
    
    /* Camera input - mobile optimized */
    button[kind="header"] {
        min-height: 44px;
    }
    
    /* Responsive images in chat */
    .stChatMessage img {
        max-width: 100%;
        height: auto;
        border-radius: 10px;
    }
    
    /* Tablet and Desktop: Media queries for larger screens */
    @media (min-width: 768px) {
        .main {
            padding: 1rem;
        }
        
        .header-title {
            font-size: 3rem;
        }
        
        .header-subtitle {
            font-size: 1.2rem;
        }
        
        .header-container {
            padding: 2rem;
            border-radius: 20px;
            margin-bottom: 2rem;
        }
        
        .stChatMessage {
            padding: 15px;
            margin: 10px 0;
            font-size: 1rem;
        }
        
        .footer {
            padding: 1rem;
            font-size: 1rem;
        }
        
        .stButton>button {
            width: auto;
            padding: 0.5rem 2rem;
        }
    }
    
    /* Large Desktop */
    @media (min-width: 1200px) {
        .header-title {
            font-size: 3.5rem;
        }
    }
    
    /* Improve touch scrolling on mobile */
    .main, .stChatMessageContainer {
        -webkit-overflow-scrolling: touch;
    }
    
    /* Prevent text selection on buttons (better mobile UX) */
    button {
        -webkit-tap-highlight-color: transparent;
        user-select: none;
    }
    
    /* Optimize sidebar for mobile */
    @media (max-width: 768px) {
        [data-testid="stSidebar"] {
            width: 100% !important;
        }
        
        [data-testid="stSidebar"][aria-expanded="false"] {
            margin-left: -100%;
        }
    }
</style>
""", unsafe_allow_html=True)

# System prompt
style_genie_system_prompt = """<system_prompt>

👔 **STYLE GENIE — MULTILINGUAL AI FASHION EXPERT, MEMORY-AWARE IMAGE STYLIST & SHOPPING FINDER**

YOU ARE **STYLE GENIE**, THE WORLD'S MOST ADVANCED MULTILINGUAL AI FASHION ASSISTANT.  
YOU SPECIALIZE IN STYLE ANALYSIS, IDENTITY-PRESERVING IMAGE EDITING, GLOBAL OUTFIT DISCOVERY, AND LONG-TERM USER MEMORY MANAGEMENT.

YOUR CORE PURPOSE IS TO HELP USERS VISUALIZE, MODIFY, AND SOURCE OUTFITS ACCURATELY AND SAFELY —  
WHILE PRESERVING THEIR IDENTITY, RESPECTING THEIR LANGUAGE, AND REMEMBERING THEIR PREFERENCES OVER TIME.

---

### 🧠 MEMORY SYSTEM INTEGRATION

Your memory is powered by three tools:

- **`add_memories(prompt, user_name)`** → STORE relevant user information (style preferences, favorite colors, brands, budget, etc.).  
- **`search_memories(prompt, user_name)`** → RECALL previous interactions or fashion preferences.  
- **`get_all_memories(prompt, user_name)`** → RETRIEVE all user memories to provide personalized context.

#### 🧩 MEMORY BEHAVIOR RULES

1. **ADD MEMORIES** whenever the user shares new information about themselves or their tastes.  
2. **SEARCH MEMORIES** when the user references past discussions (e.g., "Do you remember what I liked last time?").  
3. **GET ALL MEMORIES** when generating any new suggestion or styling advice to personalize the output.  
4. **REFER POLITELY** to stored context (e.g., "Last time, you mentioned liking minimalist neutral tones.").  
5. **NEVER expose or print raw memory data** — always summarize naturally.  
6. **ONLY store factual user-approved data**, never assumptions.

---

### 🪪 USER IDENTITY MANAGEMENT

- ALWAYS CHECK if the **user's name** is known before calling memory functions.  
- IF the name is unknown, ASK ONCE POLITELY in the user's language:  
  > "To personalize your experience, could you please tell me your name?"  
- AFTER the user provides it, IMMEDIATELY call `add_memories()` to store it.  
- REUSE that name for all subsequent memory-related actions.  
- NEVER ask for the name again unless the user indicates they want to update it.  
- IF the user declines to share a name, say:  
  > "No problem — I'll continue without saving memories for now,"  
  and temporarily skip all memory-related actions.

---

### 🧭 CORE CAPABILITIES

1. **IDENTITY-PRESERVING IMAGE EDITING**
   - MODIFY outfits, colors, or accessories while keeping:
     - FACE, BODY, POSE, HAIRSTYLE, and BACKGROUND unchanged.
   - USE `generate_image` for the modification.
   - DESCRIBE edits factually and briefly, no opinions unless asked.

2. **INTELLIGENT SHOPPING ASSISTANT**
   - WHEN asked to find or buy an outfit:
     - IF **budget or country** is missing, ask once:
       > "To help you best, could you please tell me your budget and which country you are in?"
       (Translate automatically to the user's language)
     - WAIT for their response before continuing.
   - USE `user_country(country_name)` to retrieve localized data.
   - IDENTIFY each visible clothing item (type, color, style).
   - BUILD search query:
     `[item type] [color] [style keywords] [country] buy OR acheter [retailer]`
   - EXECUTE `web_search(query)` → return only verified URLs.
   - IF no results found:
       > "I couldn't find good results, I'll try different keywords."

   **POPULAR RETAILERS BY REGION**
   - France: Zalando, Asos, Zara.fr, H&M.fr, Shein  
   - Spain: Zara.es, Mango, Zalando, Asos  
   - Germany: Zalando.de, About You, Asos  
   - UK/US: Asos, Zara, H&M, Amazon, Nordstrom  

---

### 🌐 MULTILINGUAL BEHAVIOR RULES

- DETECT and RESPOND automatically in the SAME LANGUAGE as the latest user message.  
- NEVER switch languages unless explicitly requested.  
- MAINTAIN a friendly, polite, and professional tone at all times.  
- ENSURE consistency in formatting, politeness, and translation accuracy.

---

### 🖼️ RESPONSE FORMATS

#### 🔹 IF AN IMAGE WAS GENERATED
**Updated Look:** [Brief, neutral description of visual changes]

#### 🔹 IF SHOPPING RESULTS WERE FOUND
**Outfit Details:** [List main items]  
**Shopping Options:**  
- **Product:** [Exact title]  
- **Price:** [Price, if found]  
- **Link:** [Verified URL only]  
- **Retailer:** [Domain]  

**Budget Summary:**  
- **Estimated Total:** [Sum of prices]  
- **Remaining:** [Budget - total]

---

### 💬 COMMUNICATION & INTERACTION PROTOCOL

- GIVE style opinions ONLY when the user explicitly asks (e.g., "Do you like it?").  
- ASK for missing information only once, then wait.  
- ASK neutral clarifying questions if the user is uncertain.  
- NEVER fabricate URLs or modify a person's physical features.  
- PRESENT search results progressively, not all at once.  
- USE memories to personalize replies naturally.

---

### ⚙️ WORKFLOW SUMMARY

| **Intent**             | **Action** |
|------------------------|------------|
| New user               | Ask for name → `add_memories(name)` |
| Known user             | `get_all_memories()` → personalize |
| Style edit             | `generate_image()` → factual description → optional shopping |
| Shopping request       | Ask for missing info → `user_country()` → `web_search()` |
| Opinion request        | Give friendly, concise opinion |
| Personalization        | Retrieve via `search_memories()` |
| New preference shared  | `add_memories()` to update context |
| User unsure            | Ask polite clarifying question |

---

### 🧩 CHAIN OF THOUGHT PROCESS

1. **UNDERSTAND:** Identify if the user's intent is styling, shopping, opinion, or memory-related.  
2. **BASICS:** Extract garments, preferences, or missing data.  
3. **BREAK DOWN:** Plan which tools to use (memory, image, or search).  
4. **ANALYZE:** If memory exists, recall it to guide personalization.  
5. **BUILD:** Generate image, find items, or craft a personalized reply.  
6. **EDGE CASES:** Handle missing name, missing info, or empty search gracefully.  
7. **FINAL ANSWER:** Present output clearly, in the user's language, using proper format and tone.

---

### 🚫 WHAT NOT TO DO

- ❌ NEVER alter physical identity or environment in images.  
- ❌ NEVER invent URLs, brands, or prices.  
- ❌ NEVER guess the user's name or preferences — always confirm.  
- ❌ NEVER show or expose raw memory data.  
- ❌ NEVER mix personal opinions with factual results unless asked.  
- ❌ NEVER ignore user's language.  
- ❌ NEVER delete or overwrite memories unless the user requests it.

---

### 💡 FEW-SHOT EXAMPLES

**Example 1 – Image Editing**  
User: "Change my jacket to a white leather one."  
→ `get_all_memories()` (recall preferences)  
→ `generate_image`  
→ "Updated Look: The jacket was changed to a fitted white leather design while preserving your pose and background."

**Example 2 – Shopping**  
User: "Find this jacket for me."  
→ If name unknown: ask for name → store with `add_memories()`  
→ If budget or country missing: ask politely once.  
→ Then `web_search()` → return structured results.

**Example 3 – Memory Recall**  
User: "What outfit did I like last time?"  
→ `search_memories()` → summarize response politely.  
→ "Last time, you mentioned loving the black minimalist outfit with beige accents."

**Example 4 – Opinion Request**  
User: "Do you think this outfit suits me?"  
→ "Yes, it aligns perfectly with your previous preferences for neutral tones and elegant simplicity."

---

</system_prompt>
"""

# Initialize genai client (cached to avoid recreation)
@st.cache_resource
def get_genai_client():
    """Initialize and return a Google GenAI client with proper error handling"""
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
def generate_image(prompt: str, image_path: str) -> str:
    """
    This function allows you to generate an image based on the user's query.
    
    Args:
        prompt: the user's query
        image_path: the image path
    
    Returns:
        Your response with image path
    """
    system_prompt = """AI Fashion Stylist System Prompt
Core Identity

You are a creative and knowledgeable AI fashion stylist, expert in style analysis, trend integration, and visual communication. Your primary goal is to inspire and guide users in developing their personal style, offering both direct styling solutions and innovative outfit ideas.
"""
    client = get_genai_client()
    
    try:
        # Prepare contents with system prompt and user input
        contents = ([system_prompt, prompt], image_path)
        
        # Use image generation model (gemini-2.5-flash-image-preview for image generation)
        response = client.models.generate_content(
            model="gemini-2.5-flash-image-preview",
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=['Text', 'Image']
            )
        )
        
        text_response = ""
        image_generated = False
        
        # Unpack response
        for part in response.candidates[0].content.parts:
            if part.text is not None:
                # Handle text response (could be string or iterable)
                if isinstance(part.text, str):
                    text_response += part.text
                else:
                    for item in part.text:
                        text_response += item
            elif part.inline_data is not None:
                # Save the generated image
                try:
                    global _latest_generated_image_path
                    
                    image = Image.open(BytesIO(part.inline_data.data))
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    image_filename = f"generated_image_{timestamp}.png"
                    
                    # Save to disk
                    image.save(image_filename)
                    
                    # Get absolute path for reliability
                    abs_path = os.path.abspath(image_filename)
                    
                    # Store in global variable (works across threads)
                    _latest_generated_image_path = abs_path
                    
                    # Try to store in session state (may not work in agent thread)
                    try:
                        if 'generated_images' not in st.session_state:
                            st.session_state.generated_images = []
                        st.session_state.generated_images.append(abs_path)
                        st.session_state.latest_generated_image = abs_path
                    except:
                        pass  # Session state not accessible from agent thread
                    
                    image_generated = True
                except Exception as save_error:
                    return f"Error saving generated image: {str(save_error)}"
        
        if image_generated:
            return f"{text_response}\n\n✨ **Image generated successfully!** Check below to see your new look."
        else:
            return text_response if text_response else "Image generation completed, but no image was returned."
            
    except Exception as e:
        return f"Error generating image: {str(e)}"


@tool
def web_search(search: str) -> dict:
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
def user_country(name: str) -> dict:
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
def add_memories(prompt: str, user_name: str) -> dict:
    """
    This function tool allows you to save the user's message.
    
    Args:
        prompt: the user's query
        user_name: the user's name
    
    Returns:
        The status of the function tool usage
    """
    try:
        memory_api_key = st.secrets.get('MEM0_API_KEY', os.environ.get('MEM0_API_KEY'))
    except:
        memory_api_key = os.environ.get('MEM0_API_KEY')
    
    client = MemoryClient(memory_api_key)
    
    message = {
        "role": "user",
        "content": prompt
    }
    
    try:
        client.add([message], user_id=user_name)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@tool
def search_memories(prompt: str, user_name: str) -> dict:
    """
    This function tool allows you to search for relevant memories.
    
    Args:
        prompt: the search query
        user_name: the user's name
    
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
                "user_id": user_name
            }
        ]
    }
    
    try:
        results = client.search(prompt, version="v2", filters=filters)
        return {"status": "success", "results": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@tool
def get_all_memories(prompt: str, user_name: str) -> dict:
    """
    This function allows you to retrieve all memories of a user.
    
    Args:
        prompt: the user's query
        user_name: the user's name
    
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
                "user_id": user_name
            }
        ]
    }
    
    try:
        all_memories = client.get_all(version="v2", filters=filters, page=1, page_size=50)
        return {"status": "success", "memories": all_memories}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Initialize the agent
@st.cache_resource
def initialize_agent():
    # Try to get API key from Streamlit secrets first, then fall back to environment variable
    try:
        api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY"))
    except:
        api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        # Try GOOGLE_API_KEY as fallback
        try:
            api_key = st.secrets.get("GOOGLE_API_KEY", os.environ.get("GOOGLE_API_KEY"))
        except:
            api_key = os.environ.get("GOOGLE_API_KEY")
    
    if not api_key:
        raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY not found in secrets or environment variables")
    
    model = GeminiModel(
        client_args={
            'api_key': api_key,
        },
        model_id="gemini-2.0-flash-exp",  # Faster experimental model
    )
    
    agent = Agent(
        model=model,
        tools=[generate_image, user_country, web_search, get_all_memories, search_memories, add_memories],
        system_prompt=style_genie_system_prompt,
    )
    
    return agent


# Initialize session state
if "conversations" not in st.session_state:
    st.session_state.conversations = load_conversations()

if "current_conversation_id" not in st.session_state:
    # Create first conversation if none exist
    if not st.session_state.conversations:
        new_conv = create_new_conversation()
        st.session_state.conversations[new_conv['id']] = new_conv
        st.session_state.current_conversation_id = new_conv['id']
        save_conversations(st.session_state.conversations)
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

if "agent" not in st.session_state:
    st.session_state.agent = initialize_agent()

if "language" not in st.session_state:
    st.session_state.language = "English"


# Language selector at the top
col1, col2, col3 = st.columns([2, 1, 2])
with col2:
    selected_language = st.selectbox(
        get_text("language_selector"),
        ["English", "Français", "Español", "Deutsch"],
        index=["English", "Français", "Español", "Deutsch"].index(st.session_state.language),
        key="language_select"
    )
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

# Sidebar
with st.sidebar:
    # Conversations section
    st.markdown(f"### {get_text('conversations')}")
    
    # New chat button
    if st.button(get_text('new_chat'), width=True, type="primary"):
        new_conv = create_new_conversation()
        st.session_state.conversations[new_conv['id']] = new_conv
        st.session_state.current_conversation_id = new_conv['id']
        st.session_state.messages = []
        st.session_state.uploaded_image = None
        st.session_state.generated_images = []
        save_conversations(st.session_state.conversations)
        st.rerun()
    
    st.markdown("---")
    
    # Display conversations list
    if st.session_state.conversations:
        # Sort conversations by updated_at (most recent first)
        sorted_convs = sorted(
            st.session_state.conversations.items(),
            key=lambda x: x[1].get('updated_at', ''),
            reverse=True
        )
        
        for conv_id, conv in sorted_convs:
            col1, col2 = st.columns([4, 1])
            
            with col1:
                # Get conversation preview
                preview = get_conversation_preview(conv.get('messages', []))
                
                # Highlight current conversation
                is_current = conv_id == st.session_state.current_conversation_id
                button_type = "primary" if is_current else "secondary"
                
                if st.button(
                    f"{'🔵 ' if is_current else ''}{preview}",
                    key=f"conv_{conv_id}",
                    width=True,
                    disabled=is_current
                ):
                    # Switch to this conversation
                    st.session_state.current_conversation_id = conv_id
                    st.session_state.messages = conv.get('messages', [])
                    st.rerun()
            
            with col2:
                # Delete button
                if st.button("🗑️", key=f"del_{conv_id}", help=get_text('delete_chat')):
                    if len(st.session_state.conversations) > 1:
                        del st.session_state.conversations[conv_id]
                        save_conversations(st.session_state.conversations)
                        
                        # Switch to another conversation if current was deleted
                        if conv_id == st.session_state.current_conversation_id:
                            new_current = list(st.session_state.conversations.keys())[0]
                            st.session_state.current_conversation_id = new_current
                            st.session_state.messages = st.session_state.conversations[new_current].get('messages', [])
                        
                        st.rerun()
                    else:
                        st.warning("Cannot delete the last conversation!")
    else:
        st.info(get_text('no_conversations'))
    
    st.markdown("---")
    st.markdown(f"### {get_text('upload_section')}")
    st.markdown(get_text('upload_instruction'))
    
    # Image upload options
    upload_option = st.radio(
        get_text('select_input'),
        [get_text('upload_from_device'), get_text('take_photo')],
        label_visibility="collapsed"
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
            st.image(image, caption=get_text('uploaded_image'), width=True)
            
            # Save the image temporarily
            image.save("temp_uploaded_image.jpg")
    
    else:  # Camera input
        camera_photo = st.camera_input(get_text('take_photo_btn'))
        
        if camera_photo is not None:
            image = Image.open(camera_photo)
            st.session_state.uploaded_image = image
            st.image(image, caption=get_text('captured_image'), width=True)
            
            # Save the image temporarily
            image.save("temp_uploaded_image.jpg")
    
    st.markdown("---")
    
    # Clear current chat button
    if st.button(get_text('clear_chat'), width=True):
        # Clear messages in current conversation
        if st.session_state.current_conversation_id in st.session_state.conversations:
            st.session_state.conversations[st.session_state.current_conversation_id]['messages'] = []
            st.session_state.conversations[st.session_state.current_conversation_id]['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M")
            save_conversations(st.session_state.conversations)
        
        st.session_state.messages = []
        st.session_state.uploaded_image = None
        st.session_state.generated_image = None
        st.rerun()
    
    st.markdown("---")
    st.markdown(f"### {get_text('tips_title')}")
    st.markdown(get_text('tips_content'))

# Main chat interface
st.markdown(f"### {get_text('chat_title')}")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Display images if present
        if "image" in message and message["image"]:
            try:
                if os.path.exists(str(message["image"])):
                    st.image(message["image"], caption=get_text('generated_image'), use_container_width=True)
            except Exception as e:
                pass  # Silently skip if image can't be displayed

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
            agent_input = [{"text": prompt}]
            
            # Add image if available
            if st.session_state.uploaded_image is not None:
                # Convert image to bytes
                img_byte_arr = BytesIO()
                st.session_state.uploaded_image.save(img_byte_arr, format='JPEG')
                image_bytes = img_byte_arr.getvalue()
                
                agent_input.append({
                    "image": {
                        "format": "jpeg",
                        "source": {"bytes": image_bytes},
                    },
                })
            
            # Show loading indicator
            with response_placeholder:
                st.markdown(f"_{get_text('thinking')}_")
            
            # Clear previous generated image flags
            global _latest_generated_image_path
            _latest_generated_image_path = None
            st.session_state.latest_generated_image = None
            
            # Get response from agent (optimized)
            agent_response = st.session_state.agent(agent_input)
            
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
            # Try global variable first (more reliable), then session state
            generated_image_path = _latest_generated_image_path or st.session_state.get('latest_generated_image', None)
            
            # Sync global to session state
            if _latest_generated_image_path:
                st.session_state.latest_generated_image = _latest_generated_image_path
            
            # Debug: Check if image was generated
            if generated_image_path:
                try:
                    # Verify file exists before displaying
                    if os.path.exists(generated_image_path):
                        st.image(generated_image_path, caption=get_text('generated_image'), use_container_width=True)
                    else:
                        st.warning(f"Image file not found: {generated_image_path}")
                except Exception as img_error:
                    st.error(f"Error displaying image: {img_error}")
            else:
                # Debug: Log when no image is generated
                if "image generated successfully" in response.lower():
                    st.warning("Image generation was reported but no file path found.")
            
            # Add assistant message to chat (ensure serializable)
            message_to_save = {
                "role": "assistant",
                "content": response,
                "image": generated_image_path
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
                        clean_msg["image"] = str(msg["image"])
                    serializable_messages.append(clean_msg)
                
                st.session_state.conversations[st.session_state.current_conversation_id]['messages'] = serializable_messages
                st.session_state.conversations[st.session_state.current_conversation_id]['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                save_conversations(st.session_state.conversations)
            
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
