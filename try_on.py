from google import genai
from google.genai import types
from PIL import Image

from app.config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

prompt = (
    "Put this cloth on me"
)

image1 = Image.open("data/pinterest_images/summer_outfits/summer_outfits_018.jpg")
image2 = Image.open("data/pinterest_images/summer_outfits/summer_outfits_017.jpg")


response = client.models.generate_content(
    model="gemini-3.1-flash-image-preview",
    contents=[prompt, image1, image2],
)

for part in response.parts:
    if part.text is not None:
        print(part.text)
    elif part.inline_data is not None:
        image = part.as_image()
        image.save("generated_image.png")
