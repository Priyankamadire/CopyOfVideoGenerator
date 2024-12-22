from openai import OpenAI
import os
import edge_tts
import json
import asyncio
import whisper_timestamped as whisper
from utility.script.script_generator import generate_script
from utility.audio.audio_generator import generate_audio
from utility.captions.timed_captions_generator import generate_timed_captions
from utility.video.background_video_generator import generate_video_url
from utility.render.render_engine import get_output_media
from utility.video.video_search_query_generator import getVideoSearchQueriesTimed, merge_empty_intervals
from bs4 import BeautifulSoup
import requests
import argparse

# Function to scrape article text from a URL
def scrape_article(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    
    # Extract paragraphs but exclude irrelevant sections (e.g., ads, navigation)
    paragraphs = soup.find_all("p")
    article_text = " ".join([p.get_text() for p in paragraphs if p.get_text()])
    
    # Clean up the text by removing unwanted characters (optional, but useful)
    article_text = article_text.replace("\n", " ").strip()
    return article_text

# Modify generate_video_url to handle unpacking of more than 2 values in timed_video_searches
def generate_video_url(timed_video_searches, video_server):
    # Assuming timed_video_searches contains 3 elements: ((t1, t2), search_terms, extra_info)
    background_video_urls = []
    for (t1, t2), search_terms, _ in timed_video_searches:
        # Example logic: generate video URLs based on search_terms (adjust this based on your use case)
        video_url = f"{video_server}/search?q={search_terms}"  # Example URL generation
        background_video_urls.append(video_url)
    return background_video_urls

# Modify generate_script to summarize the article text and focus on relevant points
def generate_script(article_text):
    prompt = f"Summarize the following article and focus on the key events such as layoffs, restructuring, and changes introduced by the company. Provide the most relevant details.\n\n{article_text}"
    response = openai.Completion.create(
        engine="text-davinci-003",  # Or use any other model you prefer
        prompt=prompt,
        max_tokens=200,  # Adjust length based on needs
        temperature=0.5  # Lower temperature to focus on accuracy
    )
    return response.choices[0].text.strip()

if __name__ == "__main__":
    # Modify the argument to accept URL
    parser = argparse.ArgumentParser(description="Generate a video from an article URL.")
    parser.add_argument("url", type=str, help="The URL of the article")

    args = parser.parse_args()
    ARTICLE_URL = args.url  # Now takes URL
    SAMPLE_FILE_NAME = "audio_tts.wav"
    VIDEO_SERVER = "pexel"

    # Step 1: Scrape the article text
    article_text = scrape_article(ARTICLE_URL)
    print("Article text extracted.")

    # Step 2: Use the article text to generate a focused script
    response = generate_script(article_text)
    print("Script generated:\n", response)

    # Step 3: Use the script to generate audio
    asyncio.run(generate_audio(response, SAMPLE_FILE_NAME))

    # Step 4: Generate timed captions from the audio
    timed_captions = generate_timed_captions(SAMPLE_FILE_NAME)
    print("Timed captions generated:\n", timed_captions)

    # Step 5: Generate search terms for video
    search_terms = getVideoSearchQueriesTimed(response, timed_captions)
    print("Search terms generated:\n", search_terms)

    # Step 6: Generate background video URLs
    background_video_urls = None
    if search_terms is not None:
        background_video_urls = generate_video_url(search_terms, VIDEO_SERVER)
        print("Background video URLs generated:\n", background_video_urls)
    else:
        print("No background video found.")

    # Step 7: Merge empty intervals if necessary
    background_video_urls = merge_empty_intervals(background_video_urls)

    # Step 8: Generate final video with audio, captions, and background video
    if background_video_urls is not None:
        video = get_output_media(SAMPLE_FILE_NAME, timed_captions, background_video_urls, VIDEO_SERVER)
        print("Video generated:", video)
    else:
        print("No video generated.")
