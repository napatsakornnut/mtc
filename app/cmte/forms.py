from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms.validators import NumberRange, EqualTo, Email, Optional
from wtforms.widgets import ListWidget, CheckboxInput
from wtforms_alchemy import model_form_factory, QuerySelectField, QuerySelectMultipleField
from wtforms import FieldList, FormField, StringField, DecimalField, TextAreaField, PasswordField, SelectField
from wtforms_components import DateField, DateTimeField, TimeField

from app.cmte.models import *

BaseModelForm = model_form_factory(FlaskForm)


class ModelForm(BaseModelForm):
    @classmethod
    def get_session(self):
        return db.session


class CMTEEventDocForm(ModelForm):
    class Meta:
        model = CMTEEventDoc
        only = ['note']

    upload_file = FileField('Document Upload')
    note = TextAreaField('คำอธิบาย', render_kw={'class': 'textarea'})


class CMTEEventForm(ModelForm):
    class Meta:
        model = CMTEEvent
        datetime_format = '%d/%m/%Y %H:%M'

    event_type = QuerySelectField('ชนิดกิจกรรม', query_factory=lambda: CMTEEventType.query.all())
    upload_files = FieldList(FormField(CMTEEventDocForm, default=CMTEEventDoc), min_entries=3)


class CMTEAdminEventForm(ModelForm):
    class Meta:
        model = CMTEEvent
        datetime_format = '%d/%m/%Y %H:%M'
        date_format = '%d/%m/%Y'

    event_type = QuerySelectField('ประเภทกิจกรรม', query_factory=lambda: CMTEEventType.query.all())
    upload_files = FieldList(FormField(CMTEEventDocForm, default=CMTEEventDoc), min_entries=3)
    sponsor = QuerySelectField('สถาบันฝึกอบรม', query_factory=lambda: CMTEEventSponsor.query.all())
    activity = QuerySelectField('ชนิดกิจกรรม', query_factory=lambda: CMTEEventActivity.query.all())


class ParticipantForm(FlaskForm):
    license_number = StringField('License Number')
    score = DecimalField('Score', validators=[NumberRange(min=0)])
    approved_date = DateField('Approved Date', validators=[Optional()])


class IndividualScoreForm(ModelForm):
    class Meta:
        model = CMTEEventParticipationRecord
        only = ['start_date', 'end_date', 'desc']
        date_format = '%d/%m/%Y'
    upload_files = FieldList(FormField(CMTEEventDocForm, default=CMTEEventDoc), min_entries=5)


class IndividualScoreAdminForm(ModelForm):
    class Meta:
        model = CMTEEventParticipationRecord
        only = ['start_date', 'end_date', 'desc', 'score', 'reason']
        date_format = '%d/%m/%Y'
    upload_files = FieldList(FormField(CMTEEventDocForm, default=CMTEEventDoc), min_entries=5)
    activity = QuerySelectField('ชนิดกิจกรรม',
                                query_factory=lambda: CMTEEventActivity.query.all(),
                                allow_blank=True,
                                blank_text='กรุณาเลือกชนิดกิจกรรม')


class CMTEEventCodeForm(FlaskForm):
    code = QuerySelectField('Code', query_factory=lambda: CMTEEventCode.query.all(),
                            allow_blank=True, blank_text='เลือกรหัสกิจกรรม')


class CMTEFeePaymentForm(ModelForm):
    class Meta:
        model = CMTEFeePaymentRecord
        datetime_format = '%d/%m/%Y %H:%M'
        only = ['payment_datetime', 'license_number']

    license_number = StringField('License Number')


class MemberCMTEFeePaymentForm(ModelForm):
    class Meta:
        model = CMTEFeePaymentRecord
        exclude = ['start_date', 'end_date']

    payment_datetime = DateTimeField('ชำระเมือ', format='%d/%m/%Y %H:%M')
    doc = FormField(CMTEEventDocForm, default=CMTEEventDocForm)


