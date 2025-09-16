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

# ✅ Poster/backdrop fetch helper
def get_poster_url(movie_id):
    try:
        url = f"{BASE_URL}/movie/{movie_id}/images?api_key={TMDB_API_KEY}&include_image_language=hi,en,null"
        resp = requests.get(url, timeout=10).json()
        backdrops = resp.get("backdrops", [])
        posters = resp.get("posters", [])

        # Hindi (priority)
        for b in backdrops:
            if b.get("iso_639_1") == "hi":
                print("✅ Poster selected: Hindi backdrop", file=sys.stderr)
                return f"https://media.themoviedb.org/t/p/w1000_and_h563_face{b['file_path']}"

        # Hindi + region IN
        for b in backdrops:
            if b.get("iso_639_1") == "hi" and b.get("iso_3166_1") == "IN":
                print("✅ Poster selected: Hindi+IN backdrop", file=sys.stderr)
                return f"https://media.themoviedb.org/t/p/w1000_and_h563_face{b['file_path']}"

        # English fallback
        for b in backdrops:
            if b.get("iso_639_1") == "en":
                print("✅ Poster selected: English backdrop", file=sys.stderr)
                return f"https://media.themoviedb.org/t/p/w1000_and_h563_face{b['file_path']}"

        # Poster fallback
        if posters:
            print("✅ Poster selected: TMDB poster", file=sys.stderr)
            return f"https://image.tmdb.org/t/p/original{posters[0]['file_path']}"

        # Any scene fallback
        if backdrops:
            print("⚠️ Poster fallback: random backdrop", file=sys.stderr)
            return f"https://media.themoviedb.org/t/p/w1000_and_h563_face{backdrops[0]['file_path']}"

        print("❌ No poster/backdrop found", file=sys.stderr)
        return None
    except Exception as e:
        print(f"❌ get_poster_url error: {e}", file=sys.stderr)
        return None


# ✅ Movie Info command
@Client.on_message(filters.command("movieinfo"))
async def movieinfo_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("❌ Usage: /movieinfo <movie name> [year]")
        return

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

    # ✅ Languages (from spoken_languages)
    spoken_langs = details.get("spoken_languages", [])
    langs = [LANG_MAP.get(l["iso_639_1"], l["english_name"]) for l in spoken_langs]
    languages = ", ".join(langs) if langs else "N/A"

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
