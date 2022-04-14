import re
import os
import requests
import json
import xmltodict
import asyncio
import logging.handlers
from time import time, sleep
from netaddr import *
from aiohttp import ClientSession, ClientTimeout, BasicAuth
from genie.testbed import load
from requests.auth import HTTPBasicAuth
from genie.metaparser.util.exceptions import SchemaEmptyParserError
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

######   Setting up the environment ######
ise_user = os.environ.get('ISE_USER', "admin")
ise_password = os.environ.get('ISE_PASSWORD', "")
base_url = "https://" + os.environ.get('ISE_IP', "") + ":9060/ers/config/"
switch_user = os.environ.get('SWITCH_USER', "netadmin")
switch_password = os.environ.get('SWITCH_PASS', "")
switch_enable = os.environ.get('SWITCH_ENABLE', "")
syslog_server = os.environ.get('SYSLOG_SERVER', "")
voucher_group_A = "AAA-Vouchers"
voucher_group_B = "BBB-Vouchers"
voucher_group_C = "CCC-Vouchers"
timeout = 15 * 60 # in minutes
batch = 50
parse_command = "authentication session"    # 'access-session' or 'authentication session'
                                            # Some old switches do not support 'authentication session'

auth = HTTPBasicAuth(ise_user, ise_password)
async_auth = BasicAuth(ise_user, ise_password)
headers = {"Content-Type": "application/json",
           "Accept": "application/json"}

testbed_template = {'devices': {
    'device': {
        'type': 'switch',
        'connections': {
                'cli': {
                    'ip': '',
                    'port': 22,
                    'protocol': 'ssh',
                    'ssh_options': '-o KexAlgorithms=+diffie-hellman-group14-sha1'
                }
        },
        'credentials': {
            'default': {
                'username': switch_user,
                'password': switch_password,
            }
        },
        'os': 'iosxe'
    }}}

if syslog_server != "":
    # Creating the logger
    syslog_logger = logging.getLogger('syslog_logger')
    syslog_logger.setLevel(logging.INFO)
    #Creating the logging handler, directing to the syslog server
    handler = logging.handlers.SysLogHandler(address=(syslog_server,514))
    syslog_logger.addHandler(handler)
        
######   End of envrionment setup   ######

######       Async functions        ######

async def fetch(NAD, session):
    nad_url = base_url + 'networkdevice/' + NAD['id']
    try:
        async with session.get(nad_url, headers=headers, auth=async_auth, verify_ssl=False) as response:
            json_resp = await response.json()
            NAD_list_details[json_resp['NetworkDevice']['name']] = json_resp['NetworkDevice']['NetworkDeviceIPList'][0]['ipaddress']
            return await response.json()
    except:
        print("Error")
        return(None)


async def bound_fetch(sem, NAD, session):
    # Getter function with semaphore.
    async with sem:
        await fetch(NAD, session)


async def get_NAD_details():
    tasks = []
    # create instance of Semaphore
    sem = asyncio.Semaphore(batch)

    # Create client session that will ensure we dont open new connection
    # per each request.
    async with ClientSession() as session:
        for NAD in complete_NAD_list:
            # pass Semaphore and session to every GET request
            task = asyncio.ensure_future(bound_fetch(sem, NAD, session))
            tasks.append(task)

        responses = asyncio.gather(*tasks)
        await responses

######    End of Async functions    ######

######         ISE functions        ######


