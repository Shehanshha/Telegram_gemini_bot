import google.generativeai as genai
from config import Config
import logging

logger = logging.getLogger(__name__)

class GeminiHelper:
    def __init__(self):
        try:
            genai.configure(api_key=Config.GEMINI_API_KEY)
            self.text_model = genai.GenerativeModel('gemini-pro')
            self.vision_model = genai.GenerativeModel('gemini-pro-vision')
        except Exception as e:
            logger.error(f"Gemini initialization failed: {str(e)}")
            raise

    def generate_text(self, prompt):
        try:
            response = self.text_model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Text generation error: {str(e)}")
            return f"⚠️ Error generating response: {str(e)}"

    def analyze_image(self, image_bytes, prompt="Describe this image in detail"):
        try:
            response = self.vision_model.generate_content(
                [
                    prompt,
                    {
                        "mime_type": "image/png",  # or "image/jpeg" based on input
                        "data": image_bytes  # Now receiving bytes
                    }
                ]
            )
            return response.text
        except Exception as e:
            logger.error(f"Image analysis error: {str(e)}")
            return f"⚠️ Image processing failed: {str(e)}"