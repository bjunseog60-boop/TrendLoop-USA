# TrendLoop USA - Project Architecture

## Overview
Automated fashion trend blog system. Full pipeline: trend analysis -> article generation -> image creation -> multilingual translation -> multi-platform distribution.

Site: https://trendloopusa.net
Server: Ubuntu EC2 (3.85.190.183)
GitHub: https://github.com/bjunseog60-boop/TrendLoop-USA

## Tech Stack
- **Language**: Python 3.12
- **AI Models**: Gemini 2.5 Pro (trend analysis + article), Imagen 3 (images), Gemini 2.5 Flash (scripts)
- **Google Cloud APIs**: Vision, Translation, TTS (Neural2), Analytics, Maps
- **Affiliate**: Amazon Associates (trendloop-20), ShopStyle, LTK
- **Distribution**: dlvr.it (Pinterest + Tumblr via RSS), direct posting
- **Scheduling**: cron (daily 9AM EST), monitoring every 5 min
- **Backup**: GitHub Actions daily backup workflow

## Directory Structure
```
TrendLoop-USA/
├── main.py                    # Orchestrator (STEP 1-7 pipeline)
├── config.py                  # Environment variables & settings
├── safety.py                  # Rate limiting, error tracking, backup
├── monitor.py                 # Server health check (CPU/MEM/DISK)
├── google_creds.json          # Google Cloud ADC credentials (DO NOT COMMIT)
├── .env                       # API keys (DO NOT COMMIT)
├── agents/
│   ├── analyst.py             # Agent A - Trend keyword extraction (Google Trends)
│   ├── writer.py              # Agent B - Blog post generator (Gemini Flash)
│   ├── vertex_agent.py        # Agent V - Premium pipeline (Gemini 2.5 Pro + Imagen 3)
│   ├── vision_agent.py        # Vision API - Fashion image analysis
│   ├── translation_agent.py   # Translation API - 7 languages auto-translate
│   ├── analytics_agent.py     # Analytics API - Intelligent topic scheduler
│   ├── maps_agent.py          # Maps API - Fashion store trend analysis
│   ├── affiliate_links.py     # Multi-platform affiliate links (Amazon/ShopStyle/LTK)
│   ├── tts_agent.py           # Agent H - Google Cloud TTS (Neural2 voice)
│   ├── amazon_shorts.py       # Amazon Shorts - ASIN-based scripts + images
│   ├── marketer.py            # Agent C - Twitter, Google Indexing, Sitemap
│   ├── pinterest.py           # Agent D - Pinterest posting
│   ├── reddit_bot.py          # Reddit auto-poster
│   ├── tumblr_bot.py          # Tumblr auto-poster
│   ├── index_builder.py       # Homepage index.html rebuilder
│   └── rss_builder.py         # RSS feed generator
├── docs/                      # Published HTML files (served by Nginx)
│   ├── index.html
│   ├── feed.xml
│   ├── robots.txt
│   ├── sitemap.xml
│   ├── images/                # Imagen 3 generated images
│   ├── audio/                 # TTS generated MP3 files
│   └── {lang}/               # Translated posts (es/, fr/, ja/, etc.)
├── data/                      # Analysis reports, shorts scripts
├── logs/                      # Cron logs, monitor logs
├── _backups/                  # Daily tar.gz backups
└── .github/workflows/
    └── backup.yml             # Daily GitHub backup workflow
```

## Main Pipeline (main.py)
```
STEP 1   - Analyst: Trend keyword extraction (Google Trends)
STEP 1.5 - Gemini 2.5 Pro: Deep trend analysis (6-category JSON)
STEP 2   - Writer: Blog post generation (HTML)
STEP 2.5 - Imagen 3: Featured image + Pinterest pin generation
STEP 2.7 - Vision API analysis + Multi-affiliate link injection
STEP 3   - Sitemap + Index + RSS rebuild
STEP 3.5 - Pinterest: Auto-pin
STEP 4   - Marketer: Twitter + Google Indexing
STEP 5   - Reddit + Tumblr: Auto-post
STEP 6   - Amazon Shorts: ASIN-based content
STEP 7   - Translation: 7 languages (es, fr, de, ja, ko, pt, zh-CN)
```

## Cron Jobs
```
*/5 * * * *  monitor.py          # Health check every 5 min
0 14 * * *   main.py             # Full pipeline daily 2PM UTC (9AM EST)
0 3 * * *    tar backup           # Daily docs/ backup
0 4 * * *    cleanup old backups  # Remove backups older than 30 days
```

## Environment Variables (.env)
- GEMINI_API_KEY - Google Gemini API key
- AMAZON_TAG - Amazon Associates tag (trendloop-20)
- GOOGLE_APPLICATION_CREDENTIALS - Path to google_creds.json
- GA4_PROPERTY_ID - Google Analytics 4 property (to be set)
- MAPS_API_KEY - Google Maps API key (to be set)
- SHOPSTYLE_PID - ShopStyle Collective partner ID (to be set)
- LTK_ID - LTK affiliate ID (to be set)
- MONITOR_WEBHOOK_URL - Slack/Discord webhook for alerts (to be set)
- X_BEARER_TOKEN, X_API_KEY, etc. - Twitter API (disabled, 00/mo)

## Important Rules
- NEVER commit .env, google_creds.json, gcloud-adc.json
- All API keys via environment variables only
- Max runtime: 600 seconds (safety timeout)
- Max consecutive errors: 3 (auto-stop)
- File deletion -> moved to _deleted_items/ (not actual delete)
- Auto backup before every pipeline run
- Google Cloud credits: ~1.8M KRW available until 2027-02
