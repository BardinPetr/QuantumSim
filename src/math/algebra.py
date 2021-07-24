from numpy import sin, cos, array


def rot_mat(angle):
    a, b = sin(angle), cos(angle)
    return array([
        [b, -a],
        [a, b]
    ])


def ip_str_to_bytes(ip):
    return bytes([int(i) for i in ip.split('.')])


def ip_bytes_to_str(data):
    return '.'.join([str(i) for i in data])
