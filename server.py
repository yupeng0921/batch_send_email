#! /usr/bin/env python

import os
import time
import yaml
import re
import ConfigParser
import logging
import traceback
from flask import Flask, request, redirect, url_for, render_template, abort
from werkzeug import secure_filename
import boto.ses

default_pseudo_send_count = 3
default_pattern_begin = u'\{\{'
default_pattern_end = u'\}\}'
def batch_send_email(sender_file_name, subject, emailbody_file_name, dest_file_name, actualsend):
    with open(sender_file_name, u'r') as f:
        conf = yaml.safe_load(f)

    if u'aws_access_key_id' not in conf:
        return u'no aws_access_key_id'
    aws_access_key_id = conf[u'aws_access_key_id']

    if u'aws_secret_access_key' not in conf:
        return u'no aws_secret_access_key'
    aws_secret_access_key = conf[u'aws_secret_access_key']

    if u'region' not in conf:
        return u'no region'
    region = conf[u'region']

    if u'email_address' not in conf:
        return u'no email_address'
    source = conf[u'email_address']

    if u'pseudo_send_count' in conf:
        pseudo_send_count = conf[u'pseudo_send_count']
    else:
        pseudo_send_count = default_pseudo_send_count

    if u'pattern_begin' in conf:
        pattern_begin = conf[u'pattern_begin']
    else:
        pattern_begin = default_pattern_begin

    if u'pattern_end' in conf:
        pattern_end = conf[u'pattern_end']
    else:
        pattern_end = default_pattern_end

    with open(emailbody_file_name) as f:
        emailbody = f.read()

    if emailbody_file_name[-5:] == u'.html':
        format = u'html'
    elif emailbody_file_name[-4:] == u'.txt':
        format = u'text'
    else:
        return u'unsupport format'
    conn = boto.ses.connect_to_region(region, aws_access_key_id = aws_access_key_id, aws_secret_access_key = aws_secret_access_key)
    ret = []
    send_count = 0
    f = open(dest_file_name)
    for eachline in f:
        tmpbody = emailbody
        items = eachline.split(u',')
        if len(items) < 1:
            continue
        to_addresses = items[0].strip()
        if not to_addresses:
            continue
        count = 1
        for item in items[1:]:
            item = item.strip()
            m = u'%s%s%s' % (pattern_begin, count, pattern_end)
            p = re.compile(m)
            tmpbody, n = re.subn(p, item, tmpbody)
            if n == 0:
                info = u'mismatch %s %s %s' % (to_addresses, item, count)
                ret.append(info)
            count += 1
        if actualsend:
            if format == u'html':
                conn.send_email(source, subject, None, to_addresses, format=format, return_path=source, html_body=tmpbody)
            else:
                conn.send_email(source, subject, None, to_addresses, format=format, return_path=source, text_body=tmpbody)
        else:
            if send_count < pseudo_send_count:
                pseudo_subject = u'%s [%s]' % (subject, to_addresses)
                if format == u'html':
                    conn.send_email(source, pseudo_subject, None, source, format=format, return_path=source, html_body=tmpbody)
                else:
                    conn.send_email(source, pseudo_subject, None, source, format=format, return_path=source, text_body=tmpbody)
        send_count += 1
    ret.append(u'done, send %d' % send_count)
    return ret

app = Flask(__name__)

upload_folder = u'upload'
@app.route(u'/', methods=[u'GET', u'POST'])
def index():
    if request.method == u'POST':
        timestamp = u'%f' % time.time()

        sender = request.files[u'sender']
        if not sender:
            return u'no sender information'
        filename = secure_filename(sender.filename)
        if filename[-5:] != u'.yaml':
            return u'sender file should be .yaml'
        sender_file_name = u'%s.%s' % (timestamp, filename)
        sender_file_name = os.path.join(upload_folder, sender_file_name)
        sender.save(sender_file_name)

        subject = request.form[u'subject']
        if not subject:
            os.remove(sender_file_name)
            return u'no subject'

        emailbody = request.files[u'emailbody']
        if not emailbody:
            os.remove(sender_file_name)
            return u'no emailbody'
        filename = secure_filename(emailbody.filename)
        if filename[-5:] != u'.html' and filename[-4:] != '.txt':
            os.remove(sender_file_name)
            return u'emailbody should be .html or .txt'
        emailbody_file_name = u'%s.%s' % (timestamp, filename)
        emailbody_file_name = os.path.join(upload_folder, emailbody_file_name)
        emailbody.save(emailbody_file_name)

        dest = request.files[u'dest']
        if not dest:
            os.remove(sender_file_name)
            os.remove(emailbody_file_name)
            return u'no dest'
        filename = secure_filename(dest.filename)
        if filename[-4:] != u'.csv':
            os.remove(sender_file_name)
            os.remove(emailbody_file_name)
            return u'dest file should be .csv'
        dest_file_name = u'%s.%s' % (timestamp, filename)
        dest_file_name = os.path.join(upload_folder, dest_file_name)
        dest.save(dest_file_name)

        value = request.form.getlist(u'actualsend')
        if u'actualsend' in value:
            actualsend = True
        else:
            actualsend = False
        ret = batch_send_email(sender_file_name, subject, emailbody_file_name, dest_file_name, actualsend)
        os.remove(sender_file_name)
        os.remove(emailbody_file_name)
        os.remove(dest_file_name)
        return u'%s' % ret
    return render_template(u'index.html')

if __name__ == u"__main__":
    app.debug = True
    app.run(host=u'0.0.0.0', port=80)
