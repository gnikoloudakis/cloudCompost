# -*- coding: utf-8 -*-
import os, sys, threading, time, warnings, serial, random, requests
# import mongomodels as models
# import add_measurements as am
from flask.exthook import ExtDeprecationWarning

warnings.simplefilter("ignore", category=ExtDeprecationWarning)
from flask import Flask, request, json, render_template, redirect, jsonify, flash
from flask_mongoengine import MongoEngine
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = os.urandom(128)

# SOCKET IO INIT
socketio = SocketIO(app)

# MongoDB config
# app.config['MONGODB_DB'] = 'temu_compost'
# app.config['MONGODB_HOST'] = 'ds025583.mlab.com'
# app.config['MONGODB_PORT'] = 25583
# app.config['MONGODB_USERNAME'] = 'yannis'
# app.config['MONGODB_PASSWORD'] = 'spacegr'

#----------------------------------------------------#

app.config['MONGODB_DB'] = 'Raspberry_compost'
app.config['MONGODB_HOST'] = '127.0.0.1'
app.config['MONGODB_PORT'] = 27017
app.config['MONGODB_USERNAME'] = 'compost'
app.config['MONGODB_PASSWORD'] = 'compost'

# Create database connection object
db = MongoEngine(app)

# Configure ApScheduler
sched = BackgroundScheduler()
sched2 = BackgroundScheduler()
sched3 = BackgroundScheduler()
sched4 = BackgroundScheduler()
readvariables = BackgroundScheduler()

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
    meta = {'max_documents': 50}


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
    highest_air_humidity_inside = db.StringField(max_length=10, default='50')
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

def init_schedulers():
    url1 = sys.argv[1] if len(sys.argv) > 1 else 'sqlite:///' + app.root_path + os.sep + 'example1.sqlite'
    url2 = sys.argv[1] if len(sys.argv) > 1 else 'sqlite:///' + app.root_path + os.sep + 'example2.sqlite'
    url3 = sys.argv[1] if len(sys.argv) > 1 else 'sqlite:///' + app.root_path + os.sep + 'example3.sqlite'
    url4 = sys.argv[1] if len(sys.argv) > 1 else 'sqlite:///' + app.root_path + os.sep + 'example4.sqlite'
    url5 = sys.argv[1] if len(sys.argv) > 1 else 'sqlite:///' + app.root_path + os.sep + 'example5.sqlite'
    sched.add_jobstore('sqlalchemy', url=url1)
    sched2.add_jobstore('sqlalchemy', url=url2)
    sched3.add_jobstore('sqlalchemy', url=url3)
    sched4.add_jobstore('sqlalchemy', url=url4)
    readvariables.add_jobstore('sqlalchemy', url=url5)
    print('To clear the alarms, delete the example.sqlite file.')
    print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))
    try:
        sched.start()
        sched2.start()
        sched3.start()
        sched4.start()
        readvariables.start()
    except (KeyboardInterrupt, SystemExit):
        pass


def init():
    try:
        global arduino_ip
        arduino_ip = compost_devices.objects.first().arduino_ip
        r = requests.get('http://' + arduino_ip + ':8888/id')
        global compost_ID
        data = json.loads(r.content)
        compost_ID = compost_devices.objects(name=data['name']).first().id
        print(compost_ID)
        # sched4.add_job(test_sched, 'date', run_date=datetime.today(), args=['tetetetet'])
        # read_variables()
        readvariables.add_job(read_variables, 'date', run_date=datetime.now())
        stopAll()
    except requests.exceptions.ConnectionError:
        print("http error cannot connect to arduino")
        compost_ID = compost_devices.objects(name='Compost_Ilioupoli').first().id
        arduino_ip = '192.168.1.100'
        # Errors(e_timestamp=datetime.now(), error='FAILED to connect to Arduino', compost=compost_ID).save()
        sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['FAILED to connect to Arduino'])


def read_flags():
    try:
        r = requests.get('http://' + arduino_ip + ':8888/variables')
        data = json.loads(r.content)
        update_flags(data)
        # Log(l_timestamp=datetime.now(), action='Read Variables', compost=compost_ID)
        # sched4.add_job(log_stuff, 'date', run_date=datetime.today(), args=['Read Variables'],
        #                replace_existing=True)
    except requests.exceptions.ConnectionError:
        # Errors(e_timestamp=datetime.now(), error='FAILED to read variables from Arduino', compost=compost_ID).save()
        sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['FAILED to read FLAGS from Arduino'])


def update_flags(dataDict):
    compost_Flags.objects(compost=compost_ID).first().update(set__Motor_F=bool(dataDict['variables']['Motor_F']),
                                                             set__Motor_B=bool(dataDict['variables']['Motor_B']),
                                                             set__Motor_R=bool(dataDict['variables']['Motor_R']),
                                                             set__Motor_L=bool(dataDict['variables']['Motor_L']),
                                                             set__Fan=bool(dataDict['variables']['Fan']),
                                                             set__Vent=bool(dataDict['variables']['Vent']),
                                                             set__Door_1=bool(dataDict['variables']['Door_1']),
                                                             set__Emergency_Stop=bool(dataDict['variables']['Emergency_Stop']))
    # print(bool(dataDict['variables']['Emergency_Stop']))
    if dataDict['variables']['Door_1'] or dataDict['variables']['Emergency_Stop']:
        stopAll()


def read_variables():
    try:
        r = requests.get('http://' + arduino_ip + ':8888/variables')
        data = json.loads(r.content)
        update_variables(data)
        # Log(l_timestamp=datetime.now(), action='Read Variables', compost=compost_ID)
        # sched4.add_job(log_stuff, 'date', run_date=datetime.today(), args=['Read Variables'],
        #                replace_existing=True)
    except requests.exceptions.ConnectionError:
        # Errors(e_timestamp=datetime.now(), error='FAILED to read variables from Arduino', compost=compost_ID).save()
        sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['FAILED to read variables from Arduino'])


