import json
from datetime import datetime

import arrow

import os
import uuid

import boto3
from dateutil.relativedelta import relativedelta
from pprint import pprint

import requests
import pandas as pd

from flask import render_template, make_response, jsonify, current_app, flash, request, redirect, url_for, session
from flask_login import login_required, login_user, current_user, logout_user
from flask_principal import identity_changed, Identity, AnonymousIdentity
from sqlalchemy import create_engine, or_, func, and_

from app.members import member_blueprint as member
from app.members.forms import MemberSearchForm, AnonymousMemberSearchForm, MemberLoginForm, MemberLoginOldForm, \
    MemberInfoForm

from app.members.models import *
from app.cmte.forms import IndividualScoreForm, MemberCMTEFeePaymentForm
from app.cmte.models import CMTEEventType, CMTEEventParticipationRecord, CMTEEventDoc, CMTEFeePaymentRecord
from app import admin_permission

from requests.adapters import HTTPAdapter
from urllib3.util import Retry

INET_API_TOKEN = os.environ.get('INET_API_TOKEN')
BASE_URL = 'https://mtc.thaijobjob.com/api/user'
MYSQL_HOST = os.environ.get('MYSQL_HOST')
MYSQL_USER = os.environ.get('MYSQL_USER')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD')
MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE')

template = '''
<div class="box">
<span class="label">ชื่อ นามสกุล</span> <span>{} {}</span><br>
<span class="label">Name</span> <span>{} {}</span><br>
<span class="label">หมายเลขใบอนุญาต</span> <span>{}</span><br>
<span class="label">วันหมดอายุ</span> <span class="title is-size-4 {}">{}</span><br>
<span class="help">{}</span>
</div>
'''

template_cmte_admin = '''
<div class="box">
<span class="label">ชื่อ นามสกุล</span> <span>{} {}</span><br>
<span class="label">Name</span> <span>{} {}</span><br>
<span class="label">Tel.</span> <span>{}</span><br>
<span class="label">Email</span> <span>{}</span><br>
<span class="label">หมายเลขใบอนุญาต</span> <span>{}</span><br>
<span class="label">วันหมดอายุ</span> <span class="title is-size-4 {}">{}</span><br>
<span class="help has-text-{}">{} {}</span><br>
<span class="label">Valid CMTE <span class="title is-size-5 has-text-info">{} คะแนน</span>
</div>
'''

template_cmte = '''
<div class="box">
<span class="label">ชื่อ นามสกุล</span> <span>{} {}</span><br>
<span class="label">Name</span> <span>{} {}</span><br>
<span class="label">หมายเลขใบอนุญาต</span> <span>{}</span><br>
<span class="label">วันหมดอายุ</span> <span class="title is-size-4 {}">{}</span><br>
<span class="help has-text-{}">{} {}</span><br>
<span class="label">Valid CMTE <span class="title is-size-5 has-text-info">{} คะแนน</span>
</div>
'''


def load_from_mtc(firstname=None, lastname=None, license_id=None):
    engine = create_engine(f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DATABASE}')
    engine.connect()
    if firstname and lastname:
        query = f'''
        SELECT member.mem_id, member.fname AS firstnameTH, member.lname AS lastnameTH, member.e_fname AS firstnameEN, member.e_lname AS lastnameEN, member.mobilesms AS mobilesms, member.email_member AS email 
        FROM member WHERE member.fname='{firstname}' AND member.lname='{lastname}';
        '''
        data = pd.read_sql_query(query, con=engine)
        if data.empty:
            return None
        data = data.squeeze().to_dict()

        query = f'''
        SELECT lic_mem.lic_id AS license_no, lic_mem.lic_exp_date AS end_date,lic_mem.lic_b_date,
        lic_status.lic_status_name AS status_license FROM lic_mem
        INNER JOIN lic_status ON lic_mem.lic_status_id=lic_status.lic_status_id
        WHERE lic_mem.mem_id={data['mem_id']}
        '''
        lic_data = pd.read_sql_query(query, con=engine)
        lic_data = lic_data.squeeze().to_dict()
        data.update(lic_data)
    elif license_id:
        query = f'''
        SELECT lic_mem.mem_id, lic_mem.lic_id AS license_no, lic_mem.lic_exp_date AS end_date,lic_mem.lic_b_date,
        lic_status.lic_status_name AS status_license FROM lic_mem
        INNER JOIN lic_status ON lic_mem.lic_status_id=lic_status.lic_status_id
        WHERE lic_mem.lic_id={license_id}
        '''
        lic_data = pd.read_sql_query(query, con=engine)
        data = lic_data.squeeze().to_dict()

        query = f'''
        SELECT member.mem_id, member.fname AS firstnameTH, member.lname AS lastnameTH, member.e_fname AS firstnameEN, member.e_lname AS lastnameEN, member.mobilesms AS mobilesms, member.email_member AS email 
        FROM member WHERE member.mem_id={data['mem_id']};
        '''
        mem_data = pd.read_sql_query(query, con=engine)
        mem_data = mem_data.squeeze().to_dict()
        data.update(mem_data)

    return [data]


