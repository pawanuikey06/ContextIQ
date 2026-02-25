import requests
from requests.auth import HTTPBasicAuth

r = requests.get(
    'https://pawanuikey690.atlassian.net/rest/api/3/project',
    auth=HTTPBasicAuth('pawanuikey690@gmail.com', 'ATATT3xFfGF0O8ZDOLXJuVjenN_vtY5sFOZ1vIjaouN76avRSaOB2OmnoSjdLKY0ELv3PENYTi05uRXBeKjXY7E3h5mUUWS9IuiRYkBISqHvLMOVnjOXi0cbqSrotmd7Rk87QgfupW5B82Ob1SpfCAAMQkA2xcY5VTc3fm3UjAcO-DJMKG2R9tc=4EC699AD'),
    headers={'Accept': 'application/json'}
)
print("Status:", r.status_code)
if r.ok:
    projects = r.json()
    if not projects:
        print("No projects found! Create a project in Jira first.")
    for p in projects:
        print(f"  Key: {p['key']}   Name: {p['name']}")
else:
    print(r.text[:400])
