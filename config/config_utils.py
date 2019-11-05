import os


def get_default_sensors_config():
    my_dir = os.path.split(__file__)[0].replace("/", "\\")
    return os.path.join(my_dir, 'sensors_config.json')