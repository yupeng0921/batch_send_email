#! /usr/bin/env python

import os
import time
import ConfigParser
import logging
import traceback
from flask import Flask, request, redirect, url_for, render_template, abort
from werkzeug import secure_filename

app = Flask(__name__)

@app.route(u'/')
def index():
    return render_template(u'index.html')

if __name__ == u"__main__":
    app.debug = True
    app.run(host=u'0.0.0.0', port=80)
            
