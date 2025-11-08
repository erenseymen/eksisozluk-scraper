#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YouTube transcript test script"""
import sys
import json
from eksisozluk_scraper import EksisozlukScraper

def test_youtube_url(url: str):
    """Test YouTube URL transcript fetching"""
    scraper = EksisozlukScraper()
    
    print(f"Testing URL: {url}", file=sys.stderr)
    print(f"Extracting video ID...", file=sys.stderr)
    video_id = scraper._extract_youtube_video_id(url)
    
    if not video_id:
        print("ERROR: Could not extract video ID", file=sys.stderr)
        return None
    
    print(f"Video ID: {video_id}", file=sys.stderr)
    print(f"Fetching transcript...", file=sys.stderr)
    
    # Test transcript fetching
    transcript = scraper._fetch_youtube_transcript(video_id)
    
    if transcript:
        print(f"SUCCESS: Transcript fetched ({len(transcript)} characters)", file=sys.stderr)
    else:
        print("WARNING: Transcript not available", file=sys.stderr)
    
    # Test full URL content fetching
    print(f"Fetching full URL content...", file=sys.stderr)
    result = scraper._fetch_url_content(url)
    
    if result:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return result
    else:
        print("ERROR: Could not fetch URL content", file=sys.stderr)
        return None

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 test_youtube.py <youtube_url>", file=sys.stderr)
        sys.exit(1)
    
    url = sys.argv[1]
    result = test_youtube_url(url)
    sys.exit(0 if result else 1)

