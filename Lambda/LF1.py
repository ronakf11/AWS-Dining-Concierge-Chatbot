import logging
import os
import dateutil.parser
import datetime
import time
import boto3

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def get_slots(intent_request):
    return intent_request['currentIntent']['slots']


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }


def build_validation_result(is_valid, violated_slot, message_content):
    if message_content is None:
        return {
            "isValid": is_valid,
            "violatedSlot": violated_slot,
        }

    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }


def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False


def isvalid_cuisine_type(cuisine):
    cuisine_type = ['italian', 'chinese','mexican', 'lebanese', 'japanese']
    return cuisine.lower() in cuisine_type


def isvalid_city(city):
    valid_cities = ['new york']
    return city.lower() in valid_cities

def validate_order_restaurants(location, cuisine, date, time, phone_number, no_of_people):

    if location and not isvalid_city(location):
        return build_validation_result(False,
                                       'Location',
                                       'We currently do not support {} as a valid destination. '  
                                       'Try searching for New York?'.format(location))

    if cuisine and not isvalid_cuisine_type(cuisine):
        return build_validation_result(
            False,
            'Cuisine',
            'I did not recognize that cuisine.  What type of cuisine would you like to order?  '
            'Popular cuisines are chinese, lebanese, japanese, italian or mexican')

    if date:
        if not isvalid_date(date):
            return build_validation_result(False, 'Date', 'I did not understand that, what date would you like '
                                                          'to book a reservation? '
                                                          'Please enter date in the format MM-DD-YYYY (with hyphens)')
        elif datetime.datetime.strptime(date, '%Y-%m-%d').date() < datetime.date.today():
            return build_validation_result(False, 'Date',
                                           'You can book restaurants from today onwards.'
                                           'Can you try a different date?')
    
    if time:
        if datetime.datetime.strptime(date, '%Y-%m-%d').date() == datetime.date.today():
            current_time = datetime.datetime.now().time().strftime("%H")
            input_time = str(time)[:2]
            if int(input_time) <= int(str(current_time)):
                return build_validation_result(False, 'time',
                                           'Time you entered has already passed. '
                                           'Please try a different time?')
                                           
    if phone_number is not None:
        phone_number = str(phone_number)
        if not phone_number[0:2] == "+1":
            return build_validation_result(False, 'Phone_Number', 'The phone number entered does not have the country '
                                                                  'code or is not a US phone number.'
                                                                  'Please enter a US number starting with +1')
        phone_number = phone_number[2:]
        if not int(phone_number) or len(phone_number) != 10:
            if not phone_number[0:1] == "+1":
                return build_validation_result(False, 'Phone_Number',
                                               'The phone number entered is not a valid phone number '
                                               'Please enter a valid number starting with +1')

    if no_of_people and int(no_of_people) > 20:
        return build_validation_result(False, 'No_of_people',
                                           'The number of people cannot be more than 20. '
                                           'Please enter a valid number of people')

    return build_validation_result(True, None, None)


def dining_suggestions(intent_request):
    location = get_slots(intent_request)["Location"]
    cuisine = get_slots(intent_request)["Cuisine"]
    date = get_slots(intent_request)["Date"]
    time = get_slots(intent_request)["time"]
    phone_number = get_slots(intent_request)["Phone_Number"]
    no_of_people = get_slots(intent_request)["No_of_people"]
    source = intent_request['invocationSource']

    if source == 'DialogCodeHook':
        # Perform basic validation on the supplied input slots.
        # Use the elicitSlot dialog action to re-prompt for the first violation detected.
        slots = get_slots(intent_request)

        validation_result = validate_order_restaurants(location, cuisine, date, time, phone_number,
                                                       no_of_people)
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(intent_request['sessionAttributes'],
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])


        output_session_attributes = intent_request['sessionAttributes'] if intent_request[
                                                                               'sessionAttributes'] is not None else {}

        return delegate(output_session_attributes, get_slots(intent_request))


    sqs = boto3.resource('sqs', 'us-west-2')

    queue = sqs.get_queue_by_name(QueueName='ChatBotHw1')
    test_body = {
       "Date": str(date),
       "Cuisine": str(cuisine),
       "Location": str(location),
       "No_of_people": str(no_of_people),
       "Phone_Number": str(phone_number),
       "time": str(time)
    }

    response = queue.send_message(MessageBody=str(test_body))

    return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'Thanks, your order for restaurants in {} has been recorded '
                             'We will notify you details via a message on {}'.format(location, phone_number)})


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    logger.debug(
        'dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'DiningSuggestionsIntent':
        return dining_suggestions(intent_request)
    # raise Exception('Intent with name ' + intent_name + ' not supported')


def lambda_handler(event, context):
    #     # TODO implement
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))

    return dispatch(event)