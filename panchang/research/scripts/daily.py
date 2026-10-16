#!/usr/bin/env python3
"""
Daily Panchang Generator
========================

Generates complete Panchang (Hindu almanac) for any given date in JSON format.

This script calculates:
- Tithi, Nakshatra, Yoga, Karana
- Rashi (Moon and Sun signs)
- Vikram Samvat year
- Sunrise and Sunset times
- Muhurta timings (Rahu Kal, Gulik Kal, etc.)
- Season (Ritu)

All calculations follow the Surya Siddhanta astronomical system.
"""

import json
from datetime import datetime, timedelta
from math import floor
from typing import Dict, Any, Optional, List

from surya_siddhanta.time.conversions import (
    gregorian_to_jdn,
    days_since_kali,
    datetime_to_ahargana,
)
from surya_siddhanta.time.eras import (
    kali_year_from_ahargana,
    kali_to_vikram_samvat,
    kali_to_nepal_sambat,
    kali_to_shalivahana_shaka,
)
from surya_siddhanta.calendar.calendar import (
    get_tithi,
    get_nakshatra,
    get_yoga,
    get_karana,
    get_paksha,
    get_season,
    get_sun_rashi,
    get_moon_rashi,
    get_lunar_month_name,
)
from surya_siddhanta.geometry.geodesy import get_day_length
from surya_siddhanta.geography.location import Location, get_location_by_name


# ============================================================================
# Tithi Names
# ============================================================================

TITHI_NAMES = [
    "Pratipad",
    "Dwitiya",
    "Tritiya",
    "Chaturthi",
    "Panchami",
    "Shashthi",
    "Saptami",
    "Ashtami",
    "Navami",
    "Dashami",
    "Ekadashi",
    "Dwadashi",
    "Trayodashi",
    "Chaturdashi",
    "Purnima",
]

TITHI_NAMES_KRISHNA = [
    "Pratipad",
    "Dwitiya",
    "Tritiya",
    "Chaturthi",
    "Panchami",
    "Shashthi",
    "Saptami",
    "Ashtami",
    "Navami",
    "Dashami",
    "Ekadashi",
    "Dwadashi",
    "Trayodashi",
    "Chaturdashi",
    "Amavasya",
]


def get_tithi_name(tithi_number: float) -> str:
    """Get name of Tithi from number (1-30)"""
    tithi_index = int(tithi_number) - 1
    if tithi_index < 15:
        # Shukla Paksha (1-15)
        return TITHI_NAMES[tithi_index]
    else:
        # Krishna Paksha (16-30)
        return TITHI_NAMES_KRISHNA[tithi_index - 15]


# ============================================================================
# Sunrise and Sunset Calculation
# ============================================================================


def calculate_sunrise_sunset(
    ahargana: float, latitude: float, longitude: float, timezone_offset: float = 5.5
) -> Dict[str, str]:
    """
    Calculate sunrise and sunset times for a location.

    Uses the day length from Surya Siddhanta and assumes sunrise
    is at 6 AM average, adjusted by half the difference from 12-hour day.

    Args:
        ahargana: Days since Kali Yuga epoch
        latitude: Latitude in degrees
        longitude: Longitude in degrees
        timezone_offset: Local timezone offset from UTC in hours

    Returns:
        Dictionary with 'sunrise' and 'sunset' times as "HH:MM" strings
    """
    from surya_siddhanta.celestial.sun import true_longitude_sun

    # Get Sun's longitude for the day
    sun_longitude = true_longitude_sun(ahargana)

    # Calculate day length in ghatis (1 ghati = 24 minutes)
    day_length_ghatis = get_day_length(sun_longitude, latitude)
    day_length_hours = day_length_ghatis * 24.0 / 60.0  # Convert to hours
    night_length_hours = 24.0 - day_length_hours

    # Sunrise is at half the night length after midnight
    sunrise_hour = night_length_hours / 2.0
    sunset_hour = sunrise_hour + day_length_hours

    # Format as HH:MM
    def format_time(hours: float) -> str:
        h = int(hours)
        m = int((hours - h) * 60)
        return f"{h:02d}:{m:02d}"

    return {
        "sunrise": format_time(sunrise_hour),
        "sunset": format_time(sunset_hour),
        "day_length_hours": day_length_hours,
    }


# ============================================================================
# Tithi End Time Calculation
# ============================================================================


