# coding=utf-8
import socket
import time

__author__ = 'Qyon'
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

pst_command = "<PST><LLH>54.02523,20.89581,1</LLH></PST>"

sock.sendto(pst_command, ('127.0.0.1', 12000))
time.sleep(1)
