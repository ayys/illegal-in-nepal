"""
Surya-Siddhanta Calendar
========================

Implements Panchanga elements: Tithi, Nakshatra, Yoga, Karana.
[Ch. XIV] The five limbs (Panchangas) of the Vedic calendar system.
"""

from typing import Tuple
from ..celestial.sun import true_longitude_sun
from ..celestial.moon import true_longitude_moon
from ..celestial.planets import true_longitude_planet
from ..celestial.mean_motions import Body
from ..core.utils import normalize_angle
from typing import Dict, Tuple


def get_tithi(ahargana: float) -> float:
    """
    Calculate the Tithi (Lunar Day).

    [Ch. XIV, v.12] A Tithi is defined as 12° of angular separation between
    the Moon and Sun. There are 30 Tithis in a lunar month.

    Formula: Tithi = (Moon longitude - Sun longitude) / 12°

    Tithi classification:
    - 1-15: Shukla Paksha (Waxing Moon)
    - 16-30: Krishna Paksha (Waning Moon)
    - Tithi 15: Purnima (Full Moon)
    - Tithi 30/1: Amavasya (New Moon)

    Args:
        ahargana: Days since Kali Yuga epoch

    Returns:
        Tithi value (1-30)
    """
    l_sun = true_longitude_sun(ahargana)
    l_moon = true_longitude_moon(ahargana)

    # [Ch. XIV, v.12] Calculate angular separation
    diff = normalize_angle(l_moon - l_sun)
    tithi_index = diff / 12.0

    return tithi_index + 1.0  # 1-based index (e.g. 0-12° is Tithi 1)


def get_nakshatra(ahargana: float) -> Tuple[float, str]:
    """
    Calculate the Nakshatra (Lunar Mansion) of the Moon.

    [Ch. XIV, v.15] The ecliptic is divided into 27 Nakshatras,
    each spanning 13° 20' (13.333°). The Moon's Nakshatra indicates
    which lunar mansion it occupies.

    Formula: Nakshatra = Moon longitude / 13.333°

    The 27 Nakshatras represent the Moon's daily motion through fixed
    star groups, completing one cycle in approximately 27.3 days.

    Args:
        ahargana: Days since Kali Yuga epoch

    Returns:
        Nakshatra value (1-27)
    """
    l_moon = true_longitude_moon(ahargana)

    # [Ch. XIV, v.15] Each Nakshatra spans 360° / 27 = 13.333°
    nakshatra_span = 360.0 / 27.0

    nakshatra_names = [
        "Ashvini",
        "Bharani",
        "Krittika",
        "Rohini",
        "Mrigashira",
        "Ardra",
        "Punarvasu",
        "Pushya",
        "Ashlesha",
        "Magha",
        "Purva Phalguni",
        "Uttara Phalguni",
        "Hasta",
        "Chitra",
        "Svati",
        "Vishakha",
        "Anuradha",
        "Jyeshtha",
        "Mula",
        "Purva Ashadha",
        "Uttara Ashadha",
        "Shravana",
        "Dhanishtha",
        "Shatabhisha",
        "Purva Bhadrapada",
        "Uttara Bhadrapada",
        "Revati",
    ]

    index = int(l_moon / nakshatra_span)
    nakshatra_name = nakshatra_names[index]

    return index + 1.0, nakshatra_name


def get_yoga(ahargana: float) -> Tuple[float, str]:
    """
    Calculate the Yoga.

    [Ch. XIV] Yoga is calculated from the sum of Sun and Moon longitudes,
    divided into 27 divisions like Nakshatras.

    Formula: Yoga = (Sun longitude + Moon longitude) / 13.333°

    The 27 Yogas represent auspicious and inauspicious combinations
    of the Sun and Moon positions.

    Args:
        ahargana: Days since Kali Yuga epoch

    Returns:
        Yoga value (1-27)
    """
    l_sun = true_longitude_sun(ahargana)
    l_moon = true_longitude_moon(ahargana)

    # [Ch. XIV] Sum of solar and lunar longitudes
    total = normalize_angle(l_sun + l_moon)
    yoga_span = 360.0 / 27.0

    yoga_names = [
        "Vishkambha",
        "Priti",
        "Ayushman",
        "Saubhagya",
        "Shobhana",
        "Atiganda",
        "Sukarman",
        "Dhriti",
        "Shula",
        "Ganda",
        "Vriddhi",
        "Dhruva",
        "Vyaghata",
        "Harshana",
        "Vajra",
        "Siddhi",
        "Vyatipata",
        "Variyana",
        "Parigha",
        "Shiva",
        "Siddha",
        "Sadhya",
        "Shubha",
        "Shukla",
        "Brahma",
        "Indra",
        "Vaidhriti",
    ]

    index = int(total / yoga_span)
    yoga_name = yoga_names[index]

    return index + 1.0, yoga_name


