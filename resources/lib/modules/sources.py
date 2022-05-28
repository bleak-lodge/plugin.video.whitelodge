# -*- coding: utf-8 -*-

import sys,re,random,datetime,time
import simplejson as json

import six
from six.moves import urllib_parse, zip, reduce

from resources.lib.modules import trakt
from resources.lib.modules import tvmaze
from resources.lib.modules import cache
from resources.lib.modules import control
from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import workers
from resources.lib.modules import source_utils
from resources.lib.modules import log_utils
#from resources.lib.modules import thexem

try: from sqlite3 import dbapi2 as database
except: from pysqlite2 import dbapi2 as database

from kodi_six import xbmc


class sources:
    def __init__(self):
        self.getConstants()
        self.sources = []
        self.content = None


    def play(self, title, year, imdb, tmdb, season, episode, tvshowtitle, premiered, meta, select):
        try:
            self.content = 'episode' if tvshowtitle else 'movie'

            url = None

            #log_utils.log('meta: ' + repr(meta))

            try: meta = json.loads(meta)
            except: meta = {}

            if not meta: # played through library
                try:
                    if self.content == 'episode':
                        meta = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"filter":{"or": [{"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}]}, "properties" : ["title", "year", "thumbnail", "file", "runtime"]}, "id": 1}' % (year, str(int(year)+1), str(int(year)-1)))
                        meta = six.ensure_text(meta, errors='ignore')
                        meta = json.loads(meta)['result']['tvshows']
                        #log_utils.log('meta0: ' + repr(meta))

                        t = self.getTitle(tvshowtitle)
                        meta = [i for i in meta if year == str(i['year']) and t == self.getTitle(i['title'])][0]

                        tvshowid = meta['tvshowid']

                        meta = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params":{ "tvshowid": %d, "filter":{"and": [{"field": "season", "operator": "is", "value": "%s"}, {"field": "episode", "operator": "is", "value": "%s"}]}, "properties": ["title", "season", "episode", "showtitle", "firstaired", "runtime", "rating", "director", "writer", "plot", "thumbnail", "file"]}, "id": 1}' % (tvshowid, season, episode))
                        meta = six.ensure_text(meta, errors='ignore')
                        meta = json.loads(meta)['result']['episodes'][0]

                    else:
                        meta = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"filter":{"or": [{"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}]}, "properties" : ["title", "originaltitle", "year", "genre", "studio", "country", "runtime", "rating", "votes", "mpaa", "director", "writer", "plot", "plotoutline", "tagline", "thumbnail", "file"]}, "id": 1}' % (year, str(int(year)+1), str(int(year)-1)))
                        meta = six.ensure_text(meta, errors='ignore')
                        meta = json.loads(meta)['result']['movies']
                        t = self.getTitle(title)
                        meta = [i for i in meta if year == str(i['year']) and (t == self.getTitle(i['title']) or t == self.getTitle(i['originaltitle']))][0]

                    for k, v in six.iteritems(meta):
                        if type(v) == list:
                            try: meta[k] = str(' / '.join([six.ensure_str(i, errors='ignore') for i in v]))
                            except: meta[k] = ''
                        else:
                            try: meta[k] = str(six.ensure_str(v, errors='ignore'))
                            except: meta[k] = str(v)

                    #log_utils.log('meta: ' + repr(meta))
                except:
                    log_utils.log('Getting meta from lib failed', 1)
                    meta = {}

            items = self.getSources(title, year, imdb, tmdb, season, episode, tvshowtitle, premiered)

            select = control.setting('hosts.mode') if select == None else select

            title = tvshowtitle or title
            title = self.getTitle(title)

            if len(items) > 0:

                if select == '1' and 'plugin' in control.infoLabel('Container.PluginName'):
                    control.window.clearProperty(self.itemProperty)
                    control.window.setProperty(self.itemProperty, json.dumps(items))

                    control.window.clearProperty(self.metaProperty)
                    control.window.setProperty(self.metaProperty, json.dumps(meta))

                    control.sleep(200)

                    return control.execute('Container.Update(%s?action=addItem&title=%s)' % (sys.argv[0], urllib_parse.quote_plus(title)))

                elif select == '0' or select == '1':
                    url = self.sourcesDialog(items)

                else:
                    url = self.sourcesDirect(items)


            if url == 'close://' or url == None:
                self.url = url
                return self.errorForSources()

            from resources.lib.modules.player import player
            player().run(title, year, season, episode, imdb, tmdb, url, meta)
        except:
            log_utils.log('sources_play_fail', 1)
            pass


    def addItem(self, title):

        def sourcesDirMeta(metadata):
            if metadata == None: return metadata
            allowed = ['icon', 'poster', 'fanart', 'thumb', 'clearlogo', 'clearart', 'discart', 'title', 'year', 'tvshowtitle', 'season', 'episode', 'rating', 'plot', 'trailer', 'mediatype']
            return {k: v for k, v in six.iteritems(metadata) if k in allowed}

        control.playlist.clear()
        items = control.window.getProperty(self.itemProperty)
        items = json.loads(items)

        if items == None or len(items) == 0: control.idle() ; sys.exit()

        meta = control.window.getProperty(self.metaProperty)
        meta = json.loads(meta)
        meta = sourcesDirMeta(meta)

        sysaddon = sys.argv[0]

        syshandle = int(sys.argv[1])

        systitle = urllib_parse.quote_plus(title)

        listMeta = control.setting('source.list.meta')

        poster = meta.get('poster') or control.addonPoster()
        if control.setting('fanart') == 'true':
            fanart = meta.get('fanart') or control.addonFanart()
        else:
            fanart = control.addonFanart()
        thumb = meta.get('thumb') or poster or fanart
        clearlogo = meta.get('clearlogo', '') or ''
        clearart = meta.get('clearart', '') or ''
        discart = meta.get('discart', '') or ''

        #banner = meta['banner'] if 'banner' in meta else '0'
        #if banner == '0': banner = poster
        #if banner == '0': banner = control.addonBanner()


        for i in range(len(items)):
            try:
                label = str(items[i]['label'])

                syssource = urllib_parse.quote_plus(json.dumps([items[i]]))

                sysurl = '%s?action=playItem&title=%s&source=%s' % (sysaddon, systitle, syssource)

                try: item = control.item(label=label, offscreen=True)
                except: item = control.item(label=label)

                if listMeta == 'true':
                    item.setArt({'thumb': thumb, 'icon': thumb, 'poster': poster, 'fanart': fanart, 'clearlogo': clearlogo, 'clearart': clearart, 'discart': discart})
                    video_streaminfo = {'codec': 'h264'}
                    item.addStreamInfo('video', video_streaminfo)
                    item.setInfo(type='video', infoLabels=control.metadataClean(meta))
                else:
                    item.setArt({'thumb': thumb})
                    item.setInfo(type='video', infoLabels={})

                control.addItem(handle=syshandle, url=sysurl, listitem=item, isFolder=False)
            except:
                pass

        control.content(syshandle, 'files')
        control.directory(syshandle, cacheToDisc=True)


    def playItem(self, title, source):
        try:
            meta = control.window.getProperty(self.metaProperty)
            meta = json.loads(meta)

            year = meta['year'] if 'year' in meta else None
            season = meta['season'] if 'season' in meta else None
            episode = meta['episode'] if 'episode' in meta else None

            imdb = meta['imdb'] if 'imdb' in meta else None
            tvdb = meta['tvdb'] if 'tvdb' in meta else None
            tmdb = meta['tmdb'] if 'tmdb' in meta else None

            next = [] ; prev = [] ; total = []

            for i in range(1,1000):
                try:
                    u = control.infoLabel('ListItem(%s).FolderPath' % str(i))
                    if u in total: raise Exception()
                    total.append(u)
                    u = dict(urllib_parse.parse_qsl(u.replace('?','')))
                    u = json.loads(u['source'])[0]
                    next.append(u)
                except:
                    break
            for i in range(-1000,0)[::-1]:
                try:
                    u = control.infoLabel('ListItem(%s).FolderPath' % str(i))
                    if u in total: raise Exception()
                    total.append(u)
                    u = dict(urllib_parse.parse_qsl(u.replace('?','')))
                    u = json.loads(u['source'])[0]
                    prev.append(u)
                except:
                    break

            items = json.loads(source)
            items = [i for i in items+next+prev][:40]

            header = control.addonInfo('name') + ': Resolving...'

            progressDialog = control.progressDialog if control.setting('progress.dialog') == '0' else control.progressDialogBG
            progressDialog.create(header, '')
            #progressDialog.update(0)

            block = None

            for i in range(len(items)):
                try:
                    label = re.sub(' {2,}', ' ', str(items[i]['label']))
                    try:
                        if progressDialog.iscanceled(): break
                        progressDialog.update(int((100 / float(len(items))) * i), label)
                    except:
                        progressDialog.update(int((100 / float(len(items))) * i), str(header) + '[CR]' + label)

                    if items[i]['source'] == block: raise Exception()

                    w = workers.Thread(self.sourcesResolve, items[i])
                    w.start()

                    m = ''

                    for x in range(3600):
                        try:
                            if control.monitor.abortRequested(): return sys.exit()
                            if progressDialog.iscanceled(): return progressDialog.close()
                        except:
                            pass

                        k = control.condVisibility('Window.IsActive(virtualkeyboard)')
                        if k: m += '1'; m = m[-1]
                        if (w.is_alive() == False or x > 30) and not k: break
                        k = control.condVisibility('Window.IsActive(yesnoDialog)')
                        if k: m += '1'; m = m[-1]
                        if (w.is_alive() == False or x > 30) and not k: break
                        time.sleep(0.5)


                    for x in range(30):
                        try:
                            if control.monitor.abortRequested(): return sys.exit()
                            if progressDialog.iscanceled(): return progressDialog.close()
                        except:
                            pass

                        if m == '': break
                        if w.is_alive() == False: break
                        time.sleep(0.5)


                    if w.is_alive() == True: block = items[i]['source']

                    if not self.url: raise Exception()

                    try: progressDialog.close()
                    except: pass

                    control.sleep(200)
                    control.execute('Dialog.Close(virtualkeyboard)')
                    control.execute('Dialog.Close(yesnoDialog)')

                    from resources.lib.modules.player import player
                    player().run(title, year, season, episode, imdb, tmdb, self.url, meta)

                    return self.url
                except:
                    pass

            try: progressDialog.close()
            except: pass
            del progressDialog

            self.errorForSources()
        except:
            log_utils.log('playItem', 1)
            pass


    def getSources(self, title, year, imdb, tmdb, season, episode, tvshowtitle, premiered):
        progressDialog = control.progressDialog if control.setting('progress.dialog') == '0' else control.progressDialogBG
        if progressDialog == control.progressDialogBG:
            control.idle()

        progressDialog.create(self.module_name)
        #progressDialog.update(0)

        self.prepareSources()

        sourceDict = self.sourceDict

        progressDialog.update(0, control.lang(32600))

        if self.content == 'movie':
            sourceDict = [(i[0], i[1], getattr(i[1], 'movie', None)) for i in sourceDict]
        else:
            sourceDict = [(i[0], i[1], getattr(i[1], 'tvshow', None)) for i in sourceDict]

        try: sourceDict = [(i[0], i[1], control.setting('provider.' + i[0])) for i in sourceDict]
        except: sourceDict = [(i[0], i[1], 'true') for i in sourceDict]
        sourceDict = [(i[0], i[1]) for i in sourceDict if not i[2] == 'false']

        sourceDict = [(i[0], i[1], i[1].priority) for i in sourceDict]

        random.shuffle(sourceDict)
        sourceDict = sorted(sourceDict, key=lambda i: i[2])

        threads = []

        if self.content == 'movie':
            #title = self.getTitle(title)
            title, year = cleantitle.scene_title(title, year)
            localtitle = title
            aliases = cache.get(self.getAliasTitles, 168, imdb, localtitle)
            log_utils.log('Scrape - movtitle: '+title+' | localtitle: '+localtitle+' | year: '+year+' | aliases: '+repr(aliases))
            for i in sourceDict: threads.append(workers.Thread(self.getMovieSource, title, localtitle, aliases, year, imdb, tmdb, i[0], i[1]))
        else:
            #tvshowtitle = self.getTitle(tvshowtitle)
            tvshowtitle, year, season, episode = cleantitle.scene_tvtitle(tvshowtitle, year, season, episode)
            localtvshowtitle = title
            aliases = cache.get(self.getAliasTitles, 168, imdb, localtvshowtitle)
            log_utils.log('Scrape - tvtitle: '+tvshowtitle+' | localtitle: '+localtvshowtitle+' | year: '+year+' | season: '+season+' | episode: '+episode+' | aliases: '+repr(aliases))
            #Disabled on 11/11/17 due to hang. Should be checked in the future and possible enabled again.
            #season, episode = thexem.get_scene_episode_number(tvdb, season, episode)
            for i in sourceDict: threads.append(workers.Thread(self.getEpisodeSource, title, year, imdb, tmdb, season, episode, tvshowtitle, localtvshowtitle, aliases, premiered, i[0], i[1]))

        s = [i[0] + (i[1],) for i in zip(sourceDict, threads)]
        s = [(i[3].getName(), i[0], i[2]) for i in s]

        sourcelabelDict = dict([(i[0], i[1].upper()) for i in s])

        [i.start() for i in threads]

        try: timeout = int(control.setting('scrapers.timeout.1'))
        except: timeout = 40

        start_time = time.time()
        end_time = start_time + timeout

        string3 = control.lang(32406)

        lib_source = service_source = 0

        line1 = line3 = ""

        total_format = '[COLOR %s][B]%s[/B][/COLOR]'
        pdiag_format = 'LIBRARY: %s | SERVICE: %s'

        for i in range(0, 4 * timeout):

            try:

                if control.monitor.abortRequested():
                    return sys.exit()
                try:
                    if progressDialog.iscanceled():
                        break
                except:
                    pass
                try:
                    if progressDialog.isFinished():
                        break
                except:
                    pass

                if self.sources:

                    lib_source = len([e for e in self.sources if e.get('local')])
                    service_source = len([e for e in self.sources if e.get('official')])

                lib_source_label = total_format % ('red', lib_source) if lib_source == 0 else total_format % ('lime', lib_source)
                service_source_label = total_format % ('red', service_source) if service_source == 0 else total_format % ('lime', service_source)

                try:
                    info = [sourcelabelDict[x.getName()] for x in threads if x.is_alive() == True]
                    line1 = pdiag_format % (lib_source_label, service_source_label)
                    if len(info) > 6: line3 = string3 % (str(len(info)))
                    elif len(info) > 0: line3 = string3 % (', '.join(info))
                    else: break
                    current_time = time.time()
                    current_progress = current_time - start_time
                    percent = int((current_progress / float(timeout)) * 100)
                    if not progressDialog == control.progressDialogBG: progressDialog.update(max(1, percent), line1 + '[CR]' + line3)
                    else: progressDialog.update(max(1, percent), self.module_name, line1 + '[CR]' + line3)
                    if end_time < current_time: break
                except:
                    log_utils.log('Source fetching dialog exception', 1)
                    break

                control.sleep(250)
            except:
                log_utils.log('sourcefail', 1)
                pass

        self.sourcesFilter()
        progressDialog.close()

        del progressDialog
        del threads

        control.idle()

        return self.sources


    def prepareSources(self):
        try:
            control.makeFile(control.dataPath)

            dbcon = database.connect(self.sourceFile)
            dbcur = dbcon.cursor()
            dbcur.execute("CREATE TABLE IF NOT EXISTS rel_url (""source TEXT, ""imdb_id TEXT, ""season TEXT, ""episode TEXT, ""rel_url TEXT, ""UNIQUE(source, imdb_id, season, episode)"");")
            dbcur.execute("CREATE TABLE IF NOT EXISTS rel_src (""source TEXT, ""imdb_id TEXT, ""season TEXT, ""episode TEXT, ""hosts TEXT, ""added TEXT, ""UNIQUE(source, imdb_id, season, episode)"");")
        except:
            pass


    def getMovieSource(self, title, localtitle, aliases, year, imdb, tmdb, source, call):

        try:
            dbcon = database.connect(self.sourceFile)
            dbcur = dbcon.cursor()
        except:
            pass

        ''' Fix to stop items passed with a 0 IMDB id pulling old unrelated sources from the database. '''
        if imdb == '0':
            try:
                dbcur.execute("DELETE FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
                dbcur.execute("DELETE FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
                dbcon.commit()
            except:
                pass
        ''' END '''

        try:
            sources = []
            dbcur.execute("SELECT * FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
            match = dbcur.fetchone()
            t1 = int(re.sub('[^0-9]', '', str(match[5])))
            t2 = int(datetime.datetime.now().strftime("%Y%m%d%H%M"))
            update = abs(t2 - t1) > 60
            if update == False:
                sources = eval(six.ensure_str(match[4]))
                return self.sources.extend(sources)
        except:
            pass

        try:
            url = None
            dbcur.execute("SELECT * FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
            url = dbcur.fetchone()
            url = eval(six.ensure_str(url[4]))
        except:
            pass

        try:
            if url == None: url = call.movie(imdb, tmdb, title, localtitle, aliases, year)
            if url == None: raise Exception()
            dbcur.execute("DELETE FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
            dbcur.execute("INSERT INTO rel_url Values (?, ?, ?, ?, ?)", (source, imdb, '', '', repr(url)))
            dbcon.commit()
        except:
            pass

        try:
            sources = []
            sources = call.sources(url)
            if sources == None or sources == []: raise Exception()
            sources = [json.loads(t) for t in set(json.dumps(d, sort_keys=True) for d in sources)]
            for i in sources: i.update({'provider': source})
            self.sources.extend(sources)
            dbcur.execute("DELETE FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
            dbcur.execute("INSERT INTO rel_src Values (?, ?, ?, ?, ?, ?)", (source, imdb, '', '', repr(sources), datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
            dbcon.commit()
        except:
            pass


    def getEpisodeSource(self, title, year, imdb, tmdb, season, episode, tvshowtitle, localtvshowtitle, aliases, premiered, source, call):
        try:
            dbcon = database.connect(self.sourceFile)
            dbcur = dbcon.cursor()
        except:
            pass

        try:
            sources = []
            dbcur.execute("SELECT * FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, season, episode))
            match = dbcur.fetchone()
            t1 = int(re.sub('[^0-9]', '', str(match[5])))
            t2 = int(datetime.datetime.now().strftime("%Y%m%d%H%M"))
            update = abs(t2 - t1) > 60
            if update == False:
                sources = eval(six.ensure_str(match[4]))
                return self.sources.extend(sources)
        except:
            pass

        try:
            url = None
            dbcur.execute("SELECT * FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
            url = dbcur.fetchone()
            url = eval(six.ensure_str(url[4]))
        except:
            pass

        try:
            if url == None: url = call.tvshow(imdb, tmdb, tvshowtitle, localtvshowtitle, aliases, year)
            if url == None: raise Exception()
            dbcur.execute("DELETE FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
            dbcur.execute("INSERT INTO rel_url Values (?, ?, ?, ?, ?)", (source, imdb, '', '', repr(url)))
            dbcon.commit()
        except:
            pass

        try:
            ep_url = None
            dbcur.execute("SELECT * FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, season, episode))
            ep_url = dbcur.fetchone()
            ep_url = eval(six.ensure_str(ep_url[4]))
        except:
            pass

        try:
            if url == None: raise Exception()
            if ep_url == None: ep_url = call.episode(url, imdb, tmdb, title, premiered, season, episode)
            if ep_url == None: raise Exception()
            dbcur.execute("DELETE FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, season, episode))
            dbcur.execute("INSERT INTO rel_url Values (?, ?, ?, ?, ?)", (source, imdb, season, episode, repr(ep_url)))
            dbcon.commit()
        except:
            pass

        try:
            sources = []
            sources = call.sources(ep_url)
            if sources == None or sources == []: raise Exception()
            sources = [json.loads(t) for t in set(json.dumps(d, sort_keys=True) for d in sources)]
            for i in sources: i.update({'provider': source})
            self.sources.extend(sources)
            dbcur.execute("DELETE FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, season, episode))
            dbcur.execute("INSERT INTO rel_src Values (?, ?, ?, ?, ?, ?)", (source, imdb, season, episode, repr(sources), datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
            dbcon.commit()
        except:
            pass


    def alterSources(self, url, meta):

        try:
            if control.setting('hosts.mode') == '2': url += '&select=1'
            else: url += '&select=2'
            control.execute('RunPlugin(%s)' % url)
        except:
            pass


    def clearSources(self):
        try:
            control.idle()

            yes = control.yesnoDialog(control.lang(32407))
            if not yes: return

            control.makeFile(control.dataPath)
            dbcon = database.connect(control.providercacheFile)
            dbcur = dbcon.cursor()
            dbcur.execute("DROP TABLE IF EXISTS rel_src")
            dbcur.execute("DROP TABLE IF EXISTS rel_url")
            dbcur.execute("VACUUM")
            dbcon.commit()

            control.infoDialog(control.lang(32408), sound=True, icon='INFO')
        except:
            pass


    def sourcesFilter(self):

        for s in self.sources:
            s.update({'quality': s.get('quality', 'SD').upper()})
            if s['quality'] == 'HD':
                s.update({'quality': '720P'})
            if self.content == 'episode' and s['quality'] in ['SCR', 'CAM']:
                s.update({'quality': 'SD'})

        filter = []
        filter += [i for i in self.sources if i['quality'] == '4K']
        filter += [i for i in self.sources if i['quality'] == '1080P']
        filter += [i for i in self.sources if i['quality'] == '720P']
        filter += [i for i in self.sources if i['quality'] == 'SD']
        filter += [i for i in self.sources if i['quality'] in ['SCR', 'CAM']]
        self.sources = filter

        self.sources = [i for i in self.sources if i.get('local')] + [i for i in self.sources if i.get('official')]


        official_color = control.setting('official.identify') or '15'
        official_identify = self.getPremColor(official_color)

        prem_color = control.setting('prem.identify') or '20'
        prem_identify = self.getPremColor(prem_color)

        sec_color = control.setting('sec.identify') or '17'
        sec_identify = self.getPremColor(sec_color)

        double_line = control.setting('linesplit') == '1'

        for i in range(len(self.sources)):

            u = self.sources[i]['url']

            p = self.sources[i]['provider'].upper()

            q = self.sources[i]['quality']

            n = self.sources[i].get('name', '') or ''

            o = self.sources[i].get('official', False)

            s = self.sources[i]['source'].upper()

            t = ''
            if n:
                t = n
            else:
                #f1 = self.sources[i].get('info', '') or ''
                f1 = ' / '.join(['%s' % info.strip() for info in self.sources[i].get('info', '').split('|')])
                f2 = '.'.join((n, u)) if n else u
                f2 = source_utils.getFileType(f2)
                t = ' / '.join((f1, f2))
            try: size_info = self.sources[i].get('info', '').split(' /')[0]
            except: size_info = ''
            if size_info and size_info.strip().lower().endswith('gb'):
                t = ' / '.join((size_info, t))
            t = t.strip(' /')
            if t:
                t = '[COLOR %s][I]%s[/I][/COLOR]' % (sec_identify, t)

            if double_line:
                if o:
                    label = '[COLOR %s]%03d | %s | [B]%s[/B][/COLOR][CR] ' % (official_identify, int(i+1), p, s)
                else:
                    label = '[COLOR %s]%03d | %s | [B]%s[/B][/COLOR][CR]    %s' % (prem_identify, int(i+1), p, q, t)

            else:
                if o:
                    label = '[COLOR %s]%03d | %s | [B]%s[/B][/COLOR]' % (official_identify, int(i+1), p, s)
                else:
                    label = '[COLOR %s]%03d | %s | [B]%s[/B] |[/COLOR] %s' % (prem_identify, int(i+1), p, q, t)

            label = label.replace(' |  |', ' |').replace('| 0 |', '|')

            # nasty
            if double_line and t:
                label_up, label_down = label.split('[CR]')
                label_up_clean = label_up.replace('[COLOR %s]' % prem_identify, '').replace('[/COLOR]', '').replace('[B]', '').replace('[/B]', '')
                label_down_clean = label_down.replace('[COLOR %s]' % sec_identify, '').replace('[/COLOR]', '').replace('[I]', '').replace('[/I]', '')
                if len(label_down_clean) > len(label_up_clean):
                    label_up += (len(label_down_clean) - len(label_up_clean)) * '  '
                    label = '[CR]'.join((label_up, label_down))

            self.sources[i]['label'] = label

        self.sources = [i for i in self.sources if 'label' in i]


    def sourcesResolve(self, item, info=False):
        try:
            self.url = None

            u = url = item['url']

            local = item.get('local', False)
            provider = item['provider']
            call = [i[1] for i in self.sourceDict if i[0] == provider][0]
            u = url = call.resolve(url)

            if not url or (not '://' in url and not local and 'magnet:' not in url): raise Exception()

            self.url = url

            return url
        except:
            log_utils.log('Resolve failure for url: {}'.format(item['url']), 1)
            if info == True: self.errorForSources()
            return


    def sourcesDialog(self, items):
        try:

            labels = [i['label'] for i in items]

            select = control.selectDialog(labels)
            if select == -1: return 'close://'

            next = [y for x,y in enumerate(items) if x >= select]
            prev = [y for x,y in enumerate(items) if x < select][::-1]

            items = [items[select]]
            items = [i for i in items+next+prev][:40]

            header = control.addonInfo('name') + ': Resolving...'

            progressDialog = control.progressDialog if control.setting('progress.dialog') == '0' else control.progressDialogBG
            progressDialog.create(header, '')
            #progressDialog.update(0)

            block = None

            for i in range(len(items)):
                try:
                    if items[i]['source'] == block: raise Exception()

                    w = workers.Thread(self.sourcesResolve, items[i])
                    w.start()

                    label = re.sub(' {2,}', ' ', str(items[i]['label']))

                    try:
                        if progressDialog.iscanceled(): break
                        progressDialog.update(int((100 / float(len(items))) * i), label)
                    except:
                        progressDialog.update(int((100 / float(len(items))) * i), str(header) + '[CR]' + label)

                    m = ''

                    for x in range(3600):
                        try:
                            if control.monitor.abortRequested(): return sys.exit()
                            if progressDialog.iscanceled(): return progressDialog.close()
                        except:
                            pass

                        k = control.condVisibility('Window.IsActive(virtualkeyboard)')
                        if k: m += '1'; m = m[-1]
                        if (w.is_alive() == False or x > 30) and not k: break
                        k = control.condVisibility('Window.IsActive(yesnoDialog)')
                        if k: m += '1'; m = m[-1]
                        if (w.is_alive() == False or x > 30) and not k: break
                        time.sleep(0.5)


                    for x in range(30):
                        try:
                            if control.monitor.abortRequested(): return sys.exit()
                            if progressDialog.iscanceled(): return progressDialog.close()
                        except:
                            pass

                        if m == '': break
                        if w.is_alive() == False: break
                        time.sleep(0.5)


                    if w.is_alive() == True: block = items[i]['source']

                    if self.url == None: raise Exception()

                    self.selectedSource = items[i]['label']

                    try: progressDialog.close()
                    except: pass

                    control.execute('Dialog.Close(virtualkeyboard)')
                    control.execute('Dialog.Close(yesnoDialog)')
                    return self.url
                except:
                    pass

            try: progressDialog.close()
            except: pass
            del progressDialog

        except:
            try: progressDialog.close()
            except: pass
            del progressDialog
            log_utils.log('sourcesDialog', 1)


    def sourcesDirect(self, items):
        u = None

        header = control.addonInfo('name') + ': Resolving...'

        try:
            control.sleep(1000)

            progressDialog = control.progressDialog if control.setting('progress.dialog') == '0' else control.progressDialogBG
            progressDialog.create(header, '')
            #progressDialog.update(0)
        except:
            pass

        for i in range(len(items)):
            label = re.sub(' {2,}', ' ', str(items[i]['label']))
            try:
                if progressDialog.iscanceled(): break
                progressDialog.update(int((100 / float(len(items))) * i), label)
            except:
                progressDialog.update(int((100 / float(len(items))) * i), str(header) + '[CR]' + label)

            try:
                if control.monitor.abortRequested(): return sys.exit()

                url = self.sourcesResolve(items[i])
                if u == None: u = url
                if not url == None: break
            except:
                pass

        try: progressDialog.close()
        except: pass
        del progressDialog

        return u


    def errorForSources(self):
        control.infoDialog(control.lang(32401), sound=False, icon='INFO')


    def getAliasTitles(self, imdb, localtitle):
        lang = 'en'

        try:
            t = trakt.getMovieAliases(imdb) if self.content == 'movie' else trakt.getTVShowAliases(imdb)
            t = [i for i in t if i.get('country', '').lower() in [lang, '', 'us']] # and i.get('title', '').lower() != localtitle.lower()]
            t = [i for n, i in enumerate(t) if i.get('title') not in [y.get('title') for y in t[n + 1:]]]
            return t
        except:
            return []


    def getTitle(self, title):
        title = cleantitle.normalize(title)
        return title


    def getPremColor(self, n):
        if n == '0': n = 'blue'
        elif n == '1': n = 'red'
        elif n == '2': n = 'yellow'
        elif n == '3': n = 'deeppink'
        elif n == '4': n = 'cyan'
        elif n == '5': n = 'lawngreen'
        elif n == '6': n = 'gold'
        elif n == '7': n = 'magenta'
        elif n == '8': n = 'yellowgreen'
        elif n == '9': n = 'white'
        elif n == '10': n = 'black'
        elif n == '11': n = 'crimson'
        elif n == '12': n = 'goldenrod'
        elif n == '13': n = 'powderblue'
        elif n == '14': n = 'deepskyblue'
        elif n == '15': n = 'springgreen'
        elif n == '16': n = 'darkcyan'
        elif n == '17': n = 'aquamarine'
        elif n == '18': n = 'mediumturquoise'
        elif n == '19': n = 'khaki'
        elif n == '20': n = 'darkorange'
        elif n == '21': n = 'none'
        else: n = 'gold'
        return n


    def getConstants(self):
        self.itemProperty = 'plugin.video.whitelodge.container.items'

        self.metaProperty = 'plugin.video.whitelodge.container.meta'

        self.sourceFile = control.providercacheFile

        from resources.lib import sources
        self.sourceDict = sources.sources()
        self.module_name = 'Whitelodge:'

