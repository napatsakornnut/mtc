import os
from pprint import pprint

import click
import pandas as pd
import pytz
from flask import session, render_template
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from flask_principal import identity_loaded, UserNeed, RoleNeed, ActionNeed
from sqlalchemy import create_engine, extract

from app import create_app, admin

app = create_app()

from app.models import *


class ClientAdminView(ModelView):
    column_display_pk = True
    form_columns = ['id', 'name']

    def create_model(self, form):
        client = Client(id=form.id.data, name=form.name.data)
        client.generate_api_key()
        return client


admin.add_view(ModelView(User, db.session))
admin.add_view(ClientAdminView(Client, db.session))
admin.add_view(ModelView(Role, db.session, category='Permissions'))


from app.cmte.models import *

admin.add_view(ModelView(CMTEEvent, db.session, category='CMTE'))
admin.add_view(ModelView(CMTEEventCategory, db.session, category='CMTE'))
admin.add_view(ModelView(CMTEEventType, db.session, category='CMTE'))
admin.add_view(ModelView(CMTEEventFormat, db.session, category='CMTE'))
admin.add_view(ModelView(CMTEEventFeeRate, db.session, category='CMTE'))
admin.add_view(ModelView(CMTEEventCode, db.session, category='CMTE'))
admin.add_view(ModelView(CMTEEventDoc, db.session, category='CMTE'))
admin.add_view(ModelView(CMTEEventParticipationRecord, db.session, category='CMTE'))
admin.add_view(ModelView(CMTEEventActivity, db.session, category='CMTE'))

admin.add_view(ModelView(CMTESponsorMember, db.session, category='Sponsor'))
admin.add_view(ModelView(CMTEEventSponsor, db.session, category='Sponsor'))
admin.add_view(ModelView(CMTESponsorDoc, db.session, category='Sponsor'))
admin.add_view(ModelView(CMTEReceiptDoc, db.session, category='Sponsor'))
admin.add_view(ModelView(CMTEReceiptDetail, db.session, category='Sponsor'))
admin.add_view(ModelView(CMTESponsorRequest, db.session, category='Sponsor'))
admin.add_view(ModelView(CMTESponsorEditRequest, db.session, category='Sponsor'))
admin.add_view(ModelView(CMTESponsorQualification, db.session, category='Sponsor'))

admin.add_view(ModelView(CMTEFeePaymentRecord, db.session, category='Members'))

from app.members.models import Member, License

admin.add_view(ModelView(License, db.session, category='Members'))
admin.add_view(ModelView(Member, db.session, category='Members', endpoint='members_'))


@login_manager.user_loader
def load_user(user_id):
    if session.get('login_as') == 'member':
        return Member.query.get(int(user_id))
    elif session.get('login_as') == 'cmte_sponsor_admin':
        return CMTESponsorMember.query.get(int(user_id))

    return User.query.get(int(user_id))


@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
    # Set the identity user object
    identity.user = current_user

    # Add the UserNeed to the identity
    if hasattr(current_user, 'unique_id'):
        identity.provides.add(UserNeed(current_user.unique_id))

    # Assuming the User model has a list of roles, update the
    # identity with the roles that the user provides
    if isinstance(current_user, User):
        for role in current_user.roles:
            identity.provides.add(RoleNeed(role.role_need))
    elif isinstance(current_user, CMTESponsorMember):
        identity.provides.add(RoleNeed('CMTESponsorAdmin'))
        # TODO: modify this after adding expire date
        # if current_user.sponsor.expire_date > arrow.now('Asia/Bangkok').date():
        #     print('sponsor is valid')
        identity.provides.add(ActionNeed('manageEvents'))


HOST = os.environ.get('MYSQL_HOST')
DATABASE = os.environ.get('MYSQL_DATABASE')
PASSWORD = os.environ.get('MYSQL_PASSWORD')
USER = os.environ.get('MYSQL_USER')
# HOST = '127.0.0.1'
# DATABASE = 'testdb'
# PASSWORD = 'Intrinity0'
# USER = 'root'
if os.environ.get('DATABASE_URL').startswith('postgresql'):
    DEST_DATABASE = os.environ.get('DATABASE_URL')
else:
    DEST_DATABASE = os.environ.get('DATABASE_URL').replace('postgres', 'postgresql')

