from langchain_google_genai import ChatGoogleGenerativeAI

import os
import dotenv 

dotenv.load_dotenv()  # Load environment variables from .env file





def get_llm():
    """Return a configured chat model instance.

    Expects GOOGLE_API_KEY in environment.
    """
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0,)