def get_all_NADs():
    '''
    This function will retrieve all NADs configured on ISE, and return a dictionary with
    the NADs hostname (as configured on ISE) and IP address.

    Example output:
    {'CSR1Kv.ebc.iseslab.cisco.com': '10.7.250.222',
    'Cat9K-1.lab.cisco.com': '10.255.7.15',
    'Cat9K-2.lab.cisco.com': '10.255.7.14',
    'Metro-3850': '10.7.250.200'}
    '''
    url = base_url + 'networkdevice/?size=100'
    print(f'About to fetch the NAD list from {url}')
    try:
        isDone = False
        global NAD_list_details
        global complete_NAD_list
        NAD_list_details = {}
        complete_NAD_list = []
        while not isDone:
            NAD_list = requests.get(url=url, headers=headers, auth=auth, verify=False).json()
            complete_NAD_list += NAD_list['SearchResult']['resources']
            if 'nextPage' in NAD_list['SearchResult'].keys():
                url = NAD_list['SearchResult']['nextPage']['href']
            else:
                isDone = True       
        print(f"Found {len(complete_NAD_list)} NADs.")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        #loop = asyncio.get_event_loop()
        future = asyncio.ensure_future(get_NAD_details())
        loop.run_until_complete(future)
        return(NAD_list_details)
    except:
        print('\033[1;31mAn error has occured trying to fetch the NAD list\033[0m')
        return({'ERROR', 'ERROR'})


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
        print(f"\033[1;31mERROR: Group {group_name} was not found\033[0m")
        return("ERROR")


def update_ise_endpoint_group(mac_address: str, group_name: str):
    ise_group_id = get_ise_group_id(group_name)
    print(f"ISE endpoint group name: {group_name}, id: {ise_group_id}")
    if ise_group_id != "ERROR":
        url = base_url + "endpoint/name/" + mac_address
        response = requests.get(
            url=url, auth=auth, headers=headers, verify=False)
        if response.status_code == 200:
            endpoint_id = response.json()["ERSEndPoint"]["id"]
            print(f"ISE endpoint {mac_address}, id: {endpoint_id}")
            # The endpoint exists in the database, need to update its endpoint group assignment
            url = base_url + "endpoint/" + endpoint_id
            data = (
                '{"ERSEndPoint": {"groupId": "%s","staticGroupAssignment": "true"}}' % ise_group_id)
            response = requests.put(
                url=url, data=data, auth=auth, headers=headers, verify=False)
            print(response.json())
            #
        elif response.status_code == 404:
            # The does endpoint exist in the database, need to create it
            # and assign it to the endpoint group
            print(
                f"ISE endpoint {mac_address} was not found. Creating a new one")
            url = base_url + "endpoint/"
            data = {"ERSEndPoint":
                    {
                        "mac": mac_address,
                        "groupId": ise_group_id,
                        "staticGroupAssignment": "true"
                    }
                    }
            response = requests.post(url=url, data=json.dumps(
                data), auth=auth, headers=headers, verify=False)
            print(f"Creation status code: {response.status_code}")
        return("Done")
    else:
        return("ERROR")


def remove_ise_endpoint_group(mac_address: str, group_name: str):
    ise_group_id = get_ise_group_id(group_name)
    if ise_group_id != "ERROR":
        url = base_url + "endpoint/name/" + mac_address
        endpoint_id = requests.get(url=url, auth=auth, headers=headers,
                                   verify=False).json()["ERSEndPoint"]["id"]
        #
        url = base_url + "endpoint/" + endpoint_id
        data = (
            '{"ERSEndPoint": {"groupId": "%s","staticGroupAssignment": "true"}}' % ise_group_id)
        response = requests.delete(
            url=url, data=data, auth=auth, headers=headers, verify=False)
        print(response)
        return("Done")
    else:
        return("ERROR")


def initialize_ise(name, passw):
    '''
    This function validates the user-provided credentials against ISE.
    If the credentials allow access to ISE's APIs - it will return "Done", otherwise - "ERROR".
    '''
    print(f"Logging into ISE with username: {name}")
    url = "https://" + os.environ.get('ISE_IP', "") + ":9060/ers/sdk"
    user_auth = HTTPBasicAuth(name,passw)
    try:
        Iresponse = requests.get(url=url, headers=headers, auth=user_auth, verify=False, timeout=5)
        if Iresponse.status_code == 200:
            print(f"User {name} has suffecient permissions to login to ISE") 
            return("Done")
        else:
            print(f"\033[1;31mERROR: Can't access ISE/failed User. Code: {Iresponse.status_code}\033[0m")
            return("ERROR")
    except requests.exceptions.Timeout:
        print(f"\033[1;31mTimeout error. Please check ISE connectivity\033[0m")
        return("ERROR")


