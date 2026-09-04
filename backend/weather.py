import asyncio
import math
import time
import httpx
from fastapi import HTTPException

LAT, LON = 28.09, -16.74
TZ = "Atlantic/Canary"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
CACHE_TTL = 1800
_cache: dict[str, tuple[float, dict]] = {}

COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO"]

SPOT_ADDRESS = {
    "Playa del Duque / Fañabé": "Playa de Fañabé — parking Avenida de Bruselas, Costa Adeje (van Canary Foil Club côté nord de la plage)",
    "La Caleta / Playa Paraíso": "La Caleta — parking du front de mer, Calle La Caleta, Adeje (van sur la cale de mise à l'eau)",
    "El Puertito de Adeje": "El Puertito de Adeje — parking en haut de la cale, Armeñime (van au bord de la crique)",
    "Puerto Colón (bassin abrité)": "Puerto Colón — rampe de mise à l'eau côté Playa La Pinta, Costa Adeje",
}


def conditions_label(summary: dict, lang: str = "fr") -> str:
    w, g, wave, d = summary.get("wind_avg"), summary.get("gust_max"), summary.get("wave_avg"), summary.get("wind_dir_label")
    if w is None:
        return ""
    if lang == "en":
        return f"Wind {w} km/h {d or ''} (gusts {g}), swell {wave} m".strip()
    if lang == "es":
        return f"Viento {w} km/h {d or ''} (rachas {g}), oleaje {wave} m".strip()
    return f"Vent {w} km/h {d or ''} (rafales {g}), houle {wave} m".strip()


def compass(deg):
    return None if deg is None else COMPASS[int((deg + 11.25) // 22.5) % 16]


def circular_mean(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    x = sum(math.sin(math.radians(v)) for v in vals)
    y = sum(math.cos(math.radians(v)) for v in vals)
    return round((math.degrees(math.atan2(x, y)) + 360) % 360)


def _max(values):
    vals = [v for v in values if v is not None]
    return round(max(vals), 1) if vals else None


def _avg(values):
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 1) if vals else None


async def _fetch(client, url, params):
    try:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        if data.get("error"):
            raise HTTPException(502, data.get("reason", "Open-Meteo error"))
        return data
    except httpx.TimeoutException:
        raise HTTPException(504, "Météo indisponible (timeout)")
    except httpx.HTTPStatusError as e:
        raise HTTPException(502, f"Météo indisponible (HTTP {e.response.status_code})")
    except ValueError:
        raise HTTPException(502, "Météo indisponible (réponse invalide)")


def recommend_spot(wind_kmh, gust_kmh, wind_dir, wave_m):
    if wind_kmh is None or wave_m is None:
        return {"level": "unknown", "spot": "—", "reason": "Prévisions indisponibles pour cette date."}
    if wave_m > 1.3 or (gust_kmh or 0) > 45 or wind_kmh > 32:
        return {"level": "nogo", "spot": "Puerto Colón (bassin abrité)", "reason": "Houle ou vent trop forts pour un vol confortable — session à reporter ou bassin abrité uniquement."}
    d = compass(wind_dir) or ""
    if d.startswith("N") or d.startswith("E") or d == "ENE":
        spot, why = "Playa del Duque / Fañabé", "Alizés de N-NE : la côte sud-ouest est sous le vent, plan d'eau lisse."
    elif d.startswith("S") or d.startswith("SO") or d == "OSO":
        spot, why = "La Caleta / Playa Paraíso", "Vent de secteur sud-ouest : criques nord de la baie abritées."
    else:
        spot, why = "El Puertito de Adeje", "Vent d'ouest : le Puertito reste protégé par la pointe."
    if wave_m <= 0.5 and wind_kmh <= 15:
        return {"level": "ideal", "spot": spot, "reason": f"Conditions idéales. {why}"}
    if wave_m <= 0.9 and wind_kmh <= 24:
        return {"level": "good", "spot": spot, "reason": f"Bonnes conditions. {why}"}
    return {"level": "caution", "spot": spot, "reason": f"Conditions limites : privilégier les créneaux du matin. {why}"}


async def get_weather(day: str) -> dict:
    from datetime import date, timedelta
    d, today = date.fromisoformat(day), date.today()
    if d > today + timedelta(days=15):
        raise HTTPException(400, "Prévisions disponibles jusqu'à 15 jours à l'avance")
    if d < today - timedelta(days=60):
        raise HTTPException(400, "Historique météo limité aux 60 derniers jours")
    hit = _cache.get(day)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return {**hit[1], "cached": True}
    common = {"latitude": LAT, "longitude": LON, "start_date": day, "end_date": day, "timezone": TZ}
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
        wind, waves = await asyncio.gather(
            _fetch(client, FORECAST_URL, {**common, "hourly": "wind_speed_10m,wind_direction_10m,wind_gusts_10m,temperature_2m,weather_code", "wind_speed_unit": "kmh"}),
            _fetch(client, MARINE_URL, {**common, "hourly": "wave_height,wave_period,wave_direction"}),
        )
    wh, mh = wind["hourly"], waves["hourly"]
    hourly = []
    for i, t in enumerate(wh["time"]):
        hour = int(t[11:13])
        if hour < 8 or hour > 20:
            continue
        get = lambda arr: arr[i] if i < len(arr) else None
        hourly.append({
            "time": t[11:16],
            "wind": get(wh["wind_speed_10m"]),
            "gust": get(wh["wind_gusts_10m"]),
            "wind_dir": get(wh["wind_direction_10m"]),
            "temp": get(wh["temperature_2m"]),
            "wave": get(mh["wave_height"]),
            "period": get(mh["wave_period"]),
            "wave_dir": get(mh["wave_direction"]),
        })
    wind_avg = _avg([h["wind"] for h in hourly])
    gust_max = _max([h["gust"] for h in hourly])
    wind_dir = circular_mean([h["wind_dir"] for h in hourly])
    wave_max = _max([h["wave"] for h in hourly])
    wave_dir = circular_mean([h["wave_dir"] for h in hourly])
    result = {
        "date": day,
        "summary": {
            "wind_avg": wind_avg,
            "wind_max": _max([h["wind"] for h in hourly]),
            "gust_max": gust_max,
            "wind_dir": wind_dir,
            "wind_dir_label": compass(wind_dir),
            "wave_avg": _avg([h["wave"] for h in hourly]),
            "wave_max": wave_max,
            "period_avg": _avg([h["period"] for h in hourly]),
            "wave_dir": wave_dir,
            "wave_dir_label": compass(wave_dir),
            "temp_max": _max([h["temp"] for h in hourly]),
        },
        "spot": recommend_spot(wind_avg, gust_max, wind_dir, wave_max),
        "hourly": hourly,
        "source": "Weather data by Open-Meteo.com",
        "cached": False,
    }
    _cache[day] = (time.time(), result)
    return result
