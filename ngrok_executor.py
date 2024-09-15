import os

from pyngrok import ngrok


def start_ngrok():
    ngrok_token = os.environ.get("NGROK_TOKEN")
    port = os.environ.get("WEBAPP_PORT")
    ngrok.set_auth_token(ngrok_token)
    http_tunnel = ngrok.connect(f":{port}", "http")
    return http_tunnel.public_url
