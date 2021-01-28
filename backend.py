import re, os, requests, datetime
from netaddr import *
from genie.testbed import load
from requests.auth import HTTPBasicAuth
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

######   Setting up the environment ######
ise_user = os.environ.get('ISE_USER', "admin")
ise_password = os.environ.get('ISE_PASSWORD', "")
base_url = "https://" + os.environ.get('ISE_IP', "") + ":9060/ers/config/"
switch_user = os.environ.get('SWITCH_USER', "netadmin")
switch_password = os.environ.get('SWITCH_PASS', "")
switch_enable = os.environ.get('SWITCH_ENABLE', "")

headers = {"Content-Type": "application/json",
    "Accept": "application/json"}
auth = HTTPBasicAuth(ise_user, ise_password)

testbed_template = {'devices':{
        'device':{
        'ip':'',
        'port': 22,
        'protocol': 'ssh',
        'username': switch_user,
        'password': switch_password,
        'os': 'iosxe' }}}
######   End of envrionment setup   ######

def get_all_NADs():
    '''
    This function will retrieve all NADs configured on ISE, and return a disctionary with
    the NADs hostname (as configured on ISE) and IP address.

    Example output:
    {'CSR1Kv.ebc.iseslab.cisco.com': '10.7.250.222',
    'Cat9K-1.lab.cisco.com': '10.255.7.15',
    'Cat9K-2.lab.cisco.com': '10.255.7.14',
    'Metro-3850': '10.7.250.200'}
    '''
    url = base_url + 'networkdevice/'
    print(f'About to fetch the NAD list from {url}')
    try:
        NAD_list = requests.get(url=url, headers=headers, auth=auth, verify=False).json()
        NAD_list_details = {}
        for NAD in NAD_list['SearchResult']['resources']:
            nad_url = url + NAD['id']
            NAD_details = requests.get(url=url+NAD['id'], headers=headers, auth=auth, verify=False).json()
            NAD_list_details[NAD_details['NetworkDevice']['name']] = NAD_details['NetworkDevice']['NetworkDeviceIPList'][0]['ipaddress']
            return(NAD_list_details)
    except:
        print('An error has occured trying to fetch the NAD list')
        return({'ERROR','ERROR'})


def get_device_auth_sessions(device_ip):
    '''
    This function will retrieve the active authentication sessions on a 
    given NAD/Switch (required: NAD's ip address), and returns a list of 
    authentication sessions.
    '''
    print('Verifying IP Address validity')
    try:
        ip = IPAddress(device_ip)
        print(f'The IP address is {ip.format()}')
    except:
        print('Error, invalid device IP address')
        return("ERROR: Invalid IP address")
    testbed_input = testbed_template
    testbed_input['devices']['device']['ip'] = ip.format()
    testbed = load(testbed_input)
    device = testbed.devices['device']
    try:
        device.connect(via='cli', learn_hostname=True)
        auth_sessions = device.parse('show authentication sessions')
        relevant_sessions = []
        for interface in auth_sessions['interfaces']:
            for client in auth_sessions['interfaces'][interface]['client']:
                if auth_sessions['interfaces'][interface]['client'][client]['domain'] != "UNKNOWN":
                    session = { 'Interface': interface,
                                'Endpoint MAC': client,
                                'NIC Vendor': EUI(client).oui.registration()['org']
                                'Status': auth_sessions['interfaces'][interface]['client'][client]['status'],
                                'Method': auth_sessions['interfaces'][interface]['client'][client]['method']
                        }
                    # TODO: Add failure reason, add IP address, add username...
                    relevant_sessions.append(session)
        return(relevant_sessions)
    except:
        print(f"ERROR: Problem connecting to {device_ip}...")
        return([f"ERROR: Problem connecting to {device_ip}..."])


def format_mac(mac_address):
    try:
        mac = EUI(mac_address)
        mac.dialect = mac_cisco
        return(mac)
    except:
        print("ERROR: Invalid mac address")
        return("ERROR")


def read_voucher_list():
    try:
        print("Reading the voucher list")
        with open('voucher.txt', 'r') as f:
            voucher_list = f.readlines()
        return(voucher_list)
    except:
        print("Looks like the voucher list does not exist. Creating a new one")
        with open('voucher.txt', 'w') as f:
            f.write("")
            return("")


def add_voucher(mac_address, duration):
    mac = format_mac(mac_address)
    if mac != "ERROR":
        # Update the voucher file
        voucher_list = read_voucher_list()
        print(f"Adding MAC {mac_address} with a duration of {duration} minutes to the voucher list")
        voucher_list.append(f"{mac_address},{duration}")
        with open('voucher.txt', 'w') as f:
            f.write(voucher_list)
        # Update ISE
        update_ise_endpoint(mac_address, "AAA-Vouchers")


def revoke_voucher(mac_address):
    voucher_list = read_voucher_list()


def get_ise_groups():
    '''
    This function will retrieve all group IDs from Cisco ISE
    and return a disctionary.
    {'group_id': 'group_name'}
    '''
    url = base_url + "endpointgroup/"
    ise_groups = {}
    while True:
        response = requests.get(url=url, auth=auth, headers=headers, verify=False)
        data = response.json()
        for each in data["SearchResult"]["resources"]:
            ise_groups[each["name"]] = each["id"]
        try:
            if data["SearchResult"]["nextPage"]["href"]:
                url = data["SearchResult"]["nextPage"]["href"]
        except:
            break
    return (ise_groups)


def get_ise_group_id(group_name):
    '''
    This function will return the ISE group id a given group name.
    '''
    ise_groups = get_ise_groups()
    for group in ise_groups:
        if group == group_name:
            return(ise_groups[group])
    print(f"ERROR: Group {group_name} was not found")
    return("ERROR")


def update_ise_endpoint(mac_address, group_name):
    group_id = get_group_id(group_name)
    if group_id != "ERROR":
        url = base_url + "endpoint/name/" + mac_address
        endpoint_id = requests.get(url=url, auth=auth, headers=headers, 
            verify=False).json()["ERSEndPoint"]["id"]
        #
        url = base_url + "endpoint/" + endpoint_id
        data = ('{"ERSEndPoint": {"groupId": "%s","staticGroupAssignment": "true"}}' % ise_group_id)
        response = requests.post(url=url, data=data, auth=auth, headers=headers, verify=False)
        print(response)

    