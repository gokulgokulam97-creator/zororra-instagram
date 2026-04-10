#!/usr/bin/env python3
"""
Zororra Instagram Auto Poster
- Generates caption + image using Google Gemini
- Posts to Instagram via Graph API
- Runs daily via GitHub Actions
"""

import os
import sys
import json
import random
import base64
import time
import requests
from datetime import datetime
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO

# === CONFIG ===
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
INSTAGRAM_ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
INSTAGRAM_USER_ID = os.environ["INSTAGRAM_USER_ID"]

# === PRODUCT INFO ===
PRODUCT = {
    "name": "AshwaCalm+ KSM-66",
    "type": "Premium Ashwagandha supplement",
    "key_ingredient": "KSM-66 Ashwagandha (full-spectrum root extract)",
    "benefits": [
        "Reduces stress and cortisol levels",
        "Improves sleep quality",
        "Enhances focus and mental clarity",
        "Supports natural energy without stimulants",
        "Promotes calm and relaxation",
        "Clinically studied KSM-66 formula",
    ],
    "brand": "Zororra",
    "website": "zororra.com",
    "tagline": "Nature's answer to modern stress",
}

# === POST STYLES — rotates daily for variety ===
POST_STYLES = [
    {
        "style": "Lifestyle - Calm Morning",
        "image_prompt": "A serene, photorealistic scene of a stylish woman in her 30s sitting cross-legged on a soft white bed in golden morning light, holding a premium dark supplement bottle with a calm smile. Minimalist Scandinavian bedroom, warm tones, soft bokeh. The bottle has a sleek matte black label. Professional product photography style, 4K quality.",
        "caption_angle": "morning routine / starting the day calm",
    },
    {
        "style": "Lifestyle - After Workout",
        "image_prompt": "A photorealistic image of an athletic man in his late 20s in a modern gym, relaxed after a workout, holding a premium dark supplement bottle. He looks calm and focused. Clean modern gym background with soft lighting, slight sweat glow. Professional fitness photography, cinematic lighting.",
        "caption_angle": "post-workout recovery and stress relief",
    },
    {
        "style": "Educational - Science",
        "image_prompt": "A stunning, modern infographic-style image about ashwagandha and cortisol reduction. Show a beautiful botanical illustration of the ashwagandha plant alongside a simple graph showing cortisol going down. Dark luxury background with gold and green accents. Clean typography space at the top. Premium health brand aesthetic.",
        "caption_angle": "the science behind KSM-66 ashwagandha and cortisol reduction",
    },
    {
        "style": "Lifestyle - Evening Wind Down",
        "image_prompt": "A photorealistic cozy evening scene: a woman's hand holding a premium dark supplement bottle next to a cup of herbal tea on a marble side table. Warm ambient lighting, candles in the background, soft blanket texture visible. Luxury lifestyle photography, moody golden tones, shallow depth of field.",
        "caption_angle": "evening self-care ritual and better sleep",
    },
    {
        "style": "Motivational - Mental Clarity",
        "image_prompt": "A photorealistic image of a focused professional woman at a clean minimalist desk with a laptop, a premium dark supplement bottle placed elegantly beside her. She looks calm and in control. Soft natural window light, modern office aesthetic, warm neutral tones. Professional brand photography.",
        "caption_angle": "mental clarity and focus during a busy workday",
    },
    {
        "style": "Product Hero - Dark Luxury",
        "image_prompt": "A stunning product photography shot of a premium dark matte supplement bottle on a black marble surface. Dramatic side lighting creating elegant shadows. Gold and emerald green accents. Scattered ashwagandha root pieces and green leaves artfully placed around the bottle. Ultra-luxury beauty brand aesthetic, 4K, cinematic.",
        "caption_angle": "premium quality and natural ingredients",
    },
    {
        "style": "Lifestyle - Nature Connection",
        "image_prompt": "A photorealistic scene of a person meditating outdoors in a lush green garden at sunrise, a premium dark supplement bottle placed on a wooden surface nearby. Dewy morning atmosphere, rays of golden light through trees. Earthy, natural wellness aesthetic. Professional lifestyle photography.",
        "caption_angle": "connecting with nature and inner calm",
    },
    {
        "style": "Educational - Benefits List",
        "image_prompt": "A beautiful, modern graphic design layout with a dark luxury background. Show 5 minimalist icons representing: sleep, stress, focus, energy, calm — arranged in a clean grid. Gold and green color palette. Premium health brand aesthetic. Space for text overlay at top and bottom. Clean, editorial magazine style.",
        "caption_angle": "5 key benefits of AshwaCalm+ for daily wellness",
    },
    {
        "style": "Social Proof - Testimonial",
        "image_prompt": "A photorealistic image of a happy, relaxed couple in their 30s laughing together in a beautiful kitchen, a premium dark supplement bottle visible on the counter. Warm, natural lighting. They look genuinely content and stress-free. Modern lifestyle photography, candid feel, warm tones.",
        "caption_angle": "real results and transformation stories",
    },
    {
        "style": "Lifestyle - Travel Calm",
        "image_prompt": "A photorealistic flat-lay of travel essentials on a white marble surface: passport, sunglasses, a premium dark supplement bottle, a journal, and a boarding pass. Bright natural lighting from above, clean composition. Premium travel lifestyle aesthetic, Instagram-worthy arrangement.",
        "caption_angle": "staying calm and balanced while traveling",
    },
    {
        "style": "Problem-Solution",
        "image_prompt": "A split-image concept: left side shows a stressed person in chaotic city environment with grey desaturated tones, right side shows the same scene but the person is calm, colors are warm and golden, holding a premium dark supplement bottle. Dramatic before-after visual storytelling. Professional photography.",
        "caption_angle": "from stressed to blessed — solving modern stress",
    },
    {
        "style": "Educational - Ingredient Spotlight",
        "image_prompt": "A photorealistic close-up of fresh ashwagandha roots and leaves arranged beautifully on a dark slate surface, with a premium dark supplement bottle in the background slightly out of focus. Droplets of water on the roots. Botanical photography style, rich earthy tones, macro detail. Premium natural supplement aesthetic.",
        "caption_angle": "deep dive into KSM-66 — the gold standard of ashwagandha",
    },
    {
        "style": "Lifestyle - Self Care Sunday",
        "image_prompt": "A photorealistic overhead shot of a luxurious self-care setup: bath with flower petals, candles, a silk robe, skincare products, and a premium dark supplement bottle artfully placed. Soft pink and gold tones, steam rising. Luxury wellness spa aesthetic, magazine-quality photography.",
        "caption_angle": "self-care Sunday featuring AshwaCalm+",
    },
    {
        "style": "Bold Quote Card",
        "image_prompt": "A premium dark background with a powerful bold quote in elegant serif typography: 'Calm is a superpower'. Minimal gold line accents. A small premium dark supplement bottle subtly placed in the bottom corner. High-end brand poster aesthetic, clean and impactful. Magazine advertisement quality.",
        "caption_angle": "inspirational message about the power of calm",
    },
]


