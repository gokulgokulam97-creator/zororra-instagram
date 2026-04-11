#!/usr/bin/env python3
"""
Zororra Instagram Auto Poster
- Downloads real product image from Cloudinary
- Sends it to Gemini to create scenes around the real product
- Uploads final image to Cloudinary
- Posts to Instagram via Graph API
- Runs daily via GitHub Actions
"""

import os
import sys
import json
import random
import base64
import time
import hashlib
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
CLOUDINARY_CLOUD_NAME = os.environ["CLOUDINARY_CLOUD_NAME"]
CLOUDINARY_API_KEY = os.environ["CLOUDINARY_API_KEY"]
CLOUDINARY_API_SECRET = os.environ["CLOUDINARY_API_SECRET"]

# === REAL PRODUCT IMAGE URL ===
PRODUCT_IMAGE_URL = "https://res.cloudinary.com/dt3vzadez/image/upload/v1775866611/azmdnpf4qbqlcz1m0kay.png"

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
        "image_prompt": "Place this exact product (do NOT change anything about the product — keep the label, shape, colors, and all details exactly the same) into a serene morning scene: a stylish woman in her 30s sitting cross-legged on a soft white bed in golden morning light, holding this exact product bottle with a calm smile. Minimalist Scandinavian bedroom, warm tones, soft bokeh. Professional product photography style, 4K quality. The product must look exactly as provided — no modifications.",
        "caption_angle": "morning routine / starting the day calm",
    },
    {
        "style": "Lifestyle - After Workout",
        "image_prompt": "Place this exact product (do NOT change anything about the product — keep the label, shape, colors, and all details exactly the same) into a gym scene: an athletic man in his late 20s in a modern gym, relaxed after a workout, holding this exact product bottle. He looks calm and focused. Clean modern gym background with soft lighting. Professional fitness photography, cinematic lighting. The product must look exactly as provided.",
        "caption_angle": "post-workout recovery and stress relief",
    },
    {
        "style": "Educational - Science",
        "image_prompt": "Create a stunning, modern infographic-style image featuring this exact product (do NOT change anything about it). Place the product prominently on the right side. On the left, show a beautiful botanical illustration of the ashwagandha plant alongside a simple graph showing cortisol going down. Dark luxury background with gold and green accents. Premium health brand aesthetic. The product must look exactly as provided — no modifications.",
        "caption_angle": "the science behind KSM-66 ashwagandha and cortisol reduction",
    },
    {
        "style": "Lifestyle - Evening Wind Down",
        "image_prompt": "Place this exact product (do NOT change anything about it) into a cozy evening scene: the product bottle next to a cup of herbal tea on a marble side table. Warm ambient lighting, candles in the background, soft blanket texture visible. Luxury lifestyle photography, moody golden tones, shallow depth of field. The product must look exactly as provided.",
        "caption_angle": "evening self-care ritual and better sleep",
    },
    {
        "style": "Motivational - Mental Clarity",
        "image_prompt": "Place this exact product (do NOT change anything about it) into a workspace scene: a focused professional woman at a clean minimalist desk with a laptop, this exact product bottle placed elegantly beside her. She looks calm and in control. Soft natural window light, modern office aesthetic, warm neutral tones. Professional brand photography. The product must look exactly as provided.",
        "caption_angle": "mental clarity and focus during a busy workday",
    },
    {
        "style": "Product Hero - Dark Luxury",
        "image_prompt": "Place this exact product (do NOT change anything about it) as the hero on a black marble surface. Dramatic side lighting creating elegant shadows. Gold and emerald green accents. Scattered ashwagandha root pieces and green leaves artfully placed around the product. Ultra-luxury beauty brand aesthetic, 4K, cinematic. The product must look exactly as provided — no modifications to label, shape, or colors.",
        "caption_angle": "premium quality and natural ingredients",
    },
    {
        "style": "Lifestyle - Nature Connection",
        "image_prompt": "Place this exact product (do NOT change anything about it) into a nature scene: the product placed on a wooden surface near a person meditating outdoors in a lush green garden at sunrise. Dewy morning atmosphere, rays of golden light through trees. Earthy, natural wellness aesthetic. Professional lifestyle photography. The product must look exactly as provided.",
        "caption_angle": "connecting with nature and inner calm",
    },
    {
        "style": "Educational - Benefits List",
        "image_prompt": "Create a beautiful, modern graphic design layout featuring this exact product (do NOT change anything about it) in the center. Dark luxury background. Show 5 minimalist gold icons around the product representing: sleep, stress relief, focus, energy, calm. Gold and green color palette. Premium health brand aesthetic. Clean, editorial magazine style. The product must look exactly as provided.",
        "caption_angle": "5 key benefits of AshwaCalm+ for daily wellness",
    },
    {
        "style": "Social Proof - Testimonial",
        "image_prompt": "Place this exact product (do NOT change anything about it) into a lifestyle scene: a happy, relaxed couple in their 30s laughing together in a beautiful kitchen, this exact product bottle visible on the counter. Warm, natural lighting. They look genuinely content and stress-free. Modern lifestyle photography, candid feel. The product must look exactly as provided.",
        "caption_angle": "real results and transformation stories",
    },
    {
        "style": "Lifestyle - Travel Calm",
        "image_prompt": "Create a photorealistic flat-lay featuring this exact product (do NOT change anything about it) alongside travel essentials on a white marble surface: passport, sunglasses, a journal, and a boarding pass arranged around the product. Bright natural lighting from above, clean composition. Premium travel lifestyle aesthetic. The product must look exactly as provided.",
        "caption_angle": "staying calm and balanced while traveling",
    },
    {
        "style": "Problem-Solution",
        "image_prompt": "Create a split-image concept featuring this exact product (do NOT change anything about it): left side shows a stressed person in chaotic city environment with grey desaturated tones, right side shows the same person calm and smiling, holding this exact product, colors warm and golden. Dramatic before-after visual storytelling. The product must look exactly as provided.",
        "caption_angle": "from stressed to blessed — solving modern stress",
    },
    {
        "style": "Educational - Ingredient Spotlight",
        "image_prompt": "Place this exact product (do NOT change anything about it) in the background (slightly out of focus) behind a beautiful close-up arrangement of fresh ashwagandha roots and leaves on a dark slate surface. Droplets of water on the roots. Botanical photography style, rich earthy tones, macro detail. Premium natural supplement aesthetic. The product must look exactly as provided.",
        "caption_angle": "deep dive into KSM-66 — the gold standard of ashwagandha",
    },
    {
        "style": "Lifestyle - Self Care Sunday",
        "image_prompt": "Place this exact product (do NOT change anything about it) into a luxurious self-care overhead shot: bath with flower petals, candles, a silk robe, skincare products, and this exact product bottle artfully placed among them. Soft pink and gold tones, steam rising. Luxury wellness spa aesthetic, magazine-quality photography. The product must look exactly as provided.",
        "caption_angle": "self-care Sunday featuring AshwaCalm+",
    },
    {
        "style": "Bold Quote Card",
        "image_prompt": "Create a premium dark background with a powerful bold quote in elegant serif typography: 'Calm is a superpower'. Minimal gold line accents. Place this exact product (do NOT change anything about it) subtly in the bottom right corner. High-end brand poster aesthetic, clean and impactful. Magazine advertisement quality. The product must look exactly as provided.",
        "caption_angle": "inspirational message about the power of calm",
    },
]