def get_karana(ahargana: float) -> Tuple[int, str]:
    """
    Calculate the Karana (half-tithi).

    [Ch. XIV, v.67] Each Tithi (lunar day) is divided into two halves called
    Karana. Each Karana spans 6° of separation between Moon and Sun.

    Formula: Karana = (Moon longitude - Sun longitude) / 6°

    There are 11 Karanas that repeat cyclically:
    - 4 fixed (Sthira): Shakuni, Chatushpada, Naga, Kimstughna
    - 7 movable (Chara): Bava, Balava, Kaulava, Taitila, Gara, Vanija, Vishti

    Args:
        ahargana: Days since Kali Yuga epoch

    Returns:
        Tuple of (karana_index, karana_name)
    """
    l_sun = true_longitude_sun(ahargana)
    l_moon = true_longitude_moon(ahargana)

    # [Ch. XIV, v.67] Karana is half-tithi: 6° of separation
    diff = normalize_angle(l_moon - l_sun)
    karana_index_float = diff / 6.0

    # Karana index from 0 to 59
    karana_of_60 = int(karana_index_float) % 60

    # There are 11 Karanas in total
    karana_names = [
        "Kimstughna",  # Fixed, occurs only once at the beginning
        "Bava",  # Movable
        "Balava",  # Movable
        "Kaulava",  # Movable
        "Taitila",  # Movable
        "Gara",  # Movable
        "Vanija",  # Movable
        "Vishti",  # Movable
        "Shakuni",  # Fixed
        "Chatushpada",  # Fixed
        "Naga",  # Fixed
    ]

    # The first Karana (Kimstughna) happens once.
    # From the 2nd half of the 1st tithi, the 7 movable karanas repeat 8 times.
    # The last 3 karanas are fixed.

    karana_num = (karana_of_60 + 59) % 60  # Shift to start from Kimstughna

    if karana_num == 0:
        karana_name = karana_names[0]
    elif karana_num >= 57:
        karana_name = karana_names[karana_num - 57 + 8]
    else:
        karana_name = karana_names[(karana_num - 1) % 7 + 1]

    return karana_of_60 + 1, karana_name


def get_solar_month_sign(ahargana: float) -> int:
    """
    Get the Solar Month (Rasi) based on Sun's position.

    [Ch. XIV, v.16] The solar month is determined by which zodiac sign
    (30° division) the Sun occupies. Returns 1-12 corresponding to:
    1=Aries, 2=Taurus, ..., 12=Pisces.

    Args:
        ahargana: Days since Kali Yuga epoch

    Returns:
        Solar month number (1-12)
    """
    l_sun = true_longitude_sun(ahargana)
    return int(l_sun / 30.0) + 1


def get_solar_month_name(ahargana: float) -> str:
    """
    Get the name of the solar month.

    [Ch. XIV, v.16] Each solar month is named according to the Nakshatra
    where the full moon occurs. The month begins when the Sun enters
    a new zodiac sign.

    Args:
        ahargana: Days since Kali Yuga epoch

    Returns:
        Solar month name with lunar equivalent
    """
    solar_month_idx = get_solar_month_sign(ahargana)

    # [Ch. XIV, v.16] Solar month names with lunar month equivalents
    month_names = [
        "Mesha (Caitra)",  # Aries (Mar-Apr)
        "Vrishabha (Vaishakha)",  # Taurus (Apr-May)
        "Mithuna (Jyeshtha)",  # Gemini (May-Jun)
        "Karkataka (Ashadha)",  # Cancer (Jun-Jul)
        "Simha (Shravana)",  # Leo (Jul-Aug)
        "Kanya (Bhadrapada)",  # Virgo (Aug-Sep)
        "Tula (Ashvini)",  # Libra (Sep-Oct)
        "Vrishchika (Karttika)",  # Scorpio (Oct-Nov)
        "Dhanu (Margacirsha)",  # Sagittarius (Nov-Dec)
        "Makara (Pausya)",  # Capricorn (Dec-Jan)
        "Kumbha (Magha)",  # Aquarius (Jan-Feb)
        "Meena (Phalguna)",  # Pisces (Feb-Mar)
    ]

    idx = (solar_month_idx - 1) % 12
    return month_names[idx]


