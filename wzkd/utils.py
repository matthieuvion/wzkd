import datetime
from datetime import datetime, timezone

  
  
# Getting the current date

def ToTimestamp(date):
    """
    API requires UTC timestamp in milliseconds for the end/{end}/ path variable
    """
    date = datetime.now(timezone.utc)
    epoch_millis = int(date.timestamp() * 1000)
    
    return epoch_millis

# summary2 = await player.matchesSummary(Title.ModernWarfare, Mode.Warzone, end= utc_timestamp, limit=15)