def check_license_status(delta, status):
    if status == 'ปกติ' and delta.days > 0:
        return 'ปกติ'
    elif status == 'ปกติ' and delta.days < 0:
        return 'หมดอายุ'
    else:
        return status


@member.route('/search/test/<license_id>')
def search_test(license_id):
    try:
        response = requests.get(f'{BASE_URL}/GetdataBylicenseAndfirstnamelastname',
                                params={'search': license_id},
                                headers={'Authorization': 'Bearer {}'.format(INET_API_TOKEN)}, stream=True, timeout=99)

    except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout) as e:
        return str(e)
    else:
        data_ = response.json().get('results', [])
        return jsonify(data_)


@member.route('/admin')
@login_required
def admin_index():
    print(admin_permission.can())
    return render_template('members/admin/index.html')


@member.route('/admin/members', methods=['GET', 'POST'])
@login_required
def view_members():
    form = MemberSearchForm()
    if form.validate_on_submit():
        data_ = load_from_mtc(license_id=form.license_id.data)
        message = ''
        engine = create_engine(f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DATABASE}')
        engine.connect()
        for rec in data_:
            exp_date = arrow.get(rec.get('end_date', 'YYYY-MM-DD'), locale='th')
            delta = exp_date - arrow.now()
            license_status = check_license_status(delta, rec.get('status_license'))
            if form.license_renewal_date.data:
                renewal_date = form.license_renewal_date.data + relativedelta(years=-543)
                expire_date = renewal_date + relativedelta(years=5)
                query = f'''
                    SELECT cpd_work.w_title, cpd_work.w_bdate, cpd_work.w_edate, cpd_work.cpd_score FROM cpd_work
                    INNER JOIN member ON member.mem_id=cpd_work.mem_id
                    INNER JOIN lic_mem ON lic_mem.mem_id=member.mem_id
                    WHERE lic_id={form.license_id.data}
                    AND cpd_work.w_bdate BETWEEN '{renewal_date}' AND '{expire_date}'
                    AND cpd_work.w_appr_date IS NOT NULL
                    ORDER BY cpd_work.w_bdate DESC
                    '''
            else:
                query = f'''
                    SELECT cpd_work.w_title, cpd_work.w_bdate, cpd_work.w_edate, cpd_work.cpd_score FROM cpd_work
                    INNER JOIN member ON member.mem_id=cpd_work.mem_id
                    INNER JOIN lic_mem ON lic_mem.mem_id=member.mem_id
                    WHERE lic_id={form.license_id.data}
                    AND cpd_work.w_bdate BETWEEN lic_mem.lic_b_date AND lic_mem.lic_exp_date
                    AND cpd_work.w_appr_date IS NOT NULL
                    ORDER BY cpd_work.w_bdate DESC
                    '''
            valid_score_df = pd.read_sql_query(query, con=engine)
            message += template_cmte_admin.format(rec.get('firstnameTH'),
                                                  rec.get('lastnameTH'),
                                                  rec.get('firstnameEN'),
                                                  rec.get('lastnameEN'),
                                                  rec.get('mobilesms'),
                                                  rec.get('email'),
                                                  int(rec.get('license_no')),
                                                  'has-text-success' if delta.days > 0 else 'has-text-danger',
                                                  exp_date.format('DD MMMM YYYY', locale='th'),
                                                  'success' if license_status == 'ปกติ' else 'danger',
                                                  exp_date.humanize(granularity=['year', 'day'], locale='th'),
                                                  license_status,
                                                  valid_score_df.cpd_score.sum(),
                                                  )
            message += valid_score_df.to_html(classes='table is-fullwidth is-striped')
        resp = make_response(message)
        return resp
    else:
        print(form.errors)
    return render_template('members/admin/members.html', form=form)