def check_ise_auth_status(mac_address: str):
    '''
    This function will return the authentication status of a given endpoint.
    Assumption: there was an authentication event during the last 24 hours.
    '''
    duration = 86400  # 24 hours
    mac = format_mac(mac_address)
    status_details = {}
    if mac != "ERROR":
        # URL explanation: https://<ISE>/admin/API/mnt/AuthStatus/MACAddress/
        # <endpoint's MAC address>/
        # <duration in seconds>/
        # <number of records>/
        # <"All" or "0" determies if the output is full or filtered>
        url = "https://" + \
            os.environ.get('ISE_IP', "") + "/admin/API/mnt/AuthStatus/MACAddress/" + \
            mac + "/" + str(duration) + "/1/All"
        response = requests.get(url=url, auth=auth, verify=False)
        if response.status_code != 200:
            return(f"ERROR: Response status code is {response.status_code}.")
        else:
            if response.text.rfind("authStatusElements") == -1:
                return(f"ERROR: No authentication events for MAC Address {mac} during the last {duration/3600} hours.")
            else:
                status = xmltodict.parse(response.text)
                status_details['MACAddress'] = status['authStatusOutputList']['authStatusList']['@key']
                status_details['NAD'] = status['authStatusOutputList']['authStatusList']['authStatusElements']['network_device_name']
                status_details['Interface'] = status['authStatusOutputList']['authStatusList']['authStatusElements']['nas_port_id']
                status_details['AuthMethod'] = status['authStatusOutputList'][
                    'authStatusList']['authStatusElements']['authentication_method']
                status_details['Username'] = status['authStatusOutputList']['authStatusList']['authStatusElements']['user_name']
                status_details['IdentityGroup'] = status['authStatusOutputList']['authStatusList']['authStatusElements']['identity_group']
                # Mention failure reason (if failed, or "none" is succeeded)
                if status['authStatusOutputList']['authStatusList']['authStatusElements']['passed']['#text'] == "true":
                    status_details['Status'] = "Success"
                    status_details['FailureReason'] = "None"
                else:
                    status_details['Status'] = "Failure"
                    status_details['FailureReason'] = status['authStatusOutputList'][
                        'authStatusList']['authStatusElements']['failure_reason']
                # Add SGT, if exists
                if 'cts_security_group' in status['authStatusOutputList']['authStatusList']['authStatusElements'].keys():
                    status_details['SGT'] = status['authStatusOutputList']['authStatusList']['authStatusElements']['cts_security_group']
                else:
                    status_details['SGT'] = "None"
                return(status_details)
######       End of ISE functions      ######