def get_today_style():
    """Pick a style based on the day of year — cycles through all styles."""
    day_of_year = datetime.now().timetuple().tm_yday
    return POST_STYLES[day_of_year % len(POST_STYLES)]


def generate_caption(style_info):
    """Use Gemini to generate an Instagram caption."""
    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""You are a world-class social media copywriter for a premium wellness brand called Zororra.

Write an Instagram caption for their product: {PRODUCT['name']}
Product type: {PRODUCT['type']}
Key ingredient: {PRODUCT['key_ingredient']}
Benefits: {', '.join(PRODUCT['benefits'])}
Website: {PRODUCT['website']}

TODAY'S ANGLE: {style_info['caption_angle']}
TODAY'S STYLE: {style_info['style']}

RULES:
- Write 3-5 short, punchy paragraphs (use line breaks between them)
- Start with a HOOK that stops the scroll (question, bold statement, or relatable pain point)
- Include a clear call to action (visit website, link in bio, comment, share)
- Add 15-20 relevant hashtags at the end
- Use 2-3 emojis max, placed strategically (not every line)
- Tone: confident, warm, premium — NOT salesy or desperate
- Mention the product name naturally, not forced
- Make it feel authentic, like a real brand would post
- DO NOT use any markdown formatting (no *, no #, no bold)
- Just write the caption as plain text ready to paste into Instagram

Write ONLY the caption text. Nothing else."""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    return response.text.strip()


def generate_image(style_info):
    """Use Gemini to generate a product image."""
    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = style_info["image_prompt"]

    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
        ),
    )

    # Extract the image from the response
    for part in response.candidates[0].content.parts:
        if hasattr(part, "inline_data") and part.inline_data:
            image_data = part.inline_data.data
            image = Image.open(BytesIO(image_data))

            # Save as high-quality JPEG for Instagram (1080x1080)
            image = image.resize((1080, 1080), Image.LANCZOS)
            output = BytesIO()
            image.save(output, format="JPEG", quality=95)
            output.seek(0)
            return output.getvalue()

    raise Exception("No image was generated by Gemini")


def upload_image_to_hosting(image_bytes):
    """Upload image to Telegraph for a public URL (no API key needed)."""
    files = {"file": ("post.jpg", BytesIO(image_bytes), "image/jpeg")}
    response = requests.post("https://telegra.ph/upload", files=files)
    response.raise_for_status()

    result = response.json()
    if isinstance(result, list) and len(result) > 0 and "src" in result[0]:
        return "https://telegra.ph" + result[0]["src"]

    raise Exception(f"Image upload failed: {result}")


def post_to_instagram(image_url, caption):
    """Post to Instagram using the Graph API (2-step process)."""
    base_url = "https://graph.facebook.com/v21.0"

    # Step 1: Create media container
    print("Creating Instagram media container...")
    create_response = requests.post(
        f"{base_url}/{INSTAGRAM_USER_ID}/media",
        data={
            "image_url": image_url,
            "caption": caption,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        },
    )
    create_response.raise_for_status()
    creation_id = create_response.json()["id"]
    print(f"Container created: {creation_id}")

    # Step 2: Wait for processing then publish
    time.sleep(10)
    print("Publishing post...")
    publish_response = requests.post(
        f"{base_url}/{INSTAGRAM_USER_ID}/media_publish",
        data={
            "creation_id": creation_id,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        },
    )
    publish_response.raise_for_status()
    post_id = publish_response.json()["id"]
    print(f"Post published! ID: {post_id}")

    return post_id


def main():
    print("=" * 50)
    print("ZORORRA INSTAGRAM AUTO POSTER")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    # 1. Pick today's style
    style = get_today_style()
    print(f"\nToday's style: {style['style']}")
    print(f"Angle: {style['caption_angle']}")

    # 2. Generate caption
    print("\nGenerating caption with Gemini...")
    caption = generate_caption(style)
    print(f"Caption preview: {caption[:100]}...")

    # 3. Generate image
    print("\nGenerating image with Gemini...")
    image_bytes = generate_image(style)
    print(f"Image generated: {len(image_bytes)} bytes")

    # 4. Upload image to get public URL
    print("\nUploading image...")
    image_url = upload_image_to_hosting(image_bytes)
    print(f"Image URL: {image_url}")

    # 5. Post to Instagram
    print("\nPosting to Instagram...")
    post_id = post_to_instagram(image_url, caption)

    print("\n" + "=" * 50)
    print("SUCCESS! Post is live on Instagram!")
    print(f"Post ID: {post_id}")
    print(f"Style used: {style['style']}")
    print("=" * 50)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)