@member.route('/search', methods=['GET', 'POST'])
def search_member():
    form = MemberSearchForm()
    if form.validate_on_submit():
        message = ''
        form.firstname.data = form.firstname.data.strip()
        form.lastname.data = form.lastname.data.strip()
        form.license_id.data = form.license_id.data.strip()
        if form.firstname.data and form.lastname.data:
            try:
                response = requests.get(f'{BASE_URL}/GetdataBylicenseAndfirstnamelastname',
                                        params={'search': f'{form.firstname.data} {form.lastname.data}'},
                                        headers={'Authorization': 'Bearer {}'.format(INET_API_TOKEN)}, stream=True,
                                        timeout=99)
            except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout) as e:
                resp = make_response(str(e))
            else:
                try:
                    data_ = response.json().get('results', [])
                except requests.exceptions.JSONDecodeError as e:
                    data_ = load_from_mtc(form.firstname.data, form.lastname.data)
                    for rec in data_:
                        exp_date = arrow.get(rec.get('end_date', 'YYYY-MM-DD'))
                        delta = exp_date - arrow.now()
                        license_status = check_license_status(delta, rec.get('status_license'))
                        message += template.format(rec.get('firstnameTH'),
                                                   rec.get('lastnameTH'),
                                                   rec.get('firstnameEN'),
                                                   rec.get('lastnameEN'),
                                                   int(rec.get('license_no')),
                                                   'has-text-success' if delta.days > 0 else 'has-text-danger',
                                                   exp_date.format('DD MMMM YYYY', locale='th'),
                                                   exp_date.humanize(granularity=['year', 'day'], locale='th'),
                                                   'is-success' if license_status == 'ปกติ' else 'is-danger',
                                                   license_status,
                                                   )

                    resp = make_response(message)
                else:
                    if not data_:
                        data_ = load_from_mtc(form.firstname.data, form.lastname.data)
                        if data_ is None:
                            message = '<h1 class="title has-text-danger">ไม่พบข้อมูลในระบบ</h1>'
                            resp = make_response(message)
                            resp.headers['HX-Trigger-After-Swap'] = json.dumps({"stopLoading": "#submit-btn"})
                            return resp
                    for rec in data_:
                        exp_date = arrow.get(rec.get('end_date', 'YYYY-MM-DD'))
                        delta = exp_date - arrow.now()
                        license_status = check_license_status(delta, rec.get('status_license'))
                        message += template.format(rec.get('firstnameTH'),
                                                   rec.get('lastnameTH'),
                                                   rec.get('firstnameEN'),
                                                   rec.get('lastnameEN'),
                                                   int(rec.get('license_no')),
                                                   'has-text-success' if delta.days > 0 else 'has-text-danger',
                                                   exp_date.format('DD MMMM YYYY', locale='th'),
                                                   exp_date.humanize(granularity=['year', 'day'], locale='th'),
                                                   'is-success' if license_status == 'ปกติ' else 'is-danger',
                                                   license_status,
                                                   )

                    resp = make_response(message)
        elif form.license_id.data:
            try:
                response = requests.get(f'{BASE_URL}/GetdataBylicenseAndfirstnamelastname',
                                        params={'search': f'{form.license_id.data}'},
                                        headers={'Authorization': 'Bearer {}'.format(INET_API_TOKEN)},
                                        stream=True, timeout=99,
                                        )
            except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout) as e:
                resp = make_response(str(e))
            else:
                try:
                    data_ = response.json().get('results', [])
                except requests.exceptions.JSONDecodeError as e:
                    print(f'***************{form.license_id.data}*************')
                    pprint(response.text)
                    # pprint(e)
                    data_ = load_from_mtc(license_id=form.license_id.data)
                    for rec in data_:
                        exp_date = arrow.get(rec.get('end_date', 'YYYY-MM-DD'), locale='th')
                        delta = exp_date - arrow.now()
                        license_status = check_license_status(delta, rec.get('status_license'))
                        message += template.format(rec.get('firstnameTH'),
                                                   rec.get('lastnameTH'),
                                                   rec.get('firstnameEN'),
                                                   rec.get('lastnameEN'),
                                                   int(rec.get('license_no')),
                                                   'has-text-success' if delta.days > 0 else 'has-text-danger',
                                                   exp_date.format('DD MMMM YYYY', locale='th'),
                                                   exp_date.humanize(granularity=['year', 'day'], locale='th'),
                                                   'is-success' if license_status == 'ปกติ' else 'is-danger',
                                                   license_status,
                                                   )
                    resp = make_response(message)
                else:
                    if not data_:
                        data_ = load_from_mtc(license_id=form.license_id.data)
                    for rec in data_:
                        exp_date = arrow.get(rec.get('end_date', 'YYYY-MM-DD'))
                        delta = exp_date - arrow.now()
                        pprint(response.json().get('results'))
                        # print(exp_date, delta.days)
                        license_status = check_license_status(delta, rec.get('status_license'))
                        message += template.format(
                            # rec.get('profile'),
                            rec.get('firstnameTH'),
                            rec.get('lastnameTH'),
                            rec.get('firstnameEN'),
                            rec.get('lastnameEN'),
                            int(rec.get('license_no')),
                            'has-text-success' if delta.days > 0 else 'has-text-danger',
                            exp_date.format('DD MMMM YYYY', locale='th'),
                            exp_date.humanize(granularity=['year', 'day'], locale='th'),
                            'is-success' if license_status == 'ปกติ' else 'is-danger',
                            license_status,
                        )

                    resp = make_response(message)
        else:
            resp = make_response('Error, no input found.')

        resp.headers['HX-Trigger-After-Swap'] = json.dumps({"stopLoading": "#submit-btn"})

        return resp

    return render_template('members/search_form.html', form=form)


