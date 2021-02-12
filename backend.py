import re, os, requests, json, xmltodict
from time import time
from netaddr import *
from genie.testbed import load
from requests.auth import HTTPBasicAuth
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
from genie.metaparser.util.exceptions import SchemaEmptyParserError

######   Setting up the environment ######
ise_user = os.environ.get('ISE_USER', "admin")
ise_password = os.environ.get('ISE_PASSWORD', "")
base_url = "https://" + os.environ.get('ISE_IP', "") + ":9060/ers/config/"
switch_user = os.environ.get('SWITCH_USER', "netadmin")
switch_password = os.environ.get('SWITCH_PASS', "")
switch_enable = os.environ.get('SWITCH_ENABLE', "")
voucher_group_name = "AAA-Vouchers"

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

######         ISE functions        ######
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
        print(f"Found {len(NAD_list_details)} NADs.")
        return(NAD_list_details)
    except:
        print('An error has occured trying to fetch the NAD list')
        return({'ERROR','ERROR'})


def get_ise_group_id(group_name: str):
    '''
    This function will return the ISE group id a given group name.
    '''
    print(f"Fetching for ISE for endpoint group {group_name}...")
    url = base_url + "endpointgroup/name/" + group_name
    response = requests.get(url=url, auth=auth, headers=headers, verify=False)
    if response.status_code == 200:
        group_id = response.json()['EndPointGroup']['id']
        print(f"ISE endpoint group {group_name}, id: {group_id}")
        return(group_id)
    else:
        print(f"ERROR: Group {group_name} was not found")
        return("ERROR")


def update_ise_endpoint_group(mac_address:str, group_name:str):
    ise_group_id = get_ise_group_id(group_name)
    print(f"ISE endpoint group name: {group_name}, id: {ise_group_id}")
    if ise_group_id != "ERROR":
        url = base_url + "endpoint/name/" + mac_address
        try:
            endpoint_id = requests.get(url=url, auth=auth, headers=headers, 
                verify=False).json()["ERSEndPoint"]["id"]
            print(f"ISE endpoint {mac_address}, id: {endpoint_id}")
        except:
            print(f"Endpoint {mac_address} wasn't found.") 
            #
        url = base_url + "endpoint/" + endpoint_id
        data = ('{"ERSEndPoint": {"groupId": "%s","staticGroupAssignment": "true"}}' % ise_group_id)
        response = requests.put(url=url, data=data, auth=auth, headers=headers, verify=False)
        print(response)
        return("Done")
    else:
        return("ERROR")


def remove_ise_endpoint_group(mac_address:str, group_name:str):
    ise_group_id = get_ise_group_id(group_name)
    if ise_group_id != "ERROR":
        url = base_url + "endpoint/name/" + mac_address
        endpoint_id = requests.get(url=url, auth=auth, headers=headers, 
            verify=False).json()["ERSEndPoint"]["id"]
        #
        url = base_url + "endpoint/" + endpoint_id
        data = ('{"ERSEndPoint": {"groupId": "%s","staticGroupAssignment": "true"}}' % ise_group_id)
        response = requests.delete(url=url, data=data, auth=auth, headers=headers, verify=False)
        print(response)
        return("Done")
    else:
        return("ERROR")


def initialize_ise():
    url = "https://" + os.environ.get('ISE_IP', "") + "/admin/"
    response = requests.get(url=url, auth=auth, headers=headers, verify=False)
    if response.status_code == 200:
        return("Done")
    else:
        print(f"ERROR: Can't access ISE. Code: {response.status_code}")
        return("ERROR")


def check_ise_auth_status(mac_address:str):
    '''
    This function will return the authentication status of a given endpoint.
    '''
    mac = format_mac(mac_address)
    status_details = {}
    if mac != "ERROR":
        url = "https://" + os.environ.get('ISE_IP', "") + "/admin/API/mnt/AuthStatus/MACAddress/" + mac + "/84600/1/All"
        response = requests.get(url=url, auth=auth, verify=False)
        if response.status_code == 200:
            status = xmltodict.parse(response.text)
            if status['authStatusOutputList']['authStatusList']['authStatusElements']['passed']['#text'] == "true":
                status_details['Status'] = "Success"
                status_details['MACAddress'] = status['authStatusOutputList']['authStatusList']['@key']
                status_details['NAD'] = status['authStatusOutputList']['authStatusList']['authStatusElements']['network_device_name']
                status_details['Interface'] = status['authStatusOutputList']['authStatusList']['authStatusElements']['nas_port_id']
                status_details['AuthMethod'] = status['authStatusOutputList']['authStatusList']['authStatusElements']['authentication_method']
                status_details['Username'] = status['authStatusOutputList']['authStatusList']['authStatusElements']['user_name']
            else:
                status_details['Status'] = "Failure"
                status_details['MACAddress'] = status['authStatusOutputList']['authStatusList']['@key']
                status_details['NAD'] = status['authStatusOutputList']['authStatusList']['authStatusElements']['network_device_name']
                status_details['Interface'] = status['authStatusOutputList']['authStatusList']['authStatusElements']['nas_port_id']
                status_details['AuthMethod'] = status['authStatusOutputList']['authStatusList']['authStatusElements']['authentication_method']
                status_details['Username'] = status['authStatusOutputList']['authStatusList']['authStatusElements']['user_name']
                status_details['FailureReason'] = status['authStatusOutputList']['authStatusList']['authStatusElements']['failure_reason']
            return(status_details)
