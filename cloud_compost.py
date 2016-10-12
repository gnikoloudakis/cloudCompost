# -*- coding: utf-8 -*-
import os, threading, time, warnings, serial, random
from flask.exthook import ExtDeprecationWarning

warnings.simplefilter("ignore", category=ExtDeprecationWarning)
from flask import Flask, request, json, render_template, redirect, jsonify
from flask_mongoengine import MongoEngine
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from m_stats import Stats

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

# Configure ApScheduler
sched = BackgroundScheduler()
sched2 = BackgroundScheduler()

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

sunlight_in = Stats
sunlight_out = Stats
soil_temperature = Stats
soil_humidity = Stats
air_temperature_in = Stats
air_temperature_out = Stats
air_humidity_in = Stats
air_humidity_out = Stats


# ##################    MODELS     ###################################
class compost_devices(db.Document):
    name = db.StringField(max_length=50)
    country = db.StringField(max_length=50)
    region = db.StringField(max_length=50)
    area = db.StringField(max_length=50)
    ip = db.StringField(max_length=100)


class Log(db.Document):
    l_timestamp = db.DateTimeField(default=datetime.now(), format='%d-%m-%Y')
    action = db.StringField()
    compost = db.ReferenceField(compost_devices, required=True)
    meta = {'max_documents': 100}


class Errors(db.Document):
    e_timestamp = db.DateTimeField(default=datetime.now(), format='%d-%m-%Y')
    error = db.StringField()
    compost = db.ReferenceField(compost_devices, required=True)
    meta = {'max_documents': 100}


class compost_Settings(db.Document):
    daily_steering_time = db.StringField(default='12:00')
    steering_duration = db.StringField(max_length=10, default='30000')
    lowest_soil_humidity = db.StringField(max_length=10, default='55')
    highest_soil_humidity = db.StringField(max_length=10, default='65')
    lowest_soil_temperature = db.StringField(max_length=10, default='50')
    usb_port = db.StringField(default='/dev/cu.usbmodem1411')
    sleep_time_for_motors = db.StringField(max_length=10, default='30')


class compost_Flags(db.Document):
    Motor_F = db.BooleanField(default=False)
    Motor_B = db.BooleanField(default=False)
    Motor_R = db.BooleanField(default=False)
    Motor_L = db.BooleanField(default=False)
    Fan = db.BooleanField(default=False)
    Vent = db.BooleanField(default=False)
    Door_1 = db.BooleanField(default=False)
    # Door_2 = db.BooleanField(default=False)
    Emergency_Stop = db.BooleanField(default=False)
    compost = db.ReferenceField(compost_devices, required=True)

    def __str__(self):
        return self.name


class measurements(db.Document):
    m_type = db.StringField(max_length=100)
    m_value = db.FloatField(max_length=6)
    compost = db.ReferenceField(compost_devices, required=True)
    m_timestamp = db.DateTimeField(default=datetime.now(), format='%d-%m-%Y')
    meta = {'max_documents': 5000}

    def __str__(self):
        return self.name


# Initialize Serial Interface
# ser = serial.Serial(compost_Settings.objects.first().usb_port, 115200)  # setup serial communicatin port


###########################################################################

#############################  BASIC FUNCTIONS  ###########################
def read_variables(compost_id):
    ser = serial.Serial(compost_Settings.objects.first().usb_port, 115200)  # setup serial communication port
    ser.write('/variables\r'.encode())
    update_variables(ser.readline())
    Log(l_timestamp=datetime.now(), action='variables', compost=compost_id)