def update_variables(dataDict):

    socketio.emit('dashboard', dataDict)

    timestamp = datetime.now()
    # compost_id = compost_devices.objects(name=dataDict['name']).first().id
    measurements(m_type="sunlight_in", m_value=float(dataDict['variables']['sunlight_in']), compost=compost_ID, m_timestamp=timestamp).save()
    measurements(m_type="sunlight_out", m_value=float(dataDict['variables']['sunlight_out']), compost=compost_ID, m_timestamp=timestamp).save()
    measurements(m_type="soil_temp", m_value=float(dataDict['variables']['soil_temp']), compost=compost_ID, m_timestamp=timestamp).save()
    measurements(m_type="soil_hum", m_value=float(dataDict['variables']['soil_hum']), compost=compost_ID, m_timestamp=timestamp).save()
    measurements(m_type="air_temp_in", m_value=float(dataDict['variables']['air_temp_in']), compost=compost_ID, m_timestamp=timestamp).save()
    measurements(m_type="air_hum_in", m_value=float(dataDict['variables']['air_hum_in']), compost=compost_ID, m_timestamp=timestamp).save()
    measurements(m_type="air_temp_out", m_value=float(dataDict['variables']['air_temp_out']), compost=compost_ID, m_timestamp=timestamp).save()
    measurements(m_type="air_hum_out", m_value=float(dataDict['variables']['air_hum_out']), compost=compost_ID, m_timestamp=timestamp).save()
    compost_Flags.objects(compost=compost_ID).first() \
        .update(set__Motor_F=bool(dataDict['variables']['Motor_F']),
                set__Motor_B=bool(dataDict['variables']['Motor_B']),
                set__Motor_R=bool(dataDict['variables']['Motor_R']),
                set__Motor_L=bool(dataDict['variables']['Motor_L']),
                set__Fan=bool(dataDict['variables']['Fan']),
                set__Vent=bool(dataDict['variables']['Vent']),
                set__Door_1=bool(dataDict['variables']['Door_1']),
                set__Emergency_Stop=bool(dataDict['variables']['Emergency_Stop']))
    # print(bool(dataDict['variables']['Emergency_Stop']))
    if dataDict['variables']['Door_1'] or dataDict['variables']['Emergency_Stop']:
        stopAll()


##################################    MOTOR FUNCTIONS  ###################################
def start_motor_forward():
    # ser.write('/stirForwardOn\r'.encode())  # Stir Forward
    # ser.write('/variables\r'.encode())
    if not compost_Flags.objects(compost=compost_ID).first().Motor_F:
        if not compost_Flags.objects.first().Door_1 and not compost_Flags.objects.first().Emergency_Stop:
            try:
                requests.get('http://' + arduino_ip + ':8888/stirForwardOn')
                print('sent motor f on')
            except requests.exceptions.ConnectionError:
                # Errors(e_timestamp=datetime.now(), error='Failed to post to Arduino stirForwardOn',
                #        compost=compost_ID).save()
                sched4.add_job(error_stuff, 'date', run_date=datetime.now(),
                               args=['Failed to post to Arduino stirForwardOn'])
            # sched2.add_job(read_variables, 'date', run_date=datetime.today(), id='read_variables')
            # readvariables.add_job(read_variables, 'date', run_date=datetime.now(), id='read_variables',
            #                       replace_existing=True)
            read_flags()
            if compost_Flags.objects(compost=compost_ID).first().Motor_F:
                # Log(l_timestamp=datetime.now(), action='Motor Forward Started', compost=compost_ID).save()
                sched4.add_job(log_stuff, 'date', run_date=datetime.now(), args=['Motor Forward Started'])
            else:
                # Errors(e_timestamp=datetime.now(), error='Motor Forward FAILED to Start', compost=compost_ID).save()
                sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Motor Forward FAILED to Start'])
        else:
            # Errors(e_timestamp=datetime.now(),
            #        error='Door OPEN OR EMERGENCY BUTTON PRESSED- Failed to post to Arduino stirForwardOn',
            #        compost=compost_ID).save()
            sched4.add_job(error_stuff, 'date', run_date=datetime.now(),
                           args=['Door OPEN OR EMERGENCY BUTTON PRESSED- Failed to post to Arduino stirForwardOn'])
    else:
        sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Motor Forward is already ON'])


def stop_motor_forward():
    # ser.write('/stirForwardOff\r'.encode())  # Stir Forward Off
    # ser.write('/variables\r'.encode())
    # update_variables(ser.readline())
    # if not compost_Flags.objects.first().Door_1 and not compost_Flags.objects.first().Emergency_Stop:
    if compost_Flags.objects(compost=compost_ID).first().Motor_F:
        try:
            requests.get('http://' + arduino_ip + ':8888/stirForwardOff')
        except requests.exceptions.ConnectionError:
            # Errors(e_timestamp=datetime.now(), error='Failed to post to Arduino stirForwardOff',
            #        compost=compost_ID).save()
            sched4.add_job(error_stuff, 'date', run_date=datetime.now(),
                           args=['Failed to post to Arduino stirForwardOff'])
            # sched2.add_job(read_variables, id='read_variables')
            # readvariables.add_job(read_variables, 'date', run_date=datetime.now(), id='read_variables',
            #                       replace_existing=True)
        read_flags()
        if not compost_Flags.objects(compost=compost_ID).first().Motor_F:
            # Log(l_timestamp=datetime.now(), action='Motor Forward Stopped', compost=compost_ID).save()
            sched4.add_job(log_stuff, 'date', run_date=datetime.now(), args=['Motor Forward Stopped'])
        else:
            # Errors(e_timestamp=datetime.now(), error='Motor Forward FAILED to Stop', compost=compost_ID).save()
            sched4.add_job(error_stuff, 'date', run_date=datetime.now(),
                           args=['Motor Forward FAILED to Stop'])
            # else:
            #     # Errors(e_timestamp=datetime.now(),
            #     #        error='Door OPEN OR EMERGENCY BUTTON PRESSED- Failed to post to Arduino stirForwardOff',
            #     #        compost=compost_ID).save()
            #     sched4.add_job(error_stuff, 'date', run_date=datetime.today(),
            #                    args=['Door OPEN OR EMERGENCY BUTTON PRESSED- Failed to post to Arduino stirForwardOff'],
            #                    id='error_stuff')
    else:
        sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Motor Forward is already OFF'])


