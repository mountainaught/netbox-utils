# A really basic script that pulls ISP sponsor data off of the RIPE DB and makes em importable by netbox. 
# Splits info into two parts, Tenancy info and allocated IP ranges.
# Good framework to copy and build more off of, such as pulling address and management info.

# copyleft mount 2024

import json
from urllib.request import Request, urlopen

# below request can be used to extract all tenants sponsored by a ISP or similar IP owner.
req = Request('http://rest.db.ripe.net/search?inverse-attribute=sponsoring-org&type-filter=inetnum&source=ripe&query-string=YOUR-ORG-HERE')
req.add_header('Accept', 'application/json')

with urlopen(req) as url:
    jdata = json.load(url)

print("name, slug",file=open("ultron-tenants.csv", 'w'))
print("tenant, start_address, end_address", file=open("ultron-ips.csv", "w"))

for i in jdata["objects"]['object']:

    if (i['primary-key']['attribute'][0]['name'] == "inetnum"):
        inetnum = i['attributes']['attribute'][0]['value']
        netname = i['attributes']['attribute'][1]['value']


        iplist = inetnum.split()
        ipstart = iplist[0]
        ipend = iplist[2]

    elif (i['primary-key']['attribute'][0]['name'] == "organisation"):
        orgname = i['attributes']['attribute'][1]['value']

        print(orgname, netname, sep=',')
        print(orgname, ipstart, ipend, sep=',')

        print(orgname, netname, sep=',',file=open("ultron-tenants.csv", 'a'))
        print(orgname, ipstart, ipend, sep=',',file=open("ultron-ips.csv",'a'))
