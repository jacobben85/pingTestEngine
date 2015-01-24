import urllib
import requests
import xml.etree.ElementTree as ET
import subprocess
import datetime
import multiprocessing
import os
import time


# variables
workspace = '/tmp/'
ping_frequency = 5
source_xml = 'http://nfl.univision.com/feed/sports/american-football/nfl/2014/scheduleWithScores.xml'
event_list = []
error_list = []
event_count = 0


def init():
    global event_list
    global error_list
    global event_count

    event_list[:] = []
    error_list[:] = []
    event_count = 0


def send_notification(display_message):
    subprocess.check_call(['/usr/bin/osascript', '-e', 'display notification "' + display_message + '" with title "NFL ping test"'])


def source_list():
    global event_count
    global event_list

    message = ''

    # download the source xml
    # urllib.urlopen(source_xml)
    response = requests.get(source_xml)
    if response.status_code == 200:
        if response.headers['Content-Type'].find('xml') > -1:
            urllib.urlretrieve(source_xml, '/tmp/scheduleWithScores.xml')
            xml_data = ET.parse('/tmp/scheduleWithScores.xml')
            for node in xml_data.iter('uim-american-football'):
                last_update = node.attrib.get('last-updated')
                received = datetime.datetime.strptime(last_update, "%Y-%m-%dT%H:%MZ")
                utc_now = datetime.datetime.utcnow()
                time_diff = utc_now - received

                if int(time_diff.total_seconds() / 60) > 62:
                    message = 'Schedule last updated at :' + last_update

                for tournament in node.iter('tournament-stage'):

                    for tournament_round in tournament.iter('tournament-round'):

                        for event_meta in tournament_round.iter('event-metadata'):
                            event_name = event_meta.attrib.get('event-key')
                            event_count += 1

                            for event_status in event_meta.iter('sports-property'):
                                event_status_id = event_status.attrib.get('id')
                                if int(event_status_id) > 0:
                                    event_list.append(event_name[22:])

            os.remove('/tmp/scheduleWithScores.xml')

        else:
            message = 'XML not found, header detail' + response.headers['Content-Type']
    else:
        message = 'Http request failed, status code : ' + response.status_code

    if message != '':
        send_notification(message)


def validate_events():
    global event_list
    global error_list

    for event_id in event_list:
        event_response = requests.get('http://nfl.univision.com/feed/sports/american-football/nfl/2014/event-nfl-' + event_id + '.xml')
        if event_response.status_code != 200:
            error_list.append("event:" + event_id + " error code:" + str(event_response.status_code))


def display_error_list():
    global error_list

    if len(error_list):
        send_notification("failed list : " + ', '.join(error_list))


def display_report():
    global event_count
    global event_list
    global error_list

    message = "Total events : " + str(event_count) + " events validated : " + str(len(event_list)) + " total errors : " + str(len(error_list))
    send_notification(message)


def multi_event_process(events):
    for event_id in events:
        event_xml = 'http://nfl.univision.com/feed/sports/american-football/nfl/2014/event-nfl-' + event_id + '.xml'
        event_response = requests.get(event_xml)
        if event_response.status_code != 200:
            send_notification("Error : " + event_id)
        else:
            urllib.urlretrieve(event_xml, '/tmp/' + event_id + '.xml')
            xml_data = ET.parse('/tmp/' + event_id + '.xml')
            for node in xml_data.iter('event-metadata'):
                event_key = node.attrib.get('event-key')
                if event_id != event_key[28:]:
                    send_notification("Event Id mismatch : " + event_id)
            os.remove('/tmp/' + event_id + '.xml')


def start_processing():
    global event_list

    source_list()
    validate_events()
    display_error_list()
    display_report()
    chunks = [event_list[x:x+60] for x in xrange(0, len(event_list), 60)]

    for chunk in chunks:
        process = multiprocessing.Process(target=multi_event_process, args=(chunk, ))
        process.demon = True
        process.start()


if __name__ == "__main__":

    # while True:
    init()
    start_processing()
    # time.sleep(60)