def start_motor_backward():
    # ser.write('/stirBackwardOn\r'.encode())  # Stir Forward
    # ser.write('/variables\r'.encode())
    # update_variables(ser.readline())
    if not compost_Flags.objects(compost=compost_ID).first().Motor_B:
        if not compost_Flags.objects(compost=compost_ID).first().Door_1 and not compost_Flags.objects(compost=compost_ID).first().Emergency_Stop:
            try:
                requests.get('http://' + arduino_ip + ':8888/stirBackwardOn')
            except requests.exceptions.ConnectionError:
                # Errors(e_timestamp=datetime.now(), error='Failed to post to Arduino stirBackwardOn',
                #        compost=compost_ID).save()
                sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Failed to post to Arduino stirBackwardOn'])
            # sched2.add_job(read_variables, id='read_variables')
            # readvariables.add_job(read_variables, 'date', run_date=datetime.now(), id='read_variables',
            #                       replace_existing=True)
            read_flags()
            if compost_Flags.objects(compost=compost_ID).first().Motor_B:
                # sched3.add_job(log_stuff, args=['Motor Backward Started'])
                # sched4.add_job(test_sched, None, args=['test'])
                sched4.add_job(log_stuff, 'date', run_date=datetime.now(), args=['Motor Backward Started'])
            else:
                # Errors(e_timestamp=datetime.now(), error='Motor Backward FAILED to Start', compost=compost_ID).save()
                # time.sleep(int(compost_Settings.objects.first().motor_B_duration))
                sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Motor Backward FAILED to Start'])
        else:
            # Errors(e_timestamp=datetime.now(),
            #        error='Door OPEN OR EMERGENCY BUTTON PRESSED- Failed to post to Arduino stirBackwardOn',
            #        compost=compost_ID).save()
            sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Door OPEN OR EMERGENCY BUTTON PRESSED- Failed to post to Arduino stirBackwardOn'])
    else:
        sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Motor Backwards is already ON'])


def stop_motor_backward():
    # ser.write('/stirBackwardOff\r'.encode())  # Stir Forward Off
    # ser.write('/variables\r'.encode())
    # update_variables(ser.readline())
    # if not compost_Flags.objects.first().Door_1 and not compost_Flags.objects.first().Emergency_Stop:
    if compost_Flags.objects(compost=compost_ID).first().Motor_B:
        try:
            requests.get('http://' + arduino_ip + ':8888/stirBackwardOff')
        except requests.exceptions.ConnectionError:
            # Errors(e_timestamp=datetime.now(), error='Failed to post to Arduino stirBackwardOff',
            #        compost=compost_ID).save()
            sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Failed to post to Arduino stirBackwardOff'])
            # sched2.add_job(read_variables, id='read_variables')
            # readvariables.add_job(read_variables, 'date', run_date=datetime.now(), id='read_variables',
            #                       replace_existing=True)
        read_flags()
        if not compost_Flags.objects(compost=compost_ID).first().Motor_B:
            # sched3.add_job(log_stuff, args=['Motor Backward Stopped'])
            # sched4.add_job(test_sched, None, args=['test'])
            sched4.add_job(log_stuff, 'date', run_date=datetime.now(), args=['Motor Backward Stopped'])
        else:
            # Errors(e_timestamp=datetime.now(), error='Motor Backward FAILED to Stop', compost=compost_ID).save()
            sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Motor Backward FAILED to Stop'])
            # else:
            #     # Errors(e_timestamp=datetime.now(),
            #     #        error='Door OPEN OR EMERGENCY BUTTON PRESSED- Failed to post to Arduino stirBackwardOff',
            #     #        compost=compost_ID).save()
            #     sched4.add_job(error_stuff, 'date', run_date=datetime.today(),
            #                    args=['Door OPEN OR EMERGENCY BUTTON PRESSED- Failed to post to Arduino stirBackwardOff'],
            #                    id='error_stuff')
    else:
        sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Motor Backwards is already OFF'])


def start_motor_right():
    # ser.write('/stirRightOn\r'.encode())  # Stir Right
    # ser.write('/variables\r'.encode())
    # update_variables(ser.readline())
    if not compost_Flags.objects(compost=compost_ID).first().Motor_R:
        if not compost_Flags.objects(compost=compost_ID).first().Door_1 and not compost_Flags.objects(
                compost=compost_ID).first().Emergency_Stop:
            try:
                requests.get('http://' + arduino_ip + ':8888/stirRightOn')
            except requests.exceptions.ConnectionError:
                Errors(e_timestamp=datetime.now(), error='Failed to post to Arduino stirRightOn', compost=compost_ID).save()
            # sched2.add_job(read_variables, id='read_variables')
            # readvariables.add_job(read_variables, 'date', run_date=datetime.now(), id='read_variables',
            #                       replace_existing=True)
            read_flags()
            if compost_Flags.objects(compost=compost_ID).first().Motor_R:
                # sched3.add_job(log_stuff, args=['Motor Right Started'])
                # sched4.add_job(test_sched, None, args=['test'])
                sched4.add_job(log_stuff, 'date', run_date=datetime.now(), args=['Motor Right Started'])
            else:
                # Errors(e_timestamp=datetime.now(), error='Motor Right FAILED to Start', compost=compost_ID).save()
                # time.sleep(int(compost_Settings.objects.first().motor_R_duration))
                sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Motor Right FAILED to Start'])
        else:
            # Errors(e_timestamp=datetime.now(),
            #        error='Door OPEN OR EMERGENCY BUTTON PRESSED- Failed to post to Arduino stirRightOn',
            #        compost=compost_ID).save()
            sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Door OPEN OR EMERGENCY BUTTON PRESSED- Failed to post to Arduino stirRightOn'])
    else:
        sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Motor Right is already ON'])


