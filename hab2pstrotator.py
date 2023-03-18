from __future__ import annotations

__author__ = 'SQ5RWU'
__author_email__ = 'qyonek+SQ5RWU@gmail.com'

import datetime
import json
import socket
import tkinter
from tkinter import *
import logging
import sys
import requests as requests
import sondehub

__version__ = "1.0.1"
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


def update_statusbar(args):
    tracked_v = args[1].tracked_vehicle
    if tracked_v.get('pst_sent_time'):
        delta_s = int((datetime.datetime.now() - tracked_v.get('pst_sent_time')).total_seconds())
        args[1].status.set("Last POS for ''%s'' %ds ago", tracked_v.get('name'), delta_s)
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
    def __init__(self, root: tkinter.Tk):
        self.sh: sondehub.Stream | None = None
        self.tracked_vehicle_name = None
        self.tracked_vehicle = {'lat': None, 'lon': None, 'alt': None,
                                'datetime': None,
                                'pst_notified': False,
                                'pst_sent_time': None}
        self.ws = None
        self.root = root
        self.vehicle_data = {}
        self.vehicle_list = []

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

        self.track_button = Button(root, text="Track", command=self.send_track)
        self.track_button.pack(fill=BOTH, expand=1)
        self.track_button.config(state=DISABLED)

        root.resizable(width=FALSE, height=FALSE)
        root.title(__full_app_name__)

    def refresh_list(self):
        logger.info("refresh_list")
        self.track_button.config(state=DISABLED)
        self.track_button.config(state=DISABLED)
        self.status.set("Loading list")
        try:
            response = requests.get("https://api.v2.sondehub.org/amateur/telemetry?duration=1d", timeout=30)
            hab_data = json.loads(response.text)
            logger.info("Got data %d objects" % (len(hab_data)))
            self.status.set("Got data %d objects" % (len(hab_data)))

            self.listbox.delete(0, END)
            self.vehicle_data = {}

            for key, row in hab_data.items():
                if len(row):
                    for sentence in row.values():
                        vehicle_name = key
                        if vehicle_name:
                            if vehicle_name not in self.vehicle_data:
                                try:
                                    dt = datetime.datetime.strptime(sentence['datetime'].split('.')[0],
                                                                    '%Y-%m-%dT%H:%M:%S')
                                except:
                                    dt = None
                                self.vehicle_data[vehicle_name] = {
                                    'name': vehicle_name,
                                    'datetime': dt,
                                    'lat': sentence.get('lat', None),
                                    'lon': sentence.get('lon', None),
                                    'alt': sentence.get('alt', None),
                                }
            self.vehicle_list = sorted(self.vehicle_data.keys())

            for vehicle_name in self.vehicle_list:
                self.listbox.insert(END, vehicle_name)
        except Exception as e:
            logger.exception('While refreshing list')
            self.status.set("Error while loading list")
            return

        self.status.set("Loaded")
        self.track_button.config(state=NORMAL)
        self.track_button.config(state=NORMAL)

    def send_track(self):
        cur_sel = self.listbox.curselection()
        if len(cur_sel):
            vehicle_name = self.vehicle_list[int(cur_sel[0])]
            vehicle = self.vehicle_data[vehicle_name]
            logger.info(vehicle)
            self.status.set("Starting tracking %s" % (vehicle_name,))
            self.start_tracking(vehicle)

    def start_tracking(self, vehicle):
        self.tracked_vehicle_name = vehicle['name']
        self.tracked_vehicle = vehicle
        self.tracked_vehicle['pst_notified'] = False
        self.update_pst()
        if not self.sh:
            self.sh = sondehub.Stream(prefix='amateur', on_message=self.on_stream_message,
                                      on_connect=self.on_connect, on_log=self.on_log)

    def on_stream_message(self, payload):
        if self.tracked_vehicle_name and payload and isinstance(payload, dict):
            if payload.get('payload_callsign') == self.tracked_vehicle_name:
                try:
                    dt = datetime.datetime.strptime(payload['datetime'].split('.')[0], '%Y-%m-%dT%H:%M:%S')
                    if not self.tracked_vehicle['datetime'] or self.tracked_vehicle['datetime'] < dt:
                        self.tracked_vehicle['name'] = self.tracked_vehicle_name
                        self.tracked_vehicle['lat'] = payload['lat']
                        self.tracked_vehicle['lon'] = payload['lon']
                        self.tracked_vehicle['alt'] = payload['alt']
                        self.tracked_vehicle['datetime'] = dt
                        self.tracked_vehicle['pst_notified'] = False
                        self.tracked_vehicle['pst_sent_time'] = None
                        self.update_pst()
                except Exception as e:
                    logger.exception('While processing MQTT data')

    def on_connect(self, *args, **kwargs):
        logger.info("Connected MQTT")

    def on_log(self, mqtt_client, userdata, level, message, *args, **kwargs):
        pass #logger.info("MQTT: %s" % (message,))

    def update_pst(self):
        if self.tracked_vehicle.get('pst_notified', False):
            return

        self.tracked_vehicle['pst_notified'] = True
        self.tracked_vehicle['pst_sent_time'] = datetime.datetime.now()

        try:
            pst_command = "<PST><LLH>%(lat)s,%(lon)s,%(alt)s</LLH></PST>" % self.tracked_vehicle
            logger.info("Sending PST DATA: %s" % (pst_command,))
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(pst_command.encode(), ('127.0.0.1', 12000))
        except Exception as e:
            logger.exception('While sending PST data!')


if __name__ == '__main__':
    logger.info("Staring program")
    tk_root = Tk()

    app = App(tk_root)

    tk_root.after(500, update_statusbar, (tk_root, app,))
    tk_root.mainloop()
    try:
        tk_root.destroy()
    except:
        pass