src_engine = create_engine(f'mysql+pymysql://{USER}:{PASSWORD}@{HOST}/{DATABASE}?charset=utf8')
dest_engine = create_engine(DEST_DATABASE)


@app.cli.command('load-sponsor-admin-accounts')
def load_sponsor_admin_accounts():
    df = pd.read_sql_query(f'SELECT * FROM training_center;', con=src_engine)
    print(df)


@app.cli.command('load-members')
def load_members():
    # TODO: remove duplicated PID
    # TODO: add back unique constraints to some fields
    query = f'''SELECT mem_id AS old_mem_id, title_id AS th_title,
    fname AS th_firstname, lname AS th_lastname, e_title AS en_title,
    e_fname AS en_firstname, e_lname AS en_lastname, persion_id AS pid,
    login_user AS username, login_password AS password, mobilesms AS tel,
    birthday as dob, email_member AS email, mem_id_txt AS number
    FROM member
    WHERE mem_id_txt IS NOT NULL AND mem_id < 50000;'''
    df = pd.read_sql_query(query, con=src_engine)
    df['dob'] = df.dob.apply(lambda dt: None if dt == '0000-00-00' else dt)
    df.to_sql('members', dest_engine, if_exists='append', index=False)


@app.cli.command('load-licenses')
def load_licenses():
    query = f'''SELECT mem_id AS mem_id, appr_date AS issue_date,
    lic_b_date AS start_date, lic_exp_date AS end_date, CAST(lic_id AS CHAR) AS number
    FROM lic_mem;'''
    df = pd.read_sql_query(query, con=src_engine)
    for idx, row in df.iterrows():
        mem_id = row['mem_id']
        member = Member.query.filter_by(old_mem_id=mem_id).first()
        license = License.query.filter_by(number=row['number']).first()
        if member:
            if license is None:
                license = License(issue_date=row['issue_date'],
                                  start_date=row['start_date'],
                                  end_date=row['end_date'],
                                  member=member,
                                  number=row['number'])
                db.session.add(license)
                db.session.commit()
                print(f'{license.number} has been added!')
            else:
                print(f'{license.number} already exists!')
        else:
            print(f'Member {mem_id} is not matched!')


@app.cli.command('load-training-centers')
def load_training_centers():
    query = f'''SELECT training_center_id AS old_id, training_center_name AS name,
    training_center_code AS code, training_center_add AS address,
    training_center_zipcode AS zipcode, training_center_tel as telephone
    FROM training_center;'''
    df = pd.read_sql_query(query, con=src_engine)
    df['telephone'] = df.telephone.map(lambda x: x.replace('-', '') if x else x)
    df.to_sql('cmte_event_sponsors', dest_engine, if_exists='append', index=False)


@app.cli.command('load-training-center-members')
def load_training_center_members():
    query = f'''SELECT user_id AS old_user_id, user_password AS password,
    fname AS firstname, lname AS lastname, user_email AS email,
    mobile_phone AS telephone, training_center_id AS training_center_id
    FROM user;'''
    df = pd.read_sql_query(query, con=src_engine)
    for idx, row in df.iterrows():
        user_id = row['old_user_id']
        member = CMTESponsorMember.query.filter_by(old_user_id=user_id).first()
        sponsor = CMTEEventSponsor.query.filter_by(old_id=row['training_center_id']).first()
        if not sponsor:
            continue
        if not member:
            member = CMTESponsorMember(old_user_id=user_id,
                                       firstname=row['firstname'],
                                       lastname=row['lastname'],
                                       email=row['email'],
                                       telephone=row['telephone'],
                                       sponsor=sponsor
                                       )
            member.password = row['password']
            db.session.add(member)
            db.session.commit()
            print(f'{member.email} has been added!')
        else:
            print(f'{member.email} already exists!')


@app.cli.command('load-cpd-types')
def load_cpd_types():
    query = f'''SELECT cpd_type_no AS old_id, type_name AS name,
    type_detail AS 'desc', max_score AS max_score FROM cpd_type;'''
    df = pd.read_sql_query(query, con=src_engine)
    df.to_sql('cmte_event_types', dest_engine, if_exists='append', index=False)


