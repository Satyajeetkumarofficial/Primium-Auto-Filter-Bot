import sys
import requests
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from info import TMDB_API_KEY

BASE_URL = "https://api.themoviedb.org/3"

print("✅ movieinfo plugin imported", file=sys.stderr)

# 🌐 Language map
LANG_MAP = {
    "hi": "Hindi", "te": "Telugu", "ta": "Tamil", "ml": "Malayalam", "kn": "Kannada",
    "en": "English", "bn": "Bengali", "mr": "Marathi", "gu": "Gujarati",
    "pa": "Punjabi", "or": "Odia", "as": "Assamese", "ur": "Urdu"
}

# 🔹 Helper: Select best landscape (16:9) backdrop
def get_landscape_url(images, lang=None, region=None):
    for img in images:
        if (not lang or img.get("iso_639_1") == lang) and (not region or img.get("iso_3166_1") == region):
            w, h = img.get("width", 0), img.get("height", 0)
            if w and h and abs(w / h - 16/9) < 0.15:  # ~16:9 ratio check
                return f"https://image.tmdb.org/t/p/original{img['file_path']}"
    return None

# 🔹 Poster/Backdrop fetch
def get_poster_url(movie_id):
    try:
        url = f"{BASE_URL}/movie/{movie_id}/images?api_key={TMDB_API_KEY}"
        resp = requests.get(url, timeout=10).json()
        backdrops = resp.get("backdrops", [])
        posters = resp.get("posters", [])

        return (
            get_landscape_url(backdrops, "hi") or
            get_landscape_url(backdrops, "hi", "IN") or
            get_landscape_url(backdrops, "en") or
            get_landscape_url(backdrops) or
            (f"https://image.tmdb.org/t/p/original{posters[0]['file_path']}" if posters else None)
        )
    except Exception as e:
        print(f"❌ get_poster_url error: {e}", file=sys.stderr)
        return None


# ✅ Movie Info command
@Client.on_message(filters.command("movieinfo"))
async def movieinfo_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("❌ Usage: /movieinfo movie name [year]")
        return

    # Name + optional year
    if message.command[-1].isdigit() and len(message.command[-1]) == 4:
        year = message.command[-1]
        name = " ".join(message.command[1:-1])
    else:
        year = None
        name = " ".join(message.command[1:])

    print(f"🔎 Searching movieinfo for: {name} ({year})", file=sys.stderr)

    # 🔎 Search movie
    search_url = f"{BASE_URL}/search/movie?api_key={TMDB_API_KEY}&query={name}"
    if year:
        search_url += f"&year={year}"

    resp = requests.get(search_url, timeout=10).json()
    results = resp.get("results", [])
    if not results:
        await message.reply_text(f"❌ No results found for {name} ({year or ''})")
        return

    movie = results[0]
    movie_id = movie["id"]

    # 🔹 Details
    details_url = f"{BASE_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}&language=en-US"
    details = requests.get(details_url, timeout=10).json()

    # 🔹 Credits
    credits_url = f"{BASE_URL}/movie/{movie_id}/credits?api_key={TMDB_API_KEY}&language=en-US"
    credits = requests.get(credits_url, timeout=10).json()
    cast = credits.get("cast", [])
    crew = credits.get("crew", [])

    top_actors = ", ".join([actor["name"] for actor in cast[:10]]) or "N/A"
    directors = [m["name"] for m in crew if m.get("job") == "Director"]
    director_names = ", ".join(directors) if directors else "N/A"

    title = details.get("title")
    release_date = details.get("release_date", "N/A")
    year = release_date.split("-")[0] if release_date else "N/A"
    overview = details.get("overview", "No description available.")
    genres = ", ".join([g["name"] for g in details.get("genres", [])]) or "N/A"
    runtime = details.get("runtime", "N/A")

    # ✅ Languages (release_dates se actual theatre releases)
    rel_url = f"{BASE_URL}/movie/{movie_id}/release_dates?api_key={TMDB_API_KEY}"
    rel_resp = requests.get(rel_url, timeout=10).json()
    results = rel_resp.get("results", [])

    langs = []
    for r in results:
        iso = r.get("iso_3166_1")
        releases = r.get("release_dates", [])
        for rel in releases:
            if rel.get("type") == 3:  # Theatrical
                lang_code = rel.get("iso_639_1") or details.get("original_language")
                lang_name = LANG_MAP.get(lang_code, lang_code.upper())
                if lang_name not in langs:
                    langs.append(lang_name)

    languages = ", ".join(langs) if langs else LANG_MAP.get(details.get("original_language"), "N/A")

    poster_url = get_poster_url(movie_id)

    caption = (
        f"🎬 <b>{title}</b> ({year})\n\n"
        f"<b>🗓 Release Date:</b> <code>{release_date}</code>\n"
        f"<b>⏱ Runtime:</b> <code>{runtime} min</code>\n"
        f"<b>🌐 Languages:</b> <code>{languages}</code>\n"
        f"<b>🎭 Genres:</b> <code>{genres}</code>\n"
        f"<b>🎬 Director:</b> <code>{director_names}</code>\n"
        f"<b>⭐ Cast:</b> <code>{top_actors}</code>\n\n"
        f"📝 <code>{overview}</code>\n\n"
        f"Powered By : @ProBotXUpdate"
    )

    try:
        if poster_url:
            await message.reply_photo(poster_url, caption=caption, parse_mode=ParseMode.HTML)
        else:
            await message.reply_text(caption, parse_mode=ParseMode.HTML)
        print(f"✅ Movieinfo sent for {title} ({year})", file=sys.stderr)
    except Exception as e:
        print(f"❌ Failed to send movieinfo: {e}", file=sys.stderr)
        await message.reply_text(f"❌ Error: {e}")
