/**
 *  RESTful HomeBrite CSRMesh Light Device Type
 *
 *  Copyright 2016 Dan Isla
 *
 *  Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
 *  in compliance with the License. You may obtain a copy of the License at:
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 *  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License
 *  for the specific language governing permissions and limitations under the License.
 *
 */
metadata {
  definition (name: "RESTful CSRMesh Light Control", namespace: "restful_csrmesh_light", author: "Dan Isla") {
    capability "Switch"
    capability "Switch Level"

    command "bright"
    command "dim"
    command "setLevel"
  }

  simulator {
    // TODO: define status and reply messages here
  }

  tiles {
    multiAttributeTile(name:"switch", type: "lighting", width: 6, height: 4, canChangeIcon: true) {
      tileAttribute ("device.switch", key: "PRIMARY_CONTROL") {
        attributeState "on", label:'${name}', action:"switch.off", icon:"st.lights.philips.hue-single", backgroundColor:"#79b821", nextState:"turningOff"
        attributeState "off", label:'${name}', action:"switch.on", icon:"st.lights.philips.hue-single", backgroundColor:"#ffffff", nextState:"turningOn"
        attributeState "turningOn", label:'${name}', action:"switch.off", icon:"st.lights.philips.hue-single", backgroundColor:"#79b821", nextState:"turningOff"
        attributeState "turningOff", label:'${name}', action:"switch.on", icon:"st.lights.philips.hue-single", backgroundColor:"#ffffff", nextState:"turningOn"
      }
      tileAttribute ("device.power", key: "SECONDARY_CONTROL") {
          attributeState "power", label:'Power level: ${currentValue}W', icon: "st.Appliances.appliances17"
      }
      tileAttribute ("device.level", key: "SLIDER_CONTROL") {
          attributeState "level", action:"switch level.setLevel"
      }
    }
  }
}

// parse events into attributes
def parse(String description) {
    def usn = getDataValue('ssdpUSN')
    log.debug "Parsing device description ${device.deviceNetworkId} ${usn} '${description}'"

    def parsedEvent = parseDiscoveryMessage(description)

    if (parsedEvent['body'] != null) {
        def xmlText = new String(parsedEvent.body.decodeBase64())
        def xmlTop = new XmlSlurper().parseText(xmlText)
        def cmd = xmlTop.cmd[0]
        def targetUsn = xmlTop.usn[0].toString()

        log.debug "Processing command ${cmd} for ${targetUsn}"

        parent.getAllChildDevices().each { child ->
            def childUsn = child.getDataValue("ssdpUSN").toString()
            if (childUsn == targetUsn) {
              log.debug "Cmd for child: ${child.device.label}: ${cmd}"
              /*
                if (cmd == 'poll') {
                    log.debug "Instructing child ${child.device.label} to poll"
                    child.poll()
                } else if (cmd == 'status-open') {
                    def value = 'open'
                    log.debug "Updating ${child.device.label} to ${value}"
                    child.sendEvent(name: 'contact', value: value)
                } else if (cmd == 'status-closed') {
                    def value = 'closed'
                    log.debug "Updating ${child.device.label} to ${value}"
                    child.sendEvent(name: 'contact', value: value)
                }
              */
            }
        }
    }
    null
}

private def parseDiscoveryMessage(String description) {
    def device = [:]
    def parts = description.split(',')
    parts.each { part ->
        part = part.trim()
        if (part.startsWith('devicetype:')) {
            def valueString = part.split(":")[1].trim()
            device.devicetype = valueString
        } else if (part.startsWith('mac:')) {
            def valueString = part.split(":")[1].trim()
            if (valueString) {
                device.mac = valueString
            }
        } else if (part.startsWith('networkAddress:')) {
            def valueString = part.split(":")[1].trim()
            if (valueString) {
                device.ip = valueString
            }
        } else if (part.startsWith('deviceAddress:')) {
            def valueString = part.split(":")[1].trim()
            if (valueString) {
                device.port = valueString
            }
        } else if (part.startsWith('ssdpPath:')) {
            def valueString = part.split(":")[1].trim()
            if (valueString) {
                device.ssdpPath = valueString
            }
        } else if (part.startsWith('ssdpUSN:')) {
            part -= "ssdpUSN:"
            def valueString = part.trim()
            if (valueString) {
                device.ssdpUSN = valueString
            }
        } else if (part.startsWith('ssdpTerm:')) {
            part -= "ssdpTerm:"
            def valueString = part.trim()
            if (valueString) {
                device.ssdpTerm = valueString
            }
        } else if (part.startsWith('headers')) {
            part -= "headers:"
            def valueString = part.trim()
            if (valueString) {
                device.headers = valueString
            }
        } else if (part.startsWith('body')) {
            part -= "body:"
            def valueString = part.trim()
            if (valueString) {
                device.body = valueString
            }
        }
    }

    device
}

private Integer convertHexToInt(hex) {
    Integer.parseInt(hex,16)
}

private String convertHexToIP(hex) {
    [convertHexToInt(hex[0..1]),convertHexToInt(hex[2..3]),convertHexToInt(hex[4..5]),convertHexToInt(hex[6..7])].join(".")
}

private getHostAddress() {
    def ip = getDataValue("ip")
    def port = getDataValue("port")

    if (!ip || !port) {
        def parts = device.deviceNetworkId.split(":")
        if (parts.length == 2) {
            ip = parts[0]
            port = parts[1]
        } else {
            //log.warn "Can't figure out ip and port for device: ${device.id}"
        }
    }

    //convert IP/port
    ip = convertHexToIP(ip)
    port = convertHexToInt(port)
    log.debug "Using ip: ${ip} and port: ${port} for device: ${device.id}"
    return ip + ":" + port
}

def getRequest(path) {
    log.debug "Sending request for ${path} from ${device.deviceNetworkId}"

    new physicalgraph.device.HubAction(
        'method': 'GET',
        'path': path,
        'headers': [
            'HOST': getHostAddress(),
        ], device.deviceNetworkId)
}


def on() {
    log.debug "Executing 'on'"
    getRequest("/light_on")
    // sendEvent(name:"switch", value:"on")
}

def off() {
    log.debug "Executing 'off'"
    getRequest("/light_off")
    // sendEvent(name:"switch", value:"off")
}

def setLevel(number) {
    log.debug "Executing 'setLevel' to ${number} for ${this.device.label}"
    getRequest("/light_level?level=${number}")
}

def bright() {
  log.debug "Executing bright()"
    getRequest("/light_bright")
}

def dim() {
  log.debug "Executing dim()"
    getRequest("/light_dim")
}