def stop_motor_right():
    # ser.write('/stirRightOff\r'.encode())  # Stir Right Off
    # ser.write('/variables\r'.encode())
    # update_variables(ser.readline())
    # if not compost_Flags.objects.first().Door_1 and not compost_Flags.objects.first().Emergency_Stop:
    if compost_Flags.objects(compost=compost_ID).first().Motor_R:
        try:
            requests.get('http://' + arduino_ip + ':8888/stirRightOff')
        except requests.exceptions.ConnectionError:
            # Errors(e_timestamp=datetime.now(), error='Failed to post to Arduino stirRightOff',
            #        compost=compost_ID).save()
            sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Failed to post to Arduino stirRightOff'])
            # sched2.add_job(read_variables, id='read_variables')
            # readvariables.add_job(read_variables, 'date', run_date=datetime.now(), id='read_variables',
            #                       replace_existing=True)
        read_flags()
        if not compost_Flags.objects(compost=compost_ID).first().Motor_R:
            # sched3.add_job(log_stuff, args=['Motor Right Stopped'])
            # sched4.add_job(test_sched, None, args=['test'])
            sched4.add_job(log_stuff, 'date', run_date=datetime.now(), args=['Motor Right Stopped'])
        else:
            # Errors(e_timestamp=datetime.now(), error='Motor Right FAILED to Stop', compost=compost_ID).save()
            sched4.add_job(error_stuff, 'date', run_date=datetime.now(),
                           args=['Motor Right FAILED to Stop'])
            # else:
            #     # Errors(e_timestamp=datetime.now(),
            #     #        error='Door OPEN OR EMERGENCY BUTTON PRESSED- Failed to post to Arduino stirRightOff',
            #     #        compost=compost_ID).save()
            #     sched4.add_job(error_stuff, 'date', run_date=datetime.today(),
            #                    args=['Door OPEN OR EMERGENCY BUTTON PRESSED- Failed to post to Arduino stirRightOff'],
            #                    id='error_stuff')
    else:
        sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Motor Right is already OFF'])


def start_motor_left():
    # ser.write('/stirLeftOn\r'.encode())  # Stir Left
    # ser.write('/variables\r'.encode())
    # update_variables(ser.readline())
    if not compost_Flags.objects(compost=compost_ID).first().Motor_L:
        if not compost_Flags.objects(compost=compost_ID).first().Door_1 and not compost_Flags.objects(compost=compost_ID).first().Emergency_Stop:
            try:
                requests.get('http://' + arduino_ip + ':8888/stirLeftOn')
            except requests.exceptions.ConnectionError:
                # Errors(e_timestamp=datetime.now(), error='Failed to post to Arduino stirLeftOn', compost=compost_ID).save()
                sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Failed to post to Arduino stirLeftOn'])
            # sched2.add_job(read_variables, id='read_variables')
            # readvariables.add_job(read_variables, 'date', run_date=datetime.now(), id='read_variables',
            #                       replace_existing=True)
            read_flags()
            if compost_Flags.objects(compost=compost_ID).first().Motor_L:
                # sched3.add_job(log_stuff, args=['Motor Right Sarted'])
                # sched4.add_job(test_sched, None, args=['test'])
                sched4.add_job(log_stuff, 'date', run_date=datetime.now(), args=['Motor Left Started'])
            else:
                # Errors(e_timestamp=datetime.now(), error='Motor Left Failed to Start', compost=compost_ID).save()
                # time.sleep(int(compost_Settings.objects.first().motor_L_duration))
                sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Motor Left Failed to Start'])
        else:
            # Errors(e_timestamp=datetime.now(),
            #        error='Door OPEN OR EMERGENCY BUTTON PRESSED- Failed to post to Arduino stirLeftOn',
            #        compost=compost_ID).save()
            sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Door OPEN OR EMERGENCY BUTTON PRESSED- Failed to post to Arduino stirLeftOn'])
    else:
        sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Motor Left is already ON'])


def stop_motor_left():
    # ser.write('/stirLeftOff\r'.encode())  # Stir Left Off
    # ser.write('/variables\r'.encode())
    # update_variables(ser.readline())
    # if not compost_Flags.objects.first().Door_1 and not compost_Flags.objects.first().Emergency_Stop:
    if compost_Flags.objects(compost=compost_ID).first().Motor_L:
        try:
            requests.get('http://' + arduino_ip + ':8888/stirLeftOff')
        except requests.exceptions.ConnectionError:
            # Errors(e_timestamp=datetime.now(), error='Failed to post to Arduino stirLeftOff', compost=compost_ID).save()
            sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Failed to post to Arduino stirLeftOff'])
            # sched2.add_job(read_variables, id='read_variables')
            # readvariables.add_job(read_variables, 'date', run_date=datetime.now(), id='read_variables',
            #                       replace_existing=True)
        read_flags()
        if not compost_Flags.objects(compost=compost_ID).first().Motor_L:
            # sched3.add_job(log_stuff, args=['Motor Left Stopped'])
            # sched4.add_job(test_sched, None, args=['test'])
            sched4.add_job(log_stuff, 'date', run_date=datetime.now(), args=['Motor Left Stopped'])
        else:
            # Errors(e_timestamp=datetime.now(), error='Motor Left FAILED to Stop', compost=compost_ID).save()
            sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Motor Left FAILED to Stop'])
            # else:
            #     # Errors(e_timestamp=datetime.now(),
            #     #        error='Door OPEN OR EMERGENCY BUTTON PRESSED- Failed to post to Arduino stirLeftOff',
            #     #        compost=compost_ID).save()
            #     sched4.add_job(error_stuff, 'date', run_date=datetime.today(),
            #                    args=['Door OPEN OR EMERGENCY BUTTON PRESSED- Failed to post to Arduino stirLeftOff'],
            #                    id='error_stuff')
    else:
        sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Motor Left is already OFF'])


def startFan():
    # ser.write('/startFan\r'.encode())
    # ser.write('/variables\r'.encode())
    # update_variables(ser.readline())
    if not compost_Flags.objects(compost=compost_ID).first().Fan:
        if not compost_Flags.objects(compost=compost_ID).first().Door_1 and not compost_Flags.objects(
                compost=compost_ID).first().Emergency_Stop and not compost_Flags.objects(compost=compost_ID).first().Vent:
            try:
                requests.get('http://' + arduino_ip + ':8888/startFan')
            except requests.exceptions.ConnectionError:
                # Errors(e_timestamp=datetime.now(), error='Failed to post to Arduino startFan', compost=compost_ID).save()
                sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Failed to post to Arduino startFan'])
            # sched2.add_job(read_variables, id='read_variables')
            # readvariables.add_job(read_variables, 'date', run_date=datetime.now(), id='read_variables',
            #                       replace_existing=True)
            read_flags()
            if compost_Flags.objects(compost=compost_ID).first().Fan:
                # sched3.add_job(log_stuff, args=['Roof Fan Started'])
                # sched4.add_job(test_sched, None, args=['test'])
                sched4.add_job(log_stuff, 'date', run_date=datetime.now(), args=['Roof Fan Started'])
            else:
                # Errors(e_timestamp=datetime.now(), error='Roof Fan FAILED to Start', compost=compost_ID).save()
                sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Roof Fan FAILED to Start'])
        else:
            # Errors(e_timestamp=datetime.now(),
            #        error='Door OPEN OR EMERGENCY BUTTON PRESSED- Failed to post to Arduino startFan',
            #        compost=compost_ID).save()
            sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Door OPEN OR EMERGENCY BUTTON PRESSED- Failed to post to Arduino startFan'],
                           id='error_stuff')
    else:
        sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Fan is already ON'])