def update_variables(data):
    dataDict = json.loads(data)
    compost_id = compost_devices.objects(name=dataDict['name']).first().id
    measurements(m_type="sunlight_in", m_value=dataDict['variables']['sunlight_in'], compost=compost_id,
                 m_timestamp=datetime.now()).save()
    if sunlight_in.add_points(dataDict['variables']['sunlight_in']):
        pass
    measurements(m_type="sunlight_out", m_value=dataDict['variables']['sunlight_out'],
                 compost=compost_id, m_timestamp=datetime.now()).save()
    if sunlight_out.add_points(dataDict['variables']['sunlight_out']):
        pass
    measurements(m_type="soil_temp", m_value=dataDict['variables']['soil_temp'], compost=compost_id,
                 m_timestamp=datetime.now()).save()
    if soil_temperature.add_points(dataDict['variables']['soil_temp']):
        pass
    measurements(m_type="soil_hum", m_value=dataDict['variables']['soil_hum'], compost=compost_id,
                 m_timestamp=datetime.now()).save()
    if soil_humidity.add_points(dataDict['variables']['soil_hum']):
        pass
    measurements(m_type="air_temp_in", m_value=dataDict['variables']['air_temp_in'], compost=compost_id,
                 m_timestamp=datetime.now()).save()
    if air_temperature_in.add_points(dataDict['variables']['air_temp_in']):
        pass
    measurements(m_type="air_hum_in", m_value=dataDict['variables']['air_hum_in'], compost=compost_id,
                 m_timestamp=datetime.now()).save()
    if air_humidity_in.add_points(dataDict['variables']['air_hum_in']):
        pass
    measurements(m_type="air_temp_out", m_value=dataDict['variables']['air_temp_out'],
                 compost=compost_id, m_timestamp=datetime.now()).save()
    if air_temperature_out.add_points(dataDict['variables']['air_temp_out']):
        pass
    measurements(m_type="air_hum_out", m_value=dataDict['variables']['air_hum_out'], compost=compost_id,
                 m_timestamp=datetime.now()).save()
    if air_humidity_out.add_points(dataDict['variables']['air_hum_out']):
        pass

    compost_Flags.update(set__Motor_F=bool(dataDict['variables']['Motor_R']),
                         set__Motor_B=bool(dataDict['variables']['Motor_L']),
                         set__Fan=bool(dataDict['variables']['Fan']),
                         set__Vent=bool(dataDict['variables']['Vent']),
                         set__Door_1=bool(dataDict['variables']['Door_1']),
                         set__Emergency_Stop=bool(dataDict['variables']['Emergency_Stop']))


def motor_forward(compost_id):
    ser = serial.Serial(compost_Settings.objects.first().usb_port, 115200)  # setup serial communication port
    ser.write('/stirForwardOn\r'.encode())  # Stir Forward
    ser.write('/variables\r'.encode())
    update_variables(ser.readline())
    if compost_Flags.objects(id=compost_id).first().Motor_F:
        Log(l_timestamp=datetime.now(), action='Motor Forward Started', compost=compost_id)
    time.sleep(compost_Settings.objects.first().steering_duration)
    ser.write('/stirForwardOff\r'.encode())  # Stir Forward Off
    ser.write('/variables\r'.encode())
    update_variables(ser.readline())
    if not compost_Flags.objects(id=compost_id).first().Motor_F:
        Log(l_timestamp=datetime.now(), action='Motor Forward Stopped', compost=compost_id)


def motor_backward(compost_id):
    ser = serial.Serial(compost_Settings.objects.first().usb_port, 115200)  # setup serial communication port
    ser.write('/stirBackwoardOn\r'.encode())  # Stir Forward
    ser.write('/variables\r'.encode())
    update_variables(ser.readline())
    if compost_Flags.objects(id=compost_id).first().Motor_B:
        Log(l_timestamp=datetime.now(), action='Motor Backward Started', compost=compost_id)
    time.sleep(compost_Settings.objects.first().steering_duration)
    ser.write('/stirBackwoardOff\r'.encode())  # Stir Forward Off
    ser.write('/variables\r'.encode())
    update_variables(ser.readline())
    if not compost_Flags.objects(id=compost_id).first().Motor_B:
        Log(l_timestamp=datetime.now(), action='Motor Backward Stopped', compost=compost_id)


def motor_right(compost_id):
    ser = serial.Serial(compost_Settings.objects.first().usb_port, 115200)  # setup serial communication port
    ser.write('/stirRightOn\r'.encode())  # Stir Right
    ser.write('/variables\r'.encode())
    update_variables(ser.readline())
    if compost_Flags.objects(id=compost_id).first().Motor_R:
        Log(l_timestamp=datetime.now(), action='Motor Right Started', compost=compost_id)
    time.sleep(compost_Settings.objects.first().steering_duration)
    ser.write('/stirRightOff\r'.encode())  # Stir Right Off
    ser.write('/variables\r'.encode())
    update_variables(ser.readline())
    if not compost_Flags.objects(id=compost_id).first().Motor_R:
        Log(l_timestamp=datetime.now(), action='Motor Right Stopped', compost=compost_id)


def motor_left(compost_id):
    ser = serial.Serial(compost_Settings.objects.first().usb_port, 115200)  # setup serial communication port
    ser.write('/stirLeftOn\r'.encode())  # Stir Left
    ser.write('/variables\r'.encode())
    update_variables(ser.readline())
    if compost_Flags.objects(id=compost_id).first().Motor_L:
        Log(l_timestamp=datetime.now(), action='Motor Left Started', compost=compost_id)
    time.sleep(compost_Settings.objects.first().steering_duration)
    ser.write('/stirLeftOff\r'.encode())  # Stir Left Off
    ser.write('/variables\r'.encode())
    update_variables(ser.readline())
    if not compost_Flags.objects(id=compost_id).first().Motor_L:
        Log(l_timestamp=datetime.now(), action='Motor Left Stopped', compost=compost_id)


