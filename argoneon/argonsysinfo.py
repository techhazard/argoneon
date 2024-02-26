#!/usr/bin/python3

#
# Misc methods to retrieve system information.
#

import os
import time
import socket
import psutil
import shutil
from pathlib import Path

fanspeed = Path('/tmp/fanspeed.txt')

def checkPermission():
    """
    Determine if the user can properly execute the script.  Must have sudo or be root
    """
    if not ('SUDO_UID' in os.environ ) and os.geteuid() != 0:
        return False
    return True

#
def argonsysinfo_getCurrentFanSpeed():
    """ Get the current fanspeed of the system, by reading a file we have stored the speed in.
    This allows other applications for determine what the current fan speed is, as we cannot read
    (apparently) from the device when we set the speed.
    """
    try:
        return int(float(fanspeed.read_text()))
    except FileNotFoundError:
        return None
    except ValueError:
        return None

#
def argonsysinfo_recordCurrentFanSpeed( theSpeed ):
    """ Record the current fanspeed for external applications to use.
    """
    try:
        fanspeed.write_text(str(theSpeed))
    except:
        ...

def argonsysinfo_listcpuusage(sleepsec = 1):
    outputlist = []
    curusage_a = argonsysinfo_getcpuusagesnapshot()
    time.sleep(sleepsec)
    curusage_b = argonsysinfo_getcpuusagesnapshot()

    for cpuname in curusage_a:
        if cpuname == "cpu":
            continue
        if curusage_a[cpuname]["total"] == curusage_b[cpuname]["total"]:
            outputlist.append({"title": cpuname, "value": "0%"})
        else:
            total = curusage_b[cpuname]["total"]-curusage_a[cpuname]["total"]
            idle = curusage_b[cpuname]["idle"]-curusage_a[cpuname]["idle"]
            outputlist.append({"title": cpuname, "value": int(100*(total-idle)/(total))})
    return outputlist

def argonsysinfo_getcpuusagesnapshot():
    cpupercent = {}
    errorflag = False
    try:
        cpuctr = 0
        # user, nice, system, idle, iowait, irc, softirq, steal, guest, guest nice
        tempfp = open("/proc/stat", "r")
        alllines = tempfp.readlines()
        for temp in alllines:
            temp = temp.replace('\t', ' ')
            temp = temp.strip()
            while temp.find("  ") >= 0:
                temp = temp.replace("  ", " ")
            if len(temp) < 3:
                cpuctr = cpuctr +1
                continue

            checkname = temp[0:3]
            if checkname == "cpu":
                infolist = temp.split(" ")
                idle = 0
                total = 0
                colctr = 1
                while colctr < len(infolist):
                    curval = int(infolist[colctr])
                    if colctr == 4 or colctr == 5:
                        idle = idle + curval
                    total = total + curval
                    colctr = colctr + 1
                if total > 0:
                    cpupercent[infolist[0]] = {"total": total, "idle": idle}
            cpuctr = cpuctr +1

        tempfp.close()
    except IOError:
        errorflag = True
    return cpupercent


def argonsysinfo_liststoragetotal():
    outputlist = []
    ramtotal = 0
    errorflag = False

    try:
        with open("/proc/partitions", "r") as partitions:
            # skip header
            for partition in partitions.readlines()[1:] :
                partition.replace("  ", " ")

                major, minor, blocks, name = temp.split(" ")
                if len(infolist) >= 4:
                    # Check if header
                    if name.startswith("ram"):
                        ramtotal = ramtotal + int(blocks)

                    elif name.startswith("sd") or name.startswith("hd"):
                        lastchar = name[-1]
                        if not lastchar.isdigit():
                            outputlist.append({"title": name, "value": argonsysinfo_kbstr(int(blocks))})

                    elif name.startswith("mmc"):
                        # SD Cards
                        lastchars = name[-2]
                        if lastchars[0] != "p":
                            outputlist.append({"title": name, "value": argonsysinfo_kbstr(int(blocks))})
                    else:
                        pass

    except IOError:
        errorflag = True
    return outputlist

