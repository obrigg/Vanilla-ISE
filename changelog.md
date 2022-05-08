# Change log
##### 05-May-2022
* Added a page with a graphical representation of a switch and its port statuses.
* For each port, a detail page with the session information for the specific port was added.
* Ability to clear the authentication sessions for specific interfaces - by right clicking a port in the switch view, and choosing "Clear port".
* Ability to create a "port voucher", temporarily disabling dot1x on that interface for 24 hours.

##### 23-February-2022
* Documentation updates/clarifications, thanks to Roddie.
* Sample Docker-Compose file, thanks to Roddie.

##### 5-July-2021
* NAD List fetch converted to async for faster response.

##### 12-May-2021
* Added a welcome page, to avoid loading delay for networks with many NADs.
* Added jquery as a local file.
* Changed `show authentication session` to `show access-session` command to support older switches.

##### 6-May-2021
* Added search bar for the device list and voucher list.

##### 5-May-2021
* Updated NAD list with pagination, for more than 20 NADs.

##### 1-May-2021
* Added static vlans to device query.

##### 17-April-2021
* Added records of the user creating each voucher.
* Added auditing via syslog.

##### 10-April-2021
* Added colors to the backend.

##### 9-April-2021
* Added user authentication to Vanilla ISE.

##### 4-April-2021
* Added support for multiple voucher groups.

