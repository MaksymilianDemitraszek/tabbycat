from smtplib import SMTPException

from channels.consumer import SyncConsumer
from django.conf import settings
from django.core import mail
from django.template import Context, Template
from django.utils.html import strip_spaces_between_tags, strip_tags
from django.utils.translation import gettext_lazy as _

from draw.models import Debate
from tournaments.models import Round, Tournament

from .models import SentMessageRecord
from .utils import (adjudicator_assignment_email_generator, ballots_email_generator,
                    motion_release_email_generator, randomized_url_email_generator,
                    standings_email_generator, team_speaker_email_generator)


class NotificationQueueConsumer(SyncConsumer):

    NOTIFICATION_GENERATORS = {
        SentMessageRecord.EVENT_TYPE_DRAW: adjudicator_assignment_email_generator,
        SentMessageRecord.EVENT_TYPE_URL: randomized_url_email_generator,
        SentMessageRecord.EVENT_TYPE_BALLOT_CONFIRMED: ballots_email_generator,
        SentMessageRecord.EVENT_TYPE_POINTS: standings_email_generator,
        SentMessageRecord.EVENT_TYPE_MOTIONS: motion_release_email_generator,
        SentMessageRecord.EVENT_TYPE_TEAM: team_speaker_email_generator
    }

    def _send(self, event, messages, records):
        try:
            mail.get_connection().send_messages(messages)
        except SMTPException as e:
            self.send_error(e, _("Failed to send e-mails."), event)
            raise
        except ConnectionError as e:
            self.send_error(e, _("Connection error sending e-mails."), event)
            raise
        else:
            SentMessageRecord.objects.bulk_create(records)

    def _get_from_fields(self, t):
        from_email = "%s <%s>" % (t.short_name, settings.DEFAULT_FROM_EMAIL)
        reply_to = None
        if t.pref('reply_to_address'):
            reply_to = "%s <%s>" % (t.pref('reply_to_name'), t.pref('reply_to_address'))

        # Django wants the reply_to as an array
        return from_email, [reply_to]

    def _get_plain_text(self, html):
        """Strip tags and add spaces for paragraphs"""
        return strip_tags(strip_spaces_between_tags(html).replace("</p>","\n\n</p>"))

    def email(self, event):
        # Get database objects
        if 'debate_id' in event['extra']:
            round = Debate.objects.get(pk=event['extra']['debate_id']).round
            t = round.tournament
        elif 'round_id' in event['extra']:
            round = Round.objects.get(pk=event['extra']['round_id'])
            t = round.tournament
        else:
            round = None
            t = Tournament.objects.get(pk=event['extra']['tournament_id'])

        from_email, reply_to = self._get_from_fields(t)
        notification_type = event['message']

        subject = Template(event['subject'])
        html_body = Template(event['body'])
        plain_body = Template(self._get_plain_text(event['body']))

        data = self.NOTIFICATION_GENERATORS[notification_type](to=event['send_to'], **event['extra'])

        # Prepare messages
        messages = []
        records = []
        for instance, recipient in data:
            context = Context(instance)
            email = mail.EmailMultiAlternatives(
                subject=subject.render(context), body=plain_body.render(context),
                from_email=from_email, to=[recipient.email], reply_to=reply_to
            )
            email.attach_alternative(html_body.render(context), "text/html")
            messages.append(email)

            records.append(
                SentMessageRecord(recipient=recipient, email=recipient.email,
                                  event=notification_type,
                                  method=SentMessageRecord.METHOD_TYPE_EMAIL,
                                  round=round, tournament=t,
                                  context=instance, message=email.message())
            )

        self._send(event, messages, records)

    def email_custom(self, event):
        messages = []
        records = []

        t = Tournament.objects.get(id=event['tournament'])
        from_email, reply_to = self._get_from_fields(t)

        for pk, address in event['send_to']:
            email = mail.EmailMultiAlternatives(
                subject=event['subject'], body=self._get_plain_text(event['body']),
                from_email=from_email, to=[address], reply_to=reply_to
            )
            email.attach_alternative(event['body'], "text/html")
            messages.append(email)

            records.append(
                SentMessageRecord(
                    recipient_id=pk, email=address,
                    method=SentMessageRecord.METHOD_TYPE_EMAIL,
                    tournament=t, message=email.message())
            )

        self._send(event, messages, records)