@app.cli.command('load-cpd-activities')
def load_cpd_activities():
    query = f'''SELECT act_no AS old_id, cpd_type_no AS cpd_type_id,
    act_t_name AS name, act_e_name AS en_name, act_detail AS detail FROM cpd_activi;'''
    df = pd.read_sql_query(query, con=src_engine)
    for idx, row in df.iterrows():
        cpd_type_id = row['cpd_type_id']
        event_type = CMTEEventType.query.filter_by(old_id=cpd_type_id).first()
        activity = CMTEEventActivity.query.filter_by(old_id=row['old_id']).first()
        if not event_type:
            continue
        if not activity:
            activity = CMTEEventActivity(old_id=row['old_id'],
                                         name=row['name'],
                                         en_name=row['en_name'],
                                         detail=row['detail'],
                                         event_type=event_type
                                         )
            db.session.add(activity)
            db.session.commit()
            print(f'{activity.name} has been added!')
        else:
            print(f'{activity.name} already exists!')


@app.cli.command('load-cpd-events')
def load_cpd_events():
    query = f'''
    SELECT train_id, train_name_head AS title, begin_date, place_name_open AS venue,
    end_date, act_no AS activity_id, cpd_score,
    appr_date, exp_date, place_name_open, training_center_id AS sponsor_id
    FROM training_subject WHERE (day(begin_date) > 0 AND month(begin_date) > 0 AND year(begin_date) > 0)
    AND ((day(end_date) > 0 AND month(end_date) > 0 AND year(end_date) > 0) or end_date IS NULL)
    AND train_id > 0
    AND train_name_head IS NOT NULL
    '''
    print('Reading from db...')
    df = pd.read_sql_query(query, con=src_engine)
    df.replace({pd.NaT: None}, inplace=True)
    print(df.head())
    print(f'Total records is {len(df)}.')
    for idx, row in df.iterrows():
        activity = CMTEEventActivity.query.filter_by(old_id=row['activity_id']).first()
        sponsor = CMTEEventSponsor.query.filter_by(old_id=row['sponsor_id']).first()
        event = CMTEEvent(title=row['title'],
                          old_id=row['train_id'],
                          activity=activity,
                          venue=row['venue'],
                          start_date=row['begin_date'],
                          end_date=row['end_date'],
                          approved_datetime=row['appr_date'],
                          cmte_points=row['cpd_score'],
                          sponsor=sponsor)
        db.session.add(event)
        db.session.commit()
        print(f'{event.title} has been added!')


@app.cli.command('load-cpd-event-records')
@click.argument('year')
@click.argument('month')
def load_cpd_event_records(year, month):
    query = f'''
    SELECT train_id AS event_id, w_edate AS end_date, w_bdate AS start_date,
    mem_id, w_appr_date AS approved_datetime, cpd_score FROM cpd_work
    WHERE ((day(w_edate) > 0 AND month(w_edate) > 0 AND year(w_edate) > 0) or w_edate is null)
    AND day(w_bdate) > 0 AND month(w_bdate) = {month} AND year(w_bdate) = {year}
    AND ((day(w_appr_date) > 0 AND month(w_appr_date) > 0) OR w_appr_date IS NULL)
    AND train_id > 0
    ;
    '''
    df = pd.read_sql_query(query, con=src_engine)
    print(df.head())
    for idx, row in df.iterrows():
        member = Member.query.filter_by(old_mem_id=row['mem_id']).first()
        license = member.license
        if not license:
            print(member.old_mem_id, 'No license found.')
            continue
        event = CMTEEvent.query.filter_by(old_id=row['event_id']).first()
        end_date = row['end_date'] or row['start_date']
        if end_date > license.start_date:
            score_valid_until = license.end_date
        else:
            score_valid_until = license.start_date - timedelta(days=1)
        record = CMTEEventParticipationRecord(license=license,
                                              event=event,
                                              score=row['cpd_score'],
                                              approved_date=row['approved_datetime'],
                                              score_valid_until=score_valid_until)
        db.session.add(record)
        db.session.commit()
        print('.', end='', flush=True)


