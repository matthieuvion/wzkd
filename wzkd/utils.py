from datetime import timezone
import datetime
  
  
# Getting the current date

def EndToTimestamp(end_date):
    end_date = datetime.datetime.now(timezone.utc)
    
    utc_time = end_date.replace(tzinfo=timezone.utc)
    utc_timestamp = utc_time.timestamp()
    
    #print(utc_timestamp)
    return utc_timestamp

# summary2 = await player.matchesSummary(Title.ModernWarfare, Mode.Warzone, end= utc_timestamp, limit=15)