def stopFan():
    # ser.write('/stopFan\r'.encode())
    # ser.write('/variables\r'.encode())
    # update_variables(ser.readline())
    # if not compost_Flags.objects.first().Door_1 and not compost_Flags.objects.first().Emergency_Stop:
    if compost_Flags.objects(compost=compost_ID).first().Fan:
        try:
            requests.get('http://' + arduino_ip + ':8888/stopFan')
        except requests.exceptions.ConnectionError:
            # Errors(e_timestamp=datetime.now(), error='Failed to post to Arduino stopFan', compost=compost_ID).save()
            sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Failed to post to Arduino stopFan'])
            # sched2.add_job(read_variables, id='read_variables')
            # readvariables.add_job(read_variables, 'date', run_date=datetime.now(), id='read_variables',
            #                       replace_existing=True)
        read_flags()
        if not compost_Flags.objects(compost=compost_ID).first().Fan:
            # sched3.add_job(log_stuff, args=['Roof Fan Stopped'])
            # sched4.add_job(test_sched, None, args=['test'])
            sched4.add_job(log_stuff, 'date', run_date=datetime.now(), args=['Roof Fan Stopped'])
        else:
            # Errors(e_timestamp=datetime.now(), error='Roof Fan FAILED to Stop', compost=compost_ID).save()
            sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Roof Fan FAILED to Stop'])
            # else:
            #     # Errors(e_timestamp=datetime.now(),
            #     #        error='Door OPEN OR EMERGENCY BUTTON PRESSED- Failed to post to Arduino stopFan',
            #     #        compost=compost_ID).save()
            #     sched4.add_job(error_stuff, 'date', run_date=datetime.today(),
            #                    args=['Door OPEN OR EMERGENCY BUTTON PRESSED- Failed to post to Arduino stopFan'],
            #                    id='error_stuff')
    else:
        sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Fan is already OFF'])


def startVent():
    # ser.write('/startVent\r'.encode())
    # ser.write('/variables\r'.encode())
    # update_variables(ser.readline())
    if not compost_Flags.objects(compost=compost_ID).first().Vent:
        if not compost_Flags.objects(compost=compost_ID).first().Door_1 and not compost_Flags.objects(
                compost=compost_ID).first().Emergency_Stop and not compost_Flags.objects(compost=compost_ID).first().Fan:
            try:
                requests.get('http://' + arduino_ip + ':8888/startVent')
            except requests.exceptions.ConnectionError:
                # Errors(e_timestamp=datetime.now(), error='Failed to post to Arduino startVent', compost=compost_ID).save()
                sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Failed to post to Arduino startVent'])
                # sched2.add_job(read_variables, id='read_variables')
                # readvariables.add_job(read_variables, 'date', run_date=datetime.now(), id='read_variables',
            #                       replace_existing=True)
            read_flags()
            if compost_Flags.objects(compost=compost_ID).first().Vent:
                # sched3.add_job(log_stuff, args=['Ventilation Started'])
                # sched4.add_job(test_sched, None, args=['test'])
                sched4.add_job(log_stuff, 'date', run_date=datetime.now(), args=['Ventilation Started'])
            else:
                # Errors(e_timestamp=datetime.now(), error='Ventilation FAILED to Start', compost=compost_ID).save()
                sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Ventilation FAILED to Start'])
        else:
            # Errors(e_timestamp=datetime.now(),
            #        error='Door OPEN OR EMERGENCY BUTTON PRESSED- Failed to post to Arduino startVent',
            #        compost=compost_ID).save()
            sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Fan Started OR Door OPEN OR EMERGENCY BUTTON PRESSED- Failed to post to Arduino startVent'], id='error_stuff')
    else:
        sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Ventilation is Already ON'])


def stopVent():
    # ser.write('/stopVent\r'.encode())
    # ser.write('/variables\r'.encode())
    # update_variables(ser.readline())
    # if not compost_Flags.objects.first().Door_1 and not compost_Flags.objects.first().Emergency_Stop:
    if compost_Flags.objects(compost=compost_ID).first().Vent:
        try:
            requests.get('http://' + arduino_ip + ':8888/stopVent')
        except requests.exceptions.ConnectionError:
            # Errors(e_timestamp=datetime.now(), error='Failed to post to Arduino stopVent', compost=compost_ID).save()
            sched4.add_job(error_stuff, 'date', run_date=datetime.now(),
                           args=['Failed to post to Arduino stopVent'])
            # sched2.add_job(read_variables, id='read_variables')
            # readvariables.add_job(read_variables, 'date', run_date=datetime.now(), id='read_variables',
            #                       replace_existing=True)
        read_flags()
        if not compost_Flags.objects(compost=compost_ID).first().Vent:
            # sched3.add_job(log_stuff, args=['Ventilation Stopped'])
            # sched4.add_job(test_sched, None, args=['test'])
            sched4.add_job(log_stuff, 'date', run_date=datetime.now(), args=['Ventilation Stopped'])
        else:
            # Errors(e_timestamp=datetime.now(), error='Ventilation FAILED to Stop', compost=compost_ID).save()
            sched4.add_job(error_stuff, 'date', run_date=datetime.now(),
                           args=['Ventilation FAILED to Stop'])
            # else:
            #     # Errors(e_timestamp=datetime.now(),
            #     #        error='Door OPEN OR EMERGENCY BUTTON PRESSED- Failed to post to Arduino stopVent',
            #     #        compost=compost_ID).save()
            #     sched4.add_job(error_stuff, 'date', run_date=datetime.today(),
            #                    args=['Door OPEN OR EMERGENCY BUTTON PRESSED- Failed to post to Arduino stopVent'],
            #                    id='error_stuff')
    else:
        sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Ventilation is already OFF'])


