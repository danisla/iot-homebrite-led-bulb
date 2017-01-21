#!/usr/bin/python2.7

""" UPnP CSRMesh Dimmable Light bridge for SmartThings

Copyright 2016 Dan Isla <dan.isla@gmail.com>

Description: Control CSRMesh Dimmable Light.

Dependencies: python-twisted

Licensed under the Apache License, Version 2.0 (the "License"); you may not use
this file except in compliance with the License. You may obtain a copy of the
License at:

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import os
import argparse
import logging
from time import time, sleep
from twisted.web import server, resource
from twisted.internet import reactor
from twisted.internet.defer import succeed
from twisted.internet.protocol import DatagramProtocol
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer
from twisted.web._newclient import ResponseFailed
from zope.interface import implements
import uuid
from uuid import getnode as get_mac
import commands
import time
import random

from feit_light import Feit

SSDP_PORT = 1900
SSDP_ADDR = '239.255.255.250'
UUID = uuid.uuid3(uuid.NAMESPACE_OID, 'dimmable_light_' + str(get_mac()))
SEARCH_RESPONSE = 'HTTP/1.1 200 OK\r\nCACHE-CONTROL:max-age=30\r\nEXT:\r\nLOCATION:%s\r\nSERVER:Linux, UPnP/1.0, CSRMesh_Light/1.0\r\nST:%s\r\nUSN:uuid:%s::%s'

def determine_ip_for_host(host):
    """Determine local IP address used to communicate with a particular host"""
    test_sock = DatagramProtocol()
    test_sock_listener = reactor.listenUDP(0, test_sock) # pylint: disable=no-member
    test_sock.transport.connect(host, 1900)
    my_ip = test_sock.transport.getHost().host
    test_sock_listener.stopListening()
    return my_ip

def chip_status(fn):
    '''Wraps a function with toggling of CHIP status light'''

    def wrapper(*args, **kwargs):
        commands.getoutput('/usr/sbin/i2cset -f -y 0 0x34 0x93 0x1')
        res = fn(*args, **kwargs)
        sleep(0.5)
        commands.getoutput('/usr/sbin/i2cset -f -y 0 0x34 0x93 0x0')

        return res

    return wrapper

def retry(fn, attempts=3, delay=2):

    def wrapper(*args, **kwargs):
        last_exception = Exception("Failed to execute")

        for i in range(attempts):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                last_exception = e
                logging.warn("Exception when executing function, attempt %d/%d" % (i+1,attempts))
                sleep(delay)
        raise e

    return wrapper

class CSRMeshLightApi(resource.Resource):
    """HTTP server that controls the Soundbar"""

    isLeaf = True

    def __init__(self, device_target, mac_list, pin):
        self.device_target = device_target
        self.last_send = None
        resource.Resource.__init__(self)

        self.mac_list = mac_list
        self.pin = pin
        self.light = None
        self.level = 0

        self.connect()

    @retry
    @chip_status
    def connect(self):
        mac = self.mac_list[random.randrange(len(self.mac_list))]
        logging.info("Connecting to csrmesh device: %s" % mac)
        self.light = Feit(mac, self.pin)
        self.light.connect()
        logging.info("Connected to device")

    def disconnect(self):
        self.light.disconnect()

    @retry
    def set_brightness(self, level):
        try:
            return self.light.set_brightness(level)
        except Exception as e:
            logging.warn("Exception when sending BLE command: '%s', reconnecting." % str(e))
            self.connect()
            return self.light.set_brightness(level)

    @chip_status
    def render_GET(self, request): # pylint: disable=invalid-name
        """Handle polling requests from ST hub"""

        logging.info("CSRMeshLightApi request from %s for %s and args: %s",
                     request.getClientIP(),
                     request.path,
                     request.args)

        if request.path == '/light_on':
            self.set_brightness(255)
            self.level = 100
            return "OK"

        elif request.path == "/light_off":
            self.set_brightness(0)
            self.level = 0
            return "OK"

        elif request.path == '/light_level':
            self.level = (255/(100/int(request.args["level"][0])))
            self.set_brightness(self.level)
            return "OK"

        elif request.path == '/light_bright':
            self.level = min(self.level + 25, 100)
            self.set_brightness(self.level)
            return "OK"

        elif request.path == '/light_dim':
            self.level = max(self.level - 25, 0)
            self.set_brightness(self.level)
            return "OK"

        else:
            logging.info("Received bogus request from %s for %s",
                         request.getClientIP(),
                         request.path)
            return "OK"

class SSDPServer(DatagramProtocol):
    """Receive and response to M-SEARCH discovery requests from SmartThings hub"""

    def __init__(self, interface='', status_port=0, device_target=''):
        self.interface = interface
        self.device_target = device_target
        self.status_port = status_port
        self.port = reactor.listenMulticast(SSDP_PORT, self, listenMultiple=True) # pylint: disable=no-member
        self.port.joinGroup(SSDP_ADDR, interface=interface)
        reactor.addSystemEventTrigger('before', 'shutdown', self.stop) # pylint: disable=no-member

    def datagramReceived(self, data, (host, port)):
        try:
            header, _ = data.split('\r\n\r\n')[:2]
        except ValueError:
            return
        lines = header.split('\r\n')
        cmd = lines.pop(0).split(' ')
        lines = [x.replace(': ', ':', 1) for x in lines]
        lines = [x for x in lines if len(x) > 0]
        headers = [x.split(':', 1) for x in lines]
        headers = dict([(x[0].lower(), x[1]) for x in headers])

        logging.debug('SSDP command %s %s - from %s:%d with headers %s', cmd[0], cmd[1], host, port, headers)

        search_target = ''
        if 'st' in headers:
            search_target = headers['st']

        if cmd[0] == 'M-SEARCH' and cmd[1] == '*' and search_target in self.device_target:
            logging.info('Received %s %s for %s from %s:%d', cmd[0], cmd[1], search_target, host, port)
            url = 'http://%s:%d/status' % (determine_ip_for_host(host), self.status_port)
            response = SEARCH_RESPONSE % (url, search_target, UUID, self.device_target)
            self.port.write(response, (host, port))
        else:
            logging.debug('Ignored SSDP command %s %s', cmd[0], cmd[1])

    def stop(self):
        """Leave multicast group and stop listening"""
        self.port.leaveGroup(SSDP_ADDR, interface=self.interface)
        self.port.stopListening()

def main():
    """Main function to handle use from command line"""
    import sys

    arg_proc = argparse.ArgumentParser(description='Implements a RESTful Remote for the SmartThings hub')
    arg_proc.add_argument('--httpport', dest='http_port', help='HTTP port number', default=8080, type=int)
    arg_proc.add_argument('--deviceindex', dest='device_index', help='Device index', default=1, type=int)
    arg_proc.add_argument('--mac', dest='mac', help='One or more BLE MAC addresses, random one is picked.', type=str, nargs='+')
    arg_proc.add_argument('--pin', dest='pin', help='Light PIN', type=int)
    arg_proc.add_argument('--debug', dest='debug', help='Enable debug messages', default=False, action='store_true')
    options = arg_proc.parse_args()

    if options.mac is None:
        logging.error("No --mac given")
        sys.exit(1)

    if options.pin is None:
        logging.error("No --pin given")
        sys.exit(1)

    device_target = 'urn:schemas-upnp-org:device:DimmableLight:%d' % (options.device_index)
    log_level = logging.INFO
    if options.debug:
        log_level = logging.DEBUG

    logging.basicConfig(format='%(asctime)-15s %(levelname)-8s %(message)s', level=log_level)

    logging.info('Initializing CSRMesh Light Controller')

    # SSDP server to handle discovery
    SSDPServer(status_port=options.http_port, device_target=device_target)

    # HTTP site to handle subscriptions/polling
    light_api = CSRMeshLightApi(device_target, options.mac, options.pin)
    dev_api = server.Site(light_api)
    reactor.listenTCP(options.http_port, dev_api)

    logging.info('Initialization complete, listening on HTTP port %s' % (options.http_port))

    reactor.run() # pylint: disable=no-member

if __name__ == "__main__":
    main()
