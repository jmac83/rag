import fitparse
import json
from datetime import datetime

def simple_fit_to_json(fit_file_path):
    """Convert FIT file to JSON string, excluding GPS data"""
    # Parse the FIT file
    fitfile = fitparse.FitFile(fit_file_path)
    
   # Create a summary object
    summary = {
        "activity_type": None,
        "start_time": None,
        "duration": None,
        "distance": None,
        "calories": None,
        "avg_heart_rate": None,
        "max_heart_rate": None,
        "avg_speed": None,
        "max_speed": None,
        "avg_cadence": None,
        "elevation_gain": None,
        "training_effect": None,
        "heart_rate_zones": {
            "zone1": None,
            "zone2": None,
            "zone3": None, 
            "zone4": None,
            "zone5": None
        }
    }
    
    # Process session messages (contains the activity summary)
    for message in fitfile.messages:
        if message.name == 'session':
            for field in message:
                name = field.name
                value = field.value
                
                # Convert datetime objects to strings
                if isinstance(value, datetime):
                    value = value.isoformat()
                
                # Map common fields to our summary structure
                if name == 'sport':
                    summary["activity_type"] = value
                elif name == 'start_time':
                    summary["start_time"] = value
                elif name == 'total_elapsed_time':
                    summary["duration"] = round(value / 60, 2) if value else None  # Convert to minutes
                elif name == 'total_distance':
                    summary["distance"] = round(value / 1000, 2) if value else None  # Convert to km
                elif name == 'total_calories':
                    summary["calories"] = value
                elif name == 'avg_heart_rate':
                    summary["avg_heart_rate"] = value
                elif name == 'max_heart_rate':
                    summary["max_heart_rate"] = value
                elif name == 'avg_speed':
                    summary["avg_speed"] = round(value * 3.6, 2) if value else None  # Convert to km/h
                elif name == 'max_speed':
                    summary["max_speed"] = round(value * 3.6, 2) if value else None  # Convert to km/h
                elif name == 'avg_cadence':
                    summary["avg_cadence"] = value
                elif name == 'total_ascent':
                    summary["elevation_gain"] = value
                elif name == 'total_training_effect':
                    summary["training_effect"] = value
                elif name == 'time_in_hr_zone':
                    if isinstance(value, list) and len(value) >= 5:
                        summary["heart_rate_zones"]["zone1"] = round(value[0] / 60, 1) if value[0] else 0  # Convert to minutes
                        summary["heart_rate_zones"]["zone2"] = round(value[1] / 60, 1) if value[1] else 0
                        summary["heart_rate_zones"]["zone3"] = round(value[2] / 60, 1) if value[2] else 0
                        summary["heart_rate_zones"]["zone4"] = round(value[3] / 60, 1) if value[3] else 0
                        summary["heart_rate_zones"]["zone5"] = round(value[4] / 60, 1) if value[4] else 0
    
    # Remove any None values for cleaner output
    clean_summary = {k: v for k, v in summary.items() if v is not None}
    
    # Handle nested dictionaries (like heart_rate_zones)
    for key, value in clean_summary.items():
        if isinstance(value, dict):
            clean_summary[key] = {k: v for k, v in value.items() if v is not None}
    
    # Convert to JSON string
    return json.dumps(clean_summary, indent=3)

# Example usage
fit_file = "ACTIVITY.fit"
json_data = simple_fit_to_json(fit_file)
print(json_data)  # Or use it directly
