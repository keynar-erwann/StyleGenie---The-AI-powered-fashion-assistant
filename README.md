# 👔 StyleGenie - Your Personal AI Fashion Assistant

**StyleGenie** is an AI-powered fashion assistant that helps you visualize, modify, and source outfits. Think of it as "Shazam for clothes" - upload a photo and get instant fashion advice, outfit modifications, and shopping recommendations!

## ✨ Features

- 🔍 **Visual Fashion Search** - Find clothes based on pictures
- 🎨 **AI Image Editing** - Modify outfit colors, styles, and accessories
- 💰 **Smart Shopping** - Get shopping links with price comparisons
- 🧠 **Memory System** - Remembers your style preferences over time
- 🌍 **Multilingual Support** - Available in English, French, and Spanish
- 📸 **Camera Integration** - Take photos directly in the app
- 💬 **Conversational AI** - Natural language fashion advice

## 🚀 Tech Stack

- **Frontend**: Streamlit
- **AI Models**: Google Gemini (Vision & Text), Anthropic Claude
- **Image Generation**: Gemini Imagen
- **Memory**: Mem0 AI
- **Web Search**: Tavily API
- **Agent Framework**: Strands AI
- **Language**: Python 3.8+

## 📋 Prerequisites

Before you begin, ensure you have:
- Python 3.8 or higher
- API keys for the following services:
  - [Google Gemini API](https://ai.google.dev/)
  - [Tavily API](https://tavily.com/) (for web search)
  - [Mem0 AI](https://mem0.ai/) (for memory management)
  

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone [https://github.com/yourusername/stylegenie.git](https://github.com/yourusername/stylegenie.git)
   cd stylegenie

Create a virtual environment
bash
python -m venv my_env

# On Windows:
my_env\Scripts\activate

# On macOS/Linux:
source my_env/bin/activate
Install dependencies
bash
pip install -r requirements.txt
Set up environment variables
Copy .env.example to 
.env
bash
cp .env.example .env
Edit 
.env
 and add your API keys
🎯 Usage
Running the App
bash
streamlit run frontend_2.py
Or use the batch file (Windows):

bash
run_streamlit.bat
The app will open in your default browser at http://localhost:8501

How to Use
Upload or Take a Photo - Provide an image of an outfit or fashion item
Chat with StyleGenie - Ask questions like:
"Can you change the shirt color to blue?"
"Find me similar outfits under $100"
"What would go well with this outfit?"
"Generate a summer outfit for me"
View Results - Get AI-generated images, shopping links, and fashion advice
Switch Languages - Use the language selector for French or Spanish
📁 Project Structure
stylegenie/
├── app.py              # Main Streamlit application
├── style_genie_agent.py    # Core AI agent logic
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules
├── README.md                 # This file
└── run_streamlit.bat         # Windows launcher script
🔑 API Keys Setup
Required APIs:
Google Gemini: For vision, text generation, and image creation
Tavily: For web search and shopping results
Mem0: For user preference memory
Optional APIs:
Anthropic Claude: Alternative AI model
SERP API / Brave Search: Additional search options
🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

📝 License
This project is licensed under the MIT License - see the LICENSE file for details.

👨‍💻 Author
Keynar

Made with love ❤️

🙏 Acknowledgments
Google Gemini for powerful AI capabilities
Streamlit for the amazing web framework
All the open-source libraries that made this possible
📧 Support
If you have any questions or run into issues, please open an issue on GitHub.

Note: This is a prototype/first application project. Some features may be experimental.




