__version__ = '22.05.04.1'
__author__ = 'Oren Brigg & Ramona Renner'
__author_email__ = 'obrigg@cisco.com / ramrenne@cisco.com'
__license__ = "Cisco Sample Code License, Version 1.1 - https://developer.cisco.com/site/license/cisco-sample-code-license/"


""" Copyright (c) 2021 Cisco and/or its affiliates.
This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at
           https://developer.cisco.com/docs/licenses
All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.
"""

# Import Section
from flask import Flask, render_template, request, url_for, redirect, session
from requests.auth import HTTPBasicAuth
import backend
from time import ctime, sleep, time
from threading import Thread

# Global Variables
app = Flask(__name__)
app.secret_key = "CiscoISEShared"

# Methods
def convert_voucher_list(voucher_list):
    '''
    This function will receive a voucher list with MAC addresses (in "the cisco way" format)
    and expire timestamps (in seconds since the epoch, in UTC) and convert it
    to MAC addresses (in the format xx:xx:xx:xx:xx:xx) and expire dates (as strings in local time).
    In: {"xxxx.xxxx.xxxx": 1613129301.6337228, "xxxx.xxxx.xxxx": 1613129332.6337228}
    Out:[{'MACAddress': 'xx:xx:xx:xx:xx:xx', 'ExpDate': 'Fri Feb 12 12:28:21 2021', 'group': 'AAA-Vouchers', 'user': 'Oren'},
        {'MACAddress': 'xx:xx:xx:xx:xx:xx', 'ExpDate': 'Fri Feb 12 18:28:21 2021', 'group': 'BBB-Vouchers', 'user': 'Ramona'}]
    '''
    converted_voucher_list = []

    for voucher in voucher_list:
        
        if voucher['type'] == "host":
            dot_free_mac = voucher['mac'].replace('.', '')
            mac_address = ':'.join(dot_free_mac[i:i+2] for i in range(0, 12, 2))
            exp_date = ctime(voucher['duration'])
            voucher_group = voucher['group']
            user = voucher['user']
            converted_voucher_list.append(
                {"MACAddress": mac_address, "ExpDate": exp_date, "group": voucher_group, "user": user})

        elif voucher['type'] == "port":
            mac_address = voucher['switch_ip']
            voucher_group = voucher['interface']
            exp_date = ctime(voucher['duration'])
            user = voucher['user']
            converted_voucher_list.append(
                {"MACAddress": mac_address, "ExpDate": exp_date, "group": voucher_group, "user": user})
    return converted_voucher_list


def propagate_backend_exception(backend_response):
    '''
    This function checks the backend response for ERROR indictors to raise an frontend
    exception and thereby display a customized error message in case of an backend error.
    '''
    if 'ERROR' in str(backend_response):
        raise Exception(str(backend_response))


def voucher_cleanup_loop():
    while True:
        backend.voucher_cleanup()
        sleep(10*60)


def normalize_mac_format(mac_address):
    '''
    This function normalizes mac addresses of different formats 
    e.g. xxxxxxxxxxxx, xx-xx-xx-xx-xx-xx, xx.xx.xx.xx.xx.xx or xxxx.xxxx.xxxx
    to xx:xx:xx:xx:xx:xx
    '''
    #Remove all :, - and . 
    mac_address = mac_address.replace('.','').replace(':','').replace('-','')
    #Add : after every second char
    normalized_mac_address = ':'.join(a+b for a,b in zip(mac_address[::2], mac_address[1::2]))

    return normalized_mac_address

# Routes
@app.route('/', methods=['GET'])
def index():
    '''
    This function shows an empty welcome page (GET)
    '''
    if type(session.get('logged_in')) == int and session.get('logged_in') > int(time()):
        session['logged_in'] = int(time()) + backend.timeout
        print(f"Login for {session['username']} extended until: {ctime(session['logged_in'])}")
        try:
            if request.method == 'GET':
                return render_template('welcome.html')

        except Exception as e:
            print(e)
            return render_template('endpointQuery.html', error=True, errorcode=e)
    else:
        print("First you need to login")
        return redirect(url_for('login'))