def argonsysinfo_getram():
    totalram = 0
    totalfree = 0
    tempfp = open("/proc/meminfo", "r")
    alllines = tempfp.readlines()

    for temp in alllines:
        temp = temp.replace('\t', ' ')
        temp = temp.strip()
        while temp.find("  ") >= 0:
            temp = temp.replace("  ", " ")
        infolist = temp.split(" ")
        if len(infolist) >= 2:
            if infolist[0] == "MemTotal:":
                totalram = int(infolist[1])
            elif infolist[0] == "MemFree:":
                totalfree = totalfree + int(infolist[1])
            elif infolist[0] == "Buffers:":
                totalfree = totalfree + int(infolist[1])
            elif infolist[0] == "Cached:":
                totalfree = totalfree + int(infolist[1])
    if totalram == 0:
        return {'percent': '0', 'gb': '0'}
    return {'percent': str(int(100*totalfree/totalram)), 'gb': str((totalram+512*1024)>>20)}


def argonsysinfo_getmaxhddtemp():
    maxtempval = 0
    try:
        hddtempobj = argonsysinfo_gethddtemp()
        for curdev in hddtempobj:
            if hddtempobj[curdev] > maxtempval:
                maxtempval = hddtempobj[curdev]
        return maxtempval
    except:
        return maxtempval

def argonsysinfo_getcputemp():
    try:
        tempfp = open("/sys/class/thermal/thermal_zone0/temp", "r")
        temp = tempfp.readline()
        tempfp.close()
        return float(int(temp)/1000)
    except IOError:
        return 0

def argonsysinfo_gethddtemp():
    outputobj = {}
    hddtempcmd = "smartctl"
    #smartctl -d sat -A ${device} | grep 194 | awk -F" " '{print $10}'

    if shutil.which(hddtmpcmd) is not None:
        # try:
            command = os.popen("lsblk | grep -e '0 disk' | awk '{print $1}'")
            tmp = command.read()
            command.close()
            alllines = [l for l in tmp.split("\n") if l]
            for curdev in alllines:
                if curdev[0:2] == "sd" or curdev[0:2] == "hd":
                    # command = os.popen(hddtempcmd+" -d sat -A /dev/"+curdev+" | grep 194 | awk '{print $10}' 2>&1")
                    def getSmart(smartCmd):
                        if not checkPermission() and not smartCmd.startswith("sudo"):
                            smartCmd = "sudo " + smartCmd
                        try:
                            command = os.popen(smartCmd)
                            smartctlOutRaw = command.read()
                        except Exception as e:
                            print (e)
                        finally:
                            command.close()
                        if 'scsi error unsupported scsi opcode' in smartctlOutRaw:
                            return None

                        smartctlOut = [l for l in smartctlOutRaw.split('\n') if l]

                        for smartAttr in ["194","190"]:
                            try:
                                line = [l for l in smartctlOut if l.startswith(smartAttr)][0]
                                parts = [p for p in line.replace('\t',' ').split(' ') if p]
                                tempval = float(parts[9])
                                return tempval
                            except IndexError:
                                ## Smart Attr not found
                                ...

                        for smartAttr in ["Temperature:"]:
                            try:
                                line = [l for l in smartctlOut if l.startswith(smartAttr)][0]
                                parts = [p for p in line.replace('\t',' ').split(' ') if p]
                                tempval = float(parts[1])
                                return tempval
                            except IndexError:
                                ## Smart attrbute not found
                                ...
                        return None
                    theTemp = getSmart(f"{hddtempcmd} -d sat -n standby,0 -A /dev/{curdev}")
                    if theTemp:
                        outputobj[curdev] = theTemp
                    else: 
                        theTemp = getSmart(f"{hddtempcmd} -n standby,0 -A /dev/{curdev}")
                        if theTemp:
                            outputobj[curdev] = theTemp
    return outputobj

def argonsysinfo_getip():
    ipaddr = ""
    st = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try: 
        # Connect to nonexistent device
        st.connect(('254.255.255.255', 1))
        ipaddr = st.getsockname()[0]
    except Exception:
        ipaddr = 'N/A'
    finally:
        st.close()
    return ipaddr

def get_ip_addresses( family ):
    for interface, snics in psutil.net_if_addrs().items():
        if interface != "lo" and not interface.startswith("br"):
            for snic in snics:
                if snic.family == family:
                    yield( interface, snic.address )