@member.route('/info')
def view_member_info():
    return render_template('members/member_info.html')


@member.route('/login-otp', methods=['GET', 'POST'])
def login_otp():
    url = 'https://mtc.thaijobjob.com/api/auth/otp-confirm-login-mobile'
    form = MemberLoginForm()
    old_form = MemberLoginOldForm()
    if form.validate_on_submit():
        user = Member.query.filter_by(pid=form.pid.data).first()
        data = {
            'otp': form.otp.data,
            'license_no': user.license_number,
            'action': 'confirm_otp_login',
            'mobile_number': form.telephone.data,
            'id_card': form.pid.data
        }
        mobile_ref_id = request.form.get('mobile_ref_id')
        if mobile_ref_id:
            data['mobile_ref_id'] = mobile_ref_id
            data['action'] = 'confirm_otp_register'

        print('Confirming OTP..')
        retry = Retry(
            total=5,
            backoff_factor=2,
        )
        adapter = HTTPAdapter(max_retries=retry)
        s = requests.Session()
        s.mount('https://', adapter)
        response = s.post(f'{url}', json=data,
                          headers={'Authorization': 'Bearer {}'.format(INET_API_TOKEN)}, stream=True, timeout=99)
        print(response.status_code)
        if response.status_code == 200:
            session['login_as'] = 'member'
            login_user(user, remember=True)
            identity_changed.send(current_app._get_current_object(), identity=Identity(user.unique_id))
            flash('Logged in successfully', 'success')
            if request.args.get('next'):
                return redirect(request.args.get('next'))
            else:
                return redirect(url_for('member.index'))
        else:
            flash('OTP not matched.', 'danger')

    return render_template('members/login-otp.html', form=form, old_form=old_form)