######       End of ISE functions      ######

        
def get_device_auth_sessions(device_ip: str):
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
    except:
        print(f"ERROR: Problem connecting to {device_ip}...")
        return([f"ERROR: Problem connecting to {device_ip}..."])
    try:
        auth_sessions = device.parse('show authentication sessions')
    except SchemaEmptyParserError:
        print(f"ERROR: No authentication sessions on {device_ip}.")
        return([f"ERROR: No authentication sessions on {device_ip}."])
    except:
        print(f"ERROR: Problem parsing information from {device_ip}.")
        return([f"ERROR: Problem parsing information from {device_ip}."])
    relevant_sessions = []
    for interface in auth_sessions['interfaces']:
        for client in auth_sessions['interfaces'][interface]['client']:
            if auth_sessions['interfaces'][interface]['client'][client]['domain'] != "UNKNOWN":
                session = { 'Interface': interface,
                            'EndpointMAC': client,
                            'NICVendor': EUI(client).oui.registration()['org'],
                            'Status': auth_sessions['interfaces'][interface]['client'][client]['status'],
                            'Method': auth_sessions['interfaces'][interface]['client'][client]['method']
                    }
                # TODO: Add failure reason, add IP address, add username...
                relevant_sessions.append(session)
        return(relevant_sessions)


def format_mac(mac_address:str):
    '''
    This function will validate MAC address input and return a MAC address
    formatted in "the Cisco way" (e.g. xxxx.xxxx.xxxx).
    '''
    try:
        mac = EUI(mac_address)
        mac.dialect = mac_cisco
        return(str(mac))
    except:
        print("ERROR: Invalid mac address")
        return("ERROR")


def read_voucher_json():
    try:
        print("Reading the voucher list")
        with open('voucher.json', 'r') as f:
            voucher_json = json.loads(f.read())
    except:
        print("Looks like the voucher list does not exist. Creating a new one...")
        with open('voucher.json', 'w') as f:
            voucher_json = {}
            json.dump(voucher_json, f)
    return(voucher_json)


def add_voucher(mac_address: str, duration: int):
    '''
    This function will receive an endpoint MAC address, add it to ISE's
    voucher endpoint group, and add an entry to the voucher list file 
    with the duration of the voucher, in order to clean it up once it expires.
    '''
    mac = format_mac(mac_address)
    if mac != "ERROR":
        try:
            # Update ISE
            update_ise_endpoint_group(mac, voucher_group_name)
            # Update the voucher file
            voucher_json = read_voucher_json()
            print(f"Adding MAC {mac} with a duration of {duration} hours to the voucher list")
            voucher_json[mac] = time() + duration*60*60            
            with open('voucher.json', 'w') as f:
                json.dump(voucher_json, f)
            return("Done")
        except:
            print(f"ERROR: Wasn't able to add {mac} to the voucher list")
            return(f"ERROR: Wasn't able to add {mac} to the voucher list")
    else:
        return("ERROR")


def revoke_voucher(mac_address: str):
    '''
    This function will receive an endpoint MAC address, remove it from 
    ISE's voucher endpoint group, and from the voucher list file.
    '''
    mac = format_mac(mac_address)
    try:
        # Update ISE
        print(f"Deleting MAC {mac} from ISE")
        remove_ise_endpoint_group(mac_address, voucher_group_name)
        # Update voucher file
        voucher_json = read_voucher_json()
        if mac in voucher_json:
            print(f"Deleting MAC {mac} from the voucher list")
            del voucher_json[mac]
            with open('voucher.json', 'w') as f:
                json.dump(voucher_json, f)
            return("Done")
        else:
            print(f"ERROR: MAC address {mac} not found on the voucher list")
    except:
        print(f"ERROR: MAC address {mac} not found on ISE")
        return("ERROR")


def voucher_cleanup(voucher_group_name: str):
    '''
    This function will go through the voucher list and remove endpoints
    with an expired voucher from ISE's endpoint group.
    '''
    print("About to clean up the voucher list...")
    voucher_json = read_voucher_json()
    for mac in voucher_json:
        if voucher_json[mac] < time():
            print(f"Removing expired voucher for {mac}.")
            revoke_voucher(mac)


if __name__ == "__main__":
    print("\n\n\nThis file provides backend methods for Vanilla ISE's front-end coode.\
        \nIt is not supposed to be run directly, but to be imported.\n\n")
    x = input("Press any key to continue...")