def get_device_ports(device_ip: str):
    '''
    This function will retrieve the list of interfaces on a given NAD/Switch,
    the list of authentication sessions on that switch, and return a dictionary
    with the following structure:

    {
    "stack_members": 3,
    "stacks": {
        "member1": {
            "GigabitEthernet1/0/1": {
                "status": "connected",
                "vlan": 1234,
                "description": "one port",
                "auth_status": "Unauth",
                "clients": [
                    {"0cd0.f898.1420": "Unauth"}
                ]
            },
            "GigabitEthernet1/0/2": {
                "status": "connected",
                "vlan": 1,
                "description": "another port",
                "auth_status": "Auth",
                "clients": [
                    {"603d.26da.8612": "Unauth"}
                ]
            },
                "GigabitEthernet3/0/12": {
                "status": "connected",
                "vlan": 1234,
                "description": "one port",
                "auth_status": "Mixed",
                "clients": [
                    {"700b.4fc5.bfad": "Unauth"},
                    {"0cd0.f842.0481": "Auth"}
                ]

            },
    }}}  
    '''
    print('Verifying IP Address validity')
    try:
        ip = IPAddress(device_ip)
        print(f'The IP address is {ip.format()}')
    except:
        print('\033[1;31mError, invalid device IP address\033[0m')
        return("ERROR: Invalid IP address")
    testbed_input = testbed_template
    testbed_input['devices']['device']['connections']['cli']['ip'] = ip.format()
    testbed = load(testbed_input)
    device = testbed.devices['device']
    # Connect to the device
    try:
        device.connect(via='cli', learn_hostname=True)
    except:
        print(f"\033[1;31mERROR: Problem connecting to {device_ip}...\033[0m")
        return([f"ERROR: Problem connecting to {device_ip}..."])
    # Get authentication sessions
    try:
        auth_sessions = device.parse(f'show {parse_command}')
    except SchemaEmptyParserError:
        print(f"\033[1;31mERROR: No access sessions on {device_ip}.\033[0m")
        return([f"ERROR: No access sessions on {device_ip}."])
    except:
        print(f"\033[1;31mERROR: Problem parsing information from {device_ip}.\033[0m")
        return([f"ERROR: Problem parsing information from {device_ip}."])
    # Get interfaces' vlan assignments
    try:
        interfaces_status = device.parse('show interfaces status')
    except SchemaEmptyParserError:
        print(f"\033[1;31mERROR: No access sessions on {device_ip}.\033[0m")
        return([f"ERROR: No access sessions on {device_ip}."])
    except:
        print(f"\033[1;31mERROR: Problem parsing information from {device_ip}.\033[0m")
        return([f"ERROR: Problem parsing information from {device_ip}."])
    #
    # Create the formatted stack units' interface mapping
    #
    results = {"stack_members": 0, "stacks": {}}
    for interface in interfaces_status['interfaces']:
        member_number = re.findall(r'\d+', interface)[0]
        if member_number not in results['stacks'].keys():
            results['stacks'][member_number] = {}
        results['stacks'][member_number][interface] = interfaces_status['interfaces'][interface]
        #
        # Cross-reference with authentication sessions
        #
        if interface in auth_sessions['interfaces'].keys():
            clients = []
            for client in auth_sessions['interfaces'][interface]['client']:
                clients.append({client: auth_sessions['interfaces'][interface]['client'][client]['status']})
            results['stacks'][member_number][interface]['clients'] = clients
        #
        # Calculate the number of stack members
        #
        results['stack_members'] = len(results['stacks'].keys())
    return(results)


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
        print('\033[1;31mError, invalid device IP address\033[0m')
        return("ERROR: Invalid IP address")
    testbed_input = testbed_template
    testbed_input['devices']['device']['connections']['cli']['ip'] = ip.format()
    testbed = load(testbed_input)
    device = testbed.devices['device']
    # Connect to the device
    try:
        device.connect(via='cli', learn_hostname=True)
    except:
        print(f"\033[1;31mERROR: Problem connecting to {device_ip}...\033[0m")
        return([f"ERROR: Problem connecting to {device_ip}..."])
    # Get authentication sessions
    try:
        auth_sessions = device.parse(f'show {parse_command}')
    except SchemaEmptyParserError:
        print(f"\033[1;31mERROR: No access sessions on {device_ip}.\033[0m")
        return([f"ERROR: No access sessions on {device_ip}."])
    except:
        print(f"\033[1;31mERROR: Problem parsing information from {device_ip}.\033[0m")
        return([f"ERROR: Problem parsing information from {device_ip}."])
    # Get interfaces' vlan assignments
    try:
        interfaces_status = device.parse('show interfaces status')
    except SchemaEmptyParserError:
        print(f"\033[1;31mERROR: No access sessions on {device_ip}.\033[0m")
        return([f"ERROR: No access sessions on {device_ip}."])
    except:
        print(f"\033[1;31mERROR: Problem parsing information from {device_ip}.\033[0m")
        return([f"ERROR: Problem parsing information from {device_ip}."])
    relevant_sessions = []
    for interface in auth_sessions['interfaces']:
        for client in auth_sessions['interfaces'][interface]['client']:
            if auth_sessions['interfaces'][interface]['client'][client]['domain'] != "UNKNOWN":
                auth_details = device.parse(
                    f"show {parse_command} interface {interface} details")
                session = {'Interface': interface,
                           'EndpointMAC': client,
                           'Status': auth_sessions['interfaces'][interface]['client'][client]['status'],
                           'Method': auth_sessions['interfaces'][interface]['client'][client]['method'],
                           'Username': auth_details['interfaces'][interface]['mac_address'][client]['user_name'],
                           'IPv4': auth_details['interfaces'][interface]['mac_address'][client]['ipv4_address'],
                           'NICVendor': EUI(client).oui.registration()['org'],
                           'Vlan': interfaces_status['interfaces'][interface]['vlan']
                           }
                try:
                    if "local_policies" in auth_details['interfaces'][interface]['mac_address'][client]:
                        session['Vlan'] = auth_details['interfaces'][interface]['mac_address'][client]['local_policies']['vlan_group']['vlan']
                    if "server_policies" in auth_details['interfaces'][interface]['mac_address'][client]:
                        server_policies = auth_details['interfaces'][interface]['mac_address'][client]['server_policies']
                        for policy in server_policies:
                            if server_policies[policy]['name'] == 'SGT Value':
                                session['SGT'] = server_policies[policy]['policies']
                            elif server_policies[policy]['name'] == 'ACS ACL IPV6':
                                session['IPv6ACL'] = server_policies[policy]['policies']
                            elif server_policies[policy]['name'] == 'ACS ACL':
                                session['IPv4ACL'] = server_policies[policy]['policies']
                except:
                    pass
                relevant_sessions.append(session)
    return(relevant_sessions)


