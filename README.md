Cooltimedia Web — Wagtail + Tailwind on GCP
Sitio web del portafolio Cooltimedia construido con Wagtail (Django CMS) y TailwindCSS, desplegado en una VM de Google Compute Engine con Gunicorn + Nginx + PostgreSQL.
Stack
Python 3.12
Django / Wagtail
TailwindCSS v4 (build estático con Node)
PostgreSQL
Gunicorn
Nginx
Ubuntu 24.04 (GCP)

1) Setup del entorno (servidor)
sudo apt update
sudo apt install -y python3-full python3-venv python3-pip build-essential \
libpq-dev postgresql postgresql-contrib nginx nodejs git

2) Virtual environment
cd /var/www/cooltimedia
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