@app.cli.command('load-cpd-event-records-2')
@click.argument('year')
@click.argument('month')
@click.argument('event_id')
def load_cpd_event_records_2(year, month, event_id):
    query = f'''
    SELECT train_id AS event_id, w_edate AS end_date, w_bdate AS start_date,
    mem_id, w_appr_date AS approved_datetime, cpd_score FROM cpd_work
    WHERE ((day(w_edate) > 0 AND month(w_edate) > 0 AND year(w_edate) > 0) or w_edate is null)
    AND day(w_bdate) > 0 AND month(w_bdate) = {month} AND year(w_bdate) = {year}
    AND ((day(w_appr_date) > 0 AND month(w_appr_date) > 0) OR w_appr_date IS NULL)
    AND train_id is null AND cpd_type_no=7 AND act_no=70; 
    ;
    '''
    df = pd.read_sql_query(query, con=src_engine)
    print(df.head())
    for idx, row in df.iterrows():
        member = Member.query.filter_by(old_mem_id=row['mem_id']).first()
        license = member.license
        if not license:
            print(member.old_mem_id, 'No license found.')
            continue
        event = CMTEEvent.query.get(event_id)
        end_date = row['end_date'] or row['start_date']
        if end_date > license.start_date:
            score_valid_until = license.end_date
        else:
            score_valid_until = license.start_date - timedelta(days=1)
        record = CMTEEventParticipationRecord(license=license,
                                              event=event,
                                              score=row['cpd_score'],
                                              approved_date=row['approved_datetime'] or datetime.datetime(2022, 1, 8),
                                              score_valid_until=score_valid_until)
        db.session.add(record)
        db.session.commit()
        print('.', end='', flush=True)


@app.cli.command('load-cpd-event-individual-records')
@click.argument('year')
def load_cpd_event_individual_records(year):
    query = f'''
    SELECT train_id AS event_id, w_edate AS end_date, w_bdate AS start_date,
    mem_id, w_appr_date AS approved_datetime, cpd_score, w_title
    FROM cpd_work
    WHERE ((day(w_edate) > 0 AND month(w_edate) > 0 AND year(w_edate) > 0) or w_edate is null)
    AND day(w_bdate) > 0 AND month(w_bdate) > 0 AND year(w_bdate) = {year}
    AND ((day(w_appr_date) > 0 AND month(w_appr_date) > 0) OR w_appr_date IS NULL)
    AND train_id = 0
    ;
    '''
    df = pd.read_sql_query(query, con=src_engine)
    print(df.head())
    print(len(df))
    for idx, row in df.iterrows():
        member = Member.query.filter_by(old_mem_id=row['mem_id']).first()
        if not member:
            print(row['mem_id'], 'Member not found..')
            continue
        license = member.license
        if not license:
            print(member.old_mem_id, 'No license found.')
            continue
        end_date = row['end_date'] or row['start_date']
        if end_date > license.start_date:
            score_valid_until = license.end_date
        else:
            score_valid_until = license.start_date - timedelta(days=1)
        record = CMTEEventParticipationRecord(license=license,
                                              start_date=row['start_date'],
                                              end_date=row['end_date'],
                                              desc=row['w_title'],
                                              individual=True,
                                              score=row['cpd_score'],
                                              approved_date=row['approved_datetime'],
                                              score_valid_until=score_valid_until)
        db.session.add(record)
        db.session.commit()
        print('.', end='', flush=True)


@app.cli.command('load-cpd-payment')
def load_cpd_payment():
    query = f'''SELECT lic_id, lic_exp_date, lic_b_date FROM pay_cmte_lic;'''
    df = pd.read_sql_query(query, con=src_engine)
    print(df.head())
    for idx, row in df.iterrows():
        record = CMTEFeePaymentRecord(license_number=str(int(row['lic_id'])),
                                      payment_datetime=row['lic_b_date'],
                                      start_date=row['lic_b_date'],
                                      end_date=row['lic_exp_date'])
        db.session.add(record)
        db.session.commit()
        print('.', end='', flush=True)


@app.cli.command('convert-event-year')
def convert_event_year():
    from dateutil.relativedelta import relativedelta
    bangkok = pytz.timezone('Asia/Bangkok')
    for e in CMTEEvent.query:
        if e.start_date and e.start_date.year > 2100:
            new_start_date = e.start_date - relativedelta(years=543)
            e.start_date = new_start_date.astimezone(bangkok)
        if e.end_date and e.end_date.year > 2100:
            new_end_date = e.end_date - relativedelta(years=543)
            e.end_date = new_end_date.astimezone(bangkok)
        db.session.add(e)
    db.session.commit()