def argonsysinfo_getipList():
    iplist = []
    iplist = list(get_ip_addresses( socket.AF_INET ))

    return iplist

def argonsysinfo_getrootdev():
    with open('/etc/mtab', 'r') as mtab:
        mount_lines = mtab.read().rstrip().split("\n")
    for mountline in mount_lines:
        device, mountpoint, fstype, *other = mountline.split(' ')
        if mountpoint == "/":
            return os.path.realpath(device)
    return ""

def argonsysinfo_listhddusage():
    outputobj = {}
    raidlist = argonsysinfo_listraid()
    raiddevlist = []
    raidctr = 0
    while raidctr < len(raidlist['raidlist']):
        raiddevlist.append(raidlist['raidlist'][raidctr]['title'])
        raidctr = raidctr + 1

    rootdev = argonsysinfo_getrootdev()

    command = os.popen('df --output=source,fstype,used,avail,pcent')
    # split by lines and skip header
    alllines = command.read().rstrip().split("\n")[1:]
    command.close()
    mapper = None


    ignored_filesystems = { 'devtmpfs', 'devpts', 'tmpfs', 'proc', 'sysfs', 'configfs', 'ramfs' }


    for dfline in alllines:
        device = ""
        source, fstype, used, avail, percent = dfline.replace("  ", " ").strip().split()


        if fstype in ignored_filesystems:
            continue

        if source.startswith('/dev/mapper/'):
            from pathlib import Path
            mapper = Path(source).readlink().name

        elif source == "/dev/root" and rootdev != "":
            source = rootdev

        if fstype != "zfs":

            # resolve any symlinks (e.g. /dev/disk/by-id/nvme-my-disk-id -> /dev/nvme0n1
            source = os.path.realpath(source)

            # keep only device name /dev/nvme0n1 -> nvme0n1
            source = os.path.basename(source)
        #
        # Throw out all devices being used by raid
        #
        if source in raidlist['hddlist']:
            #print(f"in hddlist: {source} {raidlist['hddlist']}")
            continue

        elif fstype == "zfs":
            continue

        elif source not in raiddevlist and not mapper:
          #print(f"source6: {source}")
          if source[0:2] == "sd" or source[0:2] == "hd":
              #print(f"source7: {source}")
              source = source[0:-1]
          else:
              #print(f"source: {source}")
              source = source[0:-2]

        #print(f"source9: {source}")
        if source not in outputobj:
            #print(f"source10: {source}")
            outputobj[source] = {"used":0, "total":0, "percent":0}
            if mapper:
                #print(f"source11: {source}")
                outputobj[source]["mapper"] = mapper
        outputobj[source]["used"]         += int(used)
        outputobj[source]["total"]        += int(avail)
        outputobj[source]["percent"]       = round(((outputobj[source]["used"]/outputobj[source]["total"]) * 100),1)

    return outputobj

def argonsysinfo_kbstr(kbval, wholenumbers = True):
    remainder = 0
    suffixidx = 0
    suffixlist = ["KB", "MB", "GB", "TB"]
    while kbval > 1023 and suffixidx < len(suffixlist):
        remainder = kbval & 1023
        kbval  = kbval >> 10
        suffixidx = suffixidx + 1

    #return str(kbval)+"."+str(remainder) + suffixlist[suffixidx]
    remainderstr = ""
    if kbval < 100 and wholenumbers == False:
        remainder = int((remainder+50)/100)
        if remainder > 0:
            remainderstr = "."+str(remainder)
    elif remainder >= 500:
        kbval = kbval + 1
    return str(kbval)+remainderstr + suffixlist[suffixidx]

