"""miscoreblog public views.

Three pages right now:
  /             → ported landing (index.html)
  /privacidad/  → ported legal page
  /terminos/    → ported legal page

All three use madga's site context processor so analytics tags are
injected via {% madga_tracking site %} in the <head>.
"""

from django.shortcuts import render
from django.views.generic import TemplateView


class LandingView(TemplateView):
    template_name = "miscore/index.html"


class PrivacidadView(TemplateView):
    template_name = "miscore/privacidad.html"


class TerminosView(TemplateView):
    template_name = "miscore/terminos.html"