@member.route('/login', methods=['GET', 'POST'])
def login():
    url = 'https://mtc.thaijobjob.com/api/auth/otp-confirm-login-mobile'
    form = MemberLoginForm()
    old_form = MemberLoginOldForm()
    if form.validate_on_submit():
        user = Member.query.filter_by(pid=form.pid.data).first()
        data = {
            'otp': form.otp.data,
            'license_no': user.license_number,
            'action': 'confirm_otp_login',
            'mobile_number': form.telephone.data,
            'id_card': form.pid.data
        }
        mobile_ref_id = request.form.get('mobile_ref_id')
        if mobile_ref_id:
            data['mobile_ref_id'] = mobile_ref_id
            data['action'] = 'confirm_otp_register'

        print('Confirming OTP..')
        retry = Retry(
            total=5,
            backoff_factor=2,
        )
        adapter = HTTPAdapter(max_retries=retry)
        s = requests.Session()
        s.mount('https://', adapter)
        response = s.post(f'{url}', json=data,
                          headers={'Authorization': 'Bearer {}'.format(INET_API_TOKEN)}, stream=True, timeout=99)
        print(response.status_code)
        if response.status_code == 200:
            session['login_as'] = 'member'
            login_user(user, remember=True)
            identity_changed.send(current_app._get_current_object(), identity=Identity(user.unique_id))
            flash('Logged in successfully', 'success')
            if request.args.get('next'):
                return redirect(request.args.get('next'))
            else:
                return redirect(url_for('member.index'))
        else:
            flash('OTP not matched.', 'danger')

    return render_template('members/login.html', form=form, old_form=old_form)


@member.route('/logout')
def logout():
    if current_user.is_authenticated:
        logout_user()
        for key in ('identity.name', 'identity.auth_type', 'login_as'):
            session.pop(key, None)

        # Tell Flask-Principal the user is anonymous
        identity_changed.send(current_app._get_current_object(), identity=AnonymousIdentity())
        flash('Logged out successfully', 'success')
    else:
        flash('User is not logged in.', 'warning')
    return redirect(url_for('member.index'))


@member.route('/')
@login_required
def index():
    license = current_user.license
    valid_cmte_scores = db.session.query(func.sum(CMTEEventParticipationRecord.score)) \
        .filter(
        CMTEEventParticipationRecord.license == license,
        CMTEEventParticipationRecord.score_valid_until == current_user.license.end_date).scalar()
    return render_template('members/index.html', valid_cmte_scores=valid_cmte_scores)


@member.route('/cmte/individual-scores/index', methods=['GET'])
@login_required
def individual_score_index():
    return render_template('members/cmte/individual_score_index.html')


@member.route('/cmte/individual-score-group/index', methods=['GET'])
@login_required
def individual_score_group_index():
    event_types = CMTEEventType.query \
        .filter_by(for_group=True, is_sponsored=False).all()
    return render_template('members/cmte/individual_score_group_index.html', event_types=event_types)


@member.route('/cmte/individual-scores/form', methods=['GET', 'POST'])
@login_required
def individual_score_form():
    if not current_user.license.get_active_cmte_fee_payment():
        flash('กรุณาชำระค่าธรรมเนียมการยื่นขอคะแนนส่วนบุคคลก่อนดำเนินการต่อ', 'warning')
        return redirect(url_for('member.index'))
    form = IndividualScoreForm()
    if form.validate_on_submit():
        record = CMTEEventParticipationRecord()
        form.populate_obj(record)
        record.individual = True
        record.license = current_user.license
        record.create_datetime = arrow.now('Asia/Bangkok').datetime
        s3_client = boto3.client('s3', aws_access_key_id=os.environ.get('BUCKETEER_AWS_ACCESS_KEY_ID'),
                                 aws_secret_access_key=os.environ.get('BUCKETEER_AWS_SECRET_ACCESS_KEY'),
                                 region_name=os.environ.get('BUCKETEER_AWS_REGION'))
        for doc_form in form.upload_files:
            _file = doc_form.upload_file.data
            print(_file)
            if _file:
                filename = _file.filename
                key = uuid.uuid4()
                s3_client.upload_fileobj(_file, os.environ.get('BUCKETEER_BUCKET_NAME'), str(key))
                doc = CMTEEventDoc(record=record, key=key, filename=filename)
                doc.upload_datetime = arrow.now('Asia/Bangkok').datetime
                doc.note = doc_form.note.data
                record.docs.append(doc)
                db.session.add(doc)
        db.session.add(record)
        db.session.commit()
        flash('ดำเนินการบันทึกข้อมูลเรียบร้อย โปรดรอการอนุมัติคะแนน', 'success')
        return redirect(url_for('member.individual_score_index'))
    return render_template('members/cmte/individual_score_form.html', form=form)


