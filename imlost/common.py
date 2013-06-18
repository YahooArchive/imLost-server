# static common stuffs
USER_FIELDS = ['user_id', 'user_name', 'user_type', 'device_type', 'device_token', 'phone', 'password']
CHANGEABLE_FIELDS = ['phone', 'user_name', 'device_type', 'device_token']
USER_TYPES = ['caretaker','dependant']
SALT = "imLost5aBadsf,>213" # need to move to config
ONLINE_THRESHOLD = 900 # 15 mins