def startFan(compost_id):
    ser = serial.Serial(compost_Settings.objects.first().usb_port, 115200)  # setup serial communication port
    ser.write('/startFan\r'.encode())
    ser.write('/variables\r'.encode())
    update_variables(ser.readline())
    if compost_Flags.objects(id=compost_id).first().Fan:
        Log(l_timestamp=datetime.now(), action='Roof Fan Started', compost=compost_id)


def stopFan(compost_id):
    ser = serial.Serial(compost_Settings.objects.first().usb_port, 115200)  # setup serial communication port
    ser.write('/stopFan\r'.encode())
    ser.write('/variables\r'.encode())
    update_variables(ser.readline())
    if not compost_Flags.objects(id=compost_id).first().Fan:
        Log(l_timestamp=datetime.now(), action='Roof Fan Stopped', compost=compost_id)


def startVent(compost_id):
    ser = serial.Serial(compost_Settings.objects.first().usb_port, 115200)  # setup serial communication port
    ser.write('/startVent\r'.encode())
    ser.write('/variables\r'.encode())
    update_variables(ser.readline())
    if compost_Flags.objects(id=compost_id).first().Vent:
        Log(l_timestamp=datetime.now(), action='Ventilation Started', compost=compost_id)


def stopVent(compost_id):
    ser = serial.Serial(compost_Settings.objects.first().usb_port, 115200)  # setup serial communication port
    ser.write('/stopVent\r'.encode())
    ser.write('/variables\r'.encode())
    update_variables(ser.readline())
    if not compost_Flags.objects(id=compost_id).first().Vent:
        Log(l_timestamp=datetime.now(), action='Ventilation Stopped', compost=compost_id)


def add_measurement():
    measurements(m_type="sunlight_in", m_value=random.uniform(20.0, 85.0), compost="57f38923e609a8140424851b",
                 m_timestamp=datetime.now()).save()
    measurements(m_type="sunlight_out", m_value=random.uniform(20.0, 85.0), compost="57f38923e609a8140424851b",
                 m_timestamp=datetime.now()).save()
    measurements(m_type="soil_temp", m_value=random.uniform(20.0, 85.0), compost="57f38923e609a8140424851b",
                 m_timestamp=datetime.now()).save()
    measurements(m_type="soil_hum", m_value=random.uniform(20.0, 85.0), compost="57f38923e609a8140424851b",
                 m_timestamp=datetime.now()).save()
    measurements(m_type="air_temp_in", m_value=random.uniform(20.0, 85.0), compost="57f38923e609a8140424851b",
                 m_timestamp=datetime.now()).save()
    measurements(m_type="air_hum_in", m_value=random.uniform(20.0, 85.0), compost="57f38923e609a8140424851b",
                 m_timestamp=datetime.now()).save()
    measurements(m_type="air_temp_out", m_value=random.uniform(20.0, 85.0), compost="57f38923e609a8140424851b",
                 m_timestamp=datetime.now()).save()
    measurements(m_type="air_hum_out", m_value=random.uniform(20.0, 85.0), compost="57f38923e609a8140424851b",
                 m_timestamp=datetime.now()).save()


sched2.add_job(add_measurement, 'interval', seconds=10)


