import requests

response = requests.get("https://www.youtube.com/@ai-peter/streams")

print(response.text)