@member.route('/cmte/individual-score-group/<int:event_type_id>/form', methods=['GET', 'POST'])
@login_required
def individual_score_group_form(event_type_id):
    form = IndividualScoreForm()
    s3_client = boto3.client('s3', aws_access_key_id=os.environ.get('BUCKETEER_AWS_ACCESS_KEY_ID'),
                             aws_secret_access_key=os.environ.get('BUCKETEER_AWS_SECRET_ACCESS_KEY'),
                             region_name=os.environ.get('BUCKETEER_AWS_REGION'))
    all_docs = []
    for doc_form in form.upload_files:
        _file = doc_form.upload_file.data
        if _file:
            filename = _file.filename
            key = uuid.uuid4()
            s3_client.upload_fileobj(_file, os.environ.get('BUCKETEER_BUCKET_NAME'), str(key))
            all_docs.append((key, filename, doc_form.note.data))
    if form.validate_on_submit():
        for license_number in request.form.getlist('licenses'):
            record = CMTEEventParticipationRecord()
            form.populate_obj(record)
            record.individual = True
            record.license_number = license_number
            record.event_type_id = event_type_id
            record.create_datetime = arrow.now('Asia/Bangkok').datetime
            for key, filename, note in all_docs:
                doc = CMTEEventDoc(record=record, key=key, filename=filename)
                doc.upload_datetime = arrow.now('Asia/Bangkok').datetime
                doc.note = note
                db.session.add(doc)
            db.session.add(record)
        db.session.commit()
        flash('ดำเนินการบันทึกข้อมูลเรียบร้อย โปรดรอการอนุมัติคะแนน', 'success')
        return redirect(url_for('member.index'))
    return render_template('members/cmte/individual_score_group_form.html', form=form)


@member.route('/cmte/scores', methods=['GET', 'POST'])
@login_required
def summarize_cmte_scores():
    filter = request.args.get('filter', 'approved_valid')
    records = []
    query = CMTEEventParticipationRecord.query.filter_by(license_number=current_user.license_number)
    pending_query = query.filter(or_(
        and_(CMTEEventParticipationRecord.individual == True,
             CMTEEventParticipationRecord.approved_date == None,
             CMTEEventParticipationRecord.closed_date == None),
        and_(CMTEEventParticipationRecord.approved_date == None,
             CMTEEventParticipationRecord.individual == False)))
    if filter == 'pending':
        query = pending_query
    elif filter == 'approved':
        query = query.filter(CMTEEventParticipationRecord.approved_date != None)
    elif filter == 'approved_valid':
        query = query.filter(CMTEEventParticipationRecord.approved_date != None,
                             CMTEEventParticipationRecord.score_valid_until == current_user.license.end_date)
    query = query.order_by(CMTEEventParticipationRecord.create_datetime.desc())

    for record in query:
        if record.event:
            event_title = record.event.title
            start_date = record.event.start_date.strftime('%d/%m/%Y') if record.event.start_date else ''
            end_date = record.event.end_date.strftime('%d/%m/%Y') if record.event.end_date else ''
        else:
            event_title = record.activity.name if record.activity else 'กิจกรรมส่วนบุคคล'
            start_date = record.start_date.strftime('%d/%m/%Y') if record.start_date else ''
            end_date = record.end_date.strftime('%d/%m/%Y') if record.end_date else ''
        records.append({
            'ชื่อกิจกรรม': event_title,
            'รายละเอียด': record.desc or '',
            'เริ่ม': start_date,
            'สิ้นสุด': end_date,
            'หน่วยคะแนนที่ได้รับ': record.score or None,
            'สถาบันฝึกอบรม': record.event.sponsor if record.event else '-',
            'วันที่อนุมัติ': record.approved_date.strftime('%d/%m/%Y') if record.approved_date else '',
            'วันหมดอายุ': record.score_valid_until.strftime('%d/%m/%Y') if record.score_valid_until else '',
            'วันที่บันทึก': record.create_datetime.strftime('%d/%m/%Y') if record.create_datetime else '',
        })
    df = pd.DataFrame.from_dict(records)
    if not df.empty:
        total_scores = df['หน่วยคะแนนที่ได้รับ'].sum()
    else:
        total_scores = None
    # if current_user.license:
    #     pending_record_counts = current_user.license.pending_cmte_records.count()
    # else:
    #     pending_record_counts = 0
    score_table = df.to_html(index=False, classes='table table-striped')
    return render_template('members/cmte/score_summary.html',
                           pending_record_counts=pending_query.count(),
                           score_table=score_table, filter=filter,
                           total_scores=total_scores)


