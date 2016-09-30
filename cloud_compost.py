# -*- coding: utf-8 -*-
import os, threading, time, warnings, serial
from flask.exthook import ExtDeprecationWarning
warnings.simplefilter("ignore", category=ExtDeprecationWarning)
from flask import Flask, request, json, render_template, redirect
from flask_mongoengine import MongoEngine
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = os.urandom(16)

# MongoDB config
app.config['MONGODB_DB'] = 'temu_compost'
app.config['MONGODB_HOST'] = 'ds025583.mlab.com'
app.config['MONGODB_PORT'] = 25583
app.config['MONGODB_USERNAME'] = 'yannis'
app.config['MONGODB_PASSWORD'] = 'spacegr'

# Create database connection object
db = MongoEngine(app)

######################  DUMMY DATA   ###########################
dummy_data = {
    "_id": "5784e5afe609a80ad0bef2c5",
    "name": "compost_dummy",
    "country": "Greece",
    "region": "Heraklion",
    "area": "estavromenos",
    "ip": "10.0.10.97"
}
################## GLOBAL VARIABLES #########################
threadFlag_1 = True
threadFlag_2 = True

# ##################    MODELS     ###################################
class compost_Settings(db.Document):
    daily_steering_time = db.DateTimeField(default=datetime.now(), format='%d-%m-%Y')
    steering_duration = db.IntField(max_length=10, default=30000)
    lowest_soil_humidity = db.FloatField(max_length=10, default=55)
    highest_soil_humidity = db.FloatField(max_length=10, default=65)
    lowest_soil_temperature = db.FloatField(max_length=10, default=50)
    usb_port = db.StringField(default='/dev/cu.usbmodem1411')


class compost_Flags(db.Document):
    motor_1 = db.BooleanField(default=False)
    motor_2 = db.BooleanField(default=False)
    Fan = db.BooleanField(default=False)
    Vent = db.BooleanField(default=False)
    Door_1 = db.BooleanField(default=False)
    Door_2 = db.BooleanField(default=False)
    Emergency_Stop = db.BooleanField(default=False)


class compost_devices(db.Document):
    name = db.StringField(max_length=50)
    country = db.StringField(max_length=50)
    region = db.StringField(max_length=50)
    area = db.StringField(max_length=50)
    ip = db.StringField(max_length=100)

    roof_fans = db.BooleanField(default=False)
    stirring = db.BooleanField(default=False)
    ventilation = db.BooleanField(default=False)
    rails_blow = db.BooleanField(default=False)
    watering = db.BooleanField(default=False)

    def __str__(self):
        return self.name


class measurements(db.Document):
    m_type = db.StringField(max_length=100)
    m_value = db.FloatField(max_length=6)
    compost = db.ReferenceField(compost_devices, required=True)
    timestamp = db.DateTimeField(default=datetime.now(), format='%d-%m-%Y')
    meta = {'max_documents': 10000}

    def __str__(self):
        return self.name


###########################################################################

########################## THREADS ######################################

