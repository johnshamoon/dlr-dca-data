import requests
import json
import sys
import time
from datetime import datetime, timedelta

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
    headers = {"Authorization":"BEARER {}".format(access_token)}
    return headers


class Park():
    def __init__(self):
        self._id = "330339"
        self._data = None
        try:
            s = requests.get("https://api.wdpro.disney.go.com/global-pool-override-B/facility-service/theme-parks/{}".format(self._id), headers=get_headers())
            self._data = json.loads(s.content)
        except Exception as e:
            print(e)


    def get_data(self):
        return self._data


    def get_wait_times(self):
        s = requests.get("https://api.wdpro.disney.go.com/facility-service/theme-parks/{}/wait-times".format(self._id),
                headers=get_headers())
        loaded_times = json.loads(s.content)

        times = {}
        for i in range(len(loaded_times['entries'])):
            if 'postedWaitMinutes' in loaded_times['entries'][i]['waitTime']:
                times[loaded_times['entries'][i]['name']] = loaded_times['entries'][i]['waitTime']['postedWaitMinutes']
        times['time'] = time.time()

        return times


    def write_wait_times(self, file_name="data.json", current_wait_times=None):
        data = open(file_name, "a")
        if not current_wait_times:
            current_wait_times = self.get_wait_times()

        json.dump(current_wait_times, data)
        data.write(",")

        data.close()


    def read_wait_times(self, file_name="data.json"):
        try:
            data = open("data.json", "r").read()
        except FileNotFoundError:
            return None

        return json.loads('[' + data[0:-1] + ']')



# TODO
#
# 1. Only write to the file when the park is open
# 2. Create a new file when the park opens every day.
# 3. Set it up on a Raspberry Pi to gather data for a full day.
# 4. Take magic mornings into account
if __name__ == '__main__':
    time.sleep(60*60*12)
    park = Park()

    while True:
        park.write_wait_times()
        time.sleep(5*60)