def get_paksha(ahargana: float) -> str:
    """
    Get the lunar Paksha (fortnight).

    [Ch. XIV] The lunar month is divided into two Pakshas:
    - Shukla Paksha (Waxing, Tithis 1-15): Moon growing from New to Full
    - Krishna Paksha (Waning, Tithis 16-30): Moon shrinking from Full to New

    Args:
        ahargana: Days since Kali Yuga epoch

    Returns:
        Paksha name
    """
    tithi = get_tithi(ahargana)
    if tithi <= 15.0:
        return "Shukla Paksha (Waxing)"
    else:
        return "Krishna Paksha (Waning)"


def is_adhimasa(ahargana: float) -> bool:
    """
    Check if there is an Adhimasa (intercalary month).

    [Ch. II, v.66] When two lunar months (new moon to new moon) occur
    within the same solar month, the first lunar month is considered
    intercalary (Adhimasa). This synchronizes the lunar and solar calendars.

    Adhimasa occurs approximately every 2.7 years (32-33 months).

    Args:
        ahargana: Days since Kali Yuga epoch

    Returns:
        True if current time is in an Adhimasa period
    """
    current_solar_month = get_solar_month_sign(ahargana)

    # Check if Sun remains in same sign after one mean lunar month (29.53 days)
    sun_long_now = true_longitude_sun(ahargana)
    sun_long_future = true_longitude_sun(ahargana + 29.53)

    solar_month_now = int(sun_long_now / 30.0)
    solar_month_future = int(sun_long_future / 30.0)

    # [Ch. II, v.66] If Sun hasn't changed solar month after a full lunar
    # month, it indicates two new moons in one solar month (Adhimasa)
    if solar_month_now == solar_month_future:
        return True

    return False


def get_ayananta(ahargana: float) -> str:
    """
    Get the Ayana (Solsticial period).

    [Ch. I, v.68] The year is divided into two Ayanas based on the
    Sun's apparent northward or southward motion:

    - Uttarayana (Northward): Sun enters Capricorn (270°) to Cancer (90°)
      Winter solstice to Summer solstice (Dec-Jun)
    - Dakshinayana (Southward): Sun enters Cancer (90°) to Capricorn (270°)
      Summer solstice to Winter solstice (Jun-Dec)

    Args:
        ahargana: Days since Kali Yuga epoch

    Returns:
        Ayana name
    """
    sun_long = true_longitude_sun(ahargana)

    # [Ch. I, v.68] Uttarayana: 270° (Capricorn) to 90° (Cancer)
    if 270.0 <= sun_long < 360.0 or 0.0 <= sun_long < 90.0:
        return "Uttarayana (Northward)"
    else:
        return "Dakshinayana (Southward)"


def get_season(ahargana: float) -> str:
    """
    Get the Season (Ritu).

    The year is divided into six seasons of two solar months each:
    1. Vasanta (Spring): Chaitra-Vaishakha (Solar months 1-2)
    2. Grishma (Summer): Jyeshtha-Ashadha (Solar months 3-4)
    3. Varsha (Rains): Shravana-Bhadrapada (Solar months 5-6)
    4. Sarad (Autumn): Ashvina-Kartika (Solar months 7-8)
    5. Hemanta (Winter): Margashirsha-Pausha (Solar months 9-10)
    6. Sisira (Winter/Cool): Magha-Phalguna (Solar months 11-12)

    Args:
        ahargana: Days since Kali Yuga epoch

    Returns:
        Season name
    """
    solar_month = get_solar_month_sign(ahargana)

    # Each season spans two solar months.
    season_idx = (solar_month - 1) // 2

    seasons = [
        "Vasanta (Spring)",  # Months 1-2
        "Grishma (Summer)",  # Months 3-4
        "Varsha (Rains)",  # Months 5-6
        "Sarad (Autumn)",  # Months 7-8
        "Hemanta (Winter)",  # Months 9-10
        "Sisira (Winter/Cool)",  # Months 11-12
    ]

    return seasons[season_idx]