class TheBrains(threading.Thread):
    def __init__(self, threadID, name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name

    def run(self):
        MainOperation()


def MainOperation():
    if threadFlag_1:
        while 1:
            ##########   do stuffff ##############

            time.sleep(2)


poutsa1 = TheBrains(1, 'measurements')

#############################  BASIC FUNCTIONS  ###########################
def steer(duration):
    ser = serial.Serial(compost_Settings.objects.first().usb_port, 115200)



@app.route('/')
def index():
    try:
        compost_device = compost_devices.objects.first_or_404()
    except:
        compost_device = dummy_data
    return render_template('dashboard.html', compost_device=compost_device)


@app.route('/<compost_name>')
def dashboard(compost_name):
    try:
        compost_device = compost_devices.objects.get_or_404(name=compost_name)
    except:
        compost_device = dummy_data
    return render_template('dashboard.html', compost_device=compost_device)


@app.route('/init_db')
def init_db():
    compost_devices(name='Compost_Ilioupoli', country='Greece', region='Athens', area='Ilioupoli').save()
    compost_Settings(daily_steering_time=datetime.now(), steering_duration=30000, lowest_soil_humidity=55,
                     highest_soil_humidity=65, lowest_soil_temperature=50, usb_port='/dev/cu.usbmodem1411').save()
    measurements(m_type="sunlight_in", m_value=50, compost="5784e5afe609a80ad0bef2c5", timestamp=datetime.now()).save()
    measurements(m_type="sunlight_out", m_value=50, compost="5784e5afe609a80ad0bef2c5", timestamp=datetime.now()).save()
    measurements(m_type="soil_temp", m_value=50, compost="5784e5afe609a80ad0bef2c5", timestamp=datetime.now()).save()
    measurements(m_type="soil_hum", m_value=50, compost="5784e5afe609a80ad0bef2c5", timestamp=datetime.now()).save()
    measurements(m_type="air_temp_in", m_value=50, compost="5784e5afe609a80ad0bef2c5", timestamp=datetime.now()).save()
    measurements(m_type="air_hum_in", m_value=50, compost="5784e5afe609a80ad0bef2c5", timestamp=datetime.now()).save()
    measurements(m_type="air_temp_out", m_value=50, compost="5784e5afe609a80ad0bef2c5", timestamp=datetime.now()).save()
    measurements(m_type="air_hum_out", m_value=50, compost="5784e5afe609a80ad0bef2c5", timestamp=datetime.now()).save()
    compost_Flags(motor_1=False, motor_2=False, Fan=False, Vent=False, Door_1=False, Door_2=False, Emergency_Stop=False)
    return 'db initialized'


@app.route('/composts')
def composts():
    return render_template('find_compost.html')


@app.route('/settings')
def settings():
    return render_template('settings.html')


@app.route('/find_compost', methods=['POST'])
def search_compost():
    search_text = request.form['search_text']
    try:
        compost_dev = compost_devices.objects(name__contains=search_text)
    except:
        compost_dev = dummy_data
    return json.dumps(compost_dev)


@app.route('/change_compost/<compost>')
def change_compost(compost):
    try:
        device = compost_devices.objects(name=compost).first()
    except:
        device = dummy_data
    return render_template('change_compost.html', device=device)


@app.route('/change_compost/change_state', methods=['POST'])
def change_state():
    dev_id = request.form['dev_id']
    actuator = request.form['actuator']
    status = request.form['status']
    print(actuator, status)
    try:
        device = compost_devices.objects(id=dev_id)
    except:
        print('paixtike malakia')
    if actuator == 'roof_fans':
        device.update(set__roof_fans=json.loads(status))
    elif actuator == 'ventilation':
        device.update(set__ventilation=json.loads(status))
    elif actuator == 'stirring':
        device.update(set__stirring=json.loads(status))
    elif actuator == 'rails_blow':
        device.update(set__rails_blow=json.loads(status))
    elif actuator == 'watering':
        device.update(set__watering=json.loads(status))
    else:
        print('no actuator selected')
    return 'ok'


@app.route('/change_compost/save_all', methods=['POST'])
def save_all():
    dev_id = request.form['dev_id']
    name = request.form['name']
    country = request.form['country']
    region = request.form['region']
    area = request.form['area']
    ip = request.form['ip']

    device = compost_devices.objects(id=dev_id).first()
    if not device:
        compost_devices(name=name, country=country, region=region, area=area, ip=ip).save()
        print('no device')
    else:
        print('device found')
        device.update(set__name=name.strip(' \t\n\r'),
                      set__country=country.strip(' \t\n\r'),
                      set__region=region.strip(' \t\n\r'),
                      set__area=area.strip(' \t\n\r'),
                      set__ip=ip.strip(' \t\n\r'))
    return redirect('/change_compost/' + name)


if __name__ == '__main__':
    poutsa1.start()
    app.run()
