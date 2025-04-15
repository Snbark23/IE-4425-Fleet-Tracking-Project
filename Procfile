services:
  - type: web
    name: fleet-track
    env: python
    plan: free
    buildCommand: "pip install -r requirements.txt"
    startCommand: "gunicorn app:app"