def get_lunar_month_name(ahargana: float, system: str = "amanta") -> str:
    """
    Get the lunar month name based on regional calendar system.

    Traditional Indian calendars use two systems for defining lunar months:

    - Amanta system (South India): Month ends at new moon (Amavasya)
      Used in: Maharashtra, Karnataka, Andhra Pradesh, Tamil Nadu, Kerala

    - Purnimanta system (North India): Month ends at full moon (Purnima)
      Used in: Bihar, UP, MP, Rajasthan, Haryana, Punjab, Kashmir

    The lunar month is named after the solar month in which the full moon occurs.
    Each month corresponds to the Nakshatra occupied by the full moon.

    The 12 lunar months are:
    1. Chaitra (Mar-Apr)    - Chitra Nakshatra
    2. Vaishakha (Apr-May)  - Vishakha Nakshatra
    3. Jyeshtha (May-Jun)   - Jyeshtha Nakshatra
    4. Ashadha (Jun-Jul)    - Purva/Uttara Ashadha
    5. Shravana (Jul-Aug)   - Shravana Nakshatra
    6. Bhadrapada (Aug-Sep) - Purva/Uttara Bhadrapada
    7. Ashvini (Sep-Oct)    - Ashvini Nakshatra
    8. Karttika (Oct-Nov)   - Krittika Nakshatra
    9. Margashirsha (Nov-Dec) - Mrigashira Nakshatra
    10. Pausha (Dec-Jan)    - Pushya Nakshatra
    11. Magha (Jan-Feb)     - Magha Nakshatra
    12. Phalguna (Feb-Mar)  - Purva/Uttara Phalguna

    Reference: "The Calendars of India" by Vinod K. Mishra, Section 4.5

    Args:
        ahargana: Days since Kali Yuga epoch
        system: "amanta" (default) or "purnimanta"

    Returns:
        Lunar month name

    Example:
        >>> # For a date in April 2024
        >>> ahargana = 1867100.0
        >>> get_lunar_month_name(ahargana, "amanta")
        'Chaitra'
    """
    system_lower = system.lower()
    if system_lower not in ["amanta", "purnimanta"]:
        raise ValueError(f"Unknown system: {system}. Use 'amanta' or 'purnimanta'")

    # Get the solar month (which aligns with lunar months based on full moon)
    solar_month_idx = get_solar_month_sign(ahargana)

    # The 12 lunar month names (aligned with solar months at full moon)
    # Starting from Mesha (Aries) solar month = Chaitra lunar month
    lunar_month_names = [
        "Chaitra",  # Solar month 1 (Aries)
        "Vaishakha",  # Solar month 2 (Taurus)
        "Jyeshtha",  # Solar month 3 (Gemini)
        "Ashadha",  # Solar month 4 (Cancer)
        "Shravana",  # Solar month 5 (Leo)
        "Bhadrapada",  # Solar month 6 (Virgo)
        "Ashvini",  # Solar month 7 (Libra)
        "Karttika",  # Solar month 8 (Scorpio)
        "Margashirsha",  # Solar month 9 (Sagittarius)
        "Pausha",  # Solar month 10 (Capricorn)
        "Magha",  # Solar month 11 (Aquarius)
        "Phalguna",  # Solar month 12 (Pisces)
    ]

    # In purnimanta system, the month starts 15 days earlier (at previous full moon)
    # So we need to check if we're in the Krishna Paksha (waning phase)
    # If so, the purnimanta month is actually the previous solar month's name
    if system_lower == "purnimanta":
        tithi = get_tithi(ahargana)
        # If we're in Krishna Paksha (tithi > 15), purnimanta month is current solar month
        # If we're in Shukla Paksha (tithi <= 15), purnimanta month started in previous solar month
        if tithi <= 15.0:
            # Still in the purnimanta month that started with previous full moon
            solar_month_idx = solar_month_idx - 1
            if solar_month_idx < 1:
                solar_month_idx = 12

    month_name = lunar_month_names[(solar_month_idx - 1) % 12]
    return month_name


