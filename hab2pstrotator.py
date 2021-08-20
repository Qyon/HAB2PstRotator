__author__ = 'SQ5RWU'
__author_email__ = 'qyonek+SQ5RWU@gmail.com'

import urllib2
import json
import socket
from Tkinter import *
from threading import Thread
from Queue import Queue, Empty
from time import sleep, time
import logging
import sys

__version__ = "0.5.1"
__app_name__ = "HAB2PstRotator"
__full_app_name__ = "%s v.%s" % (__app_name__, __version__,)

logger = logging.getLogger()
handler = logging.FileHandler('hab2pstrotator.log')
handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

def pst_sender(com_queue, com_back_queue):
    # print "thread"
    """

    :param com_queue:
    :type com_queue: Queue
    :param com_back_queue:
    :type com_back_queue: Queue
    """
    vehicle_data = None
    last_position_id = 0
    last_sequence_id = 0
    next_wait = 0
    vehicle_name = None
    vehicle_name_old = None
    while True:
        try:
            data = com_queue.get_nowait()
            logger.info("Tracking vehicle: %s" % data)
        except Empty:
            data = None
        if data:
            vehicle_name = data

        if vehicle_name:
            if vehicle_name_old != vehicle_name:
                vehicle_name_old = vehicle_name
                last_position_id = 0
                last_sequence_id = 0
                vehicle_data = None
            else:
                logger.info('sleep')
                ttl = 150
                if next_wait:
                    ttl = next_wait
                    next_wait = 0
                while ttl > 0:
                    try:
                        data = com_queue.get_nowait()
                        logger.info(data)
                        vehicle_name = data
                        break
                    except Empty:
                        data = None
                    ttl -= 1
                    sleep(0.1)
                    if com_back_queue.empty():
                        com_back_queue.put({
                            'vehicle': vehicle_data,
                            'ttl': ttl,
                            'name': vehicle_name,
                        })
            data_url = "https://legacy-snus.habhub.org/tracker/datanew.php?mode=1day&type=positions&format=json&max_positions=1&position_id=%d&vehicles=%s" % (last_position_id, vehicle_name)
            logger.info(data_url)
            try:
                hab_data = json.loads(
                    urllib2.urlopen(
                        data_url
                    ).read()
                )
            except Exception as e:
                hab_data = {}
                logger.exception("Exception while downloading new position")

            if hab_data.get('positions'):
                for position in hab_data['positions']['position']:
                    if position['vehicle'] == vehicle_name:
                        if not last_position_id or int(position['position_id']) > last_position_id:
                            last_position_id = int(position['position_id'])
                            if not last_sequence_id or last_sequence_id < int(position['sequence']):
                                vehicle_data = position
                            else:
                                next_wait = 50

            else:
                logger.info("No new positions")
        if vehicle_data:
            last_position_id = int(vehicle_data['position_id'])
            last_sequence_id = int(vehicle_data['sequence'])
            pst_command = "<PST><LLH>%(gps_lat)s,%(gps_lon)s,%(gps_alt)s</LLH></PST>" % vehicle_data
            logger.info("%s %s" % (vehicle_data['gps_time'], pst_command,))
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(pst_command, ('127.0.0.1', 12000))

def update_statusbar(args):
    #logger.info(args)
    try:
        data = args[1].com_back_queue.get_nowait()
    except Empty:
        data = None
    if data:
        if data.get('ttl'):
            #args[1].status.set("Update POS in: %ds", data.get('ttl', 0)/10)
            args[1].status.set("Update POS for ''%s'' in: %ds", data.get('name'), data.get('ttl', 0)/10)

    args[0].after(500, update_statusbar, args)

class StatusBar(Frame):

    def __init__(self, master):
        Frame.__init__(self, master)
        self.label = Label(self, bd=1, relief=SUNKEN, anchor=W)
        self.label.pack(fill=X)

    def set(self, format, *args):
        self.label.config(text=format % args)
        self.label.update_idletasks()

    def clear(self):
        self.label.config(text="")
        self.label.update_idletasks()