@member.route('/api/members')
@login_required
def get_members():
    term = request.args.get('term')
    search = f'%{term}%'
    members = []
    for member in Member.query.filter(or_(Member.th_firstname.like(search),
                                          Member.th_lastname.like(search))):
        members.append({
            'id': member.license_number,
            'text': member.th_fullname
        })

    print(members)

    return jsonify({'results': members})


@member.route('/api/otp', methods=['POST', 'GET'])
def get_login_otp():
    url = 'https://mtc.thaijobjob.com/api/auth/login-mobile'
    telephone = request.args.get('telephone').replace('-', '').replace(' ', '')
    pid = request.args.get('pid')
    response = requests.post(f'{url}',
                             json={'id_card': pid, 'mobile_number': telephone},
                             headers={'Authorization': 'Bearer {}'.format(INET_API_TOKEN)}, stream=True, timeout=99)
    if response.status_code == 200:
        resp_data = response.json().get('results')
        refcode = resp_data.get('refcode')
        message = resp_data.get('message')
        if message == 'confirm_otp_login':
            return f'<p class="help is-warning">ระบบได้ทำการส่งรหัส OTP แล้วกรุณากรอกรหัสที่ได้รับโดยทันที รหัสอ้างอิง OTP <strong>{refcode}</strong>"<p/>'
        elif message == 'confirm_otp_register':
            mobile_ref_id = resp_data.get('mobile_ref_id')
            return f'''<p class="help is-warning">
            ระบบได้ทำการส่งรหัส OTP แล้ว รหัสอ้างอิง OTP <strong>{refcode}</strong>
            <p/>
            <input type="hidden" name="mobile_ref_id" value="{mobile_ref_id}">
            '''
    else:
        return f'<p class="help is-danger">{response.json()}!</p>'


@member.post('/login/old-form')
def old_form_login():
    form = MemberLoginOldForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            username = form.username.data
            password = form.password.data
            user = Member.query.filter_by(username=username).first()
            if user:
                if user.check_password(password):
                    session['login_as'] = 'member'
                    login_user(user, remember=True)
                    identity_changed.send(current_app._get_current_object(), identity=Identity(user.unique_id))
                    flash('Logged in successfully', 'success')
                    if request.args.get('next'):
                        return redirect(request.args.get('next'))
                    else:
                        return redirect(url_for('member.index'))
                else:
                    flash('Wrong password.', 'danger')
            else:
                flash('Username not found.', 'danger')
    return redirect(url_for('member.login'))