def get_today_style():
    """Pick a style based on the day of year — cycles through all styles."""
    day_of_year = datetime.now().timetuple().tm_yday
    return POST_STYLES[day_of_year % len(POST_STYLES)]


def download_product_image():
    """Download the real product image from Cloudinary."""
    print(f"Downloading product image from: {PRODUCT_IMAGE_URL}")
    response = requests.get(PRODUCT_IMAGE_URL)
    response.raise_for_status()
    print(f"Product image downloaded: {len(response.content)} bytes")
    return response.content


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


def generate_image(style_info, product_image_bytes):
    """Use Gemini to generate a scene with the real product image."""
    client = genai.Client(api_key=GEMINI_API_KEY)

    # Detect image format
    img = Image.open(BytesIO(product_image_bytes))
    mime_type = "image/png" if img.format == "PNG" else "image/jpeg"

    # Send the real product image + prompt to Gemini
    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=[
            types.Part.from_bytes(data=product_image_bytes, mime_type=mime_type),
            types.Part.from_text(style_info["image_prompt"]),
        ],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
        ),
    )

    # Extract the generated image
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
    """Upload image to Cloudinary for a public URL."""
    timestamp = str(int(time.time()))
    signature_string = f"timestamp={timestamp}{CLOUDINARY_API_SECRET}"
    signature = hashlib.sha1(signature_string.encode()).hexdigest()

    files = {"file": ("post.jpg", BytesIO(image_bytes), "image/jpeg")}
    data = {
        "api_key": CLOUDINARY_API_KEY,
        "timestamp": timestamp,
        "signature": signature,
    }

    response = requests.post(
        f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/image/upload",
        files=files,
        data=data,
    )
    response.raise_for_status()
    return response.json()["secure_url"]


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

    # 2. Download real product image
    print("\nDownloading product image...")
    product_image = download_product_image()

    # 3. Generate caption
    print("\nGenerating caption with Gemini...")
    caption = generate_caption(style)
    print(f"Caption preview: {caption[:100]}...")

    # 4. Generate image using real product
    print("\nGenerating scene with real product using Gemini...")
    image_bytes = generate_image(style, product_image)
    print(f"Image generated: {len(image_bytes)} bytes")

    # 5. Upload final image to Cloudinary
    print("\nUploading image to Cloudinary...")
    image_url = upload_image_to_hosting(image_bytes)
    print(f"Image URL: {image_url}")

    # 6. Post to Instagram
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