# sched.add_job(read_variables, 'interval', seconds=5)
# sched.add_job(daily_stir, 'cron', day_of_week='mon-fri', hour=12)


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
    compost_Settings(daily_steering_time='12:00', steering_duration='30000', lowest_soil_humidity='55',
                     highest_soil_humidity='65', lowest_soil_temperature='50', usb_port='/dev/cu.usbmodem1411',
                     sleep_time_for_motors='3').save()
    measurements(m_type="sunlight_in", m_value=50, compost=compost_devices.objects(name='Compost_Ilioupoli').first().id,
                 m_timestamp=datetime.now()).save()
    measurements(m_type="sunlight_out", m_value=50,
                 compost=compost_devices.objects(name='Compost_Ilioupoli').first().id,
                 m_timestamp=datetime.now()).save()
    measurements(m_type="soil_temp", m_value=50, compost=compost_devices.objects(name='Compost_Ilioupoli').first().id,
                 m_timestamp=datetime.now()).save()
    measurements(m_type="soil_hum", m_value=50, compost=compost_devices.objects(name='Compost_Ilioupoli').first().id,
                 m_timestamp=datetime.now()).save()
    measurements(m_type="air_temp_in", m_value=50, compost=compost_devices.objects(name='Compost_Ilioupoli').first().id,
                 m_timestamp=datetime.now()).save()
    measurements(m_type="air_hum_in", m_value=50, compost=compost_devices.objects(name='Compost_Ilioupoli').first().id,
                 m_timestamp=datetime.now()).save()
    measurements(m_type="air_temp_out", m_value=50,
                 compost=compost_devices.objects(name='Compost_Ilioupoli').first().id,
                 m_timestamp=datetime.now()).save()
    measurements(m_type="air_hum_out", m_value=50, compost=compost_devices.objects(name='Compost_Ilioupoli').first().id,
                 m_timestamp=datetime.now()).save()
    compost_Flags(Motor_F=False, Motor_B=False, Motor_R=False, Motor_L=False, Fan=False, Vent=False, Door_1=False,
                  Emergency_Stop=False, compost=compost_devices.objects(name='Compost_Ilioupoli').first().id).save()
    Errors(e_timestamp=datetime.now(), error='Init',
           compost=compost_devices.objects(name='Compost_Ilioupoli').first().id).save()
    Log(l_timestamp=datetime.now(), action='Init',
        compost=compost_devices.objects(name='Compost_Ilioupoli').first().id).save()
    return 'db initialized'


@app.route('/composts')
def composts():
    return render_template('find_compost.html')


@app.route('/settings')
def compost_settings():
    return render_template('settings.html', settings=compost_Settings.objects().first())


@app.route('/settings/save_all', methods=['POST'])
def save_settings():
    # print(request.form['sleep'])
    compost_Settings.objects().first().update(set__daily_steering_time=request.form['time'],
                                              set__steering_duration=request.form['duration'],
                                              set__lowest_soil_humidity=request.form['lsht'],
                                              set__highest_soil_humidity=request.form['hsht'],
                                              set__lowest_soil_temperature=request.form['lstt'],
                                              set__usb_port=request.form['usb'],
                                              set__sleep_time_for_motors=request.form['sleep'])
    return render_template('settings.html', settings=compost_Settings.objects().first())


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
    device = compost_devices.objects(name=compost).first()
    flags = compost_Flags.objects(compost=device.id).first()
    return render_template('change_compost.html', device=device, flags=flags)


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


@app.route('/log')
def log():
    log = Log.objects()
    return render_template('log.html', log=log)


@app.route('/errors')
def errors():
    errors = Errors.objects()
    return render_template('errors.html', errors=errors)


@app.route('/charts')
def charts():
    return render_template('chart_test.html')


@app.route('/test', methods=['GET', 'POST'])
def test():
    return 'test_ok'


@app.route('/preliminary/measurements', methods=['GET', 'POST'])
def prem_meas():
    data = request.form
    # print(data['m_type'])
    qq = measurements.objects(m_type=data['m_type']).order_by('m_timestamp')
    # print(len(qq))
    return jsonify(qq[(len(qq)-50):])


@app.route('/measurements', methods=['GET', 'POST'])
def measure():
    data = request.form
    qq = measurements.objects(m_type=data['m_type']).order_by('-m_timestamp').first()
    return jsonify(qq)


@app.route('/compost_controls', methods=['POST'])
def update_controls():
    compost = compost_Flags.objects(compost=request.form['compost_id']).first()
    if request.form['control'] == '#Motor_F':
        if request.form['state'] == 'ON':
            compost.update(set__Motor_F=True)
        else:
            compost.update(set__Motor_F=False)
    elif request.form['control'] == '#Motor_B':
        if request.form['state'] == 'ON':
            compost.update(set__Motor_B=True)
        else:
            compost.update(set__Motor_B=False)
    if request.form['control'] == '#Motor_R':
        if request.form['state'] == 'ON':
            compost.update(set__Motor_R=True)
        else:
            compost.update(set__Motor_R=False)
    elif request.form['control'] == '#Motor_L':
        if request.form['state'] == 'ON':
            compost.update(set__Motor_L=True)
        else:
            compost.update(set__Motor_L=False)
    elif request.form['control'] == '#Fan':
        if request.form['state'] == 'ON':
            compost.update(set__Fan=True)
        else:
            compost.update(set__Fan=False)
    elif request.form['control'] == '#Vent':
        if request.form['state'] == 'ON':
            compost.update(set__Vent=True)
        else:
            compost.update(set__Vent=False)
    return request.form['control']


if __name__ == '__main__':
    # sched.start()
    sched2.start()
    app.run(host='0.0.0.0', port=5000)