@app.route('/deviceList', methods=['GET', 'POST'])
def deviceList():
    '''
    This function will show all NAD devices in a table (GET request) and
    redirect to the specific query page of a device (POST request). The redirection
    can be manually triggered by a "Query Device" link in each table row and thereby
    for each NAD device.
    '''
    if type(session.get('logged_in')) == int and session.get('logged_in') > int(time()):
        session['logged_in'] = int(time()) + backend.timeout
        print(f"Login for {session['username']} extended until: {ctime(session['logged_in'])}")
        try:
            if request.method == 'GET':

                device_list = backend.get_all_NADs()
                propagate_backend_exception(device_list)

                return render_template('deviceList.html', device_list=device_list)

        except Exception as e:
            print(e)
            return render_template('deviceList.html', error=True, errorcode=e, reloadlink='/')
    else:
        print("First you need to login")
        return redirect(url_for('login'))

app.route('/deviceQuery?ip_address=<ip_address>')
@app.route('/deviceQuery', methods=['GET', 'POST'])
def deviceQuery():
    '''
    This function shows an empty page with IP query field and button (GET)
    or a list of queried devices with associated session information (POST).
    '''
    if type(session.get('logged_in')) == int and session.get('logged_in') > int(time()):
        session['logged_in'] = int(time()) + backend.timeout
        print(f"Login for {session['username']} extended until: {ctime(session['logged_in'])}")
        try:
            if request.method == 'GET':
                ip_address = request.args.get("ip_address")

            elif request.method == 'POST':
                ip_address = request.form.get("ip_address")

            if ip_address == None:
                ip_address = ''
                relevant_sessions={}  
            else:
                relevant_sessions = backend.get_device_auth_sessions(ip_address)
                propagate_backend_exception(relevant_sessions)

            return render_template('deviceQuery.html', ip_address=ip_address, relevant_sessions=relevant_sessions)

        except Exception as e:
            print(e)
            return render_template('deviceQuery.html', error=True, errorcode=e)
    else:
        print("First you need to login")
        return redirect(url_for('login'))


app.route('/switchView?ip_address=<ip_address>')
@app.route('/switchView', methods=['GET', 'POST'])
def switchView():
    '''
    This function shows an graphical representation of a switch and its port status. 
    '''
    if type(session.get('logged_in')) == int and session.get('logged_in') > int(time()):
        session['logged_in'] = int(time()) + backend.timeout
        print(f"Login for {session['username']} extended until: {ctime(session['logged_in'])}")
        try:    
            if request.method == 'GET':
                
                ip_address = request.args.get("ip_address")

            elif request.method == 'POST':

                ip_address = request.form.get("ip_address")

            if ip_address == None:
                ip_address = ''
                detailed_switch_status={} 
            else:
                detailed_switch_status = backend.get_device_ports(ip_address)
                propagate_backend_exception(detailed_switch_status)
   
            return render_template('switchView.html', ip_address=ip_address, detailed_switch_status=detailed_switch_status)

        except Exception as e:
            print(e)
            return render_template('switchView.html', error=True, errorcode=e)
    else:
        print("First you need to login")
        return redirect(url_for('login'))


app.route('/switchViewDetail?ip_address=<ip_address>&interface=<interface>')
@app.route('/switchViewDetail', methods=['GET', 'POST'])
def switchViewDetail():
    '''
    This function shows the associated session information for a specific interface and device.
    '''
    if type(session.get('logged_in')) == int and session.get('logged_in') > int(time()):
        session['logged_in'] = int(time()) + backend.timeout
        print(f"Login for {session['username']} extended until: {ctime(session['logged_in'])}")
        
        ip_address = ''
        interface = ''
        
        try:
            if request.method == 'GET':

                ip_address = request.args.get("ip_address")
                interface = request.args.get("interface")

                relevant_sessions = backend.get_port_auth_sessions(ip_address, interface)
                propagate_backend_exception(relevant_sessions)

                return render_template('switchViewDetail.html', ip_address=ip_address, interface=interface, relevant_sessions=relevant_sessions)

        except Exception as e:
            print(e)
            if "has no authentication sessions" in repr(e):
                return render_template('switchViewDetail.html', error=False, ip_address=ip_address, interface=interface, relevant_sessions={})
            elif "No access sessions on" in repr(e):
                return render_template('switchViewDetail.html', error=False, no_access_session=True, ip_address=ip_address, interface=interface, relevant_sessions={})

            return render_template('switchViewDetail.html', error=True, errorcode=e)

    else:
        print("First you need to login")
        return redirect(url_for('login'))


