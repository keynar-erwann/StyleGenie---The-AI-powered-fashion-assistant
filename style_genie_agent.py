from google import genai
import os
from dotenv import load_dotenv
from google.genai import types
from PIL import Image
from linkup import LinkupClient
from countryinfo import CountryInfo
from tavily import TavilyClient
from serpapi import GoogleSearch
from strands import Agent,tool
from strands.models.gemini import GeminiModel
from strands.models.anthropic import AnthropicModel
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
from strands.agent.conversation_manager import SummarizingConversationManager,SlidingWindowConversationManager
from mem0 import MemoryClient


load_dotenv()

api_key = os.environ.get("GOOGLE_API_KEY")
anthropic_key = os.environ.get("ANTHROPIC_API_KEY")


style_genie_system_prompt = """<system_prompt>

👔 **STYLE GENIE — MULTILINGUAL AI FASHION EXPERT, MEMORY-AWARE IMAGE STYLIST & SHOPPING FINDER**

YOU ARE **STYLE GENIE**, THE WORLD’S MOST ADVANCED MULTILINGUAL AI FASHION ASSISTANT.  
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
2. **SEARCH MEMORIES** when the user references past discussions (e.g., “Do you remember what I liked last time?”).  
3. **GET ALL MEMORIES** when generating any new suggestion or styling advice to personalize the output.  
4. **REFER POLITELY** to stored context (e.g., “Last time, you mentioned liking minimalist neutral tones.”).  
5. **NEVER expose or print raw memory data** — always summarize naturally.  
6. **ONLY store factual user-approved data**, never assumptions.

---

### 🪪 USER IDENTITY MANAGEMENT

- ALWAYS CHECK if the **user’s name** is known before calling memory functions.  
- IF the name is unknown, ASK ONCE POLITELY in the user’s language:  
  > “To personalize your experience, could you please tell me your name?”  
- AFTER the user provides it, IMMEDIATELY call `add_memories()` to store it.  
- REUSE that name for all subsequent memory-related actions.  
- NEVER ask for the name again unless the user indicates they want to update it.  
- IF the user declines to share a name, say:  
  > “No problem — I’ll continue without saving memories for now,”  
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
       > “To help you best, could you please tell me your budget and which country you are in?”
       (Translate automatically to the user’s language)
     - WAIT for their response before continuing.
   - USE `user_country(country_name)` to retrieve localized data.
   - IDENTIFY each visible clothing item (type, color, style).
   - BUILD search query:
     `[item type] [color] [style keywords] [country] buy OR acheter [retailer]`
   - EXECUTE `web_search(query)` → return only verified URLs.
   - IF no results found:
       > “I couldn’t find good results, I’ll try different keywords.”

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

- GIVE style opinions ONLY when the user explicitly asks (e.g., “Do you like it?”).  
- ASK for missing information only once, then wait.  
- ASK neutral clarifying questions if the user is uncertain.  
- NEVER fabricate URLs or modify a person’s physical features.  
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

1. **UNDERSTAND:** Identify if the user’s intent is styling, shopping, opinion, or memory-related.  
2. **BASICS:** Extract garments, preferences, or missing data.  
3. **BREAK DOWN:** Plan which tools to use (memory, image, or search).  
4. **ANALYZE:** If memory exists, recall it to guide personalization.  
5. **BUILD:** Generate image, find items, or craft a personalized reply.  
6. **EDGE CASES:** Handle missing name, missing info, or empty search gracefully.  
7. **FINAL ANSWER:** Present output clearly, in the user’s language, using proper format and tone.

---

### 🚫 WHAT NOT TO DO

- ❌ NEVER alter physical identity or environment in images.  
- ❌ NEVER invent URLs, brands, or prices.  
- ❌ NEVER guess the user’s name or preferences — always confirm.  
- ❌ NEVER show or expose raw memory data.  
- ❌ NEVER mix personal opinions with factual results unless asked.  
- ❌ NEVER ignore user’s language.  
- ❌ NEVER delete or overwrite memories unless the user requests it.  

---

### 💡 FEW-SHOT EXAMPLES

**Example 1 – Image Editing**  
User: “Change my jacket to a white leather one.”  
→ `get_all_memories()` (recall preferences)  
→ `generate_image`  
→ “Updated Look: The jacket was changed to a fitted white leather design while preserving your pose and background.”

**Example 2 – Shopping**  
User: “Find this jacket for me.”  
→ If name unknown: ask for name → store with `add_memories()`  
→ If budget or country missing: ask politely once.  
→ Then `web_search()` → return structured results.

**Example 3 – Memory Recall**  
User: “What outfit did I like last time?”  
→ `search_memories()` → summarize response politely.  
→ “Last time, you mentioned loving the black minimalist outfit with beige accents.”

**Example 4 – Opinion Request**  
User: “Do you think this outfit suits me?”  
→ “Yes, it aligns perfectly with your previous preferences for neutral tones and elegant simplicity.”

---

</system_prompt>

"""


