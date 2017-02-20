import json
import logging
import subprocess
from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError
from django.forms.models import model_to_dict
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from kafka import KafkaProducer
import requests
from web.models import Team


logger = logging.getLogger(__name__)


@require_GET
def index(request):
    return render(
        request,
        'web/index.html',
        {
            'client_id': settings.SLACK_CLIENT_ID,
            'page_title': 'Home',
            'redirect_uri': settings.SLACK_REDIRECT_URI
        }
    )


@require_GET
def callback(request):
    if 'error' in request.GET:
        logger.error(request.GET['error'])
        return render(
            request,
            'web/error.html',
            {
                'error': 'something went wrong - please try again later',
                'page_title': 'Error'
            }
        )

    try:
        response = requests.get(
            'https://slack.com/api/oauth.access',
            {
                'client_id': settings.SLACK_CLIENT_ID,
                'client_secret': settings.SLACK_CLIENT_SECRET,
                'code': request.GET['code'],
                'redirect_uri': settings.SLACK_REDIRECT_URI
            }
        ).json()
    except KeyError:
        logger.error('missing `code` query param')
        return render(request, 'web/error.html', {'page_title': 'Error'})

    except requests.exceptions.RequestException as e:
        logger.error(e)
        return render(
            request,
            'web/error.html',
            {
                'error': 'something went wrong - please try again later',
                'page_title': 'Error'
            }
        )

    if 'error' in response:
        logger.error(response['error'])
        return render(
            request,
            'web/error.html',
            {
                'error': 'something went wrong - please try again later',
                'page_title': 'Error'
            }
        )

    team = Team(
        slack_id=response['team_id'],
        name=response['team_name'],
        token=response['bot']['bot_access_token']
    )

    try:
        team.save()
    except IntegrityError:
        return render(
            request,
            'web/error.html',
            {
                'error': '{} already has an active bot'.format(team.name),
                'page_title': 'Error'
            }
        )

    producer = KafkaProducer(
        bootstrap_servers=settings.KAFKA_URI,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    producer.send('registration', model_to_dict(team)).get(timeout=10)

    return render(
        request,
        'web/success.html',
        {
            'name': team.name,
            'page_title': 'Success'
        }
    )


@csrf_exempt
@require_POST
def feedback(request):
    if request.POST['token'] != settings.SLACK_VERIFICATION_TOKEN:
        logger.error('invalid token %s', request.POST['token'])
        return HttpResponseBadRequest('could not validate your request')

    send_mail(
        'feedback from {} on {}.slack.com #{} @{}'.format(
            request.POST['email'],
            request.POST['team_domain'],
            request.POST['channel_name'],
            request.POST['user_name']
        ),
        request.POST['message'],
        'webmaster@deepstate.actor',
        ['support@deepstate.actor'],
        fail_silently=False
    )
    logger.info('received feedback from %s', request.POST['email'])

    return HttpResponse(
        'thank you for your feedback - we will get back to you shortly.'
    )


@require_GET
def privacy(request):
    return render(request, 'web/privacy.html', {'page_title': 'Privacy'})


@require_GET
def support(request):
    return render(request, 'web/support.html', {'page_title': 'Support'})
