#! /usr/bin/env python

import os
import time
import sqlite3
import yaml
import re
import codecs
import logging
from flask import Flask, request, redirect, url_for, render_template, abort
from werkzeug import secure_filename

with open(u'%s/conf.yaml' % os.path.dirname(__file__), u'r') as f:
    conf = yaml.safe_load(f)

db_path = conf[u'db_path']
table_name = conf[u'table_name']
magic_string = conf[u'magic_string']

app = Flask(__name__)

upload_folder = u'upload'
@app.route(u'/', methods=[u'GET', u'POST'])
def index():
    if request.method == u'POST':
        cx = sqlite3.connect(db_path)

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
        subject_file_name = os.path.join(upload_folder, u'%s.subject.txt' % timestamp)
        with codecs.open(subject_file_name, u'w', u'utf-8') as f:
            f.write(subject)

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

        cu = cx.cursor()
        cmd = u'delete from %s where magic_string="%s" and status="done"' % \
            (table_name, magic_string)
        cu.execute(cmd)
        cx.commit()
        status = u'waiting'
        complete_count = 0
        result_info = u'NA'
        sender_file_name = os.path.abspath(sender_file_name)
        subject_file_name = os.path.abspath(subject_file_name)
        emailbody_file_name = os.path.abspath(emailbody_file_name)
        dest_file_name = os.path.abspath(dest_file_name)
        cmd = u'insert into %s values("%s", "%s", "%s", "%s", "%s", %d, "%s", %d, "%s")' % \
            (table_name, magic_string, sender_file_name, subject_file_name, emailbody_file_name, \
                 dest_file_name, actualsend, status, complete_count, result_info)
        try:
            cu.execute(cmd)
            cx.commit()
        except Exception, e:
            cu.close()
            cx.close()
            return unicode(e)
        cu.close()
        cx.close()
        return redirect(url_for(u'index'))
    cx = sqlite3.connect(db_path)
    cu = cx.cursor()
    # cmd = u'select status, complete_count, result_info from %s where magic_string="%s"' % \
    #     (table_name, magic_string)
    cmd = u'select * from %s where magic_string="%s"' % \
        (table_name, magic_string)
    cu.execute(cmd)
    ret = cu.fetchone()
    if ret:
        (m, sender_file_name, subject_file_name, emailbody_file_name, \
                 dest_file_name, actualsend, status, complete_count, result_info) = ret
        if status == u'done':
            try:
                os.remove(sender_file_name)
            except Exception, e:
                pass
            try:
                os.remove(subject_file_name)
            except Exception, e:
                pass
            try:
                os.remove(emailbody_file_name)
            except Exception, e:
                pass
            try:
                os.remove(dest_file_name)
            except Exception, e:
                pass
        info = u'status: %s\ncomplete_count: %d\n%s' % \
            (status, complete_count, result_info)
    else:
        info = u'NA'
    cu.close()
    cx.close()
    return render_template(u'index.html', status=info)

if __name__ == u"__main__":
    app.debug = True
    app.run(host=u'0.0.0.0', port=80)