@app.cli.command('update-record-enddate')
@click.option('--dry-run', is_flag=True, default=False, help='Dry run')
@click.argument('license', required=False)
@click.option('--year', required=False, help='Year to update')
def update_record_enddate(dry_run, year=None, license=None):
    if dry_run:
        print('Dry running..')
    n_enddate = 0
    n_startdate = 0
    query = CMTEEventParticipationRecord.query.filter_by(individual=False)
    if year:
        query = query.join(CMTEEventParticipationRecord.event) \
            .filter(extract('year', CMTEEvent.end_date) == int(year))
    if license:
        query = query.filter_by(license_number=license)
    for record in query:
        if record.score_valid_until:
            if record.event:
                if record.event.end_date:
                    if record.event.end_date.date() >= record.license.start_date \
                            and record.score_valid_until != record.license.end_date:
                        # print(f'{record.event.start_date.date()} - {record.event.end_date.date()}: {record.license.number}({record.license.start_date} - {record.license.end_date})')
                        record.score_valid_until = record.license.end_date
                        if not dry_run:
                            db.session.add(record)
                        n_enddate += 1
                else:
                    if record.event.start_date.date() and record.event.start_date >= record.license.start_date \
                            and record.score_valid_until != record.license.end_date:
                        # print(f'{record.event.start_date.date()} - None: {record.license.start_date} - {record.license.end_date}')
                        record.score_valid_until = record.license.end_date
                        if not dry_run:
                            db.session.add(record)
                        n_startdate += 1
    if not dry_run:
        db.session.commit()
    print(f'with end date = {n_enddate}, with no end date = {n_startdate}')


@app.cli.command('update-individual-record-enddate')
@click.option('--dry-run', is_flag=True, default=False, help='Dry run')
def update_individual_record_enddate(dry_run):
    n = 0
    for record in CMTEEventParticipationRecord.query.filter_by(individual=True):
        if record.score_valid_until:
            if record.end_date:
                if record.end_date >= record.license.start_date \
                        and record.score_valid_until != record.license.end_date:
                    record.score_valid_until = record.license.end_date
                    n += 1
                    if not dry_run:
                        db.session.add(record)
            else:
                if record.start_date and record.start_date >= record.license.start_date \
                        and record.score_valid_until != record.license.end_date:
                    record.score_valid_until = record.license.end_date
                    n += 1
                    if not dry_run:
                        db.session.add(record)
    if not dry_run:
        db.session.commit()
    print(n)


@app.cli.command('test-cmte-score-endpoint')
@click.argument('base_url')
@click.argument('license_no')
def test_cmte_score_endpoint(base_url, license_no):
    import requests
    client_id = os.environ.get('MTC_CLIENT_ID')
    client_secret = os.environ.get('MTC_CLIENT_SECRET')
    print('Getting an access token..')
    resp = requests.post(f'{base_url}/api/auth/login',
                         json={'client_id': client_id,
                               'client_secret': client_secret})
    token = resp.json().get('access_token')
    print(token, resp.json())
    print('Fetching data..')
    resp = requests.get(f'{base_url}/api/members/{license_no}/cmte/scores',
                        headers={'Authorization': f'Bearer {token}'})
    print(resp.json())


@app.cli.command('test-member-pid-local-endpoint')
@click.argument('pid')
def test_member_pid_local_endpoint(pid):
    import requests
    client_id = os.environ.get('CLIENT_ID')
    client_secret = os.environ.get('CLIENT_SECRET')
    base_url = 'http://127.0.0.1:5000'
    print('Getting an access token..')
    resp = requests.post(f'{base_url}/api/auth/login',
                         json={'client_id': client_id, 'client_secret': client_secret})
    token = resp.json().get('access_token')
    print('Fetching data..')
    resp = requests.get(f'{base_url}/api/members/pids/{pid}',
                        headers={'Authorization': f'Bearer {token}'})
    if resp.status_code != 200:
        print(f'Error! {resp.status_code}')
    else:
        pprint(resp.json())


@app.cli.command('test-member-pid-endpoint')
@click.argument('pid')
def test_member_pid_endpoint(pid):
    import requests
    client_id = os.environ.get('MTC_CLIENT_ID')
    client_secret = os.environ.get('MTC_CLIENT_SECRET')
    base_url = 'https://mtc-webservices.herokuapp.com'
    print('Getting an access token..')
    resp = requests.post(f'{base_url}/api/auth/login',
                         json={'client_id': client_id, 'client_secret': client_secret})
    token = resp.json().get('access_token')
    print('Fetching data..')
    resp = requests.get(f'{base_url}/api/members/pids/{pid}',
                        headers={'Authorization': f'Bearer {token}'})
    if resp.status_code != 200:
        print(f'Error! {resp.status_code}')
    else:
        pprint(resp.json())