@member.route('/members/info', methods=['GET', 'POST'])
@login_required
def edit_member_info():
    form = MemberInfoForm(obj=current_user)
    if request.method == 'POST':
        if form.validate_on_submit():
            form.populate_obj(current_user)
            db.session.add(current_user)
            db.session.commit()
            flash('บันทึกข้อมูลเรียบร้อยแล้ว', 'success')
            return redirect(url_for('member.index'))
        else:
            flash(f'{form.errors}', 'danger')
    return render_template('members/info_form.html', form=form)


@member.route('/members/cmte-payments')
@login_required
def list_cmte_payments():
    return render_template('members/cmte_fee_payments.html')


@member.route('/members/cmte-fee-payment-form', methods=['GET', 'POST'])
@login_required
def cmte_fee_payment_form():
    form = MemberCMTEFeePaymentForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            record = CMTEFeePaymentRecord()
            record.note = form.payment_datetime.data
            record.license_number = current_user.license.number
            record.start_date = current_user.license.start_date
            record.end_date = current_user.license.end_date
            _file = form.doc.upload_file.data
            s3_client = boto3.client('s3', aws_access_key_id=os.environ.get('BUCKETEER_AWS_ACCESS_KEY_ID'),
                                     aws_secret_access_key=os.environ.get('BUCKETEER_AWS_SECRET_ACCESS_KEY'),
                                     region_name=os.environ.get('BUCKETEER_AWS_REGION'))
            if _file:
                filename = _file.filename
                key = uuid.uuid4()
                s3_client.upload_fileobj(_file, os.environ.get('BUCKETEER_BUCKET_NAME'), str(key))
                record.doc = CMTEEventDoc(key=key, filename=filename)
            db.session.add(record)
            db.session.commit()
            flash('บันทึกข้อมูลเรียบร้อย รอการตรวจสอบจากเจ้าหน้าที่', 'success')
            return redirect(url_for('member.list_cmte_payments'))
        else:
            flash(f'{form.errors}', 'danger')
    return render_template('members/cmte/individual_score_payment_form.html', form=form)


@member.route('/api/members/search', methods=['GET', 'POST'])
def search_member_api():
    query = request.args.get('query')
    query = query.strip()
    if query:
        template = '''<table class="table is-fullwidth is-striped">'''
        template += '''
        <thead><th>ชื่อ</th><th>หมายเลขใบอนุญาตฯ</th><th>วันขึ้นทะเบียน - หมดอายุ</th><th>สถานะใบอนุญาต</th></thead>
        <tbody>
        '''
        licenses = [(license.member.license, license.member) for license in License.query.filter_by(number=query)]
        if not licenses:
            try:
                firstname, lastname = query.split(" ")
            except ValueError:
                pass
            else:
                members = Member.query.filter(and_(Member.th_firstname.like(f'%{firstname}%'),
                                                  Member.th_lastname.like(f'%{lastname}%')))
                licenses = [(member.license, member) for member in members]
        if not licenses:
            members = Member.query.filter(or_(Member.th_firstname.like(f'%{query}%'),
                                              Member.th_lastname.like(f'%{query}%')))
            licenses = [(member.license, member) for member in members]
        for lic, member in licenses:
            status_tag = '<span class="tag {}">{}</span>'
            if lic.end_date <= datetime.today().date():
                lic_status = status_tag.format('is-danger', 'หมดอายุ')
            elif lic.status:
                if lic.status == 'ปกติ':
                    lic_status = status_tag.format('is-success', lic.status)
                else:
                    lic_status = status_tag.format('is-warning', lic.status)
            else:
                lic_status = status_tag.format('is-success', 'ปกติ')
            if lic:
                template += f'<tr><td>{member.th_fullname}</td><td>{lic.number}</td><td>{lic.dates}</td><td>{lic_status}</tr>'
            else:
                lic = License.query.filter_by(member_id=member.id).first()
                template += f'<tr><td>{member.th_fullname}</td><td>{lic.number}</td><td>{lic.dates}</td><td>{lic_status}</tr>'
        template += '</tbody></table>'
        return make_response(template)
    return 'กรุณาระบุชื่อ นามสกุลหรือหมายเลขใบอนุญาตประกอบวิชาชีพ'
