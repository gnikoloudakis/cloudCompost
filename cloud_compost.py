# -*- coding: utf-8 -*-
import os, threading, time, warnings, serial, random, requests
# import mongomodels as models
# import add_measurements as am
from flask.exthook import ExtDeprecationWarning

warnings.simplefilter("ignore", category=ExtDeprecationWarning)
from flask import Flask, request, json, render_template, redirect, jsonify, flash
from flask_mongoengine import MongoEngine
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from m_stats import Stats

app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = os.urandom(128)

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
sched3 = BackgroundScheduler()
sched4 = BackgroundScheduler()

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


#  INITIALIZE SERIAL INTERFACE ##########################################
# usb_port = models.compost_Settings.objects.first().usb_port
#

# ##################    MODELS     ###################################
class compost_devices(db.Document):
    name = db.StringField(max_length=50)
    country = db.StringField(max_length=50)
    region = db.StringField(max_length=50)
    area = db.StringField(max_length=50)
    raspberry_ip = db.StringField(max_length=100)
    arduino_ip = db.StringField(max_length=100)


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
    daily_soil_backward_time = db.StringField(default='14:00pm')
    daily_steering_time = db.StringField(default='06:00am')
    steering_duration = db.StringField(max_length=10, default='30000')
    motor_F_duration = db.StringField(max_length=10, default=60)
    motor_B_duration = db.StringField(max_length=10, default=60)
    motor_R_duration = db.StringField(max_length=10, default=60)
    motor_L_duration = db.StringField(max_length=10, default=60)
    vent_duration = db.StringField(max_length=10, default=300)
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
        return self.Motor_F


class measurements(db.Document):
    m_type = db.StringField(max_length=100)
    m_value = db.FloatField(max_length=6)
    compost = db.ReferenceField(compost_devices, required=True)
    m_timestamp = db.DateTimeField(default=datetime.now(), format='%d-%m-%Y')
    meta = {'max_documents': 5000}

    def __str__(self):
        return self.m_type


#############################  BASIC FUNCTIONS  ###########################


def init():
    r = requests.get('http://10.0.3.62:8888/variables')

    if r:
        global compost_ID
        data = json.loads(r.content)
        compost_ID = compost_devices.objects(name=data['name']).first().id
        # print(compost_ID)
    else:
        compost_ID = '57f76498e609a8231844226c'


def read_variables():
    r = requests.get('http://10.0.3.62:8888/variables')
    data = json.loads(r.content)
    update_variables(data)
    Log(l_timestamp=datetime.now(), action='Read Variables', compost=compost_ID)


def update_variables(dataDict):
    # compost_id = compost_devices.objects(name=dataDict['name']).first().id
    measurements(m_type="sunlight_in", m_value=float(dataDict['variables']['sunlight_in']), compost=compost_ID,
                 m_timestamp=datetime.now()).save()
    si = sunlight_in.add_points(float(dataDict['variables']['sunlight_in']))
    if si:
        print(si)
    else:
        pass
    # print(float(dataDict['variables']['sunlight_in']))
    measurements(m_type="sunlight_out", m_value=float(dataDict['variables']['sunlight_out']),
                 compost=compost_ID, m_timestamp=datetime.now()).save()
    so = sunlight_out.add_points(float(dataDict['variables']['sunlight_out']))
    if so:
        print(so)
    else:
        pass
    measurements(m_type="soil_temp", m_value=float(dataDict['variables']['soil_temp']), compost=compost_ID,
                 m_timestamp=datetime.now()).save()
    st = soil_temperature.add_points(float(dataDict['variables']['soil_temp']))
    if st:
        print(st)
    else:
        pass
    measurements(m_type="soil_hum", m_value=float(dataDict['variables']['soil_hum']), compost=compost_ID,
                 m_timestamp=datetime.now()).save()
    sh = soil_humidity.add_points(float(dataDict['variables']['soil_hum']))
    if sh:
        print(sh)
    else:
        pass
    measurements(m_type="air_temp_in", m_value=float(dataDict['variables']['air_temp_in']), compost=compost_ID,
                 m_timestamp=datetime.now()).save()
    ati = air_temperature_in.add_points(float(dataDict['variables']['air_temp_in']))
    if ati:
        print(ati)
    else:
        pass
    measurements(m_type="air_hum_in", m_value=float(dataDict['variables']['air_hum_in']), compost=compost_ID,
                 m_timestamp=datetime.now()).save()
    ahi = air_humidity_in.add_points(float(dataDict['variables']['air_hum_in']))
    if ahi:
        print(ahi)
    else:
        pass
    measurements(m_type="air_temp_out", m_value=float(dataDict['variables']['air_temp_out']),
                 compost=compost_ID, m_timestamp=datetime.now()).save()
    ato = air_temperature_out.add_points(float(dataDict['variables']['air_temp_out']))
    if ato:
        print(ato)
    else:
        pass
    measurements(m_type="air_hum_out", m_value=float(dataDict['variables']['air_hum_out']), compost=compost_ID,
                 m_timestamp=datetime.now()).save()
    aho = air_humidity_out.add_points(float(dataDict['variables']['air_hum_out']))
    if aho:
        print(aho)
    else:
        pass

    compost_Flags.objects(compost=compost_ID).first().update(set__Motor_F=bool(dataDict['variables']['Motor_F']),
                                                             set__Motor_B=bool(dataDict['variables']['Motor_B']),
                                                             set__Motor_R=bool(dataDict['variables']['Motor_R']),
                                                             set__Motor_L=bool(dataDict['variables']['Motor_L']),
                                                             set__Fan=bool(dataDict['variables']['Fan']),
                                                             set__Vent=bool(dataDict['variables']['Vent']),
                                                             set__Door_1=bool(dataDict['variables']['Door_1']),
                                                             set__Emergency_Stop=bool(
                                                                 dataDict['variables']['Emergency_Stop']))
    # print(bool(dataDict['variables']['Emergency_Stop']))


