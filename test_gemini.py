from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client()

response = client.models.generate_content(
    model="gemini-3.8-flash",
    contents="In one short sentence, explain why agriculture is important to India's economy."
)

print(response.text)