def calculate_tithi_end_time(ahargana: float, timezone_offset: float = 5.5) -> str:
    """
    Calculate when the current Tithi ends.

    A Tithi is complete when the Moon advances 12° ahead of the Sun.
    We calculate the current tithi and estimate when it will end.

    Args:
        ahargana: Days since Kali Yuga epoch
        timezone_offset: Local timezone offset from UTC in hours

    Returns:
        Time string in "HH:MM" format
    """
    current_tithi = get_tithi(ahargana)
    tithi_fraction = current_tithi - floor(current_tithi)

    # Estimate time until next tithi (rough approximation)
    # Average tithi lasts about 0.98 days (23.5 hours)
    tithi_remaining = 1.0 - tithi_fraction
    hours_until_end = tithi_remaining * 23.5

    # Add to current time (assuming ahargana fractional part is the time)
    ahargana_fraction = ahargana - floor(ahargana)
    current_hour = ahargana_fraction * 24.0

    end_hour = (current_hour + hours_until_end) % 24.0

    h = int(end_hour)
    m = int((end_hour - h) * 60)
    return f"{h:02d}:{m:02d}"


# ============================================================================
# Nakshatra End Time Calculation
# ============================================================================


def calculate_nakshatra_end_time(ahargana: float, timezone_offset: float = 5.5) -> str:
    """
    Calculate when the current Nakshatra ends.

    Args:
        ahargana: Days since Kali Yuga epoch
        timezone_offset: Local timezone offset from UTC in hours

    Returns:
        Time string in "HH:MM" format
    """
    from surya_siddhanta.celestial.moon import true_longitude_moon

    current_nakshatra_num, _ = get_nakshatra(ahargana)
    moon_longitude = true_longitude_moon(ahargana)

    # Each nakshatra spans 13.333° (360/27)
    nakshatra_span = 360.0 / 27.0
    current_nakshatra_index = int(current_nakshatra_num) - 1
    nakshatra_end_longitude = (current_nakshatra_index + 1) * nakshatra_span

    # Calculate degrees remaining
    degrees_remaining = (nakshatra_end_longitude - moon_longitude) % 360
    if degrees_remaining > 180:
        degrees_remaining -= 360

    # Moon moves about 13.2° per day
    moon_daily_motion = 13.2
    days_until_end = degrees_remaining / moon_daily_motion
    hours_until_end = days_until_end * 24.0

    # Add to current time
    ahargana_fraction = ahargana - floor(ahargana)
    current_hour = ahargana_fraction * 24.0

    end_hour = (current_hour + hours_until_end) % 24.0

    h = int(end_hour)
    m = int((end_hour - h) * 60)
    return f"{h:02d}:{m:02d}"


# ============================================================================
# Muhurta Calculations
# ============================================================================


