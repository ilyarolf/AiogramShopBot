import urllib.request


def get_sslipio_external_url():
    external_ip = urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
    sslip_url = "https://" + external_ip + ".sslip.io"
    print("external URL: " + sslip_url)
    return sslip_url


def get_bot_photo_id() -> str:
    with open("static/no_image.jpeg", "r") as f:
        return f.read()