class CMTESponsorMemberForm(ModelForm):
    class Meta:
        model = CMTESponsorMember

    password = PasswordField('รหัสผ่าน', validators=[DataRequired(), EqualTo('confirm_password', message='รหัสผ่านต้องตรงกัน')])
    confirm_password = PasswordField('ยืนยันรหัสผ่าน', validators=[DataRequired()])


class CMTESponsorMemberEditForm(ModelForm):
    class Meta:
        model = CMTESponsorMember


class CMTESponsorRequestForm(FlaskForm):
    comment = TextAreaField('เหตุผล')


class CMTESponsorMemberChangePasswordForm(FlaskForm):
    password = PasswordField('รหัสผ่าน',
                             validators=[DataRequired(), EqualTo('confirm_password', message='รหัสผ่านต้องตรงกัน')])
    confirm_password = PasswordField('ยืนยันรหัสผ่าน', validators=[DataRequired()])



class CMTESponsorMemberLoginForm(ModelForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('รหัสผ่าน', validators=[DataRequired()])


class CMTESponsorDocForm(ModelForm):
    class Meta:
        model = CMTESponsorDoc
        only = ['note']

    upload_file = FileField('Document Upload')
    note = TextAreaField('คำอธิบาย', render_kw={'class': 'textarea'})


class CMTEEventSponsorForm(ModelForm):
    class Meta:
        model = CMTEEventSponsor

    registered_date = DateField()
    qualifications = QuerySelectMultipleField('หลักฐานแสดงคุณสมบัติขององค์กร',
                                              query_factory=lambda:CMTESponsorQualification.query.all(),
                                              widget=ListWidget(prefix_label=False),
                                              option_widget=CheckboxInput())
    #upload_files = FieldList(FormField(CMTESponsorDocForm, default=CMTESponsorDoc), min_entries=3)
    private_sector = SelectField(choices=['','องค์กรรัฐ', 'องค์กรเอกชน'])


class CMTESponsorEditForm(ModelForm):
    class Meta:
        model = CMTETempSponsor

    qualifications = QuerySelectMultipleField('หลักฐานแสดงคุณสมบัติขององค์กร',
                                              query_factory=lambda:CMTESponsorQualification.query.all(),
                                              widget=ListWidget(prefix_label=False),
                                              option_widget=CheckboxInput())
    upload_files = FieldList(FormField(CMTESponsorDocForm, default=CMTESponsorDoc), min_entries=3)
    private_sector = SelectField(choices=['องค์กรรัฐ','องค์กรเอกชน'])


class CMTESponsorPaymentForm(FlaskForm):
    class Meta:
        model = CMTEEventSponsor

    name = TextAreaField('name', render_kw={'class': 'textarea'})
    receipt_item = TextAreaField('receipt_item', render_kw={'class': 'textarea'})
    tax_id = TextAreaField('tax_id', render_kw={'class': 'textarea'})
    address = TextAreaField('address', render_kw={'class': 'textarea'})
    zipcode = TextAreaField('zipcode', render_kw={'class': 'text'})
    paid_date = DateField()
    paid_time = TimeField()
    upload_file = FormField(CMTESponsorDocForm, default=CMTESponsorDoc)


class CMTESponsorReceiptDocForm(ModelForm):
    class Meta:
        model = CMTEReceiptDoc
        only = ['note']

    upload_file = FileField('Document Upload')
    note = TextAreaField('คำอธิบาย', render_kw={'class': 'textarea'})


class CMTESponsorReceiptForm(FlaskForm):
    upload_file = FormField(CMTESponsorReceiptDocForm, default=CMTEReceiptDoc)


class CMTEPaymentForm(FlaskForm):
    upload_file = FormField(CMTEEventDocForm, default=CMTEEventDoc)


class CMTEParticipantFileUploadForm(FlaskForm):
    upload_file = FileField('Participants')