def calculate_muhurtas(sunrise_time: str, sunset_time: str) -> Dict[str, Any]:
    """
    Calculate inauspicious and auspicious muhurtas based on sunrise/sunset.

    Traditional calculations based on dividing the day into 8 parts.

    Args:
        sunrise_time: Sunrise time as "HH:MM"
        sunset_time: Sunset time as "HH:MM"

    Returns:
        Dictionary with various muhurta timings
    """
    # Parse times
    sunrise_h, sunrise_m = map(int, sunrise_time.split(":"))
    sunset_h, sunset_m = map(int, sunset_time.split(":"))

    sunrise_minutes = sunrise_h * 60 + sunrise_m
    sunset_minutes = sunset_h * 60 + sunset_m

    if sunset_minutes < sunrise_minutes:
        sunset_minutes += 24 * 60

    day_duration = sunset_minutes - sunrise_minutes

    # Divide day into 8 parts for various kals
    part_duration = day_duration // 8

    def format_muhurta(start_min: int, end_min: int) -> str:
        """Format muhurta time range"""
        start_h = (start_min // 60) % 24
        start_m = start_min % 60
        end_h = (end_min // 60) % 24
        end_m = end_min % 60
        return f"{start_h:02d}:{start_m:02d}-{end_h:02d}:{end_m:02d}"

    # Rahu Kal (inauspicious): Different for each day of week
    # For now, use a standard calculation (2nd part of day for most days)
    rahu_kal_start = sunrise_minutes + part_duration
    rahu_kal_end = rahu_kal_start + part_duration

    # Gulik Kal: 7th part of day
    gulik_kal_start = sunrise_minutes + (6 * part_duration)
    gulik_kal_end = gulik_kal_start + part_duration

    # Yamaganda: 4th part of day
    yamaganda_start = sunrise_minutes + (3 * part_duration)
    yamaganda_end = yamaganda_start + part_duration

    # Abhijit Muhurta (auspicious): Noon ± 24 minutes
    noon_minutes = (sunrise_minutes + sunset_minutes) // 2
    abhijit_start = noon_minutes - 24
    abhijit_end = noon_minutes + 24

    return {
        "rahu_kal": format_muhurta(rahu_kal_start, rahu_kal_end),
        "gulik_kal": format_muhurta(gulik_kal_start, gulik_kal_end),
        "yamaganda": format_muhurta(yamaganda_start, yamaganda_end),
        "abhijit_muhurta": format_muhurta(abhijit_start, abhijit_end),
    }


# ============================================================================
# Main Panchang Generation
# ============================================================================


def generate_panchang(
    date: Optional[datetime] = None,
    location: Optional[Location] = None,
    location_name: str = "delhi",
) -> Dict[str, Any]:
    """
    Generate complete Panchang for a given date and location.

    Args:
        date: Date to generate panchang for (defaults to today)
        location: Location object (if None, uses location_name)
        location_name: Name of location (defaults to "delhi")

    Returns:
        Dictionary with complete panchang data
    """
    # Default to today if no date provided
    if date is None:
        date = datetime.now()

    # Get location
    if location is None:
        location = get_location_by_name(location_name)

    # Calculate ahargana for the date at sunrise
    ahargana = datetime_to_ahargana(date, location=location)

    # Get day of week
    weekday = date.strftime("%A")

    # Get era years
    kali_year = kali_year_from_ahargana(ahargana)
    vikram_samvat_year = kali_to_vikram_samvat(kali_year)
    nepal_sambat_year = kali_to_nepal_sambat(kali_year)

    # Get Tithi
    tithi_number = get_tithi(ahargana)
    tithi_index = int(tithi_number) - 1
    tithi_name = get_tithi_name(tithi_number)
    tithi_end = calculate_tithi_end_time(ahargana, location.timezone_offset or 5.5)

    # Get Paksha and lunar month
    paksha = get_paksha(ahargana)
    lunar_month = get_lunar_month_name(ahargana)
    paksha_name = f"{lunar_month} {paksha} Paksha"

    # Get Nakshatra
    nakshatra_number, nakshatra_name = get_nakshatra(ahargana)
    nakshatra_end = calculate_nakshatra_end_time(
        ahargana, location.timezone_offset or 5.5
    )

    # Get Yoga
    yoga_number, yoga_name = get_yoga(ahargana)

    # Get Karana
    karana_number, karana_name = get_karana(ahargana)

    # Get Rashis
    sun_rashi_num, sun_rashi_name = get_sun_rashi(ahargana)
    moon_rashi_num, moon_rashi_name = get_moon_rashi(ahargana)

    # Get Season
    season = get_season(ahargana)

    # Calculate sunrise and sunset
    sun_times = calculate_sunrise_sunset(
        ahargana, location.latitude, location.longitude, location.timezone_offset or 5.5
    )

    # Calculate muhurtas
    muhurtas = calculate_muhurtas(sun_times["sunrise"], sun_times["sunset"])

    # Build panchang JSON
    panchang = {
        "date": {
            "gregorian": date.strftime("%Y-%m-%d"),
            "day": weekday,
            "vikram_samvat": {
                "year": vikram_samvat_year,
                "notes": "",  # Could add month name here
            },
            "nepal_sambat": {
                "year": nepal_sambat_year,
                "notes": "",
            },
        },
        "panchang": {
            "tithi": {"name": tithi_name, "paksha": paksha_name, "ends_at": tithi_end},
            "nakshatra": {"name": nakshatra_name, "ends_at": nakshatra_end},
            "chandra_rashi": moon_rashi_name,
            "surya_rashi": sun_rashi_name,
            "ritu": season,
            "yoga": yoga_name,
            "karana": [karana_name],
        },
        "solar": {"sunrise": sun_times["sunrise"], "sunset": sun_times["sunset"]},
        "kala_muhurtam": {
            "rahu_kal": muhurtas["rahu_kal"],
            "gulik_kal": muhurtas["gulik_kal"],
            "yamaganda": muhurtas["yamaganda"],
            "abhijit_muhurta": muhurtas["abhijit_muhurta"],
        },
        "location": {
            "name": location.name,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "timezone": location.timezone_name or "Asia/Kolkata",
        },
    }

    return panchang


# ============================================================================
# Command-Line Interface
# ============================================================================


def main():
    """Generate panchang for today and print as JSON"""
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate daily Panchang in JSON format"
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Date in YYYY-MM-DD format (default: today)",
        default=None,
    )
    parser.add_argument(
        "--location", type=str, help="Location name (default: delhi)", default="delhi"
    )
    parser.add_argument(
        "--pretty", action="store_true", help="Pretty print JSON output"
    )

    args = parser.parse_args()

    # Parse date if provided
    if args.date:
        try:
            date = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print(
                f"Error: Invalid date format '{args.date}'. Use YYYY-MM-DD",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        date = datetime.now()

    # Generate panchang
    try:
        panchang = generate_panchang(date, location_name=args.location)

        # Print as JSON
        if args.pretty:
            print(json.dumps(panchang, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(panchang, ensure_ascii=False))

    except Exception as e:
        print(f"Error generating panchang: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