##################################    MOTOR FUNCTIONS  ###################################
def start_motor_forward():
    # ser.write('/stirForwardOn\r'.encode())  # Stir Forward
    # ser.write('/variables\r'.encode())
    requests.get('http://10.0.3.62:8888/stirForwardOn')
    sched2.add_job(read_variables)
    if compost_Flags.objects(compost=compost_ID).first().Motor_F:
        Log(l_timestamp=datetime.now(), action='Motor Forward Started', compost=compost_ID).save()
    else:
        Errors(e_timestamp=datetime.now(), error='Motor Forward FAILED to Start', compost=compost_ID).save()


def stop_motor_forward():
    # ser.write('/stirForwardOff\r'.encode())  # Stir Forward Off
    # ser.write('/variables\r'.encode())
    # update_variables(ser.readline())
    requests.get('http://10.0.3.62:8888/stirForwardOff')
    sched2.add_job(read_variables)
    if not compost_Flags.objects(compost=compost_ID).first().Motor_F:
        Log(l_timestamp=datetime.now(), action='Motor Forward Stopped', compost=compost_ID).save()
    else:
        Errors(e_timestamp=datetime.now(), error='Motor Forward FAILED to Stop', compost=compost_ID).save()


def start_motor_backward():
    # ser.write('/stirBackwardOn\r'.encode())  # Stir Forward
    # ser.write('/variables\r'.encode())
    # update_variables(ser.readline())
    requests.get('http://10.0.3.62:8888/stirBackwardOn')
    sched2.add_job(read_variables)
    if compost_Flags.objects(compost=compost_ID).first().Motor_B:
        Log(l_timestamp=datetime.now(), action='Motor Backward Started', compost=compost_ID).save()
    else:
        Errors(e_timestamp=datetime.now(), error='Motor Backward FAILED to Start', compost=compost_ID).save()
        # time.sleep(int(compost_Settings.objects.first().motor_B_duration))


def stop_motor_backward():
    # ser.write('/stirBackwardOff\r'.encode())  # Stir Forward Off
    # ser.write('/variables\r'.encode())
    # update_variables(ser.readline())
    requests.get('http://10.0.3.62:8888/stirBackwardOff')
    sched2.add_job(read_variables)
    if not compost_Flags.objects(compost=compost_ID).first().Motor_B:
        Log(l_timestamp=datetime.now(), action='Motor Backward Stopped', compost=compost_ID).save()
    else:
        Errors(e_timestamp=datetime.now(), error='Motor Backward FAILED to Stop', compost=compost_ID).save()