def get_lunar_month_number(ahargana: float, system: str = "amanta") -> int:
    """
    Get the lunar month number (1-12) based on regional calendar system.

    Returns the month number where:
    1 = Chaitra (first month, starts around March-April)
    12 = Phalguna (last month, ends around March)

    Args:
        ahargana: Days since Kali Yuga epoch
        system: "amanta" or "purnimanta"

    Returns:
        Lunar month number (1-12)
    """
    month_name = get_lunar_month_name(ahargana, system)

    month_names = [
        "Chaitra",
        "Vaishakha",
        "Jyeshtha",
        "Ashadha",
        "Shravana",
        "Bhadrapada",
        "Ashvini",
        "Karttika",
        "Margashirsha",
        "Pausha",
        "Magha",
        "Phalguna",
    ]

    return month_names.index(month_name) + 1


def is_shukla_paksha(ahargana: float) -> bool:
    """
    Check if the current phase is Shukla Paksha (waxing moon).

    Shukla Paksha is the bright half of the lunar month, from new moon to full moon.
    During this period, the moon is waxing (growing larger).

    Args:
        ahargana: Days since Kali Yuga epoch

    Returns:
        True if Shukla Paksha (Tithi 1-15), False otherwise
    """
    tithi = get_tithi(ahargana)
    return tithi <= 15.0


def is_krishna_paksha(ahargana: float) -> bool:
    """
    Check if the current phase is Krishna Paksha (waning moon).

    Krishna Paksha is the dark half of the lunar month, from full moon to new moon.
    During this period, the moon is waning (getting smaller).

    Args:
        ahargana: Days since Kali Yuga epoch

    Returns:
        True if Krishna Paksha (Tithi 16-30), False otherwise
    """
    tithi = get_tithi(ahargana)
    return tithi > 15.0


# ============================================================================
# Planetary Rashi (Zodiac Sign) Functions
# ============================================================================


def get_rashi_name(rashi_index: int) -> str:
    """
    Get the Sanskrit name for a Rashi (zodiac sign) by index.

    The 12 Rashis correspond to the 12 zodiac signs, each spanning 30° of the ecliptic.

    Args:
        rashi_index: Rashi number (1-12)

    Returns:
        Sanskrit name of the Rashi

    Raises:
        ValueError: If rashi_index is not in range 1-12
    """
    if not 1 <= rashi_index <= 12:
        raise ValueError(f"Rashi index must be 1-12, got {rashi_index}")

    rashi_names = [
        "Mesha (Aries)",  # 1: 0°-30°
        "Vrishabha (Taurus)",  # 2: 30°-60°
        "Mithuna (Gemini)",  # 3: 60°-90°
        "Karka (Cancer)",  # 4: 90°-120°
        "Simha (Leo)",  # 5: 120°-150°
        "Kanya (Virgo)",  # 6: 150°-180°
        "Tula (Libra)",  # 7: 180°-210°
        "Vrishchika (Scorpio)",  # 8: 210°-240°
        "Dhanus (Sagittarius)",  # 9: 240°-270°
        "Makara (Capricorn)",  # 10: 270°-300°
        "Kumbha (Aquarius)",  # 11: 300°-330°
        "Meena (Pisces)",  # 12: 330°-360°
    ]

    return rashi_names[rashi_index - 1]


def longitude_to_rashi(longitude: float) -> Tuple[int, str]:
    """
    Convert ecliptic longitude to Rashi (zodiac sign).

    Each Rashi spans 30° of the zodiac, starting from 0° (Mesha/Aries).

    Args:
        longitude: Ecliptic longitude in degrees (0-360)

    Returns:
        Tuple of (rashi_index, rashi_name) where rashi_index is 1-12

    Example:
        >>> longitude_to_rashi(45.0)
        (2, 'Vrishabha (Taurus)')
    """
    # Normalize longitude to [0, 360)
    longitude = normalize_angle(longitude)

    # Each Rashi is 30°
    rashi_index = int(longitude / 30.0) + 1
    if rashi_index > 12:
        rashi_index = 12

    rashi_name = get_rashi_name(rashi_index)

    return (rashi_index, rashi_name)


def get_sun_rashi(ahargana: float) -> Tuple[int, str]:
    """
    Get the Rashi (zodiac sign) occupied by the Sun.

    This is the same as the solar month calculation, as solar months
    are defined by the Sun's position in the zodiac.

    Args:
        ahargana: Days since Kali Yuga epoch

    Returns:
        Tuple of (rashi_index, rashi_name)

    Example:
        >>> # Sun in Aries around April 2024
        >>> ahargana = 1867100.0
        >>> get_sun_rashi(ahargana)
        (1, 'Mesha (Aries)')
    """
    sun_long = true_longitude_sun(ahargana)
    return longitude_to_rashi(sun_long)


