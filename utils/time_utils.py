# utils/time_utils.py

from datetime import datetime

def format_time_ago(timestamp_str):
    try:
        then = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        diff_seconds = (now - then).total_seconds()

        if diff_seconds < 60:
            return "just now"
        elif diff_seconds < 3600:
            return f"{int(diff_seconds // 60)} mins ago"
        else:
            return f"at {then.strftime('%I:%M %p')}"
    except Exception:
        return "N/A"