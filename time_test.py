from datetime import datetime

a = '12:00pm'

print(datetime.strptime(a, '%I:%M%p').hour)
# print(datetime.strptime(a, '%b %d %Y %I:%M%p'))
