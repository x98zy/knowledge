import requests


url = "http://localhost:8000/api/v1/knowledge/get_embedding_models"
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwNmEyZDVkYy0xNmNhLTdmOWQtODAwMC0yMTE3YzMyYWQwMTYiLCJleHAiOjE3ODIxMzE0MTAsImlhdCI6MTc4MjEyOTYxMCwidHlwZSI6ImFjY2VzcyIsImp0aSI6ImY0Yzc4MWRiODMzODI4Yzg5NWY5Mjc4YTFlMmYwNWNiIn0.2hdTzED_60EIRRflQ-0Kg-ECkI5k7G-sKtAdkPNT0Oc",
}
response = requests.get(url, headers=headers)
print(response.json())
