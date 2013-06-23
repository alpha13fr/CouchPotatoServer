from couchpotato import get_session
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.movie.base import MovieProvider
from couchpotato.core.settings.model import Movie
from couchpotato.environment import Env
import time

log = CPLog(__name__)


class CouchPotatoApi(MovieProvider):

    urls = {
        'search': 'https://api.couchpota.to/search/%s/',
        'info': 'https://api.couchpota.to/info/%s/',
        'is_movie': 'https://api.couchpota.to/ismovie/%s/',
        'eta': 'https://api.couchpota.to/eta/%s/',
        'suggest': 'https://api.couchpota.to/suggest/',
        'updater': 'https://api.couchpota.to/updater/?%s',
        'messages': 'https://api.couchpota.to/messages/?%s',
    }
    http_time_between_calls = 0
    api_version = 1

    def __init__(self):
        addEvent('movie.info', self.getInfo, priority = 2)
        addEvent('movie.search', self.search, priority = 2)
        addEvent('movie.release_date', self.getReleaseDate)
        addEvent('movie.suggest', self.suggest)
        addEvent('movie.is_movie', self.isMovie)

        addEvent('cp.source_url', self.getSourceUrl)
        addEvent('cp.messages', self.getMessages)

    def getMessages(self, last_check = 0):

        data = self.getJsonData(self.urls['messages'] % tryUrlencode({
            'last_check': last_check,
        }), headers = self.getRequestHeaders(), cache_timeout = 10)

        return data

    def getSourceUrl(self, repo = None, repo_name = None, branch = None):
        return self.getJsonData(self.urls['updater'] % tryUrlencode({
            'repo': repo,
            'name': repo_name,
            'branch': branch,
        }), headers = self.getRequestHeaders())

    def search(self, q, limit = 5):
        return self.getJsonData(self.urls['search'] % tryUrlencode(q) + ('?limit=%s' % limit), headers = self.getRequestHeaders())

    def isMovie(self, identifier = None):

        if not identifier:
            return

        data = self.getJsonData(self.urls['is_movie'] % identifier, headers = self.getRequestHeaders())
        if data:
            return data.get('is_movie', True)

        return True

    def getInfo(self, identifier = None):

        if not identifier:
            return

        result = self.getJsonData(self.urls['info'] % identifier, headers = self.getRequestHeaders())
        if result:
            return dict((k, v) for k, v in result.iteritems() if v)

        return {}

    def getReleaseDate(self, identifier = None):
        if identifier is None: return {}

        dates = self.getJsonData(self.urls['eta'] % identifier, headers = self.getRequestHeaders())
        log.debug('Found ETA for %s: %s', (identifier, dates))

        return dates

    def suggest(self, movies = [], ignore = []):
        suggestions = self.getJsonData(self.urls['suggest'], params = {
            'movies': ','.join(movies),
            'ignore': ','.join(ignore),
        })
        log.info('Found Suggestions for %s', (suggestions))

        return suggestions

    def suggestView(self, **kwargs):

        movies = kwargs.get('movies')
        ignore = kwargs.get('ignore', [])

        if not movies:
            db = get_session()
            active_movies = db.query(Movie).filter(Movie.status.has(identifier = 'active')).all()
            movies = [x.library.identifier for x in active_movies]

        suggestions = self.suggest(movies, ignore)

        return {
            'success': True,
            'count': len(suggestions),
            'suggestions': suggestions
        }

    def getRequestHeaders(self):
        return {
            'X-CP-Version': fireEvent('app.version', single = True),
            'X-CP-API': self.api_version,
            'X-CP-Time': time.time(),
            'X-CP-Identifier': '+%s' % Env.setting('api_key', 'core')[:10], # Use first 10 as identifier, so we don't need to use IP address in api stats
        }
