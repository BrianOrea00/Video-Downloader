# url_validator.py
import re
from urllib.parse import urlparse, parse_qs, urlunparse


def is_youtube_url(url: str) -> bool:
    """Check if URL is a valid YouTube URL."""
    if not url:
        return False
    patterns = [
        r'^https?://(www\.)?youtube\.com/watch\?v=[\w-]+',
        r'^https?://(www\.)?youtube\.com/shorts/[\w-]+',
        r'^https?://(www\.)?youtube\.com/embed/[\w-]+',
        r'^https?://youtu\.be/[\w-]+',
        r'^https?://(www\.)?youtube\.com/playlist\?list=[\w-]+',
        r'^https?://(www\.)?youtube\.com/live/[\w-]+',
    ]
    return any(re.match(pattern, url) for pattern in patterns)


def is_supported_url(url: str) -> bool:
    """Check if URL is supported by yt-dlp."""
    if is_youtube_url(url):
        return True
    supported_domains = [
        'vimeo.com', 'dailymotion.com', 'twitch.tv',
        'facebook.com', 'instagram.com', 'twitter.com',
        'tiktok.com', 'reddit.com', 'bilibili.com',
        'soundcloud.com', 'bandcamp.com', 'mixcloud.com'
    ]
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    return any(site in domain for site in supported_domains)


def sanitize_url(url: str) -> str:
    """Remove tracking parameters from URL."""
    parsed = urlparse(url)
    tracking_params = {'si', 'feature', 'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content'}
    query_params = parse_qs(parsed.query)
    cleaned_params = {k: v for k, v in query_params.items() if k not in tracking_params}
    new_query = '&'.join(f"{k}={v[0]}" for k, v in cleaned_params.items())
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))


def validate_url(url: str) -> dict:
    """Validate URL and return result with details."""
    result = {
        'valid': False,
        'supported': False,
        'youtube': False,
        'sanitized': url,
        'error': None
    }
    if not url or not url.strip():
        result['error'] = 'URL is empty'
        return result

    result['sanitized'] = sanitize_url(url)
    result['youtube'] = is_youtube_url(result['sanitized'])
    result['supported'] = is_supported_url(result['sanitized'])
    result['valid'] = result['youtube'] or result['supported']

    if not result['valid']:
        result['error'] = 'Unsupported URL. Please enter a valid video URL.'

    return result