def start_motor_right():
    # ser.write('/stirRightOn\r'.encode())  # Stir Right
    # ser.write('/variables\r'.encode())
    # update_variables(ser.readline())
    requests.get('http://10.0.3.62:8888/stirRightOn')
    sched2.add_job(read_variables)
    if compost_Flags.objects(compost=compost_ID).first().Motor_R:
        Log(l_timestamp=datetime.now(), action='Motor Right Started', compost=compost_ID).save()
    else:
        Errors(e_timestamp=datetime.now(), error='Motor Right FAILED to Start', compost=compost_ID).save()
        # time.sleep(int(compost_Settings.objects.first().motor_R_duration))


def stop_motor_right():
    # ser.write('/stirRightOff\r'.encode())  # Stir Right Off
    # ser.write('/variables\r'.encode())
    # update_variables(ser.readline())
    requests.get('http://10.0.3.62:8888/stirRightOff')
    sched2.add_job(read_variables)
    if not compost_Flags.objects(compost=compost_ID).first().Motor_R:
        Log(l_timestamp=datetime.now(), action='Motor Right Stopped', compost=compost_ID).save()
    else:
        Errors(e_timestamp=datetime.now(), error='Motor Right FAILED to Stop', compost=compost_ID).save()


def start_motor_left():
    # ser.write('/stirLeftOn\r'.encode())  # Stir Left
    # ser.write('/variables\r'.encode())
    # update_variables(ser.readline())
    requests.get('http://10.0.3.62:8888/stirLeftOn')
    sched2.add_job(read_variables)
    if compost_Flags.objects(compost=compost_ID).first().Motor_L:
        Log(l_timestamp=datetime.now(), action='Motor Left Started', compost=compost_ID).save()
    else:
        Errors(e_timestamp=datetime.now(), error='Motor Left Failed to Start', compost=compost_ID).save()
        # time.sleep(int(compost_Settings.objects.first().motor_L_duration))


def stop_motor_left():
    # ser.write('/stirLeftOff\r'.encode())  # Stir Left Off
    # ser.write('/variables\r'.encode())
    # update_variables(ser.readline())
    requests.get('http://10.0.3.62:8888/stirLeftOff')
    sched2.add_job(read_variables)
    if not compost_Flags.objects(compost=compost_ID).first().Motor_L:
        Log(l_timestamp=datetime.now(), action='Motor Left Stopped', compost=compost_ID).save()
    else:
        Errors(e_timestamp=datetime.now(), error='Motor Left FAILED to Stop', compost=compost_ID).save()


def startFan():
    # ser.write('/startFan\r'.encode())
    # ser.write('/variables\r'.encode())
    # update_variables(ser.readline())
    requests.get('http://10.0.3.62:8888/startFan')
    sched2.add_job(read_variables)
    if compost_Flags.objects(compost=compost_ID).first().Fan:
        Log(l_timestamp=datetime.now(), action='Roof Fan Started', compost=compost_ID).save()
    else:
        Errors(e_timestamp=datetime.now(), error='Roof Fan FAILED to Start', compost=compost_ID).save()


def stopFan():
    # ser.write('/stopFan\r'.encode())
    # ser.write('/variables\r'.encode())
    # update_variables(ser.readline())
    requests.get('http://10.0.3.62:8888/stopFan')
    sched2.add_job(read_variables)
    if not compost_Flags.objects(compost=compost_ID).first().Fan:
        Log(l_timestamp=datetime.now(), action='Roof Fan Stopped', compost=compost_ID).save()
    else:
        Errors(e_timestamp=datetime.now(), error='Roof Fan FAILED to Stop', compost=compost_ID).save()


def startVent():
    # ser.write('/startVent\r'.encode())
    # ser.write('/variables\r'.encode())
    # update_variables(ser.readline())
    requests.get('http://10.0.3.62:8888/startVent')
    sched2.add_job(read_variables)
    if compost_Flags.objects(compost=compost_ID).first().Vent:
        Log(l_timestamp=datetime.now(), action='Ventilation Started', compost=compost_ID).save()
    else:
        Errors(e_timestamp=datetime.now(), error='Ventilation FAILED to Start', compost=compost_ID).save()


def stopVent():
    # ser.write('/stopVent\r'.encode())
    # ser.write('/variables\r'.encode())
    # update_variables(ser.readline())
    requests.get('http://10.0.3.62:8888/stopVent')
    sched2.add_job(read_variables)
    if not compost_Flags.objects(compost=compost_ID).first().Vent:
        Log(l_timestamp=datetime.now(), action='Ventilation Stopped', compost=compost_ID).save()
    else:
        Errors(e_timestamp=datetime.now(), error='Ventilation FAILED to Stop', compost=compost_ID).save()


