# 🧠 Recon: AI Slang Reconstruction & Context Finder

> Built for **Project Chronos: The AI Archaeologist**  
> by **Rachit Samal**
> ID: **SE25UCSE136**

---

## 💡 Overview
Recon is an AI tool that decodes internet slang and abbreviations into clear English using **Google Gemini AI**, then enriches it with real-world meaning via the **Google Custom Search API**.  
It aims to preserve and interpret modern digital-era language — bridging technology, linguistics, and culture.

---

## 🚀 Key Features
- 🤖 Reconstructs slang-heavy or informal text using Gemini AI  
- 🔍 Searches authentic sources (Urban Dictionary, Wikipedia, etc.)  
- 💬 Explains each slang or abbreviation  
- 📜 Generates a Markdown “Reconstruction Report” for each run  

---

## ⚙️ Installation & Setup
```bash

1️⃣ Clone the repository
git clone https://github.com/GeneralAumsum07/recon-hackathon.git
cd recon-hackathon

2️⃣ Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

3️⃣ Install dependencies
pip install -r requirements.txt

4️⃣ Create a .env file and add your API keys
GEMINI_API_KEY=your_gemini_api_key_here
SEARCH_API_KEY=your_google_cse_key_here
SEARCH_ENGINE_CX=your_search_engine_cx_here


🧠 How to Give an Input
Once the environment is set up, simply run the following command inside your virtual environment:

python3 main.py "your slang or informal sentence here"
📝 Example:

python3 main.py "ion even kno fr fr"
This will:

Send the input to Gemini for slang reconstruction

Search the web for relevant meanings and context

Save a detailed Markdown report in the recon_reports/ folder

💬 Sample Input & Output
Input
python3 main.py "smh at the top 8 drama. ppl need to chill. g2g, ttyl."
Terminal Output

1) Calling Gemini client...
-> Reconstructed text:
Shaking my head at the drama about the 'Top 8' friends list on MySpace. People need to calm down; I have to go — talk to you later.

2) Searching web for context...
-> Top sources:
- https://en.wikipedia.org/wiki/Myspace#Features | MySpace - Top 8 (feature)
- https://www.urbandictionary.com/define.php?term=smh | SMH - Urban Dictionary
- https://www.urbandictionary.com/define.php?term=g2g | G2G - Urban Dictionary

3) Rendering report...
Report saved to recon_reports/recon_20251018_170752.md
Generated Markdown Report
markdown
# Recon Report — 20251018_170752 UTC

## 🧩 Original Fragment
"smh at the top 8 drama. ppl need to chill. g2g, ttyl."

## ✨ Reconstructed Text
Shaking my head at the drama about the 'Top 8' friends list on MySpace. People need to calm down; I have to go — talk to you later.

## 💬 Explanations
- "smh" = shaking my head (disapproval)
- "ppl" = people
- "g2g" = got to go
- "ttyl" = talk to you later

## 🔑 Keywords
drama, myspace, slang, social context

## 🌐 Top Sources
- [MySpace - Top 8 (feature)](https://en.wikipedia.org/wiki/Myspace#Features)
- [SMH - Urban Dictionary](https://www.urbandictionary.com/define.php?term=smh)
- [G2G - Urban Dictionary](https://www.urbandictionary.com/define.php?term=g2g)

🎬 **Watch the video demonstration:**
# 📺 Demo video link:
https://drive.google.com/file/d/1DBpXuUT9fxARGX5webZ9GjwFUtcq2qf2/view?usp=sharing