def argonsysinfo_listraid():
    hddlist = []
    outputlist = []
    # cat /proc/mdstat
    # multiple mdxx from mdstat
    # mdadm -D /dev/md1

    ramtotal = 0
    errorflag = False
    try:
        with open("/proc/mdstat", "r") as mdstat:
            for mdline in mdstat.readlines():
                mdline = mdline.strip()

                if " : " not in mdline:
                    continue
                if mdline.startswith("Personalities"):
                    continue
                if mdline.startswith("unused devices"):
                    continue

                # _ is the colon
                devname, _, raidstatus, raidtype, *raiddevices = mdline.split(' ')
                for raiddev in raiddevices:
                    #print(f"{devname}: {raiddev}")
                    hddlist.append(raiddev.split('[')[0])

                devdetail = argonsysinfo_getraiddetail(devname)
                outputlist.append({"title": devname, "value": raidtype, "info": devdetail})
    except IOError:
        # No raid
        errorflag = True

    return {'raidlist': outputlist, 'hddlist': hddlist}


def mdadm_to_dict(devname):
    """
    Map the output of mdadm -D to a python dictinary
    From:
    ...
        Raid Level : raid1
        Array Size : 1046528 (1022.00 MiB 1071.64 MB)
      Raid Devices : 2
    ...
    To:
    {
      'raid level': "raid1",
      'array size': "1046528 (1022.00 MiB 1071.64 MB)",
      'raid devices': "2",
    }

    N.B. devices from pool layout are added to extra "devlist" key
    """
    command = os.popen('mdadm -D /dev/'+devname)
    alllines = command.read().rstrip().split("\n")
    command.close()
    raid_metadata = {"devlist": [] }

    for mdline in alllines:
        mdline = mdline.strip().replace("  ", " ")
        if " : " in mdline:
            key, value = mdline.split(" : ", 1)
            key = key.lower()
            raid_metadata[key.lower()] = value

        # line that start with dev is the name of the array
        # (something like "/dev/md127:") which does not split.
        elif "/dev/" in mdline and not mdline.startswith("/dev/"):
            # to map bottom list of raid devices
            # only saves the final columt (i.e. device paths)
            devname = mdline.rsplit(" ", 1)[1]
            raid_metadata["devlist"].append(devname)

    return raid_metadata


def argonsysinfo_getraiddetail(devname):
    mddata = mdadm_to_dict(devname)

    resync = mddata.get('rebuild status', "")
    resync = mddata.get('resync status', "")
    resync = mddata.get('check status', "")

    hddlist = mddata.get("devlist", [])

    return {
        'state': mddata['state'],
        'raidtype': mddata['raid level'],
        'size': int(mddata['array size'].split()[0]),
        'used': int(mddata['used dev size'].split()[0]),
        'devices': int(mddata['total devices']),
        'active': int(mddata['active devices']),
        'working': int(mddata['working devices']),
        'failed': int(mddata['failed devices']),
        'spare': int(mddata['spare devices']),
        'resync': resync,
        'hddlist': hddlist,
    }


def argonsysinfo_diskusagedetail( disk,mapper : str = None ):
    readsector = 0
    writesector = 0
    discardsector = 0

    if mapper:
        this = mapper
    else:
        this = disk
    command = os.popen( "cat /sys/block/" + this + "/stat" )
    tmp = command.read()
    command.close()
    tmp.replace('\t',' ')
    tmp = tmp.strip()
    while tmp.find("  ") >= 0:
        tmp = tmp.replace("  ", " ")
    data = tmp.split(" ")
    if len(data) >= 11:
        readsector = data[2]
        writesector = data[6]

    return {'disk':disk, 'readsector':int(readsector), 'writesector':int(writesector)}

def argonsysinfo_diskusage():
    usage = []
    hddlist = argonsysinfo_listhddusage()
    for disk in hddlist:
        parms = {"disk" : disk}
        if "mapper" in hddlist[disk]:
            parms["mapper"] = hddlist[disk]["mapper"]
        temp = argonsysinfo_diskusagedetail( **parms )
        usage.append( temp )
    return usage

def argonsysinfo_truncateFloat( value, dp ):
    """ make sure the value passed in has no more decimal places than the
    passed in (dp) number of places.
    """
    value *= pow( 10, dp )
    value = round( value )
    value /= pow( 10, dp )
    return value

def argonsysinfo_convertCtoF( rawTemp, dp ):
    """ Convert a raw temperature in degrees C to degrees F, and make sure the
    value is truncated to the specified number of decimal places
    """
    rawTemp = (32 + (rawTemp * 9)/5)
    rawTemp = argonsysinfo_truncateFloat( rawTemp, dp )
    return rawTemp;

