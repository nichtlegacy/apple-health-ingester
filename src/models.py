"""Data models and mappings for Apple Health metrics.

Contains mappings from Health Auto Export metric names to entity IDs,
unit conversions, and sleep field definitions.
"""

# Mapping: Health Auto Export metric name -> entity_id
# Converts various metric names to standardized entity IDs
METRIC_MAPPING: dict[str, str] = {
    # Energy
    "active_energy": "applehealth_active_energy",
    "active_energy_burned": "applehealth_active_energy",
    "basal_energy_burned": "applehealth_basal_energy_burned",

    # Heart Rate
    "heart_rate": "applehealth_heart_rate",
    "resting_heart_rate": "applehealth_resting_heart_rate",

    # Body Measurements
    "weight_body_mass": "applehealth_weight_body_mass",
    "weight": "applehealth_weight_body_mass",
    "body_mass": "applehealth_weight_body_mass",
    "body_mass_index": "applehealth_body_mass_index",
    "body_fat_percentage": "applehealth_body_fat_percentage",
    "lean_body_mass": "applehealth_lean_body_mass",

    # Activity
    "step_count": "applehealth_step_count",
    "steps": "applehealth_step_count",
    "flights_climbed": "applehealth_flights_climbed",
    "walking_running_distance": "applehealth_walking_running_distance",
    "cycling_distance": "applehealth_cycling_distance",

    # Sleep
    "sleep_analysis": "applehealth_sleep_analysis",

    # Blood Values
    "blood_oxygen_saturation": "applehealth_blood_oxygen_saturation",
    "oxygen_saturation": "applehealth_blood_oxygen_saturation",

    # Audio
    "headphone_audio_exposure": "applehealth_headphone_audio_exposure",

    # Walking Metrics
    "walking_speed": "applehealth_walking_speed",
    "walking_step_length": "applehealth_walking_step_length",
    "walking_asymmetry_percentage": "applehealth_walking_asymmetry_percentage",
    "walking_double_support_percentage": "applehealth_walking_double_support_percentage",
}

# Unit mapping for consistent units
UNIT_MAPPING: dict[str, str] = {
    "kcal": "kJ",
    "count": "steps",
    "count/min": "bpm",
    "lb": "kg",
}

# Sleep analysis field mappings
# Maps Health Auto Export field names to entity ID suffixes
SLEEP_FIELDS: dict[str, str] = {
    "asleep": "totalsleep",
    "inBed": "inbed",
    "deep": "deep",
    "rem": "rem",
    "core": "core",
    "awake": "awake",
}

# Heart rate aggregation suffixes
HEART_RATE_FIELDS: dict[str, str] = {
    "Min": "min",
    "Avg": "avg",
    "Max": "max",
}