@app.route('/voucher', methods=['GET', 'POST'])
def voucher():
    '''
    This function shows a list of vouchers (GET), allows to add new vouchers
    or revokes existing once (POST). For better user experience the voucher data
    is converted beforehand.
    '''
    if type(session.get('logged_in')) == int and session.get('logged_in') > int(time()):
        session['logged_in'] = int(time()) + backend.timeout
        print(f"Login for {session['username']} extended until: {ctime(session['logged_in'])}")
        try:
            if request.method == 'GET':

                voucher_list = convert_voucher_list(
                    backend.read_voucher_list())
                propagate_backend_exception(voucher_list)

                return render_template('voucher.html', voucher_list=voucher_list, new_voucher=False)

            elif request.method == 'POST':

                submit_type = request.form.get("voucher_sumbit")
                row_mac_address = request.form.get("voucher_sumbit")
                form_mac_address = request.form.get("mac_address_field")
                voucher_duration = request.form.get("voucher_duration")
                voucher_group = request.form.get("voucher_group")

                if(submit_type == "Add"):

                    add_response = backend.add_host_voucher(
                        form_mac_address, int(voucher_duration), 
                        voucher_group, session['username'])
                    propagate_backend_exception(add_response)
                    voucher_list = convert_voucher_list(
                        backend.read_voucher_list())
                    propagate_backend_exception(voucher_list)

                    return render_template('voucher.html', voucher_list=voucher_list, new_voucher=True)

                else:  # Revoke

                    revoke_response = backend.revoke_host_voucher(row_mac_address, session['username'])
                    propagate_backend_exception(revoke_response)
                    voucher_list = convert_voucher_list(
                        backend.read_voucher_list())
                    propagate_backend_exception(voucher_list)

                    return render_template('voucher.html', voucher_list=voucher_list, deleted_voucher=True)

        except Exception as e:
            print(e)
            return render_template('voucher.html', error=True, errorcode=e)
    else:
        print("First you need to login")
        return redirect(url_for('login'))


@app.route('/endpointQuery?mac_address=<mac_address>')
@app.route('/endpointQuery', methods=['GET', 'POST'])
def endpointQuery():
    '''
    This function shows an empty page with MAC address query field and button (GET)
    or a list of queried endpoint devices with associated auth status (POST).
    '''
    if type(session.get('logged_in')) == int and session.get('logged_in') > int(time()):
        session['logged_in'] = int(time()) + backend.timeout
        print(f"Login for {session['username']} extended until: {ctime(session['logged_in'])}")
        mac_address = ''
        endpoint_list = ''
        try:
            if request.method == 'GET':

                mac_address = request.args.get("mac_address")

            elif request.method == 'POST':

                mac_address = request.form.get("mac_address")

            if mac_address == None:
                mac_address = ''
                endpoint_list={}  
            else:
                mac_address=normalize_mac_format(mac_address)
                endpoint_list = backend.check_ise_auth_status(mac_address)
                propagate_backend_exception(endpoint_list)

            return render_template('endpointQuery.html', endpoint_list=endpoint_list, mac_address=mac_address)

        except Exception as e:
            print(e)
            if "No authentication events for MAC Address" in repr(e) and "during the last 24.0 hours." in repr(e):
                return render_template('endpointQuery.html', error=False, no_events=True, endpoint_list={}, mac_address=mac_address)

            return render_template('endpointQuery.html', error=True, errorcode=e)
    else:
        print("First you need to login")
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login Form"""
    if request.method == 'GET':
        return render_template('login.html')
    else:
        name = request.form['username']
        passw = request.form['password']
        x  = backend.initialize_ise(name, passw)
        if x == "Done":
            print("login view - Successful Login")
            session['logged_in'] = int(time()) + backend.timeout
            session['username'] = name
            print(f"Logged in until: {ctime(session['logged_in'])}")
            return redirect(url_for('index'))
        else:
            print("Failed login")
            return render_template('login.html')


# Main Function
if __name__ == "__main__":
    t1 = Thread(target=voucher_cleanup_loop)
    t1.start()
    sleep(1)
    app.run(host='0.0.0.0', debug=False, threaded=True)