def Emergency_Stop_ON():
    # if not compost_Flags.objects.first().Door_1 and not compost_Flags.objects.first().Emergency_Stop:
    try:
        requests.get('http://' + arduino_ip + ':8888/Emergency_Stop_ON')
    except requests.exceptions.ConnectionError:
        # Errors(e_timestamp=datetime.now(), error='Failed to post to Arduino stopVent', compost=compost_ID).save()
        sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Failed to post to Arduino Emergency_Stop_ON'])
        # sched2.add_job(read_variables, id='read_variables')
        # readvariables.add_job(read_variables, 'date', run_date=datetime.now(), id='read_variables',
        #                       replace_existing=True)
    read_flags()
    if compost_Flags.objects(compost=compost_ID).first().Emergency_Stop:
        # sched3.add_job(log_stuff, args=['Ventilation Stopped'])
        # sched4.add_job(test_sched, None, args=['test'])
        sched4.add_job(log_stuff, 'date', run_date=datetime.now(), args=['Emergency_Stop PUSHED to ON'])
        stopAll()  ############################### STOP EVERYTHING  #############

    else:
        # Errors(e_timestamp=datetime.now(), error='Ventilation FAILED to Stop', compost=compost_ID).save()
        sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Emergency_Stop FAILED to be PUSHED to ON'])


def Emergency_Stop_OFF():
    # if not compost_Flags.objects.first().Door_1 and not compost_Flags.objects.first().Emergency_Stop:
    try:
        requests.get('http://' + arduino_ip + ':8888/Emergency_Stop_OFF')
    except requests.exceptions.ConnectionError:
        # Errors(e_timestamp=datetime.now(), error='Failed to post to Arduino stopVent', compost=compost_ID).save()
        sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Failed to post to Arduino Emergency_Stop_ON'])
        # sched2.add_job(read_variables, id='read_variables')
        # readvariables.add_job(read_variables, 'date', run_date=datetime.now(), id='read_variables',
        #                       replace_existing=True)
    read_flags()
    if not compost_Flags.objects(compost=compost_ID).first().Emergency_Stop:
        # sched3.add_job(log_stuff, args=['Ventilation Stopped'])
        # sched4.add_job(test_sched, None, args=['test'])
        stopAll()
        sched4.add_job(log_stuff, 'date', run_date=datetime.now(), args=['Emergency_Stop PUSHED to OFF'])
    else:
        # Errors(e_timestamp=datetime.now(), error='Ventilation FAILED to Stop', compost=compost_ID).save()
        sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['Emergency_Stop FAILED to be PUSHED to OFF'])


#

def stopAll():
    # if compost_Flags.objects(compost=compost_ID).first().Motor_F:
    stop_motor_forward()
    # elif compost_Flags.objects(compost=compost_ID).first().Motor_B:
    stop_motor_backward()
    # elif compost_Flags.objects(compost=compost_ID).first().Motor_L:
    stop_motor_left()
    # elif compost_Flags.objects(compost=compost_ID).first().Motor_R:
    stop_motor_right()
    # elif compost_Flags.objects(compost=compost_ID).first().Fan:
    stopFan()
    # elif compost_Flags.objects(compost=compost_ID).first().Vent:
    stopVent()


def add_measurement():
    measurements(m_type="sunlight_in", m_value=random.uniform(20.0, 85.0), compost=compost_ID, m_timestamp=datetime.now()).save()
    measurements(m_type="sunlight_out", m_value=random.uniform(20.0, 85.0), compost=compost_ID, m_timestamp=datetime.now()).save()
    measurements(m_type="soil_temp", m_value=random.uniform(20.0, 85.0), compost=compost_ID, m_timestamp=datetime.now()).save()
    measurements(m_type="soil_hum", m_value=random.uniform(20.0, 85.0), compost=compost_ID, m_timestamp=datetime.now()).save()
    measurements(m_type="air_temp_in", m_value=random.uniform(20.0, 85.0), compost=compost_ID, m_timestamp=datetime.now()).save()
    measurements(m_type="air_hum_in", m_value=random.uniform(20.0, 85.0), compost=compost_ID, m_timestamp=datetime.now()).save()
    measurements(m_type="air_temp_out", m_value=random.uniform(20.0, 85.0), compost=compost_ID, m_timestamp=datetime.now()).save()
    measurements(m_type="air_hum_out", m_value=random.uniform(20.0, 85.0), compost=compost_ID, m_timestamp=datetime.now()).save()


##########################################################################################################

############################ ALGORITHM FUNCTIONS #########################################################

def check_air_hum_inside():
    try:
        r = requests.get('http://' + arduino_ip + ':8888/air_hum_in')
        data = json.loads(r.content)
        sched4.add_job(log_stuff, 'date', run_date=datetime.now(), args=['Check Air Humidity Inside'])
        if data['air_hum_in'] > int(compost_Settings.objects.first().highest_air_humidity_inside):
            sched4.add_job(log_stuff, 'date', run_date=datetime.now(), args=['Air Humidity Inside OVER 85% detected'])
            startVent()
            time.sleep(10)
            while measurements.objects(m_type='air_hum_in').order_by('-m_timestamp').first().m_value > int(compost_Settings.objects.first().highest_air_humidity_inside):
                time.sleep(10)
            stopVent()
    except requests.exceptions.ConnectionError:
        # Errors(e_timestamp=datetime.now(), error='FAILED to read variables from Arduino', compost=compost_ID).save()
        sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['FAILED to read Air Humidity Inside from Arduino'])


def check_soil_hum():
    try:
        r = requests.get('http://' + arduino_ip + ':8888/soil_hum')
        data = json.loads(r.content)
        sched4.add_job(log_stuff, 'date', run_date=datetime.now(), args=['Read Soil Humidity'])
        if data['soil_hum'] > float(compost_Settings.objects.first().highest_soil_humidity):
            sched3.add_job(log_stuff, args=['Soil Humidity OVER 60% detected'])
            sched4.add_job(log_stuff, 'date', run_date=datetime.now(), args=['Soil Humidity OVER 60% detected'])
            soil_homogenization()
    except requests.exceptions.ConnectionError:
        # Errors(e_timestamp=datetime.now(), error='FAILED to read variables from Arduino', compost=compost_ID).save()
        sched4.add_job(error_stuff, 'date', run_date=datetime.now(), args=['FAILED to read Soil Humidity from Arduino'])


