# -=- encoding: utf-8 -=-

import json

MSG_TYPES = {
    'disconnect': 0,
    'connect': 1,
    'heartbeat' : 2,
    'message': 3,
    'json': 4,
    'event': 5,
    'ack': 6,
    'error': 7,
    'noop': 8,
    }

MSG_VALUES = dict((v,k) for k, v in MSG_TYPES.iteritems())

ERROR_REASONS = {
    'transport not supported': 0,
    'client not handshaken': 1,
    'unauthorized': 2
    }

ERROR_ADVICES = {
    'reconnect': 0,
    }

class Packet(object):
    # Message types
    DISCONNECT = "0"
    CONNECT = "1"
    HEARTBEAT = "2"
    MESSAGE = "3"
    JSON = "4"
    EVENT = "5"
    ACK = "6"
    ERROR = "7"
    NOOP = "8"

    socketio_packet_attributes = ['type', 'name', 'data', 'endpoint', 'args', 
                                  'ackId', 'reason', 'advice', 'qs', 'id']

    def __init__(self, type=None, name=None, data=None, endpoint=None, 
                 ack_with_data=False, qs=None, args=None,
                 reason=None, advice=None, error=None, id=None):
        """
        Models a packet

        ``type`` - One of the packet types above (MESSAGE, JSON, EVENT, etc..)
        ``name`` - The name used for events
        ``data`` - The actual data, before encoding
        ``endpoint`` - The Namespace's name to send the packet
        ``id`` - The absence of the transport id and session id segments will 
        signal the server this is a new, non-handshaken connection.
        ``ack_with_data`` - If True, return data (should be a sequence) with ack.
        ``reason`` - one of ERROR_* values
        ``advice`` - one of ADVICE_* values
        ``error``- an error message to be displayed
        """
        self.type = type
        self.name = name
        self.endpoint = endpoint
        self.ack_with_data = ack_with_data
        self.data = data
        self.qs = qs # query string
        if self.type == Packet.ACK and not msgid:
            raise ValueError("An ACK packet must have a message 'msgid'")

    @property
    def query(self):
        """Transform the query_string into a dictionary"""
        # TODO: do it
        return {}

    def _encode(self):
        """Return a dictionary with the packet parameters"""
        d = dict()
        for attr in self.socketio_packet_attributes:
            if self.__getattribute__(attr) is not None:
                d[attr] = self.__getattribute__(attr)
        return d

    def encode(self, data):
        """
        Encode an attribute dict into a byte string.
        """
        payload = ''
        type = str(MSG_TYPES[data['type']])
        msg = "" + type
        if type in ['0', '1']:
            # '1::' [path] [query]
            msg += '::' + data['endpoint']
            if 'qs' in data and data['qs'] != '':
                msg += ':' + data['qs']
        
        elif type == '2':
            # heartbeat
            msg += '::'
        
        elif type in ['3','4','5']:
            # '3:' [id ('+')] ':' [endpoint] ':' [data]
            # '4:' [id ('+')] ':' [endpoint] ':' [json]
            # '5:' [id ('+')] ':' [endpoint] ':' [json encoded event]
            # The message id is an incremental integer, required for ACKs. 
            # If the message id is followed by a +, the ACK is not handled by 
            # socket.io, but by the user instead.
            if msg == '3':
                payload = data['data']
            if msg == '4':
                payload = json.dumps(data['data'])
            if msg == '5':
                d = {}
                d['name'] = data['name']
                if data['args'] != []:
                    d['args'] = data['args'] 
                payload = json.dumps(d)
            if 'id' in data:
                msg += ':' + str(data['id'])
                if self.ack_with_data:
                    msg += '+:'
                else:
                    msg += ':'
            else:
                msg += '::'
            msg += data['endpoint'] + ':' + payload
        
        elif type == '6':
            # '6:::' [id] '+' [data]
            msg += ':::' + str(data['ackId'])
            if 'args' in data and data['args'] != []:
                msg += '+' + str(data['args'])
        
        elif type == '7':
            # '7::' [endpoint] ':' [reason] '+' [advice]
            msg += ':::'
            if 'reason' in data and data['reason'] is not '':
                msg += str(ERROR_REASONS[data['reason']])
            if 'advice' in data and data['advice'] is not '':
                msg += '+' + str(ERROR_ADVICES[data['advice']])
            msg += data['endpoint']

        return msg

    @staticmethod
    def decode(data):
        """
        Decode a rawstr packet arriving from the socket 
        into a dict.
        """
        decoded_msg = {}
        split_data = data.split(":", 3)

        msg_type = split_data[0]
        msg_id = split_data[1]
        endpoint = split_data[2]

        end_data = None

        if len(split_data) > 3:
            end_data = split_data[3]

        decoded_msg['type'] = MSG_VALUES[int(msg_type)]

        if msg_type == "0": # disconnect
            decoded_msg['endpoint'] = endpoint

        elif msg_type == "1": # connect
            decoded_msg['endpoint'] = endpoint
            decoded_msg['qs'] = endpoint

        elif msg_type == "2": # heartbeat
            decoded_msg['endpoint'] = endpoint

        elif msg_type == "3": # message
            decoded_msg['data'] = endpoint
            decoded_msg['endpoint'] = ''

        elif msg_type == "4": # json msg
            decoded_msg['data'] = json.loads(data)

        elif msg_type == "5": # event
            #print "EVENT with data", data
            try:
                decoded_msg.update(json.loads(end_data))
            except ValueError, e:
                import pdb; pdb.set_trace()
                print("Invalid JSON message", end_data)

            if "+" in msg_id:
                decoded_msg['id'] = msg_id
            else:
                pass # TODO send auto ack

        elif msg_type == "6": # ack
            tail = tail.split(':')[1]
            decoded_msg['ackId'] = tail
            decoded_msg['endpoint'] = ''

        elif msg_type == "7": # error
            els = data.split('+', 1)
            decoded_msg['reason'] = els[0]
            if len(els) == 2:
                decoded_msg['advice'] = els[1]

        elif msg_type == "8": # noop
            return None
        else:
            raise Exception("Unknown message type: %s" % msg_type)

        return decoded_msg