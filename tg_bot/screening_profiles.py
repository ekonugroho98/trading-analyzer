"""
Screening Profiles
Predefined screening configurations for different trading styles
"""

from typing import Dict, Any
from datetime import datetime
import pytz

# Screening profiles configuration
SCREENING_PROFILES = {
    'conservative': {
        'name': 'Conservative',
        'description': 'Safe approach, strict criteria, less frequent',
        'timeframe': '4h',
        'interval_minutes': 360,  # 6 hours
        'min_score': 8.0,
        'max_results': 10,
        'suitable_for': 'Swing traders, risk-averse traders'
    },
    'moderate': {
        'name': 'Moderate',
        'description': 'Balanced approach, standard criteria',
        'timeframe': '4h',
        'interval_minutes': 120,  # 2 hours
        'min_score': 7.0,
        'max_results': 15,
        'suitable_for': 'Day traders, swing traders'
    },
    'aggressive': {
        'name': 'Aggressive',
        'description': 'Active trading, more opportunities',
        'timeframe': '1h',
        'interval_minutes': 30,  # 30 minutes
        'min_score': 6.5,
        'max_results': 20,
        'suitable_for': 'Scalpers, active day traders'
    },
    'scalper': {
        'name': 'Scalper',
        'description': 'High frequency, quick moves',
        'timeframe': '1h',
        'interval_minutes': 15,  # 15 minutes
        'min_score': 6.0,
        'max_results': 25,
        'suitable_for': 'Scalpers, very active traders'
    }
}


def get_profile(profile_name: str) -> Dict[str, Any]:
    """Get screening profile by name

    Args:
        profile_name: Name of the profile (conservative, moderate, aggressive, scalper)

    Returns:
        Profile configuration dict or None if not found
    """
    return SCREENING_PROFILES.get(profile_name.lower())


def get_all_profiles() -> Dict[str, Dict[str, Any]]:
    """Get all available screening profiles

    Returns:
        Dict of all profiles
    """
    return SCREENING_PROFILES


def format_profile_list() -> str:
    """Format profile list for display

    Returns:
        Formatted string with all profiles
    """
    message = "📊 *Screening Profiles*\n\n"

    for key, profile in SCREENING_PROFILES.items():
        message += f"""*{profile['name'].upper()}* (/profile_{key})
{profile['description']}

• Timeframe: {profile['timeframe']}
• Interval: {profile['interval_minutes']} min
• Min Score: {profile['min_score']}/10
• Max Results: {profile['max_results']}
• Best for: {profile['suitable_for']}

"""

    return message.strip()


def is_active_market_hours() -> bool:
    """Check if currently in active market hours

    Active hours: 08:00 - 16:00 UTC (US/EU overlap)
    Returns:
        True if in active hours, False otherwise
    """
    utc_now = datetime.now(pytz.UTC)
    current_hour = utc_now.hour

    # Active market hours: 08:00 - 16:00 UTC
    return 8 <= current_hour < 16


def get_adaptive_interval(base_interval_minutes: int) -> int:
    """Get adaptive interval based on market hours

    During active hours: use base interval
    During slow hours: double the interval

    Args:
        base_interval_minutes: Base interval in minutes

    Returns:
        Adjusted interval in minutes
    """
    if is_active_market_hours():
        return base_interval_minutes
    else:
        # Double interval during slow hours
        return base_interval_minutes * 2


def format_profile_info(profile_name: str) -> str:
    """Format single profile info for display

    Args:
        profile_name: Name of the profile

    Returns:
        Formatted string with profile info
    """
    profile = get_profile(profile_name)

    if not profile:
        return f"❌ Profile '{profile_name}' not found"

    message = f"""📊 *{profile['name'].upper()} Profile*

{profile['description']}

*Configuration:*
• Timeframe: {profile['timeframe']}
• Check Interval: {profile['interval_minutes']} minutes
• Minimum Score: {profile['min_score']}/10
• Max Results: {profile['max_results']}

*Best For:* {profile['suitable_for']}

*To use this profile:*
/profile_{profile_name.lower()}
"""

    return message.strip()


# Valid intervals in minutes (for validation)
VALID_INTERVALS = [15, 30, 60, 120, 180, 240, 360, 720, 1440]  # 15min to 24hours


def is_valid_interval(interval_minutes: int) -> bool:
    """Check if interval is valid

    Args:
        interval_minutes: Interval in minutes

    Returns:
        True if valid, False otherwise
    """
    return interval_minutes in VALID_INTERVALS


def format_interval_choices() -> str:
    """Format valid interval choices

    Returns:
        Formatted string with interval choices
    """
    intervals_desc = {
        15: "15 min (Scalping)",
        30: "30 min (Active)",
        60: "1 hour (Standard)",
        120: "2 hours (Balanced)",
        180: "3 hours",
        240: "4 hours",
        360: "6 hours (Swing)",
        720: "12 hours",
        1440: "24 hours (Long-term)"
    }

    message = "⏰ *Valid Screening Intervals*\n\n"

    for minutes, desc in intervals_desc.items():
        message += f"• {minutes} min - {desc}\n"

    return message