def format_mac(mac_address: str):
    '''
    This function will validate MAC address input and return a MAC address
    formatted in "the Cisco way" (e.g. xxxx.xxxx.xxxx).
    '''
    try:
        mac = EUI(mac_address)
        mac.dialect = mac_cisco
        return(str(mac))
    except:
        print("\033[1;31m: Invalid mac address\033[0m")
        return("ERROR")


def read_voucher_list():
    '''
    Voucher file format:
    [
        {"mac": "00:11:22:33:44:55", "duration": 1617292081, "group": "AAA-Vouchers", "user": "Oren"},
        {"mac": "11:22:33:44:55:66", "duration": 1617293054, "group": "BBB-Vouchers", "user": "Ramona"}
    ]
    '''
    try:
        print("Reading the voucher list...")
        with open('./data/voucher.json', 'r') as f:
            voucher_list = json.loads(f.read())
    except:
        print("Looks like the voucher list does not exist. Creating a new one...")
        with open('./data/voucher.json', 'w') as f:
            voucher_list = []
            json.dump(voucher_list, f)
    print(f"Voucher list content (Current Epoch time: {int(time())}):\
        \n=======================")
    for voucher in voucher_list:
        print(voucher)
    print("=======================")
    return(voucher_list)


def add_voucher(mac_address: str, duration: int, voucher_group: str, user: str):
    '''
    This function will receive an endpoint MAC address, add it to ISE's
    voucher endpoint group, and add an entry to the voucher list file 
    with the duration of the voucher, in order to clean it up once it expires.
    '''
    mac = format_mac(mac_address)
    if mac != "ERROR":
        try:
            # Update the voucher file
            voucher_list = read_voucher_list()
            if any(mac in voucher['mac'] for voucher in voucher_list):
                print(
                    f"\033[1;31mERROR: MAC {mac} already has a voucher. Kindly revoke it first.\033[0m")
                return(f"ERROR: MAC {mac} already has a voucher. Kindly revoke it first.")
            else:
                print(
                    f"Adding MAC {mac} with a duration of {duration} hours to the voucher group {voucher_group}, user: {user}")
                voucher = {"mac": mac, "duration": int(
                    time()) + duration*60*60, "group": voucher_group, 
                    "user": user}
                voucher_list.append(voucher)
                with open('./data/voucher.json', 'w') as f:
                    json.dump(voucher_list, f)
        except:
            print("\033[1;31mERROR: Wasn't able to update the voucher file\033[0m")
            return("ERROR: Wasn't able to update the voucher file")
        try:
            # Update ISE
            update_ise_endpoint_group(mac, voucher_group)
            send_syslog(f"Voucher created! MAC: {mac}, duration: {duration} hours, voucher group: {voucher_group}, user: {user}")
            return("Done")
        except:
            print(f"\033[1;31mERROR: Wasn't able to add {mac} to ISE's voucher list\033[0m")
            return(f"ERROR: Wasn't able to add {mac} to ISE's voucher list")
    else:
        print(f"\033[1;31mERROR: Invalid MAC address: {mac_address}\033[0m")
        return("ERROR: Invalid MAC address")