def add_measurement():
    measurements(m_type="sunlight_in", m_value=random.uniform(20.0, 85.0), compost=compost_ID,
                 m_timestamp=datetime.now()).save()
    measurements(m_type="sunlight_out", m_value=random.uniform(20.0, 85.0), compost=compost_ID,
                 m_timestamp=datetime.now()).save()
    measurements(m_type="soil_temp", m_value=random.uniform(20.0, 85.0), compost=compost_ID,
                 m_timestamp=datetime.now()).save()
    measurements(m_type="soil_hum", m_value=random.uniform(20.0, 85.0), compost=compost_ID,
                 m_timestamp=datetime.now()).save()
    measurements(m_type="air_temp_in", m_value=random.uniform(20.0, 85.0), compost=compost_ID,
                 m_timestamp=datetime.now()).save()
    measurements(m_type="air_hum_in", m_value=random.uniform(20.0, 85.0), compost=compost_ID,
                 m_timestamp=datetime.now()).save()
    measurements(m_type="air_temp_out", m_value=random.uniform(20.0, 85.0), compost=compost_ID,
                 m_timestamp=datetime.now()).save()
    measurements(m_type="air_hum_out", m_value=random.uniform(20.0, 85.0), compost=compost_ID,
                 m_timestamp=datetime.now()).save()


##########################################################################################################

############################ ALGORITHM FUNCTIONS #########################################################


def hourly_ventilation():
    startVent()
    time.sleep(int(compost_Settings.objects.first().vent_duration))
    stopVent()


def bring_soil_backward():
    start_motor_backward()
    time.sleep(int(compost_Settings.objects.first().motor_B_duration))
    stop_motor_backward()


def soil_homogenization():
    start_motor_right()
    time.sleep(time.sleep(int(compost_Settings.objects.first().motor_R_duration)))
    stop_motor_right()
    time.sleep(5)  ####  Adraneia mhxanhs
    start_motor_left()
    time.sleep(time.sleep(int(compost_Settings.objects.first().motor_L_duration)))


###################################################################################################################
##############  SET SCHEDULERS   ##################################################################################
def setupSchedulers():
    sched.add_job(bring_soil_backward, 'cron', day_of_week='mon-fri',
                  hour=datetime.strptime(compost_Settings.objects.first().daily_soil_backward_time,
                                         '%I:%M%p').hour)

    sched.add_job(soil_homogenization, 'cron', day_of_week='mon-fri',
                  hour=datetime.strptime(compost_Settings.objects.first().daily_steering_time, '%I:%M%p').hour)

    # sched.add_job(read_variables, 'interval', seconds=10)  #### diavazei metrhseis ka8e 10 seconds

    sched2.add_job(add_measurement, 'interval', seconds=10)  ####  dummy metrhseis ka8e 10 seconds

    sched3.add_job(hourly_ventilation, 'interval', hours=1)  ####  ka8e wra eksaerismos gia 5 lepta


###################################################################################################################


@app.route('/')
def index():
    try:
        compost_device = compost_devices.objects.first_or_404()
        eerrors = Errors.objects
        logs = Log.objects
    except:
        compost_device = dummy_data
    return render_template('dashboard.html', compost_device=compost_device, eerrors=eerrors, logs=logs)


@app.route('/<compost_name>')
def dashboard(compost_name):
    try:
        eerrors = Errors.objects
        logs = Log.objects
        compost_device = compost_devices.objects.get_or_404(name=compost_name)
    except:
        compost_device = dummy_data
    return render_template('dashboard.html', compost_device=compost_device, eerrors=eerrors, logs=logs)