class App:
    def __init__(self, root):
        """

        :type root: Tk
        """
        self.root = root
        self.vehicle_data = {}
        self.vehicle_list = []

        self.com_queue = Queue()
        self.com_back_queue = Queue()

        self.comm_thread = Thread(target=pst_sender, args=(self.com_queue, self.com_back_queue,))
        self.comm_thread.daemon = True
        self.comm_thread.start()

        self.status = StatusBar(root)
        self.status.pack(side=BOTTOM, fill=X)

        frame = Frame(root, width=300)
        frame.pack()

        self.load_button = Button(root, text="(Re)Load active flights list", command=self.refresh_list)
        self.load_button.pack(fill=BOTH, expand=1)
        frame2 = Frame(root, width=300)

        self.scrollbar = Scrollbar(frame2, orient=VERTICAL)
        self.listbox = Listbox(frame2, yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.listbox.yview)
        self.scrollbar.pack(side=RIGHT, fill=Y)
        self.listbox.pack(fill=BOTH, expand=1)

        frame2.pack(fill=BOTH, expand=1)
        #self.refresh_list()

        self.track_button = Button(root, text="Track", command=self.send_track)
        self.track_button.pack(fill=BOTH, expand=1)
        self.track_button.config(state=DISABLED)

        root.resizable(width=FALSE, height=FALSE)
        #root.iconbitmap('spacenearus.ico')
        root.title(__full_app_name__)



    def refresh_list(self):
        logger.info("refresh_list")
        self.track_button.config(state=DISABLED)
        self.track_button.config(state=DISABLED)
        self.status.set("Loading list")
        try:
            hab_data = []
            start_key = time() - 1*365*24*60*60
            while True:
                tmp = json.loads(urllib2.urlopen(
                    "http://habitat.habhub.org/habitat/_design/flight/_view/end_start_including_payloads?include_docs=true&limit=300&startkey=[%s]" % start_key).read())
                if 'rows' not in tmp or not tmp['rows']:
                    break
                hab_data.extend(tmp['rows'])
                start_key = tmp['rows'][-1]['key'][0] + 1
                self.status.set("Got data %d of %d" % (tmp['offset'], tmp['total_rows']))
                self.root.update()

            self.listbox.delete(0, END)
            self.vehicle_data = {}

            for row in hab_data:
                if 'doc' in row and 'sentences' in row['doc']:
                    for sentence in row['doc']['sentences']:
                        vehicle_name = sentence.get('callsign')
                        if vehicle_name:
                            if vehicle_name not in self.vehicle_data:
                                pass
                            self.vehicle_data[vehicle_name] = {
                                'callsign': vehicle_name,
                                'name': row['doc'].get('name'),
                                'date': row['doc'].get('time_created', ''),
                                'listed': row['key'][3],
                                'start_date': row['key'][0],
                                'end_date': row['key'][1],
                            }
            self.vehicle_list = sorted(self.vehicle_data.keys())
            now = time()
            for vehicle_name, vehicle_data in self.vehicle_data.iteritems():
                if vehicle_data['listed'] and (vehicle_data['end_date'] > now or vehicle_data['start_date'] > now):
                    self.vehicle_list.insert(0, vehicle_name)
            for vehicle_name in self.vehicle_list:
                self.listbox.insert(END, vehicle_name)
        except:
            self.status.set("Error while loading list")
            pass
        self.status.set("Loaded")
        self.track_button.config(state=NORMAL)
        self.track_button.config(state=NORMAL)

    def send_track(self):
        cur_sel = self.listbox.curselection()
        if len(cur_sel):
            vehicle_name = self.vehicle_list[int(cur_sel[0])]
            self.com_queue.put(vehicle_name)
            vehicle = self.vehicle_data[vehicle_name]
            logger.info(vehicle)


if __name__ == '__main__':
    logger.info("Staring program")
    root = Tk()

    app = App(root)

    root.after(500, update_statusbar, (root, app,))
    root.mainloop()
    try:
        root.destroy()
    except:
        pass