def revoke_voucher(mac_address: str, user="system"):
    '''
    This function will receive an endpoint MAC address, remove it from 
    ISE's voucher endpoint group, and from the voucher list file.
    '''
    mac = format_mac(mac_address)
    try:
        # Update voucher file
        voucher_list = read_voucher_list()
        if any(mac in voucher['mac'] for voucher in voucher_list):
            for voucher in voucher_list:
                if voucher['mac'] == mac:
                    voucher_group = voucher['group']
                    print(
                        f"Deleting MAC {mac} (group {voucher_group}) from the voucher list")
                    voucher_list.remove(voucher)
                    with open('./data/voucher.json', 'w') as f:
                        json.dump(voucher_list, f)
        else:
            print(f"\033[1;31mERROR: MAC address {mac} not found on the voucher list\033[0m")
    except:
        print("\033[1;31mERROR: Wasn't able to update the voucher file\033[0m")
        return("ERROR: Wasn't able to update the voucher file")
    try:
        # Update ISE
        print(f"Deleting MAC {mac} from ISE")
        remove_ise_endpoint_group(mac_address, voucher_group)
        send_syslog(f"Voucher revoked! MAC: {mac}, user: {user}")
        return("Done")
    except:
        print(f"\033[1;31mERROR: Wasn't able to remove {mac} from ISE's voucher list\033[0m")
        return(f"ERROR: Wasn't able to remove {mac} from ISE's voucher list")


def voucher_cleanup():
    '''
    This function will go through the voucher list and remove endpoints
    with an expired voucher from ISE's endpoint group.
    '''
    print("\033[0;35mAbout to clean up the voucher list...")
    voucher_list = read_voucher_list()
    for voucher in voucher_list:
        if voucher['duration'] < int(time()):
            print(
                f"\033[0;35mRemoving expired voucher of {voucher['mac']} from voucher group {voucher['group']}.")
            revoke_voucher(voucher['mac'], "Timer")
            print("Clean-up done.\033[0m")


def send_syslog(data: str):
    '''
    This fuction will send a preconfigured syslog server messages (if syslog server is configured)
    '''
    if syslog_server != "":
        print(f"Sending syslog server {syslog_server} the following message: \
            \n{data}")
        syslog_logger.info(str(data))


if __name__ == "__main__":
    print("\n\n\nThis file provides backend methods for Vanilla ISE's front-end coode.\
        \nIt is not supposed to be run directly, but to be imported.\n\n")
    x = input("Press any key to continue...")
