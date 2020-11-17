from __future__ import print_function
import sys
import re
import fileinput
import requests
from config import ACCESS_TOKEN_VK, AD_ACCOUNT_ID, SPREADSHEET_ID
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from tkinter import *
"""from gui_utils import PlaceholderEntry
from tkinter import ttk"""

# GUI part (in place of command line style of input)
root = Tk()
root.title("Авто Бася")

'''ph_style = ttk.Style(root)

ph_style.configure("Placeholder.TEntry", foreground="#d5d5d5")
adid_input = PlaceholderEntry(root, "ID кампании в формате 1234567890", \
	style="TEntry", placeholder_style="Placeholder.TEntry")
adid_input.pack()'''

# Retrieving ad id saved earlier if one does exist
with open("config.py", "r") as f:
	text = f.read()
ad_id_regex = re.compile(r"AD_ID = (\d+)")
search_result = re.search(ad_id_regex, text)

if search_result:
	AD_ID = search_result.groups()[0]
else:
	AD_ID = None

# Here program splits its view in two versions
# One for the very first start, second is when ad id has been already stored during
# the previous launch
if AD_ID:
	Label(root, text=f"Текущий сохраненный ID кампании: {AD_ID}").pack()
else:
	Label(root, text="ID кампании не найден. Введите новый ID, чтобы продолжить выполнение программы").pack()

# Defining global variables to use in button clicking handling
DEFAULT_TEXT = True
NEW_AD_ID = None

def del_text(event):
	global DEFAULT_TEXT
	if DEFAULT_TEXT:
		adid_input.delete(0, END)
		DEFAULT_TEXT = False

def OKButton1_onclick():
	global AD_ID
	AD_ID = adid_input.get()
	if AD_ID.isdigit():
		with open("config.py", "a") as f:
			f.write(f"AD_ID = {AD_ID}\n")
		Label(root, text="Новый id кампании сохранен в файле config.py").pack()
		Label(root, text=f"Закройте окно, чтобы продолжить\n выполнение программы с ID {AD_ID}").pack()
	else:
		Label(root, text=f"ID должен состоять из цифр. Введите новый ID").pack()

def OKButton2_onclick():
	global NEW_AD_ID, AD_ID
	NEW_AD_ID = adid_input.get()
	if NEW_AD_ID.isdigit():
		old_AD_ID, AD_ID = AD_ID, NEW_AD_ID
		with fileinput.input("config.py", inplace=True) as f:
		    for line in f:
		        new_line = line.replace(f"AD_ID = {old_AD_ID}\n", f"AD_ID = {AD_ID}\n")
	        	print(new_line, end='')
		Label(root, text=f"Новый id кампании сохранен в файле config.py").pack()
		Label(root, text=f"Закройте окно, чтобы продолжить\n выполнение программы с ID {AD_ID}").pack()
	else:
		Label(root, text=f"ID должен состоять из цифр. Введите новый ID").pack()

def contButton_onclick():
	root.destroy()

if not AD_ID:
	adid_input = Entry(root, width=35, borderwidth=5)
	adid_input.insert(0, "ID кампании в формате 1234567890")
	adid_input.pack()
	adid_input.bind("<Button-1>", del_text)

	submitButton = Button(root, text="ОК", command=OKButton1_onclick)
	submitButton.pack()
elif AD_ID:
	continueButton = Button(root, text="Продолжить программу с текущим ID",\
	 command=contButton_onclick)
	continueButton.pack()
	Label(root, text="Или введите новый ID:").pack()

	adid_input = Entry(root, width=35, borderwidth=5)
	adid_input.insert(0, "ID кампании в формате 1234567890")
	adid_input.pack()
	adid_input.bind("<Button-1>", del_text)
	
	submitButton = Button(root, text="ОК", command=OKButton2_onclick)
	submitButton.pack()

root.mainloop()
# The end of GUI part 

if not AD_ID:
	raise Exception("Unknown exception during argument handling")

print(u"Выполнение обновления для id#{}\n".format(AD_ID))

# Calling ad statistics from vk api
print(u"Отправка запроса в ВК\n")
r = requests.get(f'https://api.vk.com/method/ads.getStatistics?account_id={AD_ACCOUNT_ID}&ids_type=campaign&ids={AD_ID}&period=overall&date_from=0&date_to=0&access_token={ACCESS_TOKEN_VK}&v=5.124')

json_response = r.json()

if "error" in json_response.keys():
	print(u"ВК не выполнил запрос, выход из программы\n")
	print(json_response)
	exit(1)

# Retrieving neccessary statistics
spent = json_response['response'][0]['stats'][0]['spent'].replace('.', ',')
views_count = json_response['response'][0]['stats'][0]['impressions']
clicks_count = json_response['response'][0]['stats'][0]['clicks']

print(f"Данные ВК, которые будут записаны в Гугл таблицу\n\
	Потрачено: {spent}\n\
	Просмотров: {views_count}\n\
	Кликов: {clicks_count}\n")

print(u"Отправка запроса в Гугл таблицы\n")

# Next is partly code from starter Google code
# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

creds = None
# The file token.pickle stores the user's access and refresh tokens, and is
# created automatically when the authorization flow completes for the first
# time.
if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)

service = build('sheets', 'v4', credentials=creds)

RANGE_NAME = u'Лист1'

# Call the Sheets API
sheet = service.spreadsheets()
result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                            range=RANGE_NAME).execute()
values = result.get('values', [])

if not values:
    print('Данные не найдены.\n')
else:
    print('Гугл таблица найдена\n')

# Finding a row to write values using ad id
id_column = [values[i][0] if values[i] else "" for i in range(len(values))]
if AD_ID in id_column:
	no_row_to_write = id_column.index(AD_ID)
else:
	print(u"ID компании не найден в Гугл таблице. Выход из программы.")
	exit(1)

# Columns numbers are hardcoded
columns_to_write = ['M', 'U', 'V']
values_to_write = [spent, views_count, clicks_count]
for i in range(len(values_to_write)):
    cell = columns_to_write[i] + f'{no_row_to_write+1}'
    body = {'values': [[values_to_write[i]]]}
    result = service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range=cell,
        valueInputOption='USER_ENTERED', body=body).execute()
    print('{} cell updated in the {} cell.'.format(result.get('updatedCells'), cell))

print(u"\nОбновление данных завершено. Выход из программы.\n")

