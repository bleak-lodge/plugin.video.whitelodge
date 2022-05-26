# -*- coding: utf-8 -*-

import os
import traceback
from datetime import datetime
from kodi_six import xbmc

import six

from io import open

from resources.lib.modules import control


LOGDEBUG = xbmc.LOGDEBUG
# LOGINFO = xbmc.LOGINFO
# LOGNOTICE = xbmc.LOGNOTICE if control.getKodiVersion() < 19 else xbmc.LOGINFO
# LOGWARNING = xbmc.LOGWARNING
# LOGERROR = xbmc.LOGERROR
# LOGFATAL = xbmc.LOGFATAL
# LOGNONE = xbmc.LOGNONE

name = control.addonInfo('name')
version = control.addonInfo('version')
kodi_version = control.getKodiVersion(as_str=True)
sys_platform = control._platform()
DEBUGPREFIX = '[ Whitelodge {0} | {1} | {2} | DEBUG ]'.format(version, kodi_version, sys_platform)
INFOPREFIX = '[ Whitelodge | INFO ]'
LOGPATH = control.transPath('special://logpath/')
log_file = os.path.join(LOGPATH, 'whitelodge.log')
debug_enabled = control.setting('addon.debug')
#debug_log = control.setting('debug.location')


def log(msg, trace=0):

    #print(DEBUGPREFIX + ' Debug Enabled?: ' + six.ensure_str(debug_enabled))
    #print(DEBUGPREFIX + ' Debug Log?: ' + six.ensure_str(debug_log))

    if not debug_enabled == 'true':
        return

    try:
        if trace == 1:
            head = DEBUGPREFIX
            failure = six.ensure_str(traceback.format_exc(), errors='replace')
            _msg = ' %s:\n  %s' % (six.ensure_text(msg, errors='replace'), failure)
        else:
            head = INFOPREFIX
            _msg = '\n    %s' % six.ensure_text(msg, errors='replace')

        #if not debug_log == '0':
        if not os.path.exists(log_file):
            f = open(log_file, 'w')
            f.close()
        with open(log_file, 'a', encoding='utf-8') as f:
            line = '[%s %s] %s%s' % (datetime.now().date(), str(datetime.now().time())[:8], head, _msg)
            f.write(line.rstrip('\r\n')+'\n\n')
        #else:
            #xbmc.log('%s: %s' % (head, _msg), LOGDEBUG)
    except Exception as e:
        try:
            xbmc.log('Whitelodge Logging Failure: %s' % e, LOGDEBUG)
        except:
            pass


def upload_log():
    url = 'https://paste.kodi.tv/'

    if not os.path.exists(log_file):
        w = open(log_file, 'w')
        w.close()
    f = open(log_file, 'rb')
    data = f.read()
    f.close()

    if not data:
        msg = control.lang(32140)
        ok = control.dialog.ok(name, msg)
        if ok: control.openSettings('7.0')

    else:
        import requests
        session = requests.Session()
        UserAgent = 'Whitelodge %s' % version
        try:
            response = session.post(url + 'documents', data=data, headers={'User-Agent': UserAgent})
            #log('log_response: ' + str(response))
            if 'key' in response.json():
                result = url + response.json()['key']
                msg = control.lang(32141) % str(result)
                log('log_upload_url: ' + result)
                control.dialog.ok(name, msg)
            elif 'message' in response.json():
                control.infoDialog('Log upload failed: %s' % str(response.json()['message']), sound=True)
                log('log_upload_msg: %s' % str(response.json()['message']))
            else:
                control.infoDialog('Log upload failed', sound=True)
                log('log_error: %s' % response.text)
        except:
            control.infoDialog('Unable to retrieve the paste url', sound=True)
            log('log_upload_fail', 1)


def empty_log():
    try:
        open(log_file, 'w').close()
        control.infoDialog(control.lang(32057), sound=True, icon='INFO')
    except:
        control.infoDialog('Error emptying log file', sound=True)
        log('log_empty_fail', 1)


def view_log():
    try:
        control.textViewer(file=log_file, heading=log_file)
    except:
        control.infoDialog('Error opening log file', sound=True)
        log('log_view_fail', 1)

