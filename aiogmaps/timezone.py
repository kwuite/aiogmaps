from googlemaps.timezone import timezone as _timezone
import googlemaps


async def timezone(client, location, timestamp=None, language=None):
    return await _timezone(client, location,
                           timestamp=timestamp,
                           language=language)
