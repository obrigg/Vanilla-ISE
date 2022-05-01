<img src="img/vanilla_ISE_logo.png">

##### Your endpoint specialists will thank you later...
[![published](https://static.production.devnetcloud.com/codeexchange/assets/images/devnet-published.svg)](https://developer.cisco.com/codeexchange/github/repo/obrigg/Vanilla-ISE)
## The Challenge

Cisco ISE (Identity Services Engine) is **THE** policy engine for your network. It provides many (many) different services that are all required to meet today's user expectations while protecting the organization from threats:
* TACACS+/RADIUS for central management of networking equipment.
* Network Admission Control (NAC) identifying endpoints as they connect to the network (both wired and wireless).
* Group-based Policy using Cisco TrustSec.
* VPN policy with Cisco ASA/FTD.
* Guest lifecycle management.
* Device profiling.
* And more...

While Cisco ISE's richness of features and capabilities is highly appreciated by networking and security experts, endpoint technicians and helpdesk representatives prefer a simpler, limited GUI for their day-to-day tasks.

A specific capability asked by endpoint teams is the concept of a "voucher": a time-limited access token, given to a specific endpoint in order to grant immediate network access (while bypassing security checks) for a distressed user, allowing the technicians to remediate gaps in the endpoint's posture later.

## The Solution

Using Cisco ISE's open APIs, primarily ERS (External RESTful Services), we have created "Vanilla ISE": a simple UI for endpoint technicians and helpdesk representatives.

### Vanilla ISE's Capabilities:
* List the network access devices configured on ISE.
<img src="img/device list.png">
* Switch view provides a graphical representation of the switch. Which ports are up/down, authenticated or unauthenticated. Clicking a port will provide more details about the endpoint behind the port (similar to device query - but shorter response time).
  * <span style="color:green">Green</span>: Authenticated endpoint(s).
  * <span style="color:red">Red</span>: Unauthenticated endpoint(s).
  * <span style="color:grey">Grey</span>: The interface is not connected.
  
<img src="img/switch_view.png">
<img src="img/switch_view_port.png">

* Query a network device for current authentication sessions.
<img src="img/device query.png">
* Query a specific endpoint for details (status, NAD's IP and interface, authentication mechanism, username, and failure reason - if failed)
<img src="img/endpoint query.png">
* Grant and revoke network access "vouchers".
<img src="img/voucher list.png">
<img src="img/add voucher.png">
* **Vanilla ISE now requires authentication**. Use the your ISE credentials to authenticate to Vanilla ISE.
* Auditing: Vanilla ISE will keep track of the users creating and revoking vouchers, as well as send audit messages to a syslog server configured in the environment variables.
##### Communication with the devices, and data parsing is powered by <img src="/img/pyats.png">
More information about pyATS is available at: https://developer.cisco.com/pyats/
## Running vanilla ISE:

There are several options for running vanilla ISE:
1. Running the code on a computer/server with Python.
2. Running the code on a Docker container. Requires to <a href="https://docs.docker.com/get-docker/"> install Docker</a>.

### Enable ISE ERS API

The ISE REST APIs (AKA External RESTful Services or ERS) are disabled by default for security. You must enable it:
1. Login to your ISE PAN using the admin or other SuperAdmin user.
2. Navigate to **Administration** > **System** > **Settings** and select **ERS Settings** from the left panel.
4. Enable the ERS APIs by selecting **Enable ERS for Read/Write**
5. Do not enable CSRF unless you know how to use the tokens.
6. Select **Save** to save your changes.

Note: its good practice to disable CSRF to make sure you are able to authenticate successfully.

<a href="https://community.cisco.com/t5/security-documents/ise-ers-api-examples/ta-p/3622623#toc-hId--623796905"> Reference to official documentation </a>

### Option 1: Running Vanilla ISE on a server/workstation
#### Virtual Environment

I recommend running Vanilla ISE in a Python virtual environment. This will help keep your host system clean and allow you to have multiple environments to try new things. If you are not using a virtual environment, start at the download/clone step below.

You will also need Python 3 and venv installed on your host system.

In your project directory, create your virtual environment
``` console
python3 -m venv env
```
Activate the new virtual environment:
``` console
source env/bin/activate
```
Download or clone the Vanilla ISE repository:

``` console
git clone https://github.com/obrigg/Vanilla-ISE.git
```
Install the required packages
```
cd Vanilla-ISE
pip install -r requirements.txt
```
#### Set environment variables (one-time, non-persistent)
```
export ISE_IP= <ISE hostname/IP>
export ISE_USER= <ISE username>
export ISE_PASSWORD= <ISE password>
export SYSLOG_SERVER= <Syslog server IP, for auditing>
export SWITCH_USER= <username for network devices>
export SWITCH_PASS= <password for network devices>
export SWITCH_ENABLE= <enable password for network devices>
```
#### Set environment variables (persistent, for multiple activations)
Edit the env/bin/activate file with nano/vi/other editor
```
nano env/bin/activate
```
Add the following lines to the file, to make the environment variables persist for multiple activations of the environment.
```
export ISE_IP= <ISE hostname/IP>
export ISE_USER= <ISE username>
export ISE_PASSWORD= <ISE password>
export SYSLOG_SERVER= <Syslog server IP, for auditing>
export SWITCH_USER= <username for network devices>
export SWITCH_PASS= <password for network devices>
export SWITCH_ENABLE= <enable password for network devices>
```
#### Run the code
```
python app.py
```

### Option 2: Running Vanilla ISE as a Docker container (CLI)
#### Create an environment variable file
```
ISE_IP= <ISE hostname/IP>
ISE_USER= <ISE username>
ISE_PASSWORD= <ISE password>
SYSLOG_SERVER= <Syslog server IP, for auditing>
SWITCH_USER= <username for network devices>
SWITCH_PASS= <password for network devices>
SWITCH_ENABLE= <enable password for network devices>
```

##### Run the Docker container as a daemon:
`docker run -d --env-file <path to env file> -p 5000:5000 -v <path to data dir>:/Vanilla-ISE/data obrigg/vanilla-ise`

##### Run the Docker container in interactive mode:
`docker run -ti --env-file <path to env file> -p 5000:5000 -v <path to data dir>:/Vanilla-ISE/data obrigg/vanilla-ise`

### Option 3: Running Vanilla ISE as a Docker container (Docker Compose)
#### Create a `docker-compose.yaml` file (sample in repo)

```
version: '3'
services:
  vanilla-ise:
    image: obrigg/vanilla-ise
    container_name: vanilla-ise
    environment:
      - ISE_IP= <ISE hostname/IP>
      - ISE_USER= <ISE username>
      - ISE_PASSWORD= <ISE password>
      - SYSLOG_SERVER= <Syslog server IP, for auditing>
      - SWITCH_USER= <username for network devices>
      - SWITCH_PASS= <password for network devices>
      - SWITCH_ENABLE= <enable password for network devices>
    volumes:
      - <path to data dir>:/Vanilla-ISE/data
    ports:
      - 5000:5000
```

#### Run the Docker container:
`docker-compose up -d`

----

You can access the Vanilla ISE GUI at `http://<host ip>:5000` using your ISE username/password to login.

----
### Licensing info
Copyright (c) 2021 Cisco and/or its affiliates.

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
