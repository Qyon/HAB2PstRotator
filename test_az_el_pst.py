# coding=utf-8
import socket
import time

__author__ = 'Qyon'
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

for az_g in range(0, 100):

    pst_command = "<PST><ELEVATION>%0.2f</ELEVATION></PST>" % (az_g / 10.0)


    sock.sendto(pst_command, ('127.0.0.1', 12000))
    time.sleep(1)