@app.route('/init_db')
def init_db():
    compost_devices(name='Compost_Ilioupoli', country='Greece', region='Athens', area='Ilioupoli',
                    raspberry_ip='192.168.1.100', arduino_ip='192.168.1.200').save()
    compost_Settings(daily_soil_backward_time='06:00am',
                     daily_steering_time='14:00pm',
                     steering_duration='60',
                     motor_F_duration='60',
                     motor_B_duration='60',
                     motor_R_duration='60',
                     motor_L_duration='60',
                     vent_duration='300',
                     lowest_soil_humidity='55',
                     highest_soil_humidity='65',
                     lowest_soil_temperature='50',
                     usb_port='/dev/cu.usbmodem1411',
                     sleep_time_for_motors='3').save()
    measurements(m_type="sunlight_in", m_value=50,
                 compost=compost_devices.objects(name='Compost_Ilioupoli').first().id,
                 m_timestamp=datetime.now()).save()
    measurements(m_type="sunlight_out", m_value=50,
                 compost=compost_devices.objects(name='Compost_Ilioupoli').first().id,
                 m_timestamp=datetime.now()).save()
    measurements(m_type="soil_temp", m_value=50,
                 compost=compost_devices.objects(name='Compost_Ilioupoli').first().id,
                 m_timestamp=datetime.now()).save()
    measurements(m_type="soil_hum", m_value=50,
                 compost=compost_devices.objects(name='Compost_Ilioupoli').first().id,
                 m_timestamp=datetime.now()).save()
    measurements(m_type="air_temp_in", m_value=50,
                 compost=compost_devices.objects(name='Compost_Ilioupoli').first().id,
                 m_timestamp=datetime.now()).save()
    measurements(m_type="air_hum_in", m_value=50,
                 compost=compost_devices.objects(name='Compost_Ilioupoli').first().id,
                 m_timestamp=datetime.now()).save()
    measurements(m_type="air_temp_out", m_value=50,
                 compost=compost_devices.objects(name='Compost_Ilioupoli').first().id,
                 m_timestamp=datetime.now()).save()
    measurements(m_type="air_hum_out", m_value=50,
                 compost=compost_devices.objects(name='Compost_Ilioupoli').first().id,
                 m_timestamp=datetime.now()).save()
    compost_Flags(Motor_F=False, Motor_B=False, Motor_R=False, Motor_L=False, Fan=False, Vent=False,
                  Door_1=False,
                  Emergency_Stop=False,
                  compost=compost_devices.objects(name='Compost_Ilioupoli').first().id).save()
    Errors(e_timestamp=datetime.now(), error='Init',
           compost=compost_devices.objects(name='Compost_Ilioupoli').first().id).save()
    Log(l_timestamp=datetime.now(), action='Init',
        compost=compost_devices.objects(name='Compost_Ilioupoli').first().id).save()
    return 'db initialized'


@app.route('/composts')
def composts():
    eerrors = Errors.objects
    logs = Log.objects
    return render_template('find_compost.html', eerrors=eerrors, logs=logs)


@app.route('/settings')
def compost_settings():
    eerrors = Errors.objects
    logs = Log.objects
    return render_template('settings.html', settings=compost_Settings.objects().first(), eerrors=eerrors,
                           logs=logs)


@app.route('/settings/save_all', methods=['POST'])
def save_settings():
    # print(request.form['sleep'])
    eerrors = Errors.objects
    logs = Log.objects
    compost_Settings.objects().first().update(set__daily_steering_time=request.form['time'],
                                              set__steering_duration=request.form['duration'],
                                              set__lowest_soil_humidity=request.form['lsht'],
                                              set__highest_soil_humidity=request.form['hsht'],
                                              set__lowest_soil_temperature=request.form['lstt'],
                                              set__usb_port=request.form['usb'],
                                              set__sleep_time_for_motors=request.form['sleep'],
                                              set__daily_soil_backward_time=request.form['sb_time'],
                                              set__motor_F_duration=request.form['mf_time'],
                                              set__motor_B_duration=request.form['mb_time'],
                                              set__motor_R_duration=request.form['mr_time'],
                                              set__motor_L_duration=request.form['ml_time'],
                                              set__vent_duration=request.form['vent_time'])
    # return render_template('settings.html', settings=compost_Settings.objects().first())
    return redirect('/settings')


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
    eerrors = Errors.objects
    logs = Log.objects
    device = compost_devices.objects(name=compost).first()
    flags = compost_Flags.objects(compost=device.id).first()
    return render_template('change_compost.html', device=device, flags=flags, eerrors=eerrors, logs=logs)


@app.route('/change_compost/save_all', methods=['POST'])
def save_all():
    dev_id = request.form['dev_id']
    name = request.form['name']
    country = request.form['country']
    region = request.form['region']
    area = request.form['area']
    rip = request.form['rip']
    aip = request.form['aip']

    device = compost_devices.objects(id=dev_id).first()
    if not device:
        compost_devices(name=name, country=country, region=region, area=area, raspberry_ip=rip,
                        arduino_ip=aip).save()
        print('no device')
    else:
        print('device found')
        device.update(set__name=name.strip(' \t\n\r'),
                      set__country=country.strip(' \t\n\r'),
                      set__region=region.strip(' \t\n\r'),
                      set__area=area.strip(' \t\n\r'),
                      set__raspberry_ip=rip.strip(' \t\n\r'),
                      set__arduino_ip=aip.strip(' \t\n\r'))
    return redirect('/change_compost/' + name)


@app.route('/log')
def log():
    eerrors = Errors.objects
    logs = Log.objects
    log = Log.objects()
    return render_template('log.html', log=log, eerrors=eerrors, logs=logs)


@app.route('/log/clear')
def clear_log():
    Log.drop_collection()
    return redirect('/log')


@app.route('/errors')
def errors():
    eerrors = Errors.objects
    logs = Log.objects
    return render_template('errors.html', eerrors=eerrors, logs=logs)


@app.route('/errors/clear')
def clear_errors():
    Errors.drop_collection()
    return redirect('/errors')


@app.route('/measurements/clear')
def clear_measurements():
    measurements.drop_collection()
    return redirect('/')


@app.route('/charts')
def charts():
    eerrors = Errors.objects
    logs = Log.objects
    return render_template('chart_test.html', eerrors=eerrors, logs=logs)


@app.route('/preliminary/measurements', methods=['GET', 'POST'])
def prem_meas():
    data = request.form
    # print(data['m_type'])
    qq = measurements.objects(m_type=data['m_type']).order_by('m_timestamp')
    # print('preliminary size is :', len(qq))
    if qq:
        if (len(qq) - 50) > 0:
            return jsonify(qq[(len(qq) - 50):])
        else:
            return jsonify(qq)
    else:
        return jsonify({0, 0})


@app.route('/measurements', methods=['GET', 'POST'])
def measure():
    data = request.form
    qq = measurements.objects(m_type=data['m_type']).order_by('-m_timestamp').first()
    # print(qq.m_type, qq.m_value, qq.compost.name)
    return jsonify(qq)


@app.route('/compost_controls', methods=['POST'])
def update_controls():
    # compost = compost_Flags.objects(compost=request.form['compost_id']).first()
    if request.form['control'] == '#Motor_F':
        if request.form['state'] == 'ON':
            sched2.add_job(start_motor_forward)
            # compost.update(set__Motor_F=True)
        else:
            sched2.add_job(stop_motor_forward)
            # compost.update(set__Motor_F=False)
    elif request.form['control'] == '#Motor_B':
        if request.form['state'] == 'ON':
            sched2.add_job(start_motor_backward)
            # compost.update(set__Motor_B=True)
        else:
            sched2.add_job(stop_motor_backward)
            # compost.update(set__Motor_B=False)
    if request.form['control'] == '#Motor_R':
        if request.form['state'] == 'ON':
            sched2.add_job(start_motor_right)
            # compost.update(set__Motor_R=True)
        else:
            sched2.add_job(stop_motor_right)
            # compost.update(set__Motor_R=False)
    elif request.form['control'] == '#Motor_L':
        if request.form['state'] == 'ON':
            sched2.add_job(start_motor_left)
            # compost.update(set__Motor_L=True)
        else:
            sched2.add_job(stop_motor_left)
            # compost.update(set__Motor_L=False)
    elif request.form['control'] == '#Fan':
        if request.form['state'] == 'ON':
            sched2.add_job(startFan)
            # compost.update(set__Fan=True)
        else:
            sched2.add_job(stopFan)
            # compost.update(set__Fan=False)
    elif request.form['control'] == '#Vent':
        if request.form['state'] == 'ON':
            sched2.add_job(startVent)
            # compost.update(set__Vent=True)
        else:
            sched2.add_job(stopVent)
            # compost.update(set__Vent=False)
    # return request.form['control']
    return 'ok'


if __name__ == '__main__':
    init()
    setupSchedulers()
    sched.start()
    sched2.start()
    # sched3.start()
    # sched4.start()

    app.run(host='0.0.0.0', port=5000)
