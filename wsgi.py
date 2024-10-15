import os

from flask import session
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from flask_principal import identity_loaded, UserNeed, RoleNeed, ActionNeed
import arrow
from sqlalchemy import create_engine
import pandas as pd

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
admin.add_view(ModelView(CMTEEventSponsor, db.session, category='CMTE'))
admin.add_view(ModelView(CMTEEventFeeRate, db.session, category='CMTE'))
admin.add_view(ModelView(CMTEEventCode, db.session, category='CMTE'))
admin.add_view(ModelView(CMTEEventDoc, db.session, category='CMTE'))
admin.add_view(ModelView(CMTEEventParticipationRecord, db.session, category='CMTE'))

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

    return User.query.filter_by(id=user_id, is_activated=True).first()


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
    SELECT DISTINCT w_title AS title, w_bdate AS start_date,
    w_edate AS end_date, act_no AS activity_id, cpd_type_no AS type_id,
    train_id AS sponsor_id
    FROM cpd_work WHERE day(w_edate) > 0 AND day(w_bdate) > 0 AND month(w_edate) > 0
    AND month(w_bdate) > 0 AND month(w_edate) > 0 AND year(w_edate) > 0 AND year(w_bdate) > 0
    AND train_id > 0
    GROUP BY w_title, w_bdate, w_edate, train_id;
    '''
    df = pd.read_sql_query(query, con=src_engine)
    print(df.head())
    for idx, row in df.iterrows():
        event_type = CMTEEventType.query.filter_by(old_id=row['type_id']).first()
        activity = CMTEEventActivity.query.filter_by(old_id=row['activity_id']).first()
        sponsor = CMTEEventSponsor.query.filter_by(old_id=row['sponsor_id']).first()
        event = CMTEEvent.query.filter_by(title=row['title'],
                                          start_date=row['start_date'],
                                          end_date=row['end_date']).first()
        if not activity and not event_type:
            continue
        if not event:
            event = CMTEEvent(title=row['title'], event_type=event_type, activity=activity,
                              start_date=row['start_date'], end_date=row['end_date'])
            db.session.add(event)
            db.session.commit()
            print(f'{event.title} has been added!')
        else:
            print(f'{event.title} already exists!')
