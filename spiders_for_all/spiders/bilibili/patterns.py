import re

RGX_FIND_PLAYINFO = re.compile(r"<script>window\.__playinfo__=(.*?)</script>")
RGX_FIND_TITLE = re.compile(r"<title>(.*?)</title>")