@tool
def generate_image(prompt : str, image_path : str) -> str :

    """" 
    This function allows you to generate an image based on the user's query :

    Args :

    prompt : the user's query

    image_path : the image path

    Returns :

    Your response 
    
    """

    

    system_prompt =  """ AI Fashion Stylist System Prompt
Core Identity

You are a creative and knowledgeable AI fashion stylist, expert in style analysis, trend integration, and visual communication. Your primary goal is to inspire and guide users in developing their personal style, offering both direct styling solutions and innovative outfit ideas.

"""
    api_key = os.environ.get("GEMINI_API_KEY")
    

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
    model="gemini-2.5-flash-image",
    contents=[prompt, image_path],
    config = types.GenerateContentConfig(system_instruction=system_prompt)
)

    for part in response.candidates[0].content.parts:
        if part.text is not None:
            print(part.text)
        elif part.inline_data is not None:
            image = Image.open(BytesIO(part.inline_data.data))
            image.save("generated_image3.png")


@tool
def web_search(search: str) -> dict:
    """
    This function allows the model to make searches online based on a subject given by the user
    
    Args:
        search: the user's query
    
    Returns:
        Dictionary with search results including titles, URLs, and content snippets
    """
    api_key = os.environ.get("TAVILY_API_KEY")
    tavily_client = TavilyClient(api_key=api_key)
    
    # Get search results with URLs
    response = tavily_client.search(
        search,
        search_depth="advanced",  # Get more detailed results
        max_results=5  # Get multiple options
    )
    
    # Format results to emphasize URLs
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
def user_country(name: str) -> None:
    logging.info("calling user_country tool...")
    """
    This function allows you to find information about the user's country in order to find the appropriate websites for them to shop
    """
    country = CountryInfo(name)
    country_infos = [
        country.capital(),
        country.currencies(),
        country.languages(),
        country.borders(),
        country.provinces(),
        country.area(),
        country.calling_codes(),
        country.capital_latlng(),
        country.timezones(),
        country.population(),
        country.alt_spellings()
    ]
    return country_infos


@tool
def add_memories(prompt: str, user_name: str) -> dict:
   """ This function tool allows you to save the user's message in order to remember past  conversations with the user and infos about them

    Args :
    prompt : the user's query eg, : where can I find this outfit ?

    user_name : the user's name eg : Ines 

    Returns :
    
    The status of the function tool usage
    
    
     """
    

   memory_api_key = os.environ.get('MEM0_API_KEY')
   client = MemoryClient(memory_api_key)

    
   message = {
        "role": "user",
        "content": prompt
    }

   try:
        client.add([message], user_id=user_name)  
        return {"status": "success"}

   except :

    return {"status" : "error"}




@tool
def search_memories(prompt : str,user_name : str) -> dict :
    """ This function tool allows you to search for relevant memories based on the user's prompt

    Args :
    prompt : "Do you remember what is my favorite outfit ?"

    
    user_name : the user's name eg : what's my name ? 


    Returns :
    The status of the function tool usage
    
    
     """
    memory_api_key = os.environ.get('MEM0_API_KEY')

    client = MemoryClient(memory_api_key)


    filters = {
    "AND": [
        {
            "user_id": user_name
        }
    ]
}

    
    client.search(prompt, version="v2", filters=filters)

    return {"status": "success"}

@tool
def get_all_memories(prompt : str,user_name : str) -> dict :
    """ This function allows you to retrieve all of memories of a user

     Args :
    prompt : the user's query eg, : where can I find this outfit ?

    user_name : the user's name eg : Ines 

    Returns :
    
    The status of the function tool usage
    
    
    """

    
    memory_api_key = os.environ.get('MEM0_API_KEY')

    client = MemoryClient(memory_api_key)


    filters = {
   "AND": [
      {
         "user_id": "alex"
      }
   ]
}

    all_memories = client.get_all(version="v2", filters=filters, page=1, page_size=50)

    return {"status" : "success"}


model = GeminiModel(
    client_args = {
        'api_key': api_key,

    },
    model_id="gemini-2.5-flash",
)


   

stylist_agent = Agent(model=model,
    tools=[generate_image,user_country,web_search,get_all_memories,search_memories,add_memories],
    system_prompt=style_genie_system_prompt,
    )


with open("new_rock.jpg","rb") as img :
        image_bytes = img.read()

#phase de test
while True:
    prompt = input("\nUser: ").strip()
    if prompt.lower() == "q":
        print("Goodbye!")
        break

    

    response = stylist_agent([
        {"text": prompt},
        {
            "image": {
                "format": "jpeg",  
                "source": {"bytes": image_bytes},
            },
        },
    ])
    
    print(response)