def hourly_ventilation():
    # sched3.add_job(log_stuff, args=['Hourly Ventilation started'])
    # sched4.add_job(test_sched, None, args=['test'])
    sched4.add_job(log_stuff, 'date', run_date=datetime.now(), args=['Hourly Ventilation started'])
    startVent()
    time.sleep(int(compost_Settings.objects.first().vent_duration))
    stopVent()


def bring_soil_backward():
    # sched3.add_job(log_stuff, args=['Bringing Soil Backwards'])
    # sched4.add_job(test_sched, None, args=['test'])
    sched4.add_job(log_stuff, 'date', run_date=datetime.now(), args=['Bringing Soil Backwards'])
    start_motor_backward()
    time.sleep(int(compost_Settings.objects.first().motor_B_duration))
    stop_motor_backward()


def soil_homogenization():
    # sched3.add_job(log_stuff, args=['Soil Homogenization started'])
    # sched4.add_job(test_sched, None, args=['test'])
    sched4.add_job(log_stuff, 'date', run_date=datetime.now(), args=['Soil Homogenization started'])
    startFan()
    start_motor_right()
    time.sleep(int(compost_Settings.objects.first().motor_R_duration))
    stop_motor_right()
    time.sleep(5)  ####  Adraneia mhxanhs
    start_motor_left()
    time.sleep(int(compost_Settings.objects.first().motor_L_duration))
    stop_motor_left()
    stopFan()


def log_stuff(text):
    Log(l_timestamp=datetime.now(), action=text, compost=compost_ID).save()
    socketio.emit('log_count', Log.objects.count())
    print('loooogggg')


def error_stuff(text):

    Errors(e_timestamp=datetime.now(), error=text, compost=compost_ID).save()
    socketio.emit('error_count', Errors.objects.count())
    print('errrrroorrrr')


def test_sched(text):
    print(text)


###################################################################################################################
##############  SET SCHEDULERS   ##################################################################################
def setupSchedulers():
    readvariables.add_job(read_variables, 'interval', seconds=10)#  #### diavazei metrhseis ka8e 10 seconds

    # sched.add_job(check_air_hum_inside, 'interval', minutes=30)#, id='check_air_hum_inside')

    sched.add_job(bring_soil_backward, 'cron', day_of_week='mon-fri', hour=datetime.strptime(compost_Settings.objects.first().daily_soil_backward_time, '%H:%M%p').hour)#, id='soil_backward')

    sched.add_job(soil_homogenization, 'cron', day_of_week='mon-fri', hour=datetime.strptime(compost_Settings.objects.first().daily_steering_time, '%H:%M%p').hour)#, id='soil_homogenization')

    # sched.add_job(check_soil_hum, 'cron', day_of_week='mon-fri', hour=datetime.strptime(compost_Settings.objects.first().daily_steering_time, '%H:%M%p').hour + 1)#, id='check_soil_hum')

    sched.add_job(hourly_ventilation, 'interval', hours=1)#, id='hourly_ventilation')  ####  ka8e wra eksaerismos gia 5 lepta

    # sched.add_job(add_measurement, 'interval', seconds=10)  ####  dummy metrhseis ka8e 10 seconds


###################################################################################################################


@app.route('/')
def index():
    eerrors = Errors.objects
    log = Log.objects
    return render_template('scada2.html', eerrors=eerrors, log=log)


@app.route('/<compost_name>')
def dashboard(compost_name):
    eerrors = Errors.objects
    log = Log.objects
    compost_device = compost_devices.objects(name=compost_name).first()
    # compost_device = dummy_data
    return render_template('dashboard.html', compost_device=compost_device, eerrors=eerrors, log=log)


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
                     highest_air_humidity_inside='85',
                     lowest_soil_temperature='50',
                     usb_port='/dev/cu.usbmodem1411',
                     sleep_time_for_motors='3').save()
    measurements(m_type="sunlight_in", m_value=50,
                 compost=compost_devices.objects(name='Compost_Ilioupoli').first().id, m_timestamp=datetime.now()).save()
    measurements(m_type="sunlight_out", m_value=50,
                 compost=compost_devices.objects(name='Compost_Ilioupoli').first().id, m_timestamp=datetime.now()).save()
    measurements(m_type="soil_temp", m_value=50,
                 compost=compost_devices.objects(name='Compost_Ilioupoli').first().id, m_timestamp=datetime.now()).save()
    measurements(m_type="soil_hum", m_value=50,
                 compost=compost_devices.objects(name='Compost_Ilioupoli').first().id, m_timestamp=datetime.now()).save()
    measurements(m_type="air_temp_in", m_value=50,
                 compost=compost_devices.objects(name='Compost_Ilioupoli').first().id, m_timestamp=datetime.now()).save()
    measurements(m_type="air_hum_in", m_value=50,
                 compost=compost_devices.objects(name='Compost_Ilioupoli').first().id, m_timestamp=datetime.now()).save()
    measurements(m_type="air_temp_out", m_value=50,
                 compost=compost_devices.objects(name='Compost_Ilioupoli').first().id, m_timestamp=datetime.now()).save()
    measurements(m_type="air_hum_out", m_value=50,
                 compost=compost_devices.objects(name='Compost_Ilioupoli').first().id, m_timestamp=datetime.now()).save()
    compost_Flags(Motor_F=False, Motor_B=False, Motor_R=False, Motor_L=False, Fan=False, Vent=False, Door_1=False, Emergency_Stop=False,
                  compost=compost_devices.objects(name='Compost_Ilioupoli').first().id).save()
    Errors(e_timestamp=datetime.now(), error='Init', compost=compost_devices.objects(name='Compost_Ilioupoli').first().id).save()
    Log(l_timestamp=datetime.now(), action='Init', compost=compost_devices.objects(name='Compost_Ilioupoli').first().id).save()
    return 'db initialized'


@app.route('/composts')
def composts():
    eerrors = Errors.objects
    log = Log.objects
    return render_template('find_compost.html', eerrors=eerrors, log=log)


@app.route('/settings')
def compost_settings():
    eerrors = Errors.objects
    log = Log.objects
    return render_template('settings.html', settings=compost_Settings.objects().first(), eerrors=eerrors, log=log)


@app.route('/settings/save_all', methods=['POST'])
def save_settings():
    compost_Settings.objects().first().update(set__daily_steering_time=request.form['time'],
                                              set__steering_duration=request.form['duration'],
                                              set__lowest_soil_humidity=request.form['lsht'],
                                              set__highest_soil_humidity=request.form['hsht'],
                                              set__lowest_soil_temperature=request.form['lstt'],
                                              set__usb_port=request.form['usb'],
                                              set__highest_air_humidity_inside=request.form['hahit'],
                                              set__sleep_time_for_motors=request.form['sleep'],
                                              set__daily_soil_backward_time=request.form['sb_time'],
                                              set__motor_F_duration=request.form['mf_time'],
                                              set__motor_B_duration=request.form['mb_time'],
                                              set__motor_R_duration=request.form['mr_time'],
                                              set__motor_L_duration=request.form['ml_time'],
                                              set__vent_duration=request.form['vent_time']
                                              )
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
    log = Log.objects
    device = compost_devices.objects(name=compost).first()
    flags = compost_Flags.objects(compost=device.id).first()
    return render_template('change_compost.html', device=device, flags=flags, eerrors=eerrors, log=log)


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
    # logs = Log.objects()
    log = Log.objects()
    return render_template('log.html', log=log, eerrors=eerrors)


@app.route('/log/clear')
def clear_log():
    Log.drop_collection()
    return redirect('/log')


@app.route('/errors')
def errors():
    eerrors = Errors.objects
    log = Log.objects
    return render_template('errors.html', eerrors=eerrors, log=log)


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
# @socketio.on('preliminary_measurements')
def prem_meas():
    data = request.form
    # data = qdata
    # print(data['m_type'])
    qq = measurements.objects(m_type=data['m_type']).order_by('m_timestamp')
    # print('preliminary size is :', len(qq))
    if qq:
        if (len(qq) - 50) > 0:
            return jsonify(qq[(len(qq) - 50):])
            # socketio.emit('preliminary_return', json.dumps(qq))
        else:
            return jsonify(qq)
            # socketio.emit('preliminary_return', qq)
            # pass
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
    print(request.form['control'])
    if request.form['control'] == "#Motor_F":
        if request.form['state'] == 'ON':
            print('mfon')
            # sched2.add_job(start_motor_forward())
            start_motor_forward()
        else:
            # sched2.add_job(stop_motor_forward())
            stop_motor_forward()
            print('mfoff')
    elif request.form['control'] == "#Motor_B":
        if request.form['state'] == 'ON':
            print('mbon')
            # sched2.add_job(start_motor_backward())
            start_motor_backward()
        else:
            print('mboff')
            # sched2.add_job(stop_motor_backward())
            stop_motor_backward()
    elif request.form['control'] == "#Motor_R":
        if request.form['state'] == 'ON':
            print('mron')
            # sched2.add_job(start_motor_right())
            start_motor_right()
        else:
            print('mroff')
            # sched2.add_job(stop_motor_right())
            stop_motor_right()
    elif request.form['control'] == "#Motor_L":
        if request.form['state'] == 'ON':
            print('mlon')
            # sched2.add_job(start_motor_left())
            start_motor_left()
        else:
            print('mloff')
            # sched2.add_job(stop_motor_left())
            stop_motor_left()
    elif request.form['control'] == "#Vent":
        if request.form['state'] == 'ON':
            print('venton')
            # sched2.add_job(startVent())
            startVent()
        else:
            print('ventoff')
            # sched2.add_job(stopVent())
            stopVent()
    elif request.form['control'] == "#Fan":
        if request.form['state'] == 'ON':
            print('fanon')
            # sched2.add_job(startFan())
            startFan()
        else:
            print('fanoff')
            # sched2.add_job(stopFan())
            stopFan()
    elif request.form['control'] == "#Emergency_Stop":
        compost = compost_Flags.objects(compost=request.form['id']).first()
        if request.form['state'] == 'ON':
            print('esbon')
            # compost.update(set__Emergency_Stop=True)
            Emergency_Stop_ON()
        else:
            print('esboff')
            # compost.update(set__Emergency_Stop=False)
            Emergency_Stop_OFF()
    # return redirect('/change_compost/' + compost_devices.objects(id=compost_ID).first().name)
    return 'ok'


@app.route('/test', methods=['GET', 'POST'])
def test():

    atest = request.args.get('test')
    if atest == 'sh':
        print(1)
        soil_homogenization()
    if atest == 'mr1':
        print(2)
        start_motor_right()
    if atest == 'mr0':
        print(3)
        stop_motor_right()
    if atest == 'ml1':
        print(4)
        start_motor_left()
    if atest == 'ml0':
        print(5)
        stop_motor_left()
    if atest == 'v1':
        print(6)
        startVent()
    if atest == 'v0':
        print(7)
        stopVent()
    if atest == 'f1':
        print(8)
        startFan()
    if atest == 'f0':
        print(9)
        stopFan()
    if atest == 'mf1':
        print(10)
        start_motor_forward()
    if atest == 'mf0':
        print(11)
        stop_motor_forward()
    if atest == 'mb1':
        print(12)
        start_motor_backward()
    if atest == 'mb0':
        print(13)
        stop_motor_backward()
    if atest == 'log_test':
        socketio.emit('log_count', Log.objects.count())
    if atest == 'bring_back':
        bring_soil_backward()
        print('bringing soil back')
    if atest == 'stop_all':
        stopAll()
    if atest == 'check_soil':
        check_soil_hum()
        print('check soil hum')
    if atest == 'check_air':
        check_air_hum_inside()
        print('check air hum')
    return 'ok test'


@socketio.on('chart_test')
def chart_test(data):

    socketio.emit('chart_return', {'name': 'yannis'})


if __name__ == '__main__':

    init_schedulers()
    init()
    setupSchedulers()
    # sched.start()
    # sched2.start()
    # sched3.start()
    # sched4.start()
    # readvariables.start()

    socketio.run(host='0.0.0.0', port=5000)