def get_moon_rashi(ahargana: float) -> Tuple[int, str]:
    """
    Get the Rashi (zodiac sign) occupied by the Moon.

    The Moon's Rashi is an important element in traditional Panchanga
    calculations and is used in various astrological contexts.

    Args:
        ahargana: Days since Kali Yuga epoch

    Returns:
        Tuple of (rashi_index, rashi_name)

    Example:
        >>> ahargana = 1867100.0
        >>> get_moon_rashi(ahargana)
        (5, 'Simha (Leo)')
    """
    moon_long = true_longitude_moon(ahargana)
    return longitude_to_rashi(moon_long)


def get_planet_rashi(ahargana: float, planet: str) -> Tuple[int, str]:
    """
    Get the Rashi (zodiac sign) occupied by a planet.

    Traditional Hindu Panchanga includes the Rashi positions of all five
    visible planets (Mars, Mercury, Jupiter, Venus, Saturn), as these
    positions are important for various astrological and ritual purposes.

    [Ch. V] Surya Siddhanta provides planetary calculations for determining
    their true positions in the zodiac.

    Args:
        ahargana: Days since Kali Yuga epoch
        planet: Planet name - "mars", "mercury", "jupiter", "venus", "saturn"

    Returns:
        Tuple of (rashi_index, rashi_name)

    Raises:
        ValueError: If planet name is not recognized

    Example:
        >>> ahargana = 1867100.0
        >>> get_planet_rashi(ahargana, "mars")
        (3, 'Mithuna (Gemini)')
    """
    planet_lower = planet.lower()

    # Map planet names to Body enum
    planet_map = {
        "mars": Body.MARS,
        "mercury": Body.MERCURY,
        "jupiter": Body.JUPITER,
        "venus": Body.VENUS,
        "saturn": Body.SATURN,
    }

    if planet_lower not in planet_map:
        raise ValueError(
            f"Unknown planet: {planet}. "
            f"Supported planets: mars, mercury, jupiter, venus, saturn"
        )

    body = planet_map[planet_lower]
    planet_long = true_longitude_planet(body, ahargana)

    return longitude_to_rashi(planet_long)


def get_all_planet_rashis(ahargana: float) -> Dict[str, Tuple[int, str]]:
    """
    Get Rashi positions for Sun, Moon, and all five star planets.

    Returns a complete set of planetary positions as traditionally included
    in Hindu Panchanga (almanac) listings.

    Reference: "The Calendars of India" by Vinod K. Mishra, Chapter 5.3

    Args:
        ahargana: Days since Kali Yuga epoch

    Returns:
        Dictionary mapping celestial body names to (rashi_index, rashi_name) tuples

    Example:
        >>> ahargana = 1867100.0
        >>> positions = get_all_planet_rashis(ahargana)
        >>> positions['sun']
        (1, 'Mesha (Aries)')
        >>> positions['mars']
        (3, 'Mithuna (Gemini)')
    """
    return {
        "sun": get_sun_rashi(ahargana),
        "moon": get_moon_rashi(ahargana),
        "mars": get_planet_rashi(ahargana, "mars"),
        "mercury": get_planet_rashi(ahargana, "mercury"),
        "jupiter": get_planet_rashi(ahargana, "jupiter"),
        "venus": get_planet_rashi(ahargana, "venus"),
        "saturn": get_planet_rashi(ahargana, "saturn"),
    }


def format_planetary_positions(ahargana: float) -> str:
    """
    Format planetary Rashi positions as a human-readable string.

    Useful for displaying complete Panchanga information in traditional format.

    Args:
        ahargana: Days since Kali Yuga epoch

    Returns:
        Formatted string showing all planetary positions

    Example:
        >>> ahargana = 1867100.0
        >>> print(format_planetary_positions(ahargana))
        Sun: Mesha (Aries)
        Moon: Simha (Leo)
        Mars: Mithuna (Gemini)
        Mercury: Mesha (Aries)
        Jupiter: Vrishabha (Taurus)
        Venus: Meena (Pisces)
        Saturn: Kumbha (Aquarius)
    """
    positions = get_all_planet_rashis(ahargana)

    lines = []
    for body_name, (idx, rashi_name) in positions.items():
        # Capitalize body name
        body_display = body_name.capitalize()
        lines.append(f"{body_display}: {rashi_name}")

    return "\n".join(lines)
