import asyncio
import logging

import aiohttp
import googlemaps
from yarl import URL

from . import __version__
from .places import (place, places, places_autocomplete,  # noqa
                     places_autocomplete_query, places_nearby, places_photo,
                     places_radar)
from .roads import (nearest_roads, snap_to_roads, snapped_speed_limits,
                    speed_limits)
from .timezone import timezone

logger = logging.getLogger(__name__)


class Client:
    def __init__(self, key=None, client_id=None, client_secret=None,
                 session=None, verify_ssl=True, request_timeout=10,
                 loop=None):
        if loop is None:
            loop = asyncio.get_event_loop()

        self.loop = loop
        self.verify_ssl = verify_ssl

        if not key and not (client_secret and client_id):
            raise ValueError('Must provide API key or enterprise credentials '
                             'when creating client.')

        if key and not key.startswith('AIza'):
            raise ValueError('Invalid API key provided.')

        self.key = key
        self.client_id = client_id
        self.client_secret = client_secret
        self.request_timeout = request_timeout
        self.base_url = URL('https://maps.googleapis.com/')
        self._user_agent = 'AsyncGoogleGeoApiClientPython/{}'.format(
            __version__)
        self._headers = {
            'User-Agent': self._user_agent,
        }

    def _get_params(self, params, accepts_clientid=False):
        if accepts_clientid and self.client_id and self.client_secret:
            raise NotImplementedError

        if self.key is not None:
            if isinstance(params, (list, tuple)):
                params.append(('key', self.key))
                return params

            return {'key': self.key, **params}

    async def _request(
        self,
        url,
        params,
        data=None,
        base_url=None,
        extract_body=None,
        method='GET',
        chunked=False,
        accepts_clientid=False,
        post_json=None,
        **kwargs,
    ):
        if extract_body and not callable(extract_body):
            raise TypeError('extract_body should be callable')

        if not (base_url and isinstance(base_url, (str, URL))):
            base_url = self.base_url

        base_url = URL(base_url)

        params = self._get_params(params)

        if post_json is not None:
            method = 'POST'
            data = post_json

        try:
            async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(
                    use_dns_cache=True,
                    # loop=loop,
                    verify_ssl=self.verify_ssl,
                )
                ) as session:
                response = await session.request(
                        method,
                        base_url / url.lstrip('/'),
                        params=params,
                        data=data,
                        headers=self._headers,
                        timeout=self.request_timeout,
                        **kwargs,
                    )
        except aiohttp.ClientError as exc:
            logger.exception(exc, exc_info=exc)
            raise

        if chunked:
            return response.content.iter_chunks()

        if extract_body is not None:
            result = extract_body(response)
            if asyncio.iscoroutine(result):
                result = await result
        else:
            result = await self._get_body(response)

        return result

    async def _get_body(self, response):
        if response.status != 200:
            raise googlemaps.exceptions.HTTPError(response.status_code)

        body = await response.json()

        api_status = body['status']
        if api_status == 'OK' or api_status == 'ZERO_RESULTS':
            return body

        if api_status == 'OVER_QUERY_LIMIT':
            raise googlemaps.exceptions._OverQueryLimit(
                api_status, body.get('error_message'))

        raise googlemaps.exceptions.ApiError(api_status,
                                             body.get('error_message'))

    # async def close(self):
    #     await self.session.close()

    async def __aenter__(self):
        return self

    # async def __aexit__(self, *exc_info):
    #     await self.close()

# Places API
Client.place = place
Client.places = places
Client.places_nearby = places_nearby
Client.places_autocomplete = places_autocomplete
Client.places_photo = places_photo
Client.places_radar = places_radar

# Roads API
Client.speed_limits = speed_limits
Client.nearest_roads = nearest_roads
Client.snap_to_roads = snap_to_roads
Client.snapped_speed_limits = snapped_speed_limits

# Timezone API
Client.timezone = timezone