@app.cli.command('test-member-license-local-endpoint')
@click.argument('license_number')
def test_member_license_local_endpoint(license_number):
    import requests
    client_id = os.environ.get('CLIENT_ID')
    client_secret = os.environ.get('CLIENT_SECRET')
    base_url = 'http://127.0.0.1:5000'
    print('Getting an access token..')
    resp = requests.post(f'{base_url}/api/auth/login',
                         json={'client_id': client_id, 'client_secret': client_secret})
    token = resp.json().get('access_token')
    print('Fetching data..')
    resp = requests.get(f'{base_url}/api/members/licenses/{license_number}',
                        headers={'Authorization': f'Bearer {token}'})
    if resp.status_code != 200:
        print(f'Error! {resp.status_code}')
    else:
        pprint(resp.json())


@app.cli.command('test-member-license-endpoint')
@click.argument('license_number')
def test_member_license_endpoint(license_number):
    import requests
    client_id = os.environ.get('MTC_CLIENT_ID')
    client_secret = os.environ.get('MTC_CLIENT_SECRET')
    base_url = 'https://mtc-webservices.herokuapp.com'
    print('Getting an access token..')
    resp = requests.post(f'{base_url}/api/auth/login',
                         json={'client_id': client_id, 'client_secret': client_secret})
    token = resp.json().get('access_token')
    print('Fetching data..')
    resp = requests.get(f'{base_url}/api/members/licenses/{license_number}',
                        headers={'Authorization': f'Bearer {token}'})
    if resp.status_code != 200:
        print(f'Error! {resp.status_code}')
    else:
        pprint(resp.json())


@app.cli.command('test-member-info-endpoint')
@click.argument('pid')
def test_member_info_endpoint(pid):
    import requests
    client_id = os.environ.get('MTC_CLIENT_ID')
    client_secret = os.environ.get('MTC_CLIENT_SECRET')
    base_url = 'https://mtc-webservices.herokuapp.com'
    print('Getting an access token..')
    resp = requests.post(f'{base_url}/api/auth/login',
                         json={'client_id': client_id, 'client_secret': client_secret})
    token = resp.json().get('access_token')
    print('Fetching data..')
    resp = requests.get(f'{base_url}/api/members/{pid}/info',
                        headers={'Authorization': f'Bearer {token}'})
    if resp.status_code == 200:
        pprint(resp.json())
    else:
        print(f'Error! {resp.json()}')


@app.cli.command('test-member-info-local-endpoint')
@click.argument('pid')
def test_member_info_endpoint_local(pid):
    import requests
    base_url = 'http://127.0.0.1:5000'
    client_id = os.environ.get('CLIENT_ID')
    client_secret = os.environ.get('CLIENT_SECRET')
    print('Getting an access token..')
    resp = requests.post(f'{base_url}/api/auth/login',
                         json={'client_id': client_id,
                               'client_secret': client_secret})
    token = resp.json().get('access_token')
    print('Fetching data..')
    resp = requests.get(f'{base_url}/api/members/{pid}/info',
                        headers={'Authorization': f'Bearer {token}'})
    pprint(resp.text)


@app.cli.command('test-cmte-upcoming-events')
@click.argument('base_url')
def test_cmte_upcoming_events(base_url):
    import requests
    client_id = os.environ.get('MTC_CLIENT_ID')
    client_secret = os.environ.get('MTC_CLIENT_SECRET')
    print('Getting an access token..')
    resp = requests.post(f'{base_url}/api/auth/login',
                         json={'client_id': client_id,
                               'client_secret': client_secret})
    print(resp.status_code)
    token = resp.json().get('access_token')
    print(token)
    print('Fetching data..')
    resp = requests.get(f'{base_url}/api/cmte/upcoming-events',
                        headers={'Authorization': f'Bearer {token}'})
    if resp.status_code == 200:
        pprint(resp.json())
    else:
        print(resp.status_code, resp.text)
