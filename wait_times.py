from datetime import datetime, timedelta
from pytz import timezone
import json
import matplotlib.pyplot as plt
import pandas as pd
import requests
import sys
import time

time_of_expire = None
access_token = None


def authentication():
    r = requests.get("https://disneyworld.disney.go.com/authentication/get-client-token")
    auth = json.loads(r.content)
    return auth['access_token'], auth['expires_in']


def get_headers():
    global time_of_expire
    global access_token

    if time_of_expire == None or (datetime.now() > time_of_expire):
        access_token, expires_in = authentication()
        time_of_expire = datetime.now() + timedelta(seconds=(expires_in-10))
    headers = {"Authorization": "BEARER {}".format(access_token)}
    return headers


class Park():
    DLR_ID = "330339"
    DCA_ID = "336894"
    _RIDES = [
        "Astro Orbitor",
        "Autopia",
        "Big Thunder Mountain Railroad",
        "Casey Jr. Circus Train",
        "Disneyland Monorail",
        "Disneyland Railroad",
        "Dumbo the Flying Elephant",
        "Walt Disney's Enchanted Tiki Room",
        "Gadget's Go Coaster",
        "Haunted Mansion",
        "Jungle Cruise",
        "King Arthur Carrousel",
        "Matterhorn Bobsleds",
        "Mickey's House and Meet Mickey",
        "Pinocchio's Daring Journey",
        "Roger Rabbit's Car Toon Spin",
        "Snow White's Scary Adventures",
        "Space Mountain",
        "Splash Mountain",
        "Storybook Land Canal Boats",
        "The Many Adventures of Winnie the Pooh",
        "\"it's a small world\"",
        "Alice in Wonderland",
        "Meet Disney Princesses at Royal Hall",
        "Buzz Lightyear Astro Blasters",
        "Indiana Jones Adventure",
        "Mad Tea Party",
        "Mr. Toad's Wild Ride",
        "Peter Pan's Flight",
        "Pirates of the Caribbean",
        "Star Tours- The Adventures Continue"
    ]
    _LANDS = {
        'Tomorrowland': [
            'Astro Orbitor',
            'Autopia',
            'Buzz Lightyear Astro Blasters',
            'Disneyland Monorail',
            'Finding Nemo Submarine Voyage',
            'Space Mountain',
            'Star Tours- The Adventures Continue',
        ],
        'Fantasyland': [
            'Alice in Wonderland',
            'Casey Jr. Circus Train',
            'Dumbo the Flying Elephant',
            '"it\'s a small world"',
            'King Arthur Carrousel',
            'Mad Tea Party',
            'Matterhorn Bobsleds',
            'Mr. Toad\'s Wild Ride',
            'Peter Pan\'s Flight',
            'Pinocchio\'s Daring Journey',
            'Snow White\'s Scary Adventures',
            'Storybook Land Canal Boats'
        ],
        'Frontierland': [
            'Big Thunder Mountain Railroad'
        ],
        'Adventureland': [
            'Indiana Jones Adventure',
            'Jungle Cruise',
            'Walt Disney\'s Enchanted Tiki Room'
        ],
        'New Orleans Square': [
            'Haunted Mansion',
            'Pirates of the Caribbean'
        ],
        'Critter Country': [
            'Splash Mountain',
            'The Many Adventures of Winnie the Pooh'
        ],
        'Toon Town': [
            'Gadget\'s Go Coaster',
            'Roger Rabbit\'s Car Toon Spin',
        ],
        'Misc': [
            'Disneyland Railroad',
            'Meet Disney Princesses at Royal Hall',
            'Mickey\'s House and Meet Mickey',
        ]
    }


    def __init__(self, park_id=DLR_ID):
        self._id = park_id

        # Unused Park Data (for now).
        self._data = None
        try:
            s = requests.get("https://api.wdpro.disney.go.com/global-pool-override-B/facility-service/theme-parks/{}".format(self._id), headers=get_headers())
            self._data = json.loads(s.content)
        except Exception as e:
            print(e)


    def get_wait_times(self):
        s = requests.get("https://api.wdpro.disney.go.com/facility-service/theme-parks/{}/wait-times".format(self._id), headers=get_headers())
        loaded_times = json.loads(s.content)

        times = {}
        for i in range(len(loaded_times['entries'])):
            if 'postedWaitMinutes' in loaded_times['entries'][i]['waitTime']:
                times[loaded_times['entries'][i]['name']] = loaded_times['entries'][i]['waitTime']['postedWaitMinutes']

        # If the park is open.
        if len(times) != 0:
            for key, _ in times.items():
                # Remove unicode in key.
                if '\u00a0' in key:
                    old_key = key
                    key = key.replace('\u00a0', '')
                    # Use the new key, but keep the old value.
                    times[key] = times.pop(old_key)

            for i in range(len(self._RIDES)):
                ride = self._RIDES[i]
                if ride not in times.keys():
                    times[ride] = 0

            time = datetime.now(timezone('America/Los_Angeles'))
            if time.hour < 7:
                # Don't write anything if it's not earlier than 7am
                times = None
            else:
                # Add 24-hour timestamp (PST).
                times['time'] = time.strftime('%H:%M:%S')

        return times


    def write_wait_times(self, current_wait_times=None):
        # Get today's date. Will make a new file every day.
        file_name = 'data/' + datetime.now(timezone('America/Los_Angeles')).strftime('%m-%d-%Y') + '.json'
        if not current_wait_times:
            current_wait_times = self.get_wait_times()

        # If the park is open.
        if current_wait_times and len(current_wait_times) != 0:
            data = open(file_name, 'a')

            json.dump(current_wait_times, data)
            data.write(',')

            data.close()


    def read_wait_times(self, data_file):
        try:
            data = open(data_file, 'r').read()
        except FileNotFoundError as e:
            print(e)
            return None

        # Strip the last comma and put the dictionaries into an array.
        ride_data = json.loads('[' + data[0:-1] + ']')
        # Read in the times as HH:MM:SS and convert them into a datetime object.
        times = [d['time'] for d in ride_data]
        cleaned_time = [datetime.strptime(times[i], '%H:%M:%S').time() for i in range(len(times))]
        for i in range(len(ride_data)):
            ride_data[i]['time'] = cleaned_time[i]

        return ride_data


    def graph_all_rides(self, data_file):
        data = self.read_wait_times(data_file)

        df = pd.DataFrame(data)
        df.plot(x='time', figsize=(8, 8))
        # Outside bottom right.
        plt.legend(loc=(1.04, 0))
        plt.show()


    def graph_by_land(self, data_file):
        data = self.read_wait_times(data_file)
        df = pd.DataFrame(data)

        for key in self._LANDS.keys():
            nrows = 1
            ncols = 3
            if len(self._LANDS[key]) == 1:
                ncols = 1
                height = 4
                width = 4
            elif len(self._LANDS[key]) <= ncols:
                height = 4
                width = ncols * 4
            else:
                nrows = int((len(self._LANDS[key])) / ncols) + 1
                height = nrows * 4
                width = ncols * 4

            ax = df.plot(x='time',
                         y=self._LANDS[key],
                         figsize=(width, height),
                         subplots=True,
                         layout=(nrows, ncols),
                         title=self._LANDS[key],
                         legend=False,
                         grid=True,
                         sharex=False)

            for axes in ax:
                for axis in axes:
                    plt.setp(axis.get_xticklabels(), rotation=30, visible=True)
                    axis.set_xlabel('Time of Day')
                    axis.set_ylabel('Wait Time')

            fig = plt.gcf()
            fig.suptitle(key, y=1.05, fontsize=16)
            plt.tight_layout()
            plt.subplots_adjust(hspace=0.5)
            plt.show()


if __name__ == '__main__':
    park = Park()

    while True:
        park.write_wait_times()
        